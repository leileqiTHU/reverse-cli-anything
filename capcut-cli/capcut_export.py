"""File validation/publication for CapCut's own renderer (FFmpeg only decodes)."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent


class ExportCancellationUnconfirmed(ValueError):
    preserve_pid_lock = True


def cleanup_without_masking(label, action):
    """A dead Frida script must not erase an unknown native-operation outcome."""
    try:
        action()
    except Exception as error:
        print(json.dumps({'cleanupWarning': label, 'error': str(error)}), file=sys.stderr, flush=True)


def export_content_signature(doc):
    """Compare render content, excluding application timestamps and UI metadata."""
    return {key: doc.get(key) for key in ('id', 'duration', 'fps', 'canvas_config',
            'tracks', 'materials', 'keyframes', 'keyframe_graph_list', 'relationships',
            'group_container', 'color_space', 'retouch_cover')}


def render_frontend(req, session):
    """Drive existing native Qt methods; observe the engine's real completion."""
    req = {**req, 'allowExportSessionChanges': True}
    source = (ROOT / 'capcut_store_agent.js').read_text(encoding='utf8') + '\n' + (ROOT / 'capcut_export_frontend_agent.js').read_text(encoding='utf8')
    front = session.create_script(source)
    observer = session.create_script((ROOT / 'capcut_export_observer_agent.js').read_text(encoding='utf8'))
    events = []
    postprocess_events = []
    def message(msg, data):
        print(json.dumps(msg, ensure_ascii=False), file=sys.stderr, flush=True)
        if msg.get('type') == 'send' and msg.get('payload', {}).get('event') == 'export-engine-observe':
            events.append(msg['payload'])
        if msg.get('type') == 'send' and msg.get('payload', {}).get('event') == 'export-postprocess-suppressed':
            postprocess_events.append(msg['payload'])
    front.on('message', message)
    observer.on('message', message)
    front.load()
    observer.load()
    observing = False
    opened_by_us = False
    begin_attempted = False
    crop_guard = False
    # This deadline includes hashing, initialization, rendering and verification.
    render_deadline = req['deadline_monotonic'] - 15
    try:
        opened = front.exports_sync.exportopen(req)
        opened_by_us = True
        ready_by = min(time.monotonic() + 15, render_deadline)
        required = {'ExportWindowViewModel', 'ExportHomeBottomViewModel', 'ExportFileSelectorPanelViewModel', 'ExportVideoOptionsPanelViewModel'}
        while True:
            models = front.exports_sync.exportinspect(req)['models']
            if required.issubset({m['className'] for m in models}):
                readiness = front.exports_sync.exportstatus(req)
                if readiness.get('stage') == 'HOME' and readiness.get('preparing') == 'false' and readiness.get('isTryExporting') == 'false':
                    break
            if time.monotonic() >= ready_by:
                raise ValueError('Native export settings did not initialize')
            time.sleep(.2)
        guarded = front.exports_sync.exportguardinstall(req)
        crop_guard = True
        configured = front.exports_sync.exportconfigure(req)
        # Settings can queue preparation work; wait for its real model state.
        prepare_by = min(time.monotonic() + 15, render_deadline)
        while True:
            readiness = front.exports_sync.exportstatus(req)
            if readiness.get('stage') == 'HOME' and readiness.get('preparing') == 'false' and readiness.get('isTryExporting') == 'false':
                break
            if time.monotonic() >= prepare_by:
                raise ValueError(f'Export settings are still preparing: {readiness}')
            time.sleep(.2)
        observer.exports_sync.start(req['stage_output'])
        observing = True
        started = time.monotonic()
        if started >= render_deadline:
            raise ValueError('Export preparation exhausted the render time budget')
        while True:
            begin_attempted = True
            begun = front.exports_sync.exportbegin(req)
            if begun.get('started'):
                break
            if begun != {'started': False, 'reason': 'preparing'}:
                raise ValueError(f'Unexpected export start result: {begun}')
            if time.monotonic() >= prepare_by:
                raise ValueError('Export preparation restarted and did not settle before start')
            time.sleep(.2)
        while True:
            status = front.exports_sync.exportstatus(req)
            failures = [e for e in events if e['kind'] == 'complete' and not e.get('success')]
            if failures or status.get('exportTaskFailed') == 'true' or status.get('exportFail') == 'true':
                raise ValueError(f'CapCut native export failed: {failures or status}')
            completed = [e for e in events if e['kind'] == 'complete' and e.get('success')]
            if completed and status['stage'] == 'FINISH':
                starts = [e for e in events if e['kind'] == 'start']
                if len(starts) != 1:
                    raise ValueError('A unique native export request was not observed')
                start = starts[0]
                if (start['width'], start['height']) != (req['width'], req['height']) or abs(start['fps'] - req['fps']) > .001:
                    raise ValueError('Native render request differed from the requested export parameters')
                if completed[-1]['sid'] != start['sid']:
                    raise ValueError('Native completion did not match the export session')
                if start['sid'] != req['expected_editor_sid']:
                    raise ValueError('Native render used a different editor session')
                if req['action'] == 'preview' and (int(start['start']), int(start['end'])) != (req['start_us'], req['end_us']):
                    raise ValueError('Native renderer used a different preview range; staged output was not published')
                closed = front.exports_sync.exportclose(req)
                if not closed.get('closeAccepted'):
                    raise ValueError('Native completed export panel did not close')
                return {'opened': opened, 'configured': configured, 'engineRequest': start,
                        'engineCompletion': completed[-1], 'status': status, 'closed': closed,
                        'events': events, 'nativeCompletionVerified': True,
                        'postExportGuard': guarded, 'suppressedPostExportActions': list(postprocess_events)}
            if status.get('stage') == 'FINISH' and any(e['kind'].endswith('read-error') for e in events):
                raise ValueError(f'Export reached FINISH but native event decoding failed: {events}')
            if status.get('stage') == 'FINISH' and not completed and time.monotonic() - started > 10:
                raise ValueError(f'Export reached FINISH without the expected engine completion; inspect staged output and events: {events}')
            if time.monotonic() >= render_deadline:
                raise ValueError(f'Native export render budget exceeded; last status {status}; staged output kept at {req["stage_output"]}')
            time.sleep(.25)
    except Exception as original:
        # Only close/cancel the panel opened by this invocation. Never release the
        # PID lock while an owned native render may still be in progress.
        if opened_by_us:
            try:
                state = front.exports_sync.exportstatus(req)
                if begin_attempted and state.get('stage') == 'COMPILING':
                    front.exports_sync.exportcancel(req)
                    cancel_by = min(time.monotonic() + 10, req['deadline_monotonic'] - 1)
                    while state.get('stage') not in ('HOME', 'FINISH') and time.monotonic() < cancel_by:
                        time.sleep(.2)
                        state = front.exports_sync.exportstatus(req)
                    if not any(e['kind'] == 'complete' for e in events):
                        raise ValueError('The bound export task did not report terminal completion after cancellation')
                if state.get('stage') not in ('HOME', 'FINISH'):
                    raise ValueError(f'Export terminal state is unknown: {state}')
                closed = front.exports_sync.exportclose(req)
                if not closed.get('closeAccepted'):
                    raise ValueError('Owned export panel did not close')
            except Exception as cleanup:
                raise ExportCancellationUnconfirmed(f'{original}; cancellationUnconfirmed: {cleanup}; PID lock and staged output retained; inspect before retrying') from original
        raise
    finally:
        if crop_guard:
            cleanup_without_masking('export crop guard removal', front.exports_sync.exportguardremove)
        if observing:
            cleanup_without_masking('export observer stop', observer.exports_sync.stop)
        cleanup_without_masking('export observer unload', observer.unload)
        cleanup_without_masking('export frontend unload', front.unload)


