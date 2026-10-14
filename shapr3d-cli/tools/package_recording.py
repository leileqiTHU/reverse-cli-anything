"""Package an existing native recording with its real CLI request receipts.

No application control: original footage stays continuous, in order, at 1x.
Request panels appear at the recorded stage-completion markers, not at invented
keypress/submission times. Full requests and their hashes accompany the video.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
FFMPEG = REPO / 'capcut-cli/.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
FPS, SIZE, INTRO, OUTRO = 15, (1920, 1080), 5, 9
BG, PANEL, WHITE, MUTED, CYAN, GREEN = '#0b1220', '#121e30', '#edf3fb', '#a2b1c5', '#64d9ee', '#79e1b5'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, mono=False, bold=False):
    name = ('consolab.ttf' if bold else 'consola.ttf') if mono else ('msyhbd.ttc' if bold else 'msyh.ttc')
    return ImageFont.truetype(str(Path(os.environ['WINDIR']) / 'Fonts' / name), size)


def wrapped(text, face, width):
    result = []
    for para in text.splitlines():
        line = ''
        for char in para:
            if face.getlength(line + char) > width:
                split = line.rfind(' ')
                if split > len(line) // 3:
                    result.append(line[:split])
                    line = '  ' + line[split + 1:] + char
                else:
                    result.append(line)
                    line = '  ' + char
            else:
                line += char
        result.append(line)
    return result


def read_exact(stream, size):
    chunks, remaining = [], size
    while remaining:
        data = stream.read(remaining)
        if not data:
            break
        chunks.append(data)
        remaining -= len(data)
    return b''.join(chunks)


def run(args, env):
    return subprocess.run([str(FFMPEG), '-hide_banner', *args], env=env,
                          capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    src, work, output = a.source.resolve(), a.work.resolve(), a.output.resolve()
    if any(v.drive.upper() != 'D:' for v in (src, work, output)):
        raise ValueError('Source, work, and output must be on D:')
    if output.exists():
        raise FileExistsError(output)
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = Path('D:/Caches/Shapr3D/Temp')
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(cache), TMP=str(cache), PYTHONDONTWRITEBYTECODE='1')
    job, drill = load(src / 'job.json'), load(src / 'drill/job.json')
    evidence = load(ROOT / 'evidence/visible-drill-proof-20261013.json')
    geometry = load(work / 'geometry-verification.json')
    video = src / 'full-build.mp4'
    source_sha = sha(video)
    if source_sha != evidence['recording']['sha256'] or not geometry['passed']:
        raise ValueError('Source provenance or fresh geometry check failed')
    if geometry['source']['sha256'] != sha(src / 'drill/after.stl'):
        raise ValueError('Geometry report does not match this exported mesh')
    receipts = []
    grouped = []
    for group in (job, drill):
        rows = []
        for item in group['receipts']:
            path = Path(item['receipt'])
            original = load(path)
            if not original['ok'] or original['request']['operation'] != item['operation'] or original['result'] != item['result']:
                raise ValueError(f'Receipt mismatch: {path}')
            row = dict(path=str(path), sha256=sha(path), **original)
            receipts.append(row)
            rows.append(row)
        grouped.append(rows)
    b, d = grouped
    # Explicit receipt indices preserve the actual command sequence, including
    # selection rays and native parameter labels; no executable commands invented.
    specs = [
        ('空白模型', '已备份旧演示，原生历史清理完成。', [], 'remaining: 0'),
        ('导入二维草图', '80 × 40 mm 矩形，两个 Ø6 mm 安装孔。', b[5:6], '二维 DXF 交给 Shapr3D 原生导入器'),
        ('原生拉伸 4 mm', '选择草图区域，让 Shapr3D 计算实体。', b[6:9], '原生工具完成实体计算'),
        ('厚度改为 6 mm', '修改原生历史参数，模型立即更新。', b[9:12], 'thickness: 4 → 6 mm'),
        ('右孔向外移动', '选择圆柱侧面，向外移动 5 mm。', b[12:16], 'right hole: X = +30 mm'),
        ('孔距改为 60 mm', '左孔向外移动 5 mm，保留双孔结构。', b[16:20], 'pitch: 50 → 60 mm'),
        ('添加中心圆', '备份双孔板，导入位于顶面的 Ø8 mm 圆。', d[5:6], 'center: (0, 0, 6) mm / Ø8 mm'),
        ('精确选中圆内区域', '比较圆内外候选，按原生 ID 选区。', d[6:10], 'selectionSubmitted: true'),
        ('先切除 2 mm', '先形成浅孔，过程在前台可见。', d[10:11], 'cut depth: 2 mm'),
        ('再加深到 4 mm', '提交切除特征，再修改它的历史参数。', d[11:14], 'cut depth: 4 mm'),
        ('中心孔贯穿', '切深 8 mm，穿过 6 mm 厚的固定板。', d[14:15], 'Ø8 mm through hole'),
        ('原生导出完成', '导出 STL 网格与可编辑的 .shapr 项目。', d[15:18], 'after.stl + after.shapr / OK'),
    ]
    events = job['recording']['events']
    if len(events) != len(specs) or job['recording']['exitCode'] != 0:
        raise ValueError('Unexpected phase markers or failed source recorder')
    aliases = {job['nativeDirectory']: '$PLATE', drill['nativeDirectory']: '$DRILL'}

    def short_request(request):
        value = dict(request)
        for key in ('path', 'directory'):
            if key in value:
                value[key] = value[key].replace('\\', '/')
                for path, alias in aliases.items():
                    value[key] = value[key].replace(path.replace('\\', '/'), alias)
        return value

    phases = []
    for index, (event, spec) in enumerate(zip(events, specs)):
        title, description, rows, status = spec
        requests = [short_request(row['request']) for row in rows]
        code = '\n\n'.join('call(' + json.dumps(q, ensure_ascii=False, separators=(', ', ': ')) + ')' for q in requests)
        if not code:
            code = '# 原生清理回执（录制开始前）\n{"remaining": 0,\n "completed": true}'
        phases.append(dict(index=index + 1, title=title, description=description,
                           sourceSeconds=event['seconds'], videoSeconds=INTRO + event['seconds'],
                           phase=event['phase'], status=status, code=code,
                           receiptPaths=[row['path'] for row in rows]))
    save(work / 'commands.json', dict(schemaVersion=1, driver='python shapr3d-cli/full_demo.py …',
         displayMethod='Original JSON requests wrapped as call(...); this is a log panel, not a terminal recording.',
         alignment='Panels change at original stage-completion markers; not frame-accurate request submission timestamps.',
         pathAliases=aliases, phases=phases, originalReceipts=receipts))

    def base(stage, subtitle):
        im = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(im)
        draw.text((28, 18), 'REVERSE-CLI  /  Shapr3D', font=font(34, bold=True), fill=WHITE)
        draw.text((29, 62), subtitle, font=font(20), fill=MUTED)
        draw.text((1310, 25), stage, font=font(27, bold=True), fill=CYAN)
        return im

    def panel(phase):
        im = base('CLI 调用记录', '2026-10-13 原始连续实录 · 1× 速度 · 无鼠标、无键盘 UI 输入')
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle((1230, 104, 1892, 1024), radius=16, fill=PANEL)
        x = 1254
        draw.text((x, 124), f"{phase['index']:02d} / 12   {phase['title']}", font=font(28, bold=True), fill=WHITE)
        y = 175
        for line in wrapped(phase['description'], font(23), 610):
            draw.text((x, y), line, font=font(23), fill=MUTED)
            y += 34
        draw.text((x, 259), 'python shapr3d-cli/full_demo.py …', font=font(22, mono=True), fill=CYAN)
        draw.text((x, 299), '已完成阶段的原始请求', font=font(20), fill=GREEN)
        code_font = font(22)
        lines = wrapped(phase['code'], code_font, 610)
        if len(lines) > 18:
            code_font = font(20)
            lines = wrapped(phase['code'], code_font, 610)
        if len(lines) > 20:
            raise ValueError(f'Command panel overflow: {phase["phase"]}')
        y = 344
        for line in lines:
            draw.text((x, y), line, font=code_font, fill=WHITE)
            y += 27
        draw.line((x, 914, 1865, 914), fill='#314156', width=1)
        for j, line in enumerate(wrapped(phase['status'], font(22), 610)):
            draw.text((x, 931 + j * 30), line, font=font(22), fill=GREEN)
        draw.text((30, 1042), '命令面板依原始回执后期补充；长路径以 $PLATE / $DRILL 缩写。', font=font(18), fill=MUTED)
        return im

    panels = [panel(phase) for phase in phases]
    # Original pixels, fitted proportionally. No cropping, synthetic app UI,
    # model replacement, duplicated workflow, or omitted workflow frames.
    final_data = run(['-loglevel', 'error', '-ss', '48', '-i', str(video), '-frames:v', '1',
                      '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], env)
    if final_data.returncode or len(final_data.stdout) != 1026 * 802 * 3:
        raise ValueError('Could not decode final source frame')
    final_frame = Image.frombytes('RGB', (1026, 802), final_data.stdout)

    intro = base('原生 CAD × Agent', '复用已验收的真实录屏，补充中文解说与原始 CLI 调用记录')
    draw = ImageDraw.Draw(intro)
    draw.text((70, 182), '从空白到可打印模型', font=font(61, bold=True), fill=WHITE)
    for i, line in enumerate(['草图 → 实体 → 参数修改 → 钻孔 → 原生导出',
                              '49 秒连续过程，全程 CLI 操作',
                              'REA 恢复原生入口，Shapr3D 计算模型']):
        draw.text((75, 320 + i * 62), line, font=font(28), fill=CYAN if i == 0 else MUTED)
    draw.text((75, 635), '80 × 40 × 6 mm', font=font(49, bold=True), fill=GREEN)
    draw.text((77, 709), '双安装孔 Ø6 · 孔距 60 mm · 中心孔 Ø8', font=font(26), fill=WHITE)
    thumb = ImageOps.contain(final_frame, (880, 770), Image.Resampling.LANCZOS)
    intro.paste(thumb, (998, 173))
    draw.text((76, 963), '原始录制：2026-10-13     演示整理与独立复验：2026-10-14', font=font(24), fill=MUTED)
    outro = panels[-1].copy()
    outro.paste(ImageOps.contain(final_frame, (1180, 922), Image.Resampling.LANCZOS), (24, 104))
    draw = ImageDraw.Draw(outro)
    draw.rounded_rectangle((1230, 104, 1892, 1024), radius=16, fill=PANEL)
    draw.text((1254, 130), '独立验收 · 重新执行', font=font(30, bold=True), fill=WHITE)
    draw.text((1254, 205), f"{len(geometry['checks'])} / {len(geometry['checks'])} PASS", font=font(48, bold=True), fill=GREEN)
    facts = ['外形：80 × 40 × 6 mm', '原孔：Ø6 mm / 孔距 60 mm', '新孔：中心 Ø8 mm / 贯穿', '单实体 · 闭合流形 · 三个孔', '188 个三角形 / Euler = −4', '原生导出：after.stl + after.shapr']
    for i, line in enumerate(facts):
        draw.text((1254, 318 + i * 57), line, font=font(24), fill=WHITE)
    for i, line in enumerate(['验收的是录像对应的原生导出网格。', 'STL 使用账号允许的 Low 精度。', '本录像未包含冷启动重开。', '最终画面为原录像定格。']):
        draw.text((1254, 755 + i * 43), line, font=font(22), fill=MUTED)
    draw.rectangle((0, 1035, 1920, 1080), fill=BG)
    draw.text((30, 1041), '独立几何检查：2026-10-14 · 原视频保持连续、原速、原顺序 · 结果与原始 SHA-256 对应', font=font(19), fill=MUTED)
    intro.save(work / 'intro.png')
    outro.save(work / 'outro.png')
    log = (work / 'render.log').open('wb')
    encoder = subprocess.Popen([str(FFMPEG), '-hide_banner', '-loglevel', 'warning', '-n',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(FPS), '-i', '-',
        '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-r', '30', '-fps_mode', 'cfr', '-movflags', '+faststart', str(output)],
        stdin=subprocess.PIPE, stdout=log, stderr=log, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    decoder = subprocess.Popen([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-i', str(video),
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, stderr=log,
        env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    frames, sampled = 0, set()
    try:
        for _ in range(INTRO * FPS):
            encoder.stdin.write(intro.tobytes())
        while True:
            raw = read_exact(decoder.stdout, 1026 * 802 * 3)
            if not raw:
                break
            if len(raw) != 1026 * 802 * 3:
                raise ValueError('Truncated source frame')
            t = frames / FPS
            index = max(i for i, phase in enumerate(phases) if phase['sourceSeconds'] <= t)
            frame = panels[index].copy()
            image = Image.frombytes('RGB', (1026, 802), raw)
            frame.paste(ImageOps.contain(image, (1180, 922), Image.Resampling.LANCZOS), (24, 104))
            draw = ImageDraw.Draw(frame)
            draw.text((790, 29), f'{t:05.1f} / 49.0 s  |  1×', font=font(24, mono=True), fill=GREEN)
            draw.rectangle((24, 1027, 1204, 1031), fill='#263950')
            draw.rectangle((24, 1027, 24 + int(1180 * t / 49), 1031), fill=CYAN)
            if index not in sampled and t >= phases[index]['sourceSeconds'] + .55:
                frame.save(work / f'phase-{index:02d}.jpg', quality=92)
                sampled.add(index)
            encoder.stdin.write(frame.tobytes())
            frames += 1
        if decoder.wait() != 0 or frames != 735:
            raise ValueError(f'Unexpected source decode/frame count: {frames}')
        for _ in range(OUTRO * FPS):
            encoder.stdin.write(outro.tobytes())
    finally:
        decoder.stdout.close()
        if decoder.poll() is None:
            decoder.terminate()
            decoder.wait()
        encoder.stdin.close()
        encoder.wait()
        log.close()
    if encoder.returncode:
        raise RuntimeError('Encoding failed; inspect render.log')
    checks = run(['-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'], env)
    (work / 'full-decode.log').write_bytes(checks.stderr)
    metadata = run(['-i', str(output)], env).stderr.decode('utf-8', errors='replace')
    (work / 'metadata.txt').write_text(metadata, encoding='utf-8')
    report = dict(schemaVersion=1, passed=checks.returncode == 0 and sha(video) == source_sha,
        source=dict(path=str(video), sha256=source_sha, frames=frames, fps=FPS, seconds=frames/FPS),
        output=dict(path=str(output), sha256=sha(output), bytes=output.stat().st_size,
                    width=1920, height=1080, fps=30, expectedFrames=1890, seconds=63),
        reuse=dict(originalFramesContinuous=True, speed=1, introSeconds=INTRO, outroSeconds=OUTRO,
                   commandPanels='Added from original receipts at recorded stage-completion markers',
                   originalRecordingDate='2026-10-13', nativeApplicationRerun=False),
        checks=dict(sourceHashMatchesPriorEvidence=True, allReceiptResultsMatch=True,
                    receiptCount=len(receipts), freshGeometryPassed=geometry['passed'],
                    geometryChecks=len(geometry['checks']), decodeExitCode=checks.returncode,
                    originalFileUnchanged=sha(video) == source_sha),
        visualReview='pending', limitations=['Source recording is 1026x802 at 15 fps; delivery is upscaled.',
                    'Native STL Low resolution.', 'No cold app restart claimed by this recording.'])
    save(work / 'verification.json', report)
    save(work / 'chapters.json', dict(introSeconds=INTRO, phases=phases, verificationStart=54))
    print(json.dumps({'passed': report['passed'], 'output': str(output), 'seconds': 63,
                      'receipts': len(receipts), 'geometryChecks': len(geometry['checks'])}))
    if not report['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
