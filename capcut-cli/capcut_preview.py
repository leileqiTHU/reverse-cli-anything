"""Validated native timeline frame output; no whole-timeline render fallback."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent


def render_preview(req, session, saved_before, sid, hashes):
    """Temporarily use CapCut's export-range API, then restore the native config."""
    from capcut_export import render_frontend, ExportCancellationUnconfirmed, cleanup_without_masking
    project = Path(req['project'])
    index = json.loads((project / 'Timelines/project.json').read_text(encoding='utf-8-sig'))
    context = {'pid': req['pid'], 'verifiedHashes': hashes, 'expectedSid': sid,
               'expectedProjectId': req['project_id'], 'expectedProjectPath': str(project),
               'expectedActiveDraftUUID': req['timeline_id'], 'targetDraftUUID': req['timeline_id'],
               'expectedMainTimelineId': index['main_timeline_id']}
    source = (ROOT / 'capcut_timeline_agent.js').read_text(encoding='utf8') + '\n' + (ROOT / 'capcut_preview_range_agent.js').read_text(encoding='utf8')
    bridge = session.create_script(source)
    bridge.on('message', lambda msg, data: print(json.dumps(msg), file=sys.stderr, flush=True))
    bridge.load()
    desired = {'start': req['start_us'], 'duration': req['end_us'] - req['start_us']}
    original = None
    attempted = False
    recovery_path = ROOT / '.runtime' / ('preview-range-' + Path(req['stage_output']).parent.name + '.json')
    recovery = None
    def journal(status, **extra):
        recovery.update(status=status, **extra)
        temporary = recovery_path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf8') as stream:
            json.dump(recovery, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, recovery_path)
    def wait_saved(expected):
        deadline = min(time.monotonic() + 8, req['deadline_monotonic'] - 2)
        while True:
            try:
                doc = json.loads((project / 'Timelines' / req['timeline_id'] / 'draft_content.json').read_text(encoding='utf-8-sig'))
                if doc.get('config', {}).get('export_range') == expected:
                    return
            except (OSError, json.JSONDecodeError):
                pass  # Autosave can briefly replace the file while it is being read.
            if time.monotonic() >= deadline:
                raise ValueError('Native export range did not converge with the saved draft')
            time.sleep(.2)
    try:
        original = bridge.exports_sync.previewrange(context)['range']
        if original != saved_before.get('config', {}).get('export_range'):
            raise ValueError('Original native export range and saved draft disagree')
        recovery = {'pid': req['pid'], 'sid': sid, 'project': str(project),
                    'projectId': req['project_id'], 'timelineId': req['timeline_id'],
                    'originalRange': original, 'previewRange': desired,
                    'stageOutput': req['stage_output'], 'output': req['output']}
        journal('prepared-before-native-change')
        print(json.dumps({'previewRangeRecovery': str(recovery_path)}), file=sys.stderr, flush=True)
        attempted = True
        changed = bridge.exports_sync.previewsetrange({**context, 'expectedRange': original, 'desiredRange': desired})
        wait_saved(desired)
        # Reserve another 10s for range restoration before independent verification.
        native = render_frontend({**req, 'verifiedHashes': hashes, 'expected_editor_sid': sid,
                                  'deadline_monotonic': req['deadline_monotonic'] - 10}, session)
    except Exception as error:
        if attempted and not getattr(error, 'preserve_pid_lock', False):
            try:
                current = bridge.exports_sync.previewrange(context)['range']
                if current not in (original, desired):
                    raise ValueError('Another range replaced the requested preview range')
                bridge.exports_sync.previewsetrange({**context, 'expectedRange': current, 'desiredRange': original})
                wait_saved(original)
                journal('restored-after-error', renderError=str(error))
            except Exception as restore:
                raise ExportCancellationUnconfirmed(f'{error}; exportRangeRestoreUnconfirmed: {restore}; PID lock and staged output retained') from error
        raise
    else:
        try:
            restored = bridge.exports_sync.previewsetrange({**context, 'expectedRange': desired, 'desiredRange': original})
            wait_saved(original)
            journal('restored')
        except Exception as error:
            raise ExportCancellationUnconfirmed(f'Preview rendered but exportRangeRestoreUnconfirmed: {error}; PID lock and staged output retained') from error
        native.update(rangeChange=changed, rangeRestore=restored, exportRangeRestored=True,
                      requestedStartUs=req['start_us'], requestedEndUs=req['end_us'],
                      rangeRecoveryRecord=str(recovery_path))
        return native
    finally:
        cleanup_without_masking('preview range bridge unload', bridge.unload)