def prepare_export(args, content):
    output = Path(args.output).resolve()
    if output.suffix.lower() != '.mp4':
        raise ValueError('Export output must have an .mp4 suffix')
    if any(c in str(output) for c in ('"', '\n', '\r', '\0')):
        raise ValueError('Unsupported characters in export path')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    if not output.parent.is_dir():
        raise ValueError(f'Output directory does not exist: {output.parent}')
    if (args.width is None) != (args.height is None):
        raise ValueError('Provide both --width and --height, or neither')
    canvas = content.get('canvas_config', {})
    width = args.width if args.width is not None else canvas.get('width')
    height = args.height if args.height is not None else canvas.get('height')
    if not all(isinstance(n, int) and 16 <= n <= 8192 and n % 2 == 0 for n in (width, height)):
        raise ValueError('H.264 export dimensions must be even integers between 16 and 8192')
    resolution = {480: '480P', 720: '720P', 1080: '1080P', 1440: '2K', 2160: '4K', 4320: '8K'}.get(min(width, height))
    if resolution is None or abs(width / height - canvas.get('width', 0) / max(1, canvas.get('height', 0))) > .002:
        raise ValueError('Export supports native 480P/720P/1080P/2K/4K/8K presets at the draft canvas aspect ratio')
    fps = args.fps if args.fps is not None else content.get('fps', 30)
    if not isinstance(fps, (int, float)) or not math.isfinite(fps) or not 1 <= fps <= 120:
        raise ValueError('Export fps must be finite and between 1 and 120')
    duration = content.get('duration', 0)
    if not isinstance(duration, int) or not 0 < duration <= 2**53 - 1:
        raise ValueError('A finite, nonempty timeline is required')
    if args.timeout < 30:
        raise ValueError('Export requires --timeout of at least 30 seconds; default is 60')
    # Resolve explicit configuration, PATH or existing bundled dependencies.
    sys.path.insert(0, str(ROOT.parent))
    from reverse_cli.config import ffmpeg
    found = ffmpeg('capcut')
    if found is None:
        raise ValueError('Configure REVERSE_CLI_FFMPEG or install a local FFmpeg decoder')
    decoder = str(found.resolve())
    if not Path(decoder).is_file():
        raise ValueError('The local FFmpeg decoder is unavailable')
    stage_dir = output.parent / ('.capcut-export-' + uuid.uuid4().hex)
    stage_dir.mkdir()
    return {'output': str(output), 'stage_output': str(stage_dir / 'video.mp4'),
            'width': width, 'height': height, 'fps': float(fps), 'duration_us': duration, 'resolution_label': resolution,
            'decoder': decoder}


