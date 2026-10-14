"""Local-file frame/preview tools. FFmpeg decodes media; no CapCut claims here.

Times are relative to the first decoded video presentation timestamp. A frame
request selects the first video frame whose timestamp is >= the request. Preview
includes frames in [start, end), starts at the actual selected first frame,
preserves VFR timestamp differences, and trims audio at sample boundaries.
Encoded AAC can contain a final partially padded AAC packet.
"""
from fractions import Fraction
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from reverse_cli.config import ffmpeg
DECODER = ffmpeg('capcut') or ROOT / '.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
_VIDEO = re.compile(r'\bn:\s*\d+\s+pts:\s*(-?\d+)\s+pts_time:\S+\s+'
                    r'duration:\s*(\d+)\s+duration_time:\S+\s+fmt:\S+.*?\bs:(\d+)x(\d+)')
_TIMEBASE = re.compile(r'config in time_base:\s*(\d+)/(\d+)')
_AUDIO = re.compile(r'\bpts:\s*(-?\d+)\s+pts_time:\S+\s+fmt:\S+.*?\brate:(\d+)\s+nb_samples:(\d+)')


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**53 - 1:
        raise ValueError(f'{name} must be a nonnegative integer in microseconds')
    return value


def _local_path(value, name):
    raw = str(value)
    # No URL, UNC server, device path, or named-pipe input. -protocol_whitelist
    # below also protects nested local demuxers from opening network protocols.
    if not raw or '://' in raw or raw.startswith(('\\\\', '//')) or '\0' in raw:
        raise ValueError(f'{name} must be a local filesystem path')
    if ':' in raw[2:] or (':' in raw and not re.match(r'^[A-Za-z]:[\\/]', raw)):
        raise ValueError(f'{name} must be a local filesystem path, not a protocol or alternate stream')
    return Path(raw).resolve()


def prepare_media(args):
    """Validate CLI arguments without creating files; return a serializable request."""
    action = getattr(args, 'action', None) or getattr(args, 'media_action', None)
    if action not in ('frame', 'preview'):
        raise ValueError('Media action must be frame or preview')
    source = _local_path(args.input, 'Input')
    output = _local_path(args.output, 'Output')
    if source == output:
        raise ValueError('Input and output must be different files')
    if not source.is_file():
        raise ValueError(f'Input file does not exist: {source}')
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    if not output.parent.is_dir():
        raise ValueError(f'Output directory does not exist: {output.parent}')
    if os.name == 'nt' and output.drive.lower() != 'd:':
        raise ValueError('Media outputs and temporary files must be on D:')
    suffix = '.png' if action == 'frame' else '.mp4'
    if output.suffix.lower() != suffix:
        raise ValueError(f'{action} output must have a {suffix} suffix')
    timeout = getattr(args, 'timeout', 60)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Media timeout must be a positive finite number')
    decoder = DECODER.resolve()
    if not decoder.is_file():
        raise ValueError(f'The installed local FFmpeg executable is missing: {decoder}')
    req = {'action': action, 'input': str(source), 'output': str(output),
           'decoder': str(decoder), 'timeout': timeout,
           'deadline_monotonic': getattr(args, 'deadline_monotonic', None) or time.monotonic() + timeout}
    if action == 'frame':
        req['at_us'] = _integer(args.at_us, '--at-us')
    else:
        req['start_us'] = _integer(args.start_us, '--start-us')
        req['end_us'] = _integer(args.end_us, '--end-us')
        if req['end_us'] <= req['start_us']:
            raise ValueError('Preview requires --end-us greater than --start-us')
    return req


def _remaining(req):
    remaining = req['deadline_monotonic'] - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Media operation exceeded its total timeout')
    return remaining