def prepare_preview(args, content):
    from capcut_export import prepare_export
    duration = content.get('duration', 0)
    if not all(isinstance(value, int) for value in (args.start_us, args.end_us)) or not 0 <= args.start_us < args.end_us <= duration:
        raise ValueError('Preview range must satisfy 0 <= start-us < end-us <= timeline duration')
    if args.end_us - args.start_us < 1000000 / content.get('fps', 30):
        raise ValueError('A native video preview must contain at least one timeline frame')
    if args.timeout < 45:
        raise ValueError('Native preview requires --timeout of at least 45 seconds to allow range restoration and verification')
    result = prepare_export(args, {**content, 'duration': args.end_us - args.start_us})
    result.update(start_us=args.start_us, end_us=args.end_us, timeline_duration_us=duration)
    return result


def prepare_frame(args, content):
    output = Path(args.output).resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Timeline frame output must be a PNG')
    if any(c in str(output) for c in ('"', '\n', '\r', '\0')):
        raise ValueError('Unsupported characters in frame output path')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    if not output.parent.is_dir():
        raise ValueError('Frame output parent directory must exist')
    duration = content.get('duration', 0)
    if not isinstance(args.at_us, int) or not 0 <= args.at_us < duration:
        raise ValueError('Frame timestamp must be inside the timeline: 0 <= at-us < duration')
    canvas = content['canvas_config']
    short_side = args.short_side if args.short_side is not None else min(canvas['width'], canvas['height'])
    if not isinstance(short_side, int) or not 1 <= short_side <= 4096:
        raise ValueError('Frame short side must be an integer between 1 and 4096')
    stage = output.parent / ('.capcut-frame-' + uuid.uuid4().hex)
    stage.mkdir()
    return {'output': str(output), 'frame_directory': str(stage),
            'frame_directory_bytes': list(stage.as_posix().encode('utf8')),
            'at_us': args.at_us, 'short_side': short_side, 'duration_us': duration,
            'canvas_width': canvas['width'], 'canvas_height': canvas['height']}


def verify_frame_and_publish(req, native):
    from PIL import Image
    root, output = Path(req['frame_directory']).resolve(), Path(req['output']).resolve()
    if root.parent != output.parent or not root.name.startswith('.capcut-frame-'):
        raise ValueError('Invalid private frame directory')
    extras = [item for item in native.get('extras', []) if item.get('name') == 'extract_frames']
    if len(extras) != 1 or native.get('affected_segments'):
        raise ValueError('Expected one read-only native frame extraction result')
    info = extras[0]
    if info.get('draft_id') != req['timeline_id'] or info.get('mode') != 'draft' or info.get('operate_result', {}).get('status') != 'succeed':
        raise ValueError('Native frame result does not identify the requested draft')
    manifest_path = Path(info['manifest_path']).resolve()
    if manifest_path.parent != root or manifest_path.name != 'manifest.json':
        raise ValueError('Native manifest path escaped the private frame directory')
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    if any(manifest.get(key) != info.get(key) for key in ('draft_id', 'mode', 'sampling', 'materials', 'task_id')):
        raise ValueError('Saved frame manifest differs from the native response')
    materials = manifest['materials']
    if len(materials) != 1 or materials[0].get('segment_id') or len(materials[0]['frames']) != 1:
        raise ValueError('Expected exactly one composed timeline frame')
    frame = materials[0]['frames'][0]
    path = (root / frame['path']).resolve()
    if path.parent != root or path.suffix.lower() != '.png':
        raise ValueError('Native frame path escaped the output directory')
    if frame['draft_time_us'] != req['at_us'] or manifest['sampling']['timestamp_us'] != req['at_us']:
        raise ValueError('Native frame time differs from the request')
    with Image.open(path) as picture:
        if picture.format != 'PNG':
            raise ValueError('Native output is not a PNG')
        picture.load()
        width, height = picture.size
        if (width, height) != (frame['width'], frame['height']):
            raise ValueError('Decoded frame dimensions differ from the manifest')
        scale = req['short_side'] / min(req['canvas_width'], req['canvas_height'])
        if abs(min(width, height) - req['short_side']) > 1 or abs(width - req['canvas_width'] * scale) > 2 or abs(height - req['canvas_height'] * scale) > 2:
            raise ValueError('Frame dimensions do not match the requested canvas/short side')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    os.link(path, output)
    result = {'output': str(output), 'width': width, 'height': height, 'format': 'png',
              'sizeBytes': output.stat().st_size, 'sha256': digest, 'requestedAtUs': req['at_us'],
              'nativeFramePtsUs': frame['pts_us'], 'nativeDraftTimeUs': frame['draft_time_us'],
              'nativeTaskId': manifest['task_id'], 'nativeManifest': manifest,
              'renderer': 'CapCut native draft video extract-frames / VideoClient',
              'timestampSemantics': 'Native timeline request/response timestamp; not a claim about original source decoder PTS',
              'fullImageDecodeVerified': True, 'wholeTimelineExportUsed': False}
    try:
        path.unlink()
        manifest_path.unlink()
        root.rmdir()
    except OSError as error:
        result['cleanupWarning'] = str(error)
    return result