def validate_probe(probe, req):
    if probe.get('container_format') != 'mp4' or probe.get('video_codec') != 'h264':
        raise ValueError('Renderer output is not an H.264 MP4')
    if (probe.get('width'), probe.get('height')) != (req['width'], req['height']):
        raise ValueError('Renderer output dimensions differ from the requested dimensions')
    if abs(probe.get('fps', 0) - req['fps']) > .02:
        raise ValueError('Renderer output frame rate differs from the request')
    if abs(probe.get('duration_us', 0) - req['duration_us']) > math.ceil(1000000 / req['fps']):
        raise ValueError('Renderer output duration differs by more than one frame')


def verify_and_publish(req):
    stage, output = Path(req['stage_output']), Path(req['output'])
    if not stage.is_file() or stage.stat().st_size < 100:
        raise ValueError('Native renderer returned without producing a video')
    # Probe in a disposable native host, independently of the live editor.
    def remaining():
        value = req['deadline_monotonic'] - time.monotonic() - 1
        if value <= 0:
            raise ValueError('Export verification exceeded the total time budget; staged video retained')
        return value
    child = subprocess.run([sys.executable, '-B', str(ROOT / 'capcut_agent.py'),
                            '--capcut-dir', req['capcut_dir'], 'probe', '--input', str(stage)],
                           capture_output=True, encoding='utf8', timeout=min(15, remaining()),
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    response = json.loads(child.stdout)
    if child.returncode or not response.get('ok'):
        raise ValueError(f'Exported file probe failed: {response}')
    probe = response['result']
    validate_probe(probe, req)
    decoded = subprocess.run([req['decoder'], '-hide_banner', '-loglevel', 'error', '-xerror',
                              '-i', str(stage), '-map', '0:v:0', '-map', '0:a?', '-progress', 'pipe:1',
                              '-nostats', '-f', 'null', '-'], capture_output=True, encoding='utf8',
                             timeout=remaining(), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if decoded.returncode or decoded.stderr.strip():
        raise ValueError('Exported file did not fully decode: ' + decoded.stderr[-2000:])
    progress = {}
    for line in decoded.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            progress[key] = value.strip()
    frames = int(progress.get('frame', '0'))
    expected = req['duration_us'] * req['fps'] / 1000000
    if progress.get('progress') != 'end' or frames <= 0 or abs(frames - expected) > 1:
        raise ValueError(f'Complete frame count was not verified: {frames}, expected {expected}')
    with stage.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    # On Windows this fails atomically if output exists; never overwrite a file.
    os.link(stage, output)
    cleanup_warning = None
    try:
        stage.unlink()
        stage.parent.rmdir()
    except OSError as error:
        cleanup_warning = str(error)
    result = {'output': str(output), 'sizeBytes': output.stat().st_size, 'sha256': digest,
              'container': probe['container_format'], 'videoCodec': probe['video_codec'],
              'width': probe['width'], 'height': probe['height'], 'fps': probe['fps'],
              'durationUs': probe['duration_us'], 'hasAudio': probe['has_audio'],
              'decodedFrames': frames, 'fullDecodeVerified': True,
              'probeLogs': response.get('logs'), 'renderer': 'CapCut native frontend ExportClient renderer',
              'verification': 'Independent native media probe and FFmpeg full-file decode'}
    if cleanup_warning:
        result['cleanupWarning'] = cleanup_warning
    return result
