"""Narrow Frida adapter for an explicit CapCut PID and verified project identity."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.native-tools'))
from capcut_cli_worker import PINS


def saved_matching(req, summary):
    expected = {sid for row in summary if row['type'] == 'track' for sid in row['attributes']['segments']}
    path = Path(req['project']) / 'Timelines' / req['timeline_id'] / 'draft_content.json'
    deadline = time.monotonic() + 8
    while True:
        try:
            doc = json.loads(path.read_text(encoding='utf-8-sig'))
            segments = {s['id']: s for t in doc['tracks'] for s in t['segments']}
            actual = set(segments)
            # IDs alone cannot verify a trim/move: wait for saved timing too.
            timing_matches = all(
                row['id'] in segments and all(abs(segments[row['id']]['target_timerange'][key] - row['timeline'][key + '.ms'] * 1000) < 1000
                    for key in ('start', 'duration'))
                for row in summary if 'timeline' in row)
            # In this pinned build full-scope video attributes are in us despite
            # their '.ms' labels (confirmed against saved source ranges).
            source_matches = all(
                segments[row['id']]['source_timerange'][key] == row['attributes'][key + '.ms']
                for row in summary if row.get('type') == 'video' and row.get('attributes', {}).get('meta_type') == 'video'
                and row['id'] in segments and segments[row['id']].get('source_timerange')
                for key in ('start', 'duration'))
            if doc['id'] == req['timeline_id'] and actual == expected and timing_matches and source_matches:
                return doc
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise ValueError('Saved draft and native state did not converge; edit outcome may be unknown')
        time.sleep(.2)


def execute(req):
    import frida
    base = Path(req['capcut_dir']).resolve()
    pins = PINS
    if req['action'] in ('switch-timeline', 'export', 'preview'):
        from capcut_store_worker import STORE_PINS
        pins = STORE_PINS
    for name, expected in pins.items():
        with (base / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError('Unsupported CapCut build: ' + name)
    lock = ROOT / '.runtime' / f'editor-{req["pid"]}.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError(f'Another editor operation owns {lock}; inspect it before removing a stale lock')
    session = None
    keep_lock = False
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps({'workerPid': os.getpid(), 'capcutPid': req['pid'], 'created': time.time()}))
        session = frida.attach(req['pid'])
        script = session.create_script((ROOT / 'capcut_editor_agent.js').read_text(encoding='utf8'))
        script.on('message', lambda msg, data: print(json.dumps(msg), file=sys.stderr, flush=True))
        script.load()
        identity = script.exports_sync.identity()
        if Path(identity['executable']).resolve() != base / 'CapCut.exe':
            raise ValueError('Selected PID is not the expected CapCut executable')
        if any(Path(p).resolve() != base / Path(p).name for p in identity['modules']):
            raise ValueError('Loaded module path mismatch')
        inventory = script.exports_sync.inventory()
        if req['action'] == 'sessions':
            return inventory
        if req['action'] == 'switch-timeline':
            return switch_timeline(req, script, session, pins)
        if req['action'] == 'inspect':
            result = script.exports_sync.run(req)
            saved = saved_matching(req, result['summary'])
            from capcut_state import items_from_doc
            result['clips'] = clip_rows(saved)
            result['items'] = items_from_doc(saved)
            result['itemsReadback'] = 'CapCut-autosaved state, native IDs/timing cross-checked'
            return result
        if req['action'] in ('add-audio','captions-import','set-clip'):
            from capcut_extensions import execute_extension
            return execute_extension(req,script,saved_matching)
        if req['action'] == 'frame':
            from capcut_preview import verify_frame_and_publish
            from capcut_export import export_content_signature
            before = script.exports_sync.run({**req, 'action': 'inspect'})
            saved_before = saved_matching(req, before['summary'])
            if saved_before.get('duration') != req['duration_us']:
                raise ValueError('Timeline duration changed before frame extraction')
            directory, output = Path(req['frame_directory']).resolve(), Path(req['output']).resolve()
            if output.exists() or not directory.is_dir() or list(directory.iterdir()) or directory.parent != output.parent or not directory.name.startswith('.capcut-frame-'):
                raise ValueError('Frame staging directory is not private/empty or output already exists')
            result = script.exports_sync.run(req)
            saved_after = saved_matching(req, result['summary'])
            if export_content_signature(saved_after) != export_content_signature(saved_before):
                raise ValueError('Timeline changed during native frame extraction; frame was not published')
            result.update(verify_frame_and_publish(req, result['native']), timelineUnchanged=True, clips=clip_rows(saved_after))
            return result
        if req['action'] in ('export', 'preview'):
            from capcut_export import verify_and_publish, render_frontend, export_content_signature
            before = script.exports_sync.run({**req, 'action': 'inspect'})
            saved_before = saved_matching(req, before['summary'])
            if saved_before.get('duration') != req.get('timeline_duration_us', req['duration_us']):
                raise ValueError('Timeline duration changed while preparing export')
            stage, output = Path(req['stage_output']), Path(req['output'])
            if output.exists() or stage.exists():
                raise ValueError('Export output or private staging file already exists')
            if (stage.parent.parent.resolve() != output.parent.resolve()
                    or not stage.parent.name.startswith('.capcut-export-') or not stage.parent.is_dir()):
                raise ValueError('Unexpected export staging directory')
            if req['action'] == 'preview':
                from capcut_preview import render_preview
                native = render_preview(req, session, saved_before, before['sid'], pins)
            else:
                native = render_frontend({**req, 'verifiedHashes': pins, 'expected_editor_sid': before['sid']}, session)
            result = script.exports_sync.run({**req, 'action': 'inspect'})
            result['native'] = native
            print(json.dumps({'exportNativeResult': native}), file=sys.stderr, flush=True)
            after = saved_matching(req, result['summary'])
            if export_content_signature(after) != export_content_signature(saved_before):
                for name,doc in (('render-state-before.json',saved_before),('render-state-after.json',after)):
                    (Path.cwd()/name).write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
                raise ValueError('Timeline content changed during export; staged output was not published')
            result.update(verify_and_publish(req), clips=clip_rows(after), timelineUnchanged=True)
            if req['action'] == 'preview':
                result.update(requestedStartUs=req['start_us'], requestedEndUs=req['end_us'], exportRangeRestored=True,
                              wholeTimelineExportUsed=False, renderer='CapCut native export range / ExportClient')
            return result
        if req['action'] == 'add-timeline':
            result = script.exports_sync.run(req)
            print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
            new_id = result['timelineId']
            if new_id.lower() == req['timeline_id'].lower():
                raise ValueError('Native timeline creation reused the source ID')
            deadline = time.monotonic() + 10
            while True:
                try:
                    project = json.loads((Path(req['project']) / 'Timelines/project.json').read_text(encoding='utf-8-sig'))
                    content = json.loads((Path(req['project']) / 'Timelines' / new_id / 'draft_content.json').read_text(encoding='utf-8-sig'))
                    entry = next(t for t in project['timelines'] if t['id'] == new_id and not t.get('is_marked_delete'))
                    if (content['id'] == new_id and entry['name'] == req['timeline_name'] and content['tracks'] == []
                            and content.get('render_index_track_mode_on', False) == req['render_index_track_mode_on']):
                        result.update(verified='native-response-and-independent-autosaved-draft', persistenceVerified=True,
                                      path=str(Path(req['project']) / 'Timelines' / new_id),
                                      name=entry['name'], focusChanged=False)
                        return result
                except (OSError, ValueError, KeyError, StopIteration):
                    pass
                if time.monotonic() >= deadline:
                    raise ValueError('Native timeline returned, but independent saved draft was not verified; do not blindly retry')
                time.sleep(.2)
        if req['action'] in ('undo', 'redo'):
            result = script.exports_sync.run(req)
            print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
            saved_matching(req, result['summary'])
            result['verified'] = 'native-summary-and-autosaved-draft'
            return result
        if req['action'] in ('trim', 'split', 'move', 'remove'):
            print('clip-edit-inspect-enter', file=sys.stderr, flush=True)
            before = script.exports_sync.run({**req, 'action': 'inspect'})
            print('clip-edit-inspect-return', file=sys.stderr, flush=True)
            saved_before = saved_matching(req, before['summary'])
            previous = validate_clip_edit(req, saved_before)
            # CapCut's raw segment selector is case-sensitive even for UUIDs.
            req['segment_id'] = previous['id']
            req['expected_target_us'] = previous['target_timerange']
            req['expected_source_us'] = previous.get('source_timerange')
            print('clip-edit-run-enter', file=sys.stderr, flush=True)
            result = script.exports_sync.run(req)
            print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
            saved_after = saved_matching(req, result['summary'])
            verify_clip_edit(req, previous, saved_before, saved_after)
            result.update(clips=clip_rows(saved_after), persistenceVerified=True,
                          verified='native-timing-and-autosaved-draft',
                          previousClip={'id': previous['id'], 'targetUs': previous['target_timerange'],
                                        'sourceUs': previous['source_timerange']})
            return result
        if req['action'] != 'add-video':
            raise ValueError('Unsupported editor action')
        before = script.exports_sync.run({**req, 'action': 'inspect'})
        saved_before = saved_matching(req, before['summary'])
        layers = {s['render_index'] for t in saved_before['tracks'] if t['type'] == 'video' for s in t['segments']}
        if not saved_before.get('render_index_track_mode_on'):
            raise ValueError('Only the verified render-index track mode is supported for editor writes')
        if req['new_track']:
            req['track'] = max(layers, default=-1) + 1
            req['video_arguments'] += list(f' --render-index {req["track"]}'.encode('ascii'))
        elif req['track'] < 0 or req['track'] > max(layers, default=-1) + 1:
            raise ValueError('Track/layer must exist or be the next consecutive index')
        result = script.exports_sync.run(req)
        print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
        saved_after = saved_matching(req, result['summary'])
        ids = set(result['native']['segment_ids'])
        clips = []
        for track_index, track in enumerate(saved_after['tracks']):
            for segment in track['segments']:
                if segment['id'] in ids:
                    clips.append({'id': segment['id'], 'storedTrackIndex': track_index,
                                  'renderIndex': segment['render_index'],
                                  'targetUs': segment['target_timerange'], 'sourceUs': segment['source_timerange']})
        if req['new_track'] and not all(c['renderIndex'] == req['track'] and c['renderIndex'] not in layers for c in clips):
            raise ValueError('Clip was added, but requested new render layer was not confirmed; do not blindly retry')
        result.update(addedRenderLayer=any(c['renderIndex'] not in layers for c in clips), clips=clips,
                      verified='native-summary-and-autosaved-draft',
                      trackSemantics='Visual layers use renderIndex; multiple layers can share one stored track')
        return result
    except Exception as error:
        keep_lock = bool(getattr(error, 'preserve_pid_lock', False))
        raise
    finally:
        if session is not None:
            try:
                session.detach()
            except Exception as cleanup:
                print(json.dumps({'cleanupWarning': 'editor session detach', 'error': str(cleanup)}), file=sys.stderr, flush=True)
        if not keep_lock:
            lock.unlink(missing_ok=True)


def switch_timeline(req, editor, session, pins):
    project = Path(req['project'])
    meta = json.loads((project / 'draft_meta_info.json').read_text(encoding='utf-8-sig'))
    index = json.loads((project / 'Timelines/project.json').read_text(encoding='utf-8-sig'))
    target_before = json.loads((project / 'Timelines' / req['timeline_id'] / 'draft_content.json').read_text(encoding='utf-8-sig'))
    if target_before['id'] != req['timeline_id']:
        raise ValueError('Saved target timeline identity changed')
    target_signature = timeline_signature(target_before)
    editors = [s for s in editor.exports_sync.inventory()['sessions'] if s['ready']]
    if len(editors) != 1:
        raise ValueError('Exactly one ready editor session is required')
    native_req = {'pid': req['pid'], 'verifiedHashes': pins,
                  'expectedProjectId': meta['draft_id'], 'expectedProjectPath': str(project),
                  'expectedActiveDraftUUID': index['main_timeline_id'], 'expectedSid': editors[0]['sid'],
                  'expectedMainTimelineId': index['main_timeline_id'],
                  'targetDraftUUID': req['timeline_id']}
    bridge = session.create_script((ROOT / 'capcut_timeline_agent.js').read_text(encoding='utf8'))
    bridge.on('message', lambda msg, data: print(json.dumps(msg), file=sys.stderr, flush=True))
    bridge.load()
    deadline = time.monotonic() + 15
    while True:
        initial = bridge.exports_sync.activereadiness(native_req)
        if initial.get('ready'):
            break
        if time.monotonic() >= deadline:
            raise ValueError('Current timeline is still initializing; no draft extraction or switch attempted')
        time.sleep(.15)
    active_id = initial['activeDraftUUID']
    if not any(t['id'] == active_id and not t.get('is_marked_delete') for t in index['timelines']):
        raise ValueError('Active timeline does not belong to requested project')
    native_req['expectedActiveDraftUUID'] = active_id
    live = editor.exports_sync.active()
    if next(r['id'] for r in live['summary'] if r['type'] == 'draft') != active_id:
        raise ValueError('Active timeline changed after frontend readiness check')
    saved_matching({**req, 'timeline_id': active_id}, live['summary'])
    checked = bridge.exports_sync.inspect(native_req)
    print(json.dumps({'nativeTimelineModel': checked}), file=sys.stderr, flush=True)
    result = bridge.exports_sync.switchtimeline(native_req)
    print(json.dumps({'nativeTimelineSwitchReturned': result}), file=sys.stderr, flush=True)
    # switchToTimeline updates its requested UUID before asynchronous focus/load
    # finishes. Do not ask the native editing engine to extract a draft until
    # the frontend's actual active model and playback dependency confirm it.
    focused_req = {**native_req, 'expectedActiveDraftUUID': req['timeline_id']}
    deadline = time.monotonic() + 15
    while True:
        if session.is_detached:
            raise ValueError('CapCut session ended during timeline initialization; inspect logs before retrying')
        readiness = bridge.exports_sync.readiness(focused_req)
        print(json.dumps({'timelineFrontendReadiness': readiness}), file=sys.stderr, flush=True)
        if readiness.get('ready'):
            result['frontendInitializationVerified'] = True
            break
        if time.monotonic() >= deadline:
            raise ValueError('Timeline was requested but frontend initialization did not finish; native draft extraction was not attempted')
        time.sleep(.15)
    deadline = time.monotonic() + 10
    while True:
        try:
            actual = editor.exports_sync.run({**req, 'action': 'inspect'})
            doc = saved_matching(req, actual['summary'])
            if timeline_signature(doc) != target_signature:
                raise ValueError('Target timeline contents changed while switching; inspect state before further editing')
            result.update(timelineId=req['timeline_id'], summary=actual['summary'], clips=clip_rows(doc),
                          verified='frontend-model-live-editor-and-saved-draft', persistenceVerified=True)
            return result
        except Exception as error:
            print(json.dumps({'timelineVerifyError': str(error)}), file=sys.stderr, flush=True)
            if session.is_detached:
                raise ValueError('CapCut session ended before timeline switch verification; inspect logs before retrying') from error
            if time.monotonic() > deadline:
                raise ValueError('Timeline switch not verified; inspect before retrying: ' + str(error))
            time.sleep(.2)


def timeline_signature(doc):
    """Stable clip/source identity; switching must not change timeline contents."""
    materials = {m['id']: m for group in doc.get('materials', {}).values() if isinstance(group, list)
                 for m in group if isinstance(m, dict) and 'id' in m}
    return {s['id']: {'trackId': t['id'], 'trackType': t['type'],
                      'renderIndex': s.get('render_index'), 'materialId': s.get('material_id'),
                      'source': {k: materials.get(s.get('material_id'), {}).get(k)
                                 for k in ('path', 'width', 'height', 'duration')},
                      'targetUs': s.get('target_timerange'), 'sourceUs': s.get('source_timerange'),
                      'speed': s.get('speed')}
            for t in doc['tracks'] for s in t['segments']}


def clip_rows(doc):
    return [{'id': s['id'], 'storedTrackIndex': ti, 'renderIndex': s['render_index'],
             'targetUs': s['target_timerange'], 'sourceUs': s.get('source_timerange'),
             'materialId': s['material_id']}
            for ti, t in enumerate(doc['tracks']) if t['type'] == 'video' for s in t['segments']]


def validate_clip_edit(req, doc):
    clips = [s for t in doc['tracks'] if t['type'] == 'video' for s in t['segments']
             if s['id'].upper() == req['segment_id'].upper()]
    if len(clips) != 1:
        raise ValueError('Requested video segment is not in the active timeline')
    clip = clips[0]
    target, source = clip['target_timerange'], clip.get('source_timerange')
    start, duration = target['start'], target['duration']
    frame_us = 1000000 / doc.get('fps', 30)
    if req['action'] in ('trim', 'split'):
        if not source or clip.get('speed', 1) != 1 or source['duration'] != duration:
            raise ValueError('Trim/split currently require an ordinary video clip at speed 1')
    if req['action'] == 'trim':
        if not start <= req['in_us'] < req['out_us'] <= start + duration or req['out_us'] - req['in_us'] < frame_us:
            raise ValueError('Trim must retain at least one frame within the current clip; positions are absolute on the timeline')
    if req['action'] == 'split':
        boundaries = [0, *req['points_us'], duration]
        if any(b - a < frame_us for a, b in zip(boundaries, boundaries[1:])):
            raise ValueError('Split points must lie inside the clip, leaving at least one frame in each part')
    if req['action'] == 'move' and req['start_us'] + duration > 2**53 - 1:
        raise ValueError('Moved clip exceeds the supported timestamp range')
    if (req['action'] == 'move' and req['start_us'] != start and clip.get('render_index') == 0
            and doc.get('config', {}).get('maintrack_adsorb')):
        raise ValueError('Main-track magnetism prevents free positioning; move a clip on an added video layer instead')
    return clip


def verify_clip_edit(req, previous, before, after):
    all_before = {s['id']: s for t in before['tracks'] for s in t['segments']}
    all_after = {s['id']: s for t in after['tracks'] for s in t['segments']}
    sid = previous['id']
    frame_us = 1000000 / after.get('fps', 30)
    close = lambda a, b: abs(a - b) <= frame_us
    action = req['action']
    if action == 'remove':
        valid = set(all_after) == set(all_before) - {sid}
    elif action == 'split':
        pieces = [s for key, s in all_after.items() if key == sid or key not in all_before]
        pieces.sort(key=lambda s: s['target_timerange']['start'])
        videos = {v['id']: v for v in after['materials']['videos']}
        source_video = next(v for v in before['materials']['videos'] if v['id'] == previous['material_id'])
        valid = (set(all_before).issubset(all_after) and len(pieces) == len(req['points_us']) + 1
                 and all(all(videos[s['material_id']].get(k) == source_video.get(k)
                             for k in ('path', 'width', 'height', 'duration')) for s in pieces)
                 and sum(s['target_timerange']['duration'] for s in pieces) == previous['target_timerange']['duration']
                 and sum(s['source_timerange']['duration'] for s in pieces) == previous['source_timerange']['duration'])
        boundaries = [0, *req['points_us'], previous['target_timerange']['duration']]
        valid = valid and all(close(s['target_timerange']['start'], previous['target_timerange']['start'] + offset)
                              and close(s['source_timerange']['start'], previous['source_timerange']['start'] + offset)
                              for s, offset in zip(pieces, boundaries))
    else:
        clip = all_after.get(sid)
        valid = set(all_after) == set(all_before) and clip is not None
        if valid and action == 'move':
            valid = (close(clip['target_timerange']['start'], req['start_us'])
                     and clip['source_timerange'] == previous['source_timerange']
                     and clip['target_timerange']['duration'] == previous['target_timerange']['duration'])
        elif valid:
            source_start = previous['source_timerange']['start'] + req['in_us'] - previous['target_timerange']['start']
            valid = ((close(clip['target_timerange']['start'], req['in_us'])
                      or close(clip['target_timerange']['start'], previous['target_timerange']['start']))
                     and close(clip['target_timerange']['duration'], req['out_us'] - req['in_us'])
                     and close(clip['source_timerange']['start'], source_start)
                     and clip['source_timerange']['duration'] == clip['target_timerange']['duration'])
    if not valid:
        raise ValueError('Native edit returned but requested timing/clip result was not verified; inspect state before retrying')


if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    try:
        result = execute(json.loads(source.read_text(encoding='utf8')))
        report = {'exitCode': 0, 'stdout': json.dumps({'err_code': 0, 'result': result}), 'stderr': ''}
    except Exception as error:
        report = {'workerError': str(error)}
        if hasattr(error,'details'):report['mutationDetails']=error.details
    output.write_text(json.dumps(report, ensure_ascii=False), encoding='utf8')
