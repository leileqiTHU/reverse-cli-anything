"""Native project-store adapter; saved JSON is read only for verification."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.native-tools'))
from capcut_cli_worker import PINS

STORE_PINS = {**PINS,
    'VECreator.dll': '576bc1f51c0e81d50369e2ee69c157389a310151f1e75ea79813d9753be2db77',
    'Qt6Core.dll': '88f0da8219ab163c2949cb862fc00356e9c96df3bd4a0013bde14aa285bbc925'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def video_items(meta):
    return [item for group in meta['draft_materials'] if group['type'] == 0
            for item in group['value'] if item.get('metetype') == 'video']


def matching_video(meta, source):
    return [item for item in video_items(meta)
            if Path(item.get('file_Path', '')).resolve() == source]


def timeline_fingerprints(project):
    # The importer must change the bin without changing any timeline contents.
    files = list((project / 'Timelines').glob('*/draft_content.json'))
    files += [p for p in (project / 'draft_content.json', project / 'Timelines/project.json') if p.is_file()]
    return {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files}


def material_ids(meta):
    return {(group['type'], item['id']) for group in meta['draft_materials']
            for item in group['value'] if item.get('id')}


def execute(req):
    import frida
    base = Path(req['capcut_dir']).resolve()
    for name, expected in STORE_PINS.items():
        with (base / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError('Unsupported CapCut build: ' + name)
    lock = ROOT / '.runtime' / f'editor-{req["pid"]}.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError(f'Another editor operation owns {lock}; inspect it before removing a stale lock')
    session = None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps({'workerPid': os.getpid(), 'capcutPid': req['pid'], 'created': time.time()}))
        session = frida.attach(req['pid'])
        script = session.create_script((ROOT / 'capcut_store_agent.js').read_text(encoding='utf8'))
        script.on('message', lambda msg, data: print(json.dumps(msg, ensure_ascii=False), file=sys.stderr, flush=True))
        script.load()
        native = {'pid': req['pid'], 'verifiedHashes': STORE_PINS}
        inventory = script.exports_sync.inspect(native)
        native['expectedDraftRoot'] = inventory['draftRoot']
        if req['action'] == 'list':
            return inventory
        if req['action'] in ('open', 'close', 'import-media') and req.get('project') is None:
            matches = [p for p in inventory['projects'] if p['id'].lower() == req['project_id'].lower()]
            if len(matches) != 1:
                raise ValueError('Project UUID does not identify one registered project')
            req['project'] = str(Path(matches[0]['path']).resolve())
            meta = read_json(Path(req['project']) / 'draft_meta_info.json')
            if meta['draft_id'].lower() != req['project_id'].lower():
                raise ValueError('Resolved project path has a different saved identity')
        if req['action'] in ('open', 'close'):
            return lifecycle(req, native, inventory, script, session)
        if req['action'] == 'create':
            if not script.exports_sync.metadata().get('createUsesNativeInitialization'):
                raise ValueError('Native full-project initialization is required')
            if any(p['name'].casefold() == req['project_name'].casefold() for p in inventory['projects']):
                raise ValueError('Project name already exists; no project created')
            expected_path = Path(inventory['draftRoot']).resolve() / req['project_name']
            if expected_path.exists():
                raise ValueError('Project destination already exists; no project created')
            result = script.exports_sync.create({**native, 'projectNameBytes': req['project_name_bytes']})
            print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
            if any(p['id'].lower() == result['id'].lower() for p in inventory['projects']):
                raise ValueError('Native creation reused an existing project ID; inspect state before retrying')
            if Path(result['path']).resolve().parent != Path(inventory['draftRoot']).resolve():
                raise ValueError('Native project was created outside the configured draft root; inspect logs before retrying')
            result = verify_created(req, result, session, expected_name=result['name'])
            named = script.exports_sync.finishcreate({**native, 'projectId': result['id'], 'projectPath': result['path']})
            print(json.dumps({'nativeNamingBeforeDiskVerification': named}), file=sys.stderr, flush=True)
            if named['id'] != result['id'] or Path(named['path']).resolve().parent != Path(inventory['draftRoot']).resolve():
                raise ValueError('Native project identity/path changed during naming; inspect logs before retrying')
            return verify_created(req, {**result, **named}, session)
        if req['action'] != 'import-media':
            raise ValueError('Unsupported project operation')
        project, source = Path(req['project']).resolve(), Path(req['input']).resolve()
        target = [p for p in inventory['projects'] if p['id'].lower() == req['project_id'].lower()]
        if len(target) != 1 or Path(target[0]['path']).resolve() != project:
            raise ValueError('Project identity/path is not registered in the selected CapCut process')
        active = inventory['currentProject']
        if active and (active['id'].lower() == req['project_id'].lower() or Path(active['path']).resolve() == project):
            raise ValueError('Target project is currently open. Close it in CapCut before importing media.')
        meta_path = project / 'draft_meta_info.json'
        before = read_json(meta_path)
        if before['draft_id'].lower() != req['project_id'].lower():
            raise ValueError('Saved project identity changed')
        existing = matching_video(before, source)
        if existing:
            if any(existing[0].get(key) != req[source_key] for key, source_key in
                   [('duration', 'duration_us'), ('width', 'width'), ('height', 'height')]):
                raise ValueError('This path is already imported with different media metadata; automatic refresh is not supported')
            return {'backend': 'capcut-native-material-store', 'projectId': req['project_id'],
                    'projectPath': str(project), 'materialId': existing[0]['id'], 'mediaPath': str(source),
                    'alreadyImported': True, 'timelineModified': False, 'persistenceVerified': True,
                    'verified': 'existing-native-project-and-saved-material', 'targetWasClosed': True}
        fingerprints = timeline_fingerprints(project)
        result = script.exports_sync.importvideo({**native, 'projectId': req['project_id'],
            'projectPath': str(project), 'mediaPathBytes': req['media_path_bytes'],
            'fileNameBytes': req['file_name_bytes'], 'durationUs': req['duration_us'],
            'width': req['width'], 'height': req['height']})
        print(json.dumps({'nativeResultBeforeDiskVerification': result}), file=sys.stderr, flush=True)
        if not result['accepted'] or not result['syncSaveReturned']:
            raise ValueError('Native import/save did not report success; inspect the project before retrying')
        deadline = time.monotonic() + 10
        while True:
            try:
                after = read_json(meta_path)
                matches = matching_video(after, source)
                item = next(i for i in matches if i['id'] == result['materialId'])
                if (after['draft_id'].lower() == req['project_id'].lower()
                        and item['duration'] == req['duration_us'] and item['width'] == req['width']
                        and item['height'] == req['height']):
                    if timeline_fingerprints(project) != fingerprints:
                        raise RuntimeError('Import returned but timeline files changed concurrently; inspect the project')
                    if not material_ids(before).issubset(material_ids(after)):
                        raise RuntimeError('Import returned but existing material records were not all retained; inspect the project')
                    result.update(persistenceVerified=True, alreadyImported=False,
                                  verified='native-store-and-saved-material-with-unchanged-timelines')
                    return result
            except (OSError, ValueError, KeyError, StopIteration):
                pass
            if time.monotonic() >= deadline:
                raise ValueError('Native import returned, but saved material was not verified; do not blindly retry')
            time.sleep(.2)
    finally:
        if session is not None:
            try:
                print('native-session-detach-enter', file=sys.stderr, flush=True)
                session.detach()
                print('native-session-detach-return', file=sys.stderr, flush=True)
            except frida.InvalidOperationError:
                pass
        lock.unlink(missing_ok=True)


def lifecycle(req, native, inventory, script, session):
    from capcut_editor_worker import saved_matching
    project = Path(req['project']).resolve()
    targets = [p for p in inventory['projects'] if p['id'].lower() == req['project_id'].lower()]
    if len(targets) != 1 or Path(targets[0]['path']).resolve() != project:
        raise ValueError('Project identity/path is not registered in the selected CapCut process')
    editor = session.create_script((ROOT / 'capcut_editor_agent.js').read_text(encoding='utf8'))
    editor.load()
    live_before = None
    promotion_cleanup = None
    if req['action'] == 'close' and inventory['currentProject']:
        if inventory['currentProject']['id'].lower() != req['project_id'].lower():
            raise ValueError('Refusing to close a different current project')
        if inventory.get('blockingModalPresent'):
            promotion_cleanup = script.exports_sync.dismissstartuppromotion({**native,
                'projectId': req['project_id'], 'projectPath': str(project)})
            print(json.dumps({'startupPromotionCleanup': promotion_cleanup}), file=sys.stderr, flush=True)
            inventory = script.exports_sync.inspect(native)
            if inventory.get('blockingModalPresent'):
                raise ValueError('CapCut has a blocking modal window; its normal close check would refuse. No project close was attempted')
        live_before = editor.exports_sync.active()
        tid = next(r['id'] for r in live_before['summary'] if r['type'] == 'draft')
        saved_matching({**req, 'timeline_id': tid}, live_before['summary'])
    result = getattr(script.exports_sync, req['action'])({**native,
        'projectId': req['project_id'], 'projectPath': str(project)})
    if promotion_cleanup is not None:
        result['startupPromotionCleanup'] = promotion_cleanup
    print(json.dumps({'nativeLifecycleRequested': result}), file=sys.stderr, flush=True)
    deadline = time.monotonic() + 25
    last_error = ''
    requested_path = project
    renamed_path_retried = False
    while True:
        try:
            print(json.dumps({'lifecycleVerify': 'inspect-enter'}), file=sys.stderr, flush=True)
            state = script.exports_sync.inspect(native)
            print(json.dumps({'lifecycleVerify': 'inspect-return', 'currentProject': state['currentProject'],
                              'editorWindowPresent': state['editorWindowPresent'], 'projectLoading': state['projectLoading'],
                              'windowLoaded': state.get('windowLoaded'), 'inputBlocked': state.get('inputBlocked'),
                              'windowClosing': state.get('windowClosing')}), file=sys.stderr, flush=True)
            target = next(p for p in state['projects'] if p['id'].lower() == req['project_id'].lower())
            actual = Path(target['path']).resolve()
            meta = read_json(actual / 'draft_meta_info.json')
            index = read_json(actual / 'Timelines/project.json')
            if meta['draft_id'].lower() != req['project_id'].lower():
                raise ValueError('Saved project identity changed')
            if state['projectLoading']:
                raise ValueError('Project is still loading')
            # CapCut can rename a newly named project's directory after close
            # returns, even between native inventory and the first open call.
            # Recover only a proven identity-preserving rename at idle home.
            # Normal open guards still reject another project/loading state.
            if (req['action'] == 'open' and actual != requested_path
                    and not state['currentProject'] and not state['editorWindowPresent']):
                if renamed_path_retried:
                    raise ValueError('Project path changed again during open; no further request will be made')
                renamed_path_retried = True
                previous_path = requested_path
                requested_path = actual
                script = session.create_script((ROOT / 'capcut_store_agent.js').read_text(encoding='utf8'))
                script.on('message', lambda msg, data: print(json.dumps(msg, ensure_ascii=False), file=sys.stderr, flush=True))
                script.load()
                result = script.exports_sync.open({**native, 'projectId': req['project_id'],
                                                   'projectPath': str(actual)})
                result.update(recoveredNativeFolderRename=True, previousRequestedPath=str(previous_path))
                print(json.dumps({'nativeOpenAfterVerifiedRename': result}), file=sys.stderr, flush=True)
                deadline = time.monotonic() + 25
                continue
            if req['action'] == 'close':
                if state['currentProject'] or state['editorWindowPresent']:
                    raise ValueError('Native close is pending or was declined')
                # draft_fold_path may retain the old date-based directory even
                # after CapCut renames it. Bind by saved UUID + native inventory;
                # requiring that informational path to update can wait forever.
                if live_before:
                    saved_matching({**req, 'project': str(actual), 'timeline_id': tid}, live_before['summary'])
                result.update(opened=False, persistenceVerified=True, homepageVerified=True, stage='closed')
            else:
                active = state['currentProject']
                if not active or active['id'].lower() != req['project_id'].lower() or not state['editorWindowPresent']:
                    raise ValueError('Target editor is not open yet')
                if not state.get('windowLoaded') or state.get('inputBlocked') or state.get('windowClosing'):
                    raise ValueError('Frontend window initialization is not complete')
                live = editor.exports_sync.active()
                tid = next(r['id'] for r in live['summary'] if r['type'] == 'draft')
                if not any(t['id'] == tid and not t.get('is_marked_delete') for t in index['timelines']):
                    raise ValueError('Live editor timeline does not belong to requested project')
                saved_matching({**req, 'project': str(actual), 'timeline_id': tid}, live['summary'])
                result.update(opened=True, editorInitializationVerified=True, stage='ready',
                              activeTimelineId=tid, sid=live['sid'])
            result.update(projectId=req['project_id'], projectPath=str(actual), path=str(actual), name=target['name'],
                          mainTimelineId=index['main_timeline_id'], verified='native-lifecycle-and-live-saved-state')
            print(json.dumps({'lifecycleVerify': 'complete', 'result': result}), file=sys.stderr, flush=True)
            return result
        except Exception as error:
            last_error = str(error)
        if time.monotonic() >= deadline:
            raise ValueError('Project lifecycle request did not reach the verified state; do not blindly retry: ' + last_error)
        time.sleep(.25)


def verify_created(req, result, session, expected_name=None):
    import uuid
    project = Path(result['path']).resolve()
    expected_name = req['project_name'] if expected_name is None else expected_name
    editor = session.create_script((ROOT / 'capcut_editor_agent.js').read_text(encoding='utf8'))
    editor.load()
    deadline = time.monotonic() + 20
    last_error = ''
    while True:
        try:
            meta = read_json(project / 'draft_meta_info.json')
            index = read_json(project / 'Timelines/project.json')
            timeline_id = index['main_timeline_id']
            uuid.UUID(index['id'])
            uuid.UUID(timeline_id)
            content = read_json(project / 'Timelines' / timeline_id / 'draft_content.json')
            if (meta['draft_id'].lower() != result['id'].lower() or meta['draft_name'] != expected_name
                    or Path(meta['draft_fold_path']).resolve() != project or content['id'] != timeline_id
                    or content['tracks'] != [] or not any(t['id'] == timeline_id and not t.get('is_marked_delete') for t in index['timelines'])):
                raise ValueError('Created project metadata/timeline mismatch')
            live = editor.exports_sync.run({'action': 'inspect', 'capcut_dir': req['capcut_dir'],
                                           'project': str(project), 'timeline_id': timeline_id})
            result.update(persistenceVerified=True, editorInitializationVerified=True, opened=True, stage='ready',
                          projectId=result['id'], projectPath=str(project), mainTimelineId=timeline_id,
                          timelineProjectId=index['id'], sid=live['sid'],
                          verified='native-creation-saved-project-and-live-editor-draft')
            return result
        except Exception as error:
            last_error = str(error)
        if time.monotonic() >= deadline:
            raise ValueError('Native project creation returned but full initialization was not verified; '
                             'inspect logs before retrying: ' + last_error)
        time.sleep(.2)


if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    try:
        result = execute(read_json(source))
        report = {'exitCode': 0, 'stdout': json.dumps({'err_code': 0, 'result': result}), 'stderr': ''}
    except Exception as error:
        report = {'workerError': str(error)}
    output.write_text(json.dumps(report, ensure_ascii=False), encoding='utf8')