def _run(req, args, work, label):
    """Keep potentially large frame logs on D:, not in subprocess pipe memory."""
    log = work / (label + '.log')
    env = dict(os.environ, TEMP=str(work), TMP=str(work), TMPDIR=str(work))
    with log.open('wb') as errors:
        result = subprocess.run([req['decoder'], '-hide_banner', '-nostdin', '-nostats', '-xerror',
                                 '-loglevel', 'info', '-protocol_whitelist', 'file,pipe', *args],
                                stdout=subprocess.DEVNULL, stderr=errors, env=env,
                                timeout=_remaining(req), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        with log.open('rb') as stream:
            stream.seek(max(0, log.stat().st_size - 5000))
            diagnostic = stream.read().decode('utf8', 'replace')
        raise ValueError(f'FFmpeg {label} failed: {diagnostic}')
    return log


def _ceil(value):
    return -((-value.numerator) // value.denominator)


def _round(value):
    """Match av_rescale_q's nearest/away-from-zero rounding."""
    return (2 * value.numerator + value.denominator) // (2 * value.denominator) if value >= 0 else -_round(-value)


def _pts_digest(values):
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode('ascii') + b'\n')
    return digest.hexdigest()


def _read_video(log):
    """Yield actual integer PTS and rational time base, never guessed CFR indices."""
    timebase = None
    with log.open(encoding='utf8', errors='replace') as stream:
        for line in stream:
            match = _TIMEBASE.search(line)
            if match:
                timebase = Fraction(int(match[1]), int(match[2]))
            # Audio and video av_log calls can share a physical line. Require
            # the contiguous video-specific fields; never pair an earlier audio
            # PTS with a later video's duration. More than one data row may fit.
            for match in _VIDEO.finditer(line):
                if timebase is None:
                    raise ValueError('FFmpeg did not report the video time base')
                pts, duration, width, height = map(int, match.groups())
                yield {'pts': pts, 'duration': duration, 'timebase': timebase, 'width': width, 'height': height}


def _read_audio(log):
    with log.open(encoding='utf8', errors='replace') as stream:
        for line in stream:
            # FFmpeg can interleave the verbose video side-data dump with the
            # audio prefix. The complete audio data row still has a unique shape.
            for match in _AUDIO.finditer(line):
                pts, rate, samples = map(int, match.groups())
                yield {'pts': pts, 'rate': rate, 'samples': samples}


def _inspect(req, path, work, label):
    # Decoder timestamps are retained, including nonzero stream starts. Request
    # times are translated from the first video PTS rather than rounded headers.
    log = _run(req, ['-copyts', '-i', str(path), '-map', '0:v:0', '-map', '0:a:0?',
                     '-vf', 'sidedata=mode=delete,showinfo=checksum=0', '-af', 'ashowinfo', '-fps_mode', 'passthrough',
                     '-f', 'null', '-'], work, label)
    first = last = None
    frames = 0
    for frame in _read_video(log):
        if first is None:
            first = frame
        if last is not None and frame['pts'] * frame['timebase'] < last['pts'] * last['timebase']:
            raise ValueError('Video presentation timestamps are not monotonic')
        if frame['timebase'] != first['timebase'] or (frame['width'], frame['height']) != (first['width'], first['height']):
            raise ValueError('Changing time bases or frame dimensions are not supported')
        last = frame
        frames += 1
    if first is None:
        raise ValueError('Input has no decodable video frames')
    if last['duration'] <= 0:
        raise ValueError('Final frame duration is unavailable; cannot safely establish media bounds')
    audio_first = audio_last = None
    samples = 0
    for audio in _read_audio(log):
        if audio_first is None:
            audio_first = audio
        if audio['rate'] != audio_first['rate']:
            raise ValueError('Changing audio sample rates are not supported')
        audio_last = audio
        samples += audio['samples']
    return {'log': log, 'first': first, 'last': last, 'frames': frames,
            'audio_first': audio_first, 'audio_last': audio_last, 'audio_samples': samples}


def _frame_time(frame):
    return frame['pts'] * frame['timebase']


def _video_end(info):
    return (info['last']['pts'] + info['last']['duration']) * info['last']['timebase']


def _signature(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _frame_result(req, source_info, stage, work):
    origin = _frame_time(source_info['first'])
    wanted = origin + Fraction(req['at_us'], 1000000)
    if wanted >= _video_end(source_info):
        raise ValueError('Requested frame is outside the video presentation range')
    chosen = next((frame for frame in _read_video(source_info['log']) if _frame_time(frame) >= wanted), None)
    if chosen is None:
        raise ValueError('No video frame has a PTS at or after the requested time; choose an earlier --at-us')
    selected_log = _run(req, ['-copyts', '-i', req['input'], '-map', '0:v:0', '-an',
                             '-vf', f"select=eq(pts\\,{chosen['pts']}),showinfo", '-frames:v', '1',
                             '-fps_mode', 'passthrough', '-c:v', 'png', '-update', '1', '-y', str(stage)],
                        work, 'extract-frame')
    actual = next(_read_video(selected_log), None)
    if actual is None or actual['pts'] != chosen['pts'] or actual['timebase'] != chosen['timebase']:
        raise ValueError('Decoded frame did not match the selected source presentation timestamp')
    image = _inspect(req, stage, work, 'verify-png')
    if image['frames'] != 1 or (image['first']['width'], image['first']['height']) != (chosen['width'], chosen['height']):
        raise ValueError('PNG dimensions or complete decode did not match the source frame')
    relative = _frame_time(chosen) - origin
    return {'requestedAtUs': req['at_us'], 'actualAtUs': _round(relative * 1000000),
            'sourceFramePts': chosen['pts'], 'sourceTimeBase': str(chosen['timebase']),
            'sourceFirstVideoPts': source_info['first']['pts'], 'width': chosen['width'], 'height': chosen['height'],
            'format': 'png', 'decodedFrames': 1, 'fullDecodeVerified': True,
            'selection': 'first frame with presentation time >= requested time',
            'timeOrigin': 'first decoded video presentation timestamp',
            'timestampRounding': 'actualAtUs rounded to nearest microsecond; sourceFramePts/sourceTimeBase are exact'}


def _preview_result(req, source_info, stage, work):
    origin = _frame_time(source_info['first'])
    start = origin + Fraction(req['start_us'], 1000000)
    end = origin + Fraction(req['end_us'], 1000000)
    if end > _video_end(source_info):
        raise ValueError('Preview interval extends beyond the video presentation range')
    selected_first = selected_last = None
    expected_count = 0
    expected_hash = hashlib.sha256()
    for frame in _read_video(source_info['log']):
        if start <= _frame_time(frame) < end:
            if selected_first is None:
                selected_first = frame
                effective_start = _frame_time(frame)
                shift = _round(effective_start * 1000000)
            selected_last = frame
            expected_count += 1
            expected_hash.update(str(_round(_frame_time(frame) * 1000000) - shift).encode('ascii') + b'\n')
    if selected_first is None:
        raise ValueError('Preview interval contains no video presentation timestamps')
    effective_duration_us = _round(end * 1000000) - shift
    width, height = source_info['first']['width'], source_info['first']['height']
    if width % 2 or height % 2:
        raise ValueError('H.264 preview requires even source dimensions')
    timebase = source_info['first']['timebase']
    # trim in original integer ticks BEFORE settb, so rounding to microseconds
    # cannot accidentally include a frame just outside the requested interval.
    video_filter = (f'trim=start_pts={_ceil(start / timebase)}:end_pts={_ceil(end / timebase)},'
                    f'settb=1/1000000,setpts=PTS-({shift})')
    expected_audio_samples = 0
    for audio in _read_audio(source_info['log']):
        sample_start = max(audio['pts'], _ceil(effective_start * audio['rate']))
        sample_end = min(audio['pts'] + audio['samples'], _ceil(end * audio['rate']))
        expected_audio_samples += max(0, sample_end - sample_start)
    has_audio = expected_audio_samples > 0
    final_pts = _round(_frame_time(selected_last) * 1000000) - shift
    final_duration = effective_duration_us - final_pts
    # libx264 with a microsecond encoder clock can emit zero packet durations.
    # With B frames disabled, packet order is presentation order; setts supplies
    # each real next-PTS interval and clips the last display duration at end.
    packet_duration = f'setts=duration=if(gt(NEXT_PTS\\,PTS)\\,NEXT_PTS-PTS\\,{final_duration})'
    args = ['-copyts', '-i', req['input'], '-map', '0:v:0', '-vf', video_filter,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
            '-fps_mode', 'passthrough', '-enc_time_base:v', '1:1000000', '-bf', '0', '-bsf:v', packet_duration,
            '-video_track_timescale', '1000000', '-movie_timescale', '1000000']
    if has_audio:
        rate = source_info['audio_first']['rate']
        # Audio filter PTS use the sample clock (1 / sample rate). Subtracting
        # the same requested start preserves A/V timing and stream offsets.
        args += ['-map', '0:a:0', '-af',
                 f'atrim=start_pts={_ceil(effective_start * rate)}:end_pts={_ceil(end * rate)},asetpts=PTS-({_round(effective_start * rate)})',
                 '-c:a', 'aac', '-b:a', '192k']
    else:
        args += ['-an']
    args += ['-t', f"{effective_duration_us / 1000000:.6f}",
             '-map_metadata', '-1', '-movflags', '+faststart', '-y', str(stage)]
    _run(req, args, work, 'encode-preview')
    actual = _inspect(req, stage, work, 'verify-preview')
    actual_hash = _pts_digest(_round(_frame_time(frame) * 1000000) for frame in _read_video(actual['log']))
    if actual['frames'] != expected_count or actual_hash != expected_hash.hexdigest():
        raise ValueError('Preview frame count or presentation timestamps differ from the requested source interval')
    if abs(_round(_video_end(actual) * 1000000) - effective_duration_us) > 1:
        raise ValueError('Preview final display duration does not end at the requested boundary')
    if (actual['first']['width'], actual['first']['height']) != (width, height):
        raise ValueError('Preview dimensions changed during encoding')
    if bool(actual['audio_first']) != has_audio:
        raise ValueError('Preview audio presence differs from the requested source interval')
    audio_result = {'hasAudio': has_audio}
    if has_audio:
        rate = actual['audio_first']['rate']
        audio_start = Fraction(actual['audio_first']['pts'], rate)
        audio_end = Fraction(actual['audio_last']['pts'] + actual['audio_last']['samples'], rate)
        wanted_duration = end - effective_start
        # AAC works in 1024-sample frames. A container can retain a partial final
        # packet; explicitly report measured decoded padding, never call it exact.
        if (audio_start < -Fraction(1, rate) or audio_end > wanted_duration + Fraction(1024, rate)
                or not expected_audio_samples <= actual['audio_samples'] <= expected_audio_samples + 1024):
            raise ValueError('Preview decoded audio exceeds the requested sample range plus one AAC padding packet: '
                             f'first={float(audio_start)}, end={float(audio_end)}, wanted={float(wanted_duration)}, '
                             f'samples={actual["audio_samples"]}, expected={expected_audio_samples}, rate={rate}')
        audio_result.update({'audioCodec': 'aac', 'audioSampleRate': rate,
                             'trimmedSourceAudioSamples': expected_audio_samples,
                             'decodedAudioSamples': actual['audio_samples'],
                             'aacPaddingSamples': actual['audio_samples'] - expected_audio_samples,
                             'firstAudioPtsUs': _round(audio_start * 1000000),
                             'decodedAudioEndUs': _round(audio_end * 1000000)})
    return {'requestedStartUs': req['start_us'], 'requestedEndUs': req['end_us'],
            'requestedDurationUs': req['end_us'] - req['start_us'],
            'effectiveStartUs': _round((effective_start - origin) * 1000000),
            'previewDurationUs': effective_duration_us,
            'sourceFirstFramePts': selected_first['pts'], 'sourceLastFramePts': selected_last['pts'],
            'sourceTimeBase': str(timebase), 'sourceFirstVideoPts': source_info['first']['pts'],
            'firstSourceFrameAtUs': _round((_frame_time(selected_first) - origin) * 1000000),
            'lastSourceFrameAtUs': _round((_frame_time(selected_last) - origin) * 1000000),
            'firstOutputFramePtsUs': _round(_frame_time(actual['first']) * 1000000),
            'lastOutputFramePtsUs': _round(_frame_time(actual['last']) * 1000000),
            'decodedVideoEndUs': _round(_video_end(actual) * 1000000),
            'width': width, 'height': height, 'format': 'mp4', 'videoCodec': 'h264',
            'decodedFrames': actual['frames'], 'fullDecodeVerified': True,
            'presentationTimestampsVerified': True, 'presentationTimestampsSha256': actual_hash,
            'selection': 'video frame timestamps in [start, end); actual first selected frame becomes output time zero; audio follows that same start',
            'timeOrigin': 'first decoded video presentation timestamp',
            'endSemantics': 'last video display duration ends at the requested boundary; decoded AAC padding is reported',
            **audio_result}


def execute_media(req):
    """Execute a prepared media request and publish atomically without overwrite."""
    source, output = Path(req['input']), Path(req['output'])
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    signature = _signature(source)
    result = None
    # Every subprocess scratch/log/partial artifact is below the final D: parent.
    with tempfile.TemporaryDirectory(prefix='.capcut-media-', dir=output.parent) as folder:
        work = Path(folder)
        stage = work / ('frame.png' if req['action'] == 'frame' else 'preview.mp4')
        info = _inspect(req, source, work, 'inspect-source')
        if req['action'] == 'frame':
            result = _frame_result(req, info, stage, work)
        elif req['action'] == 'preview':
            result = _preview_result(req, info, stage, work)
        else:
            raise ValueError('Unknown media request action')
        _remaining(req)
        if _signature(source) != signature:
            raise ValueError('Source media changed while it was being decoded; result was not published')
        if not stage.is_file() or stage.stat().st_size < 64:
            raise ValueError('Media operation did not create a valid output file')
        with stage.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        # Atomic no-clobber publication protects against a competing writer after
        # the initial check. Source and destination are guaranteed on the same disk.
        os.link(stage, output)
        result.update({'action': req['action'], 'input': str(source), 'output': str(output),
                       'sizeBytes': output.stat().st_size, 'sha256': digest,
                       'backend': 'FFmpeg local-media decode' if req['action'] == 'frame' else 'FFmpeg local-media trim/re-encode',
                       'sourceDecodedFrames': info['frames'],
                       'sourceVideoDurationUs': _round((_video_end(info) - _frame_time(info['first'])) * 1000000)})
    return result
