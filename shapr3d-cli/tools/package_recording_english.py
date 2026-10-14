"""English, command-first edition of the existing Shapr3D recording.

Matches the CapCut/Axure application-above-terminal layout. CLI lines are
PowerShell equivalents of verified native requests, not a new execution.
"""
import argparse
import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from package_recording import ROOT, FFMPEG, load, save, sha, read_exact, run

SIZE, TOP, FPS, TAIL = (1920, 1440), 1020, 15, 7
BG, CYAN, WHITE, GREEN, MUTED = '#111827', '#67E8F9', '#FFFFFF', '#86EFAC', '#A5B4C8'


def ps_quote(value):
    return "'" + value.replace("'", "''") + "'"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    src, work, output = [getattr(args, k).resolve() for k in ('source', 'work', 'output')]
    if any(p.drive.upper() != 'D:' for p in (src, work, output)):
        raise ValueError('D: storage is required')
    if output.exists():
        raise FileExistsError(output)
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = Path('D:/Caches/Shapr3D/Temp'); cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(cache), TMP=str(cache), PYTHONDONTWRITEBYTECODE='1')
    job, drill = load(src / 'job.json'), load(src / 'drill/job.json')
    video = src / 'full-build.mp4'
    source_sha = sha(video)
    if source_sha != load(ROOT / 'evidence/visible-drill-proof-20261013.json')['recording']['sha256']:
        raise ValueError('Original recording hash changed')
    geometry = load(work / 'geometry-verification.json')
    if not geometry['passed'] or geometry['source']['sha256'] != sha(src / 'drill/after.stl'):
        raise ValueError('Matching geometry acceptance is required')
    groups, receipts = [], []
    for group in (job, drill):
        rows = []
        for item in group['receipts']:
            path = Path(item['receipt']); receipt = load(path)
            if not receipt['ok'] or receipt['result'] != item['result'] or receipt['request']['operation'] != item['operation']:
                raise ValueError('Receipt mismatch: ' + str(path))
            row = dict(path=str(path), sha256=sha(path), **receipt)
            rows.append(row); receipts.append(row)
        groups.append(rows)
    b, d = groups
    specs = [
        ('EMPTY MODEL / CLI SESSION', [], 'OK | Empty model ready; previous demonstration backed up.'),
        ('IMPORT A RECTANGLE + TWO CIRCLES', b[5:6], 'OK | Native DXF import | Plate: 80 x 40 mm | Mounting holes: diameter 6 mm'),
        ('EXTRUDE THE PLATE', b[6:9], 'OK | Shapr3D native extrusion | Thickness: 4 mm'),
        ('EDIT THE HISTORY PARAMETER', b[9:12], 'OK | Thickness updated: 4 -> 6 mm'),
        ('MOVE THE RIGHT HOLE', b[12:16], 'OK | Right cylindrical face moved +5 mm | Hole center X: +30 mm'),
        ('MOVE THE LEFT HOLE', b[16:20], 'OK | Left cylindrical face moved -5 mm | Hole spacing: 50 -> 60 mm'),
        ('IMPORT THE CENTER CIRCLE', d[5:6], 'OK | New circle: diameter 8 mm | Center: (0, 0, 6) mm'),
        ('SELECT THE EXACT CIRCULAR REGION', d[6:10], 'OK | Inside/outside ray comparison | Native region selected by exact ID'),
        ('CUT A 2 mm POCKET', d[10:11], 'OK | Native subtractive extrusion | Depth: 2 mm'),
        ('DEEPEN THE POCKET TO 4 mm', d[11:14], 'OK | Committed feature updated through native history | Depth: 4 mm'),
        ('CREATE THE THROUGH HOLE', d[14:15], 'OK | Cut depth: 8 mm through a 6 mm plate | Center hole: diameter 8 mm'),
        ('EXPORT THE NATIVE MODEL AND STL', d[15:18], 'OK | Native exports: after.shapr + after.stl | Editable model + printable mesh'),
    ]
    variables = {'S': job['session'].replace('\\', '/'),
                 'PLATE': job['nativeDirectory'].replace('\\', '/'),
                 'DRILL': drill['nativeDirectory'].replace('\\', '/')}

    def command(request):
        # Keep localized history identifiers byte-for-byte in JSON via Unicode
        # escapes. Path aliases are real PowerShell variables, not placeholders
        # inside a quoted JSON string that would fail to expand.
        if 'path' in request or 'directory' in request:
            items = []
            for key, value in request.items():
                normalized = value.replace('\\', '/') if isinstance(value, str) else value
                alias = next((k for k in ('PLATE', 'DRILL') if isinstance(normalized, str) and
                              (normalized == variables[k] or normalized.startswith(variables[k] + '/'))), None)
                encoded = ('"$' + alias + normalized[len(variables[alias]):] + '"') if alias else ps_quote(str(value))
                items.append(key + '=' + encoded)
            payload = '(@{' + '; '.join(items) + '} | ConvertTo-Json -Compress)'
        else:
            payload = ps_quote(json.dumps(request, ensure_ascii=True, separators=(',', ':')))
        return 'python -B shapr3d-cli/pilot.py call --session $S --json ' + payload

    events = job['recording']['events']
    if len(events) != len(specs) or job['recording']['exitCode'] != 0:
        raise ValueError('Invalid recording phases')
    phases = []
    for i, (event, (title, rows, status)) in enumerate(zip(events, specs)):
        commands = [command(row['request']) for row in rows]
        if not commands:
            commands = ['$' + key + ' = ' + ps_quote(value) for key, value in variables.items()]
        phases.append(dict(index=i + 1, title=title, sourceSeconds=event['seconds'],
                           commands=commands, status=status, receipts=[row['path'] for row in rows]))
    verify_command = ('python -B shapr3d-cli/verify_drilled_plate.py "' + str(src / 'drill/after.stl').replace('\\', '/') +
                      '" --before "' + str(src / 'drill/before.stl').replace('\\', '/') + '" --out "' +
                      str(work / 'geometry-verification.json').replace('\\', '/') + '"')
    transcript = [
        '# PowerShell CLI equivalents of recorded native requests; NOT re-executed for this edit.',
        '# Original recording: 2026-10-13. Readable command groups align with completed stages.',
        '# Saved IDs and output names describe that original session. Do not replay blindly.',
    ]
    for phase in phases:
        transcript += ['', '# ' + phase['title'], *phase['commands']]
    transcript += ['', '# Independent verification (executed for this edition)', verify_command]
    (work / 'cli-transcript.ps1').write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    save(work / 'commands.json', dict(variables=variables, phases=phases, receipts=receipts,
         displayMethod='Full PowerShell CLI equivalents of original requests; appended in post-production.',
         timing='Groups change at recorded stage-completion markers. Not request-start timestamps.'))
    face = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 23)
    heading = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 26)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 19)

    def footer(phase, elapsed, validation=False):
        canvas = Image.new('RGB', SIZE, BG); draw = ImageDraw.Draw(canvas)
        draw.text((24, TOP + 16), f'REVERSE-CLI  |  Shapr3D native modeling  |  {elapsed:06.1f}s  |  No mouse input', font=heading, fill=CYAN)
        draw.text((24, TOP + 57), ('VERIFICATION' if validation else f'STEP {phase["index"]:02d}/12') + '  |  ' + phase['title'], font=face, fill=MUTED)
        lines = []
        for cmd in phase['commands']:
            lines += textwrap.wrap('> ' + cmd, width=134, subsequent_indent='  ', break_long_words=True, break_on_hyphens=False)
        if len(lines) > 9:
            raise ValueError(f'Too many command lines ({len(lines)}): {phase["title"]}')
        for i, line in enumerate(lines):
            if face.getlength(line) > 1872:
                raise ValueError('Command line exceeds the canvas')
            draw.text((24, TOP + 97 + i * 27), line, font=face, fill=WHITE)
        draw.text((24, 1366), phase['status'], font=face, fill=GREEN)
        note = ('Verification of the recorded export | Final native frame held on screen | No new modeling run' if validation else
                'CLI syntax from recorded requests | Grouped by completed stage | Original footage at 1x')
        draw.text((24, 1410), note, font=small, fill=MUTED)
        return canvas

    # Preflight all command panels before writing the MP4.
    for phase in phases:
        footer(phase, phase['sourceSeconds'])
    verification = dict(index=13, title='78/78 GEOMETRY CHECKS PASSED', commands=[verify_command,
        '# 80 x 40 x 6 mm | Mounting holes: diameter 6 mm, pitch 60 mm | Center: diameter 8 mm through hole',
        '# 1 connected solid | Closed manifold | 188 triangles | Euler characteristic: -4'],
        status='OK | Native Low-resolution STL validated | MP4 decode and frame checks follow packaging')
    footer(verification, 49, validation=True)
    log = (work / 'render.log').open('wb')
    encoder = subprocess.Popen([str(FFMPEG), '-hide_banner', '-loglevel', 'warning', '-n', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', '1920x1440', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
        '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30', '-fps_mode', 'cfr',
        '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE, stdout=log, stderr=log,
        env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    decoder = subprocess.Popen([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-i', str(video),
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, stderr=log,
        env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    frames, sampled, bounds = 0, set(), None
    try:
        while True:
            raw = read_exact(decoder.stdout, 1026 * 802 * 3)
            if not raw:
                break
            if len(raw) != 1026 * 802 * 3:
                raise ValueError('Truncated source frame')
            t = frames / FPS
            index = max(i for i, phase in enumerate(phases) if phase['sourceSeconds'] <= t)
            frame = footer(phases[index], t)
            pixels = ImageOps.contain(Image.frombytes('RGB', (1026, 802), raw), (1920, TOP), Image.Resampling.LANCZOS)
            x, y = (1920 - pixels.width) // 2, (TOP - pixels.height) // 2
            frame.paste(pixels, (x, y)); bounds = [x, y, pixels.width, pixels.height]
            if index not in sampled and t >= phases[index]['sourceSeconds'] + .7:
                frame.save(work / f'phase-{index:02d}.png'); sampled.add(index)
            encoder.stdin.write(frame.tobytes()); frames += 1
        if decoder.wait() != 0 or frames != 735:
            raise ValueError('Unexpected source frame count')
        for i in range(TAIL * FPS):
            frame = footer(verification, 49 + i / FPS, validation=True)
            frame.paste(pixels, (x, y))
            if i == 0:
                frame.save(work / 'verification-frame.png')
            encoder.stdin.write(frame.tobytes())
    finally:
        decoder.stdout.close()
        if decoder.poll() is None:
            decoder.terminate(); decoder.wait()
        encoder.stdin.close(); encoder.wait(); log.close()
    if encoder.returncode:
        raise RuntimeError('Video encoding failed')
    decoded = run(['-loglevel', 'error', '-xerror', '-i', str(output), '-progress', 'pipe:1', '-f', 'null', '-'], env)
    (work / 'decode.log').write_bytes(decoded.stdout + decoded.stderr)
    actual_frames = int(re.findall(rb'frame=(\d+)', decoded.stdout)[-1])
    actual_seconds = int(re.findall(rb'out_time_us=(\d+)', decoded.stdout)[-1]) / 1e6
    report = dict(schemaVersion=2, passed=decoded.returncode == 0 and actual_frames == 1680 and actual_seconds == 56,
        output=dict(path=str(output), sha256=sha(output), bytes=output.stat().st_size, width=1920, height=1440,
                    fps=30, seconds=actual_seconds, decodedFrames=actual_frames),
        source=dict(path=str(video), sha256=source_sha, frames=frames, seconds=49, fps=15, cropBoundsInOutput=bounds),
        presentation=dict(language='English', introSeconds=0, layout='Native app above dark command footer',
                          font='Consolas 23 / 26 px', rawFootageSpeed=1, verificationHoldSeconds=TAIL,
                          receiptCount=len(receipts), displayedNativeCommands=sum(len(p['receipts']) for p in phases),
                          cliDisplay='PowerShell equivalents reconstructed from verified requests; not re-executed.',
                          originalUiLanguage='Chinese, unchanged original application pixels'),
        checks=dict(decodeExitCode=decoded.returncode, sourceUnchanged=sha(video) == source_sha,
                    allReceiptsMatch=True, geometryPassed=geometry['passed'], geometryChecks=len(geometry['checks']),
                    commandsFitWithoutTruncation=True), visualReview='pending')
    save(work / 'verification.json', report)
    save(work / 'chapters.json', dict(phases=phases, verificationStart=49, introSeconds=0))
    print(json.dumps(report['output']))
    if not report['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
