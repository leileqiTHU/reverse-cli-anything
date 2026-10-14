"""JSON CLI for verified CapCut media operations and an explicit native editor session."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from reverse_cli.config import app_path
DEFAULT_CAPCUT = str(app_path('capcut'))
TOPICS = ("root", "editor", "project", "media", "probe", "convert-image")
WRAPPER_HELP = """capcut-agent [--capcut-dir DIR] [--timeout SECONDS] COMMAND
capabilities | version | help [--topic root|editor|project|media|probe|convert-image]
probe --input FILE
media frame --input VIDEO --at-us N --output NEW.png
media preview --input VIDEO --start-us N --end-us N --output NEW.mp4
convert-image --input FILE --output NEW_FILE [--format jpg|jpeg|png]
editor sessions --pid PID
editor inspect --pid PID --project DIR [--timeline UUID]
editor add-video --pid PID --project DIR --input VIDEO [--track N] [--start-us N] [--duration-us N]
editor add-track --pid PID --project DIR --input VIDEO [--start-us N] [--duration-us N]
editor add-timeline --pid PID --project DIR --name NAME [--timeline CURRENT_UUID]
editor switch-timeline --pid PID --project DIR --timeline TARGET_UUID
editor trim --pid PID --project DIR --segment UUID --in-us N --out-us N [--timeline UUID]
editor split --pid PID --project DIR --segment UUID --points-us N [N ...] [--timeline UUID]
editor move --pid PID --project DIR --segment UUID --start-us N [--timeline UUID]
editor remove --pid PID --project DIR --segment UUID [--timeline UUID]
editor undo|redo --pid PID --project DIR [--steps N]
editor export --pid PID --project DIR --timeline UUID --output NEW.mp4 [--width N --height N] [--fps N]
editor frame --pid PID --project DIR --timeline UUID --at-us N --output NEW.png [--short-side N]
editor preview --pid PID --project DIR --timeline UUID --start-us N --end-us N --output NEW.mp4 [--width N --height N] [--fps N]
editor add-audio --pid PID --project DIR --timeline UUID --input AUDIO --duration-us N [--start-us N --source-in-us N --gain-db N --fade-in-us N --fade-out-us N --request-id ID]
editor captions-import --pid PID --project DIR --timeline UUID --input SRT_OR_JSON [--style JSON --offset-us N --request-id ID]
editor set-clip --pid PID --project DIR --timeline UUID --segment UUID --patch JSON [--request-id ID]
project import-media --pid PID (--project DIR | --project-id UUID) --input VIDEO
project create --pid PID --name NAME
project list --pid PID
project open|close --pid PID (--project DIR | --project-id UUID)
Editor commands require the target project to be open. All editor actions except sessions support --timeline UUID.
add-track creates a visual video layer with its first clip. Actual timing follows CapCut snapping and is returned in clips.targetUs.
add-timeline creates and saves an independent timeline tab without changing the active timeline.
switch-timeline activates the requested independent timeline through the original frontend.
trim uses absolute positions in the current timeline and keeps that source interval; native magnetic snapping can close the gap.
split points are relative to the clip start. trim/split support ordinary speed-1 video, with at least one frame per part.
move freely positions clips on added video layers; the magnetic main track is rejected before editing.
Use clips.targetUs/sourceUs for normalized microsecond values; raw native attribute labels are inconsistent in this build.
import-media requires the target project to be closed. Existing media paths are returned without duplication.
create requires the CapCut homepage and opens the created project. Names and folder paths can differ.
close saves through the normal frontend; open waits for the requested project's editor to initialize.
Prefer --project-id across close/open/import: CapCut may rename folders asynchronously. Empty track creation is not yet available.
export uses CapCut's native renderer, H.264 MP4 and the complete active timeline; defaults to canvas dimensions/fps.
Export requires explicit --timeline. Existing outputs are refused; output is published only after probe and full decode pass.
editor frame extracts a composed PNG directly through CapCut's native timeline frame API; at-us is end-exclusive.
editor preview renders only [start-us, end-us) through CapCut's native range API and restores the prior export range.
Both require an explicit active --timeline; preview requires --timeout >=45 seconds (90 recommended).
media frame/preview decode a local video with FFmpeg, without requiring an open editor.
media frame selects the first decoded frame at or after at-us and reports actualAtUs.
media preview retains frames in [start-us, end-us), reports effectiveStartUs and rebases output to that frame.
New editing tools require explicit active timeline and timeout >=30s. --request-id protects against duplicate execution.
add-audio creates an editable audio segment; source-in is source microseconds, target range must fit the existing timeline.
Use --volume-linear or --gain-db, exclusively. CapCut chooses actual audio/text tracks; returned items include trackId.
captions-import appends native editable subtitles, accepts UTF-8 SRT or timeline_us JSON, without speech recognition.
Caption style supports size (native units), color, outlineColor/outlineWidth and xRatio/yRatio; native default font is used.
set-clip video patch fields: transform, crop, opacity, volumeLinear/gainDb, speed; audio: volume and fadeInUs/fadeOutUs.
Transform fields: scaleX, scaleY, rotationDeg, xRatio, yRatio; crop requires left,top,right,bottom in [0,1].
Coordinates use canvas center: x positive right, y positive up, 1 is half canvas width/height. Rotation positive clockwise.
Constant speed currently requires one ordinary speed-1 video at time zero and no other items on the timeline.
Keyframed clips are refused. Changes are absolute; omitted fields remain unchanged. Multi-step calls are not atomic.
inspect items includes video/audio/text saved properties with native IDs/timing cross-check; clips remains video-only for compatibility.
See README.txt. Native media help is a reference and may list commands not exposed by this adapter.
"""


class CliError(Exception):
    def __init__(self, code, message, details=None):
        self.code, self.message, self.details = code, message, details


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError("invalid_arguments", message)


def build_parser():
    parser = Parser(add_help=False, description=__doc__)
    parser.add_argument("--capcut-dir", default=DEFAULT_CAPCUT)
    parser.add_argument("--timeout", type=int, default=60)
    sub = parser.add_subparsers(dest="operation", required=True, parser_class=Parser)
    for name in ("capabilities", "version"):
        sub.add_parser(name, add_help=False)
    help_parser = sub.add_parser("help", add_help=False)
    help_parser.add_argument("--topic", choices=TOPICS, default="root")
    probe = sub.add_parser("probe", add_help=False)
    probe.add_argument("--input", required=True)
    media = sub.add_parser('media', add_help=False)
    media_sub = media.add_subparsers(dest='media_action', required=True, parser_class=Parser)
    for action in ('frame', 'preview'):
        mp = media_sub.add_parser(action, add_help=False)
        mp.add_argument('--input', required=True)
        mp.add_argument('--output', required=True)
        if action == 'frame':
            mp.add_argument('--at-us', required=True, type=int)
        else:
            mp.add_argument('--start-us', required=True, type=int)
            mp.add_argument('--end-us', required=True, type=int)
    convert = sub.add_parser("convert-image", add_help=False)
    convert.add_argument("--input", required=True)
    convert.add_argument("--output", required=True)
    convert.add_argument("--format", choices=("jpg", "jpeg", "png"))
    project = sub.add_parser("project", add_help=False)
    project_sub = project.add_subparsers(dest="project_action", required=True, parser_class=Parser)
    for action in ("create", "import-media", "list", "open", "close"):
        pp = project_sub.add_parser(action, add_help=False)
        pp.add_argument("--pid", required=True, type=int)
        if action == "create":
            pp.add_argument("--name", required=True)
        elif action == "import-media":
            pp.add_argument("--input", required=True)
        if action in ("import-media", "open", "close"):
            identity = pp.add_mutually_exclusive_group(required=True)
            identity.add_argument("--project")
            identity.add_argument("--project-id")
    editor = sub.add_parser("editor", add_help=False)
    editor_sub = editor.add_subparsers(dest="editor_action", required=True, parser_class=Parser)
    for action in ("sessions", "inspect", "add-video", "add-track", "add-timeline", "switch-timeline", "trim", "split", "move", "remove", "undo", "redo", "export", "frame", "preview", "add-audio", "captions-import", "set-clip"):
        ep = editor_sub.add_parser(action, add_help=False)
        ep.add_argument("--pid", required=True, type=int)
        if action != "sessions":
            ep.add_argument("--project", required=True)
            ep.add_argument("--timeline", required=action in ("switch-timeline", "export", "frame", "preview", "add-audio", "captions-import", "set-clip"))
        if action in ('add-audio','captions-import','set-clip'):
            ep.add_argument('--request-id')
        if action == 'add-audio':
            ep.add_argument('--input', required=True)
            ep.add_argument('--start-us', type=int, default=0)
            ep.add_argument('--duration-us', type=int, required=True)
            ep.add_argument('--source-in-us', type=int, default=0)
            volume=ep.add_mutually_exclusive_group()
            volume.add_argument('--volume-linear',type=float)
            volume.add_argument('--gain-db',type=float)
            ep.add_argument('--fade-in-us',type=int)
            ep.add_argument('--fade-out-us',type=int)
        if action == 'captions-import':
            ep.add_argument('--input',required=True)
            ep.add_argument('--format',choices=('srt','json'))
            ep.add_argument('--offset-us',type=int,default=0)
            ep.add_argument('--style')
        if action == 'set-clip':
            ep.add_argument('--segment',required=True)
            ep.add_argument('--patch',required=True)
        if action in ('export', 'frame', 'preview'):
            ep.add_argument("--output", required=True)
        if action in ('export', 'preview'):
            ep.add_argument("--width", type=int)
            ep.add_argument("--height", type=int)
            ep.add_argument("--fps", type=float)
        if action == 'frame':
            ep.add_argument('--at-us', required=True, type=int)
            ep.add_argument('--short-side', type=int)
        if action == 'preview':
            ep.add_argument('--start-us', required=True, type=int)
            ep.add_argument('--end-us', required=True, type=int)
        if action in ("trim", "split", "move", "remove"):
            ep.add_argument("--segment", required=True)
        if action == "trim":
            ep.add_argument("--in-us", type=int, required=True)
            ep.add_argument("--out-us", type=int, required=True)
        if action == "split":
            ep.add_argument("--points-us", type=int, nargs='+', required=True)
        if action == "move":
            ep.add_argument("--start-us", type=int, required=True)
        if action in ("add-video", "add-track"):
            ep.add_argument("--input", required=True)
            ep.add_argument("--start-us", type=int, default=0)
            ep.add_argument("--duration-us", type=int)
            if action == "add-video":
                ep.add_argument("--track", type=int, default=0)
        if action in ("undo", "redo"):
            ep.add_argument("--steps", type=int, default=1)
        if action == "add-timeline":
            ep.add_argument("--name", required=True)
    return parser


def parse_args(argv):
    return build_parser().parse_args(["help"] if argv in ([], ["--help"], ["-h"]) else argv)


def local_file(value):
    path = Path(value).resolve()
    if not path.is_file():
        raise CliError("input_not_found", f"Input file does not exist: {path}")
    return path


def invoke(args, request, run_dir):
    request["capcut_dir"] = str(Path(args.capcut_dir).resolve())
    if request.get('action') in ('export', 'frame', 'preview', 'add-audio', 'captions-import', 'set-clip') and request.get('operation') == 'editor':
        # Python's monotonic clock has the same origin across Windows processes.
        # Leave time to report an orderly failure before the outer watchdog fires.
        request['deadline_monotonic'] = time.monotonic() + args.timeout - 3
    request_path, response_path = run_dir / "request.json", run_dir / "response.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf8")
    env = os.environ.copy()
    temp = run_dir / "temp"
    temp.mkdir()
    env.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp), PYTHONUTF8="1",
               PYTHONDONTWRITEBYTECODE="1", LYRA_CLI_TARGET_PLATFORM="windows",
               LYRA_CLI_ROOT_WORKSPACE=str(run_dir / "workspace"),
               LYRA_CLI_MATERIAL_DIR=str(run_dir / "materials"),
               LYRA_CLI_MATERIAL_CACHE_DIR=str(run_dir / "material-cache"))
    for key in ("LYRA_CLI_SETTINGS_JSON_FILE", "LYRA_CLI_AUTO_DOWNGRADE_DRAFT"):
        env.pop(key, None)
    with (run_dir / "native.stdout.log").open("wb") as stdout, (run_dir / "native.stderr.log").open("wb") as stderr:
        try:
            worker = {"editor": "capcut_editor_worker.py", "project": "capcut_store_worker.py"}.get(request.get("operation"), "capcut_cli_worker.py")
            child = subprocess.run([sys.executable, "-B", str(ROOT / worker),
                                    str(request_path), str(response_path)], cwd=run_dir,
                                   env=env, stdout=stdout, stderr=stderr, timeout=args.timeout,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            details=None
            if request.get('action') in ('add-audio','captions-import','set-clip'):
                details={'outcome':'unknown','retryAllowed':False,'operationId':request['request_id'],
                         'recoveryFile':str(ROOT/'.runtime/mutations'/(request['request_id']+'.json'))}
            raise CliError("native_timeout", f"Native worker exceeded {args.timeout} seconds; native cancellation is not implied",details)
    if child.returncode != 0:
        raise CliError("native_crash", f"Native worker exited with code {child.returncode}")
    if not response_path.is_file():
        raise CliError("native_no_result", "Native worker returned no result")
    report = json.loads(response_path.read_text(encoding="utf8"))
    if "workerError" in report:
        raise CliError("native_worker_error", report["workerError"], report.get('mutationDetails'))
    if report["exitCode"] != 0:
        raise CliError("native_command_failed", report["stderr"] or report["stdout"] or str(report["exitCode"]))
    if args.operation in ("help", "version"):
        return {"text": report["stdout"], "nativeExitCode": 0}
    payload = json.loads(report["stdout"])
    if payload.get("err_code") != 0:
        raise CliError("native_command_failed", payload.get("err_msg", "Native operation failed"))
    return payload["result"]


def editor_request(args, run_dir):
    req = {"operation": "editor", "action": args.editor_action, "pid": args.pid}
    if args.pid <= 0:
        raise CliError("invalid_arguments", "--pid must be positive")
    if args.editor_action == "sessions":
        return req
    project = Path(args.project).resolve()
    try:
        project_data = json.loads((project / "Timelines/project.json").read_text(encoding="utf-8-sig"))
        requested = str(uuid.UUID(args.timeline or project_data["main_timeline_id"]))
        matches = [t['id'] for t in project_data['timelines'] if t['id'].lower() == requested.lower() and not t.get('is_marked_delete')]
        if len(matches) != 1:
            raise ValueError("Timeline is not present in this project")
        timeline = matches[0]
        content = json.loads((project / "Timelines" / timeline / "draft_content.json").read_text(encoding="utf-8-sig"))
        if content["id"] != timeline:
            raise ValueError("Draft/timeline identity mismatch")
    except (OSError, ValueError, KeyError) as error:
        raise CliError("invalid_project", str(error))
    req.update(project=str(project), timeline_id=timeline)
    if args.editor_action in ('add-audio','captions-import','set-clip'):
        from capcut_extensions import prepare
        try:
            if args.timeout < 30: raise ValueError('Native editing extensions require --timeout >=30 seconds')
            req.update(prepare(args,content))
            req['project_id']=json.loads((project/'draft_meta_info.json').read_text(encoding='utf-8-sig'))['draft_id']
            if args.editor_action=='add-audio':
                probe_dir=run_dir/'probe';probe_dir.mkdir()
                probed=invoke(args,{'operation':'probe','input':req['input']},probe_dir)
                if probed.get('type')!='audio' or probed.get('duration_us',0)<=0:
                    raise ValueError('A finite local audio file is required')
                req['source_duration_us']=probed['duration_us']
                if req['source_in_us']+req['duration_us']>req['source_duration_us']:
                    raise ValueError('Requested audio source window exceeds its duration')
        except (ValueError,OSError) as error:
            raise CliError('invalid_edit_request',str(error))
    if args.editor_action == 'frame':
        from capcut_preview import prepare_frame
        try:
            req.update(prepare_frame(args, content))
        except FileExistsError as error:
            raise CliError('output_exists', str(error))
        except ValueError as error:
            raise CliError('invalid_frame', str(error))
    if args.editor_action in ('export', 'preview'):
        from capcut_export import prepare_export
        from capcut_preview import prepare_preview
        try:
            name = next(t['name'] for t in project_data['timelines'] if t['id'] == timeline)
            if sum(t.get('name') == name and not t.get('is_marked_delete') for t in project_data['timelines']) != 1:
                raise ValueError('Native frontend export currently requires a unique timeline name within the project')
            req.update((prepare_preview if args.editor_action == 'preview' else prepare_export)(args, content))
            req['project_id'] = json.loads((project / 'draft_meta_info.json').read_text(encoding='utf-8-sig'))['draft_id']
            req['timeline_name'] = next(t['name'] for t in project_data['timelines'] if t['id'] == timeline)
            req['output_dir_bytes'] = list(Path(req['stage_output']).parent.as_posix().encode('utf8'))
            req['output_parent_bytes'] = list(Path(req['output']).parent.as_posix().encode('utf8'))
            req['output_title_bytes'] = list(Path(req['stage_output']).stem.encode('utf8'))
        except FileExistsError as error:
            raise CliError("output_exists", str(error))
        except (ValueError, ImportError) as error:
            raise CliError("invalid_export", str(error))
    if args.editor_action in ("trim", "split", "move", "remove"):
        try:
            segment_id = str(uuid.UUID(args.segment)).upper()
        except ValueError:
            raise CliError("invalid_arguments", "--segment must be a UUID")
        req['segment_id'] = segment_id
        if args.editor_action == "trim":
            if not 0 <= args.in_us < args.out_us <= 2**53 - 1:
                raise CliError("invalid_range", "Require 0 <= --in-us < --out-us; values are absolute timeline positions")
            req.update(in_us=args.in_us, out_us=args.out_us)
        if args.editor_action == "split":
            points = args.points_us
            if len(points) > 100 or points != sorted(set(points)) or not all(0 < p <= 2**53 - 1 for p in points):
                raise CliError("invalid_range", "Use 1..100 distinct increasing positive split points, relative to the clip start")
            req['points_us'] = points
        if args.editor_action == "move":
            if not 0 <= args.start_us <= 2**53 - 1:
                raise CliError("invalid_range", "--start-us must be a nonnegative safe integer")
            req['start_us'] = args.start_us
    if args.editor_action == "add-timeline":
        name = args.name.strip()
        if not name or len(name.encode('utf8')) > 255 or any(ord(c) < 32 for c in name):
            raise CliError("invalid_arguments", "Timeline name must contain 1..255 UTF-8 bytes and no control characters")
        req.update(timeline_name=name, timeline_name_bytes=list(name.encode('utf8')),
                   render_index_track_mode_on=bool(content.get('render_index_track_mode_on', False)))
    if args.editor_action in ("undo", "redo"):
        if not 1 <= args.steps <= 100:
            raise CliError("invalid_arguments", "--steps must be between 1 and 100")
        req["steps"] = args.steps
    if args.editor_action in ("add-video", "add-track"):
        source = local_file(args.input)
        if any(ch in str(source) for ch in ('"', "\n", "\r", "\0")):
            raise CliError("invalid_arguments", "Unsupported characters in media path")
        probe_dir = run_dir / "probe"
        probe_dir.mkdir()
        probe = invoke(args, {"operation": "probe", "input": str(source)}, probe_dir)
        if probe.get("type") != "video" or probe.get("duration_us", 0) <= 0:
            raise CliError("invalid_media", "A finite-duration video is required")
        duration = args.duration_us if args.duration_us is not None else probe["duration_us"]
        if args.start_us < 0 or duration <= 0 or duration > probe["duration_us"] or args.start_us + duration > 2**53 - 1:
            raise CliError("invalid_range", "Start must be nonnegative; duration must fit the source video")
        resource = '"local:///' + source.as_posix() + '"'
        command = (f'--resource {resource} --start {args.start_us}us --duration {duration}us '
                   f'--width {probe["width"]}px --height {probe["height"]}px')
        req.update(action="add-video", new_track=args.editor_action == "add-track",
                   track=getattr(args, "track", 0), video_arguments=list(command.encode("utf8")))
    return req


def project_request(args, run_dir):
    if args.pid <= 0:
        raise CliError("invalid_arguments", "--pid must be positive")
    req = {"operation": "project", "action": args.project_action, "pid": args.pid}
    if args.project_action == "list":
        return req
    if args.project_action == "create":
        name = args.name.strip()
        if not name or len(name.encode('utf8')) > 100 or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name) or name.endswith('.'):
            raise CliError("invalid_arguments", "Use a valid project name of 1..100 UTF-8 bytes")
        req.update(project_name=name, project_name_bytes=list(name.encode('utf8')))
        return req
    project = Path(args.project).resolve() if args.project else None
    try:
        if args.project_id:
            project_id = str(uuid.UUID(args.project_id)).upper()
        else:
            meta = json.loads((project / 'draft_meta_info.json').read_text(encoding='utf-8-sig'))
            project_id = str(uuid.UUID(meta['draft_id'])).upper()
    except (OSError, ValueError, KeyError) as error:
        raise CliError("invalid_project", str(error))
    req.update(project=str(project) if project else None, project_id=project_id)
    if args.project_action in ('open', 'close'):
        return req
    source = local_file(args.input)
    probe_dir = run_dir / 'probe'
    probe_dir.mkdir()
    probe = invoke(args, {"operation": "probe", "input": str(source)}, probe_dir)
    if probe.get('type') != 'video' or probe.get('duration_us', 0) <= 0:
        raise CliError("invalid_media", "A finite-duration video is required")
    req.update(input=str(source),
               media_path_bytes=list(source.as_posix().encode('utf8')),
               file_name_bytes=list(source.name.encode('utf8')),
               duration_us=probe['duration_us'], width=probe['width'], height=probe['height'])
    return req


def main(argv=None):
    run_dir = stage = None
    operation = None
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        operation = args.operation
        if not 1 <= args.timeout <= 300:
            raise CliError("invalid_arguments", "--timeout must be between 1 and 300 seconds")
        if operation == "capabilities":
            result = {"backend": "CapCut 9.5.0.4050 original native APIs; local FFmpeg for media frame/preview",
                      "operations": ["capabilities", "version", "help", "probe", "convert-image", "media", "editor", "project"],
                      "editorActions": ["sessions", "inspect", "add-video", "add-track", "add-timeline", "switch-timeline", "trim", "split", "move", "remove", "undo", "redo", "export", "frame", "preview", "add-audio", "captions-import", "set-clip"],
                      "mediaActions": ['frame', 'preview'],
                      "mediaBackend": 'Local FFmpeg decoding for media files; no project or timeline required',
                      "videoExport": "Native CapCut H.264 MP4; explicit active timeline; full duration; canvas size/fps by default; independent probe/full decode; no overwrite",
                      "timelineFrame": "Native draft video extract-frames / VideoClient, composed PNG; no whole-timeline export; requested and native timeline timestamps returned",
                      "timelinePreview": "Native export-range API + renderer; exact engine range checked; original export range restored; recovery record saved before change; no full-export crop fallback",
                      "audioEditing": "Local audio, source-in/target range, gain and fades; native auto-placement; final range within existing timeline",
                      "captionEditing": "UTF-8 SRT/timeline_us JSON to editable native subtitles; basic native-unit style and position; default font; no ASR",
                      "clipProperties": "Absolute video transform/crop/opacity/gain; audio gain/fades; speed only on a sole ordinary video at time zero; no keyframes",
                      "mutationReceipts": "Optional request-id, durable per-step receipts, partial/unknown outcomes; successful replay checks affected current items without rerunning commands",
                      "mediaFrame": "First decoded video frame at or after at-us; actualAtUs and source PTS returned; full PNG decode verified",
                      "mediaPreview": "Frames in [start-us,end-us), rebased to effectiveStartUs; H.264/AAC, VFR timing retained; audio trim and AAC padding reported; full decode verified",
                      "projectActions": ["create", "open", "close", "import-media", "list"],
                      "projectRequirements": "Create/open require the homepage. Close saves and returns the actual path. Media-bin import requires a closed registered project; videos only",
                      "notYetSupported": ["empty-track-create"],
                      "editorRequirements": "CapCut must have the requested project/timeline open; explicit PID and project path are required",
                      "clipEditing": "trim/split: ordinary speed-1 videos; split points relative to clip, trim boundaries absolute before edit. Native main-track snapping may close gaps. Free move requires a nonmagnetic video layer. Source/target times are verified after autosave",
                      "addTrackBehavior": "Creates the next video render layer with its first clip; empty tracks are not supported. Multiple visual layers can share a stored track container",
                      "helpTopics": list(TOPICS), "imageFormats": ["jpg", "jpeg", "png"],
                      "scope": "Local media in an isolated worker; editor operations call original native functions in the selected running process",
                      "overwrites": False, "mediaWorkerIsolation": True,
                      "editorExecution": "In the selected CapCut process; worker isolation does not isolate CapCut from native faults"}
        elif operation == "help" and args.topic in ("root", "editor", "project", "media"):
            result = {"text": WRAPPER_HELP, "source": "adapter"}
        else:
            request = {"operation": operation}
            if operation == "help":
                request["topic"] = args.topic
            if operation in ("probe", "convert-image"):
                source = local_file(args.input)
                request["input"] = str(source)
            if operation == "convert-image":
                output = Path(args.output).resolve()
                if output == source:
                    raise CliError("same_path", "Input and output must be different paths")
                if output.exists():
                    raise CliError("output_exists", f"Output already exists: {output}")
                if not output.parent.is_dir():
                    raise CliError("output_directory_missing", f"Output directory does not exist: {output.parent}")
                fmt = args.format or output.suffix.lower().lstrip(".")
                if fmt not in ("jpg", "jpeg", "png"):
                    raise CliError("invalid_format", "Use --format jpg/jpeg/png or an appropriate output suffix")
                stage = output.parent / (".capcut-agent-" + uuid.uuid4().hex + "." + fmt)
                request.update(output=str(stage), format=fmt)
            run_dir = ROOT / ".runtime" / ("capcut-agent-" + uuid.uuid4().hex)
            run_dir.mkdir(parents=True)
            if operation == "editor":
                request = editor_request(args, run_dir)
            if operation == "project":
                request = project_request(args, run_dir)
            if operation == 'media':
                from capcut_media import prepare_media, execute_media
                args.action = args.media_action
                try:
                    request = prepare_media(args)
                    (run_dir / 'request.json').write_text(json.dumps(request, ensure_ascii=False), encoding='utf8')
                    result = execute_media(request)
                except FileExistsError as error:
                    raise CliError('output_exists', str(error))
                except (ValueError, FileNotFoundError) as error:
                    raise CliError('invalid_media_request', str(error))
                except TimeoutError as error:
                    raise CliError('media_timeout', str(error))
            else:
                result = invoke(args, request, run_dir)
            if stage is not None:
                if not stage.is_file() or stage.stat().st_size == 0:
                    raise CliError("native_no_output", "Native conversion did not produce an image")
                # Atomic publication fails if another process creates output meanwhile.
                try:
                    os.link(stage, output)
                except FileExistsError:
                    raise CliError("output_exists", f"Output already exists: {output}")
                result["output"] = str(output)
        response = {"ok": True, "operation": operation, "result": result}
        code = 0
    except CliError as error:
        response = {"ok": False, "operation": operation, "error": {"code": error.code, "message": error.message}}
        if error.details is not None:response['error'].update(error.details)
        code = 2
    except Exception as error:
        response = {"ok": False, "operation": operation, "error": {"code": "internal_error", "message": str(error)}}
        code = 1
    finally:
        if stage is not None and stage.is_file():
            try:
                stage.unlink()
            except OSError as error:
                # Keep the JSON contract even if another process locks the temporary image.
                response["cleanupWarning"] = f"Could not remove temporary image {stage}: {error}"
    if run_dir is not None:
        response["logs"] = str(run_dir)
    print(json.dumps(response, ensure_ascii=False))
    return code


if __name__ == "__main__":
    # Agent consumers decode stdout as UTF-8 even on Windows with a legacy code page.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
