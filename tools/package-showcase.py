"""Restyle existing recordings without replaying native application mutations.

CapCut and Axure use their original timed command journals. Shapr3D reuses its
accepted English edition with the same 1920x1440 app-above-terminal layout.
Only curated finished assets go into the repository; intermediates stay on D:.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FF = ROOT / 'capcut-cli/.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
CACHE = Path('D:/Caches/reverse-cli/showcase-20261014')
SIZE, TOP = (1920, 1440), 1020
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 23)
HEADING = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 26)
SMALL = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 19)
ENV = dict(os.environ, TEMP=str(CACHE / 'temp'), TMP=str(CACHE / 'temp'))


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args, **kwargs):
    return subprocess.run([str(FF), '-hide_banner', *args], env=ENV,
                          creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)


def exact(pipe, count):
    chunks = []
    while count:
        b = pipe.read(count)
        if not b:
            break
        count -= len(b); chunks.append(b)
    return b''.join(chunks)


def footer(app, elapsed, heading, command, status, note):
    canvas = Image.new('RGB', SIZE, '#111827'); d = ImageDraw.Draw(canvas)
    d.text((24, TOP + 16), f'REVERSE-CLI  |  {app}  |  {elapsed:06.1f}s  |  No mouse input', font=HEADING, fill='#67E8F9')
    d.text((24, TOP + 57), heading, font=FONT, fill='#A5B4C8')
    lines = []
    for paragraph in command.splitlines():
        lines += textwrap.wrap(paragraph, 134, subsequent_indent='  ', break_long_words=True, break_on_hyphens=False) or ['']
    if len(lines) > 9 or any(FONT.getlength(line) > 1872 for line in lines):
        raise ValueError('Command caption does not fit; refusing to truncate: ' + command)
    for i, line in enumerate(lines):
        d.text((24, TOP + 97 + i * 27), line, font=FONT, fill='white')
    status_lines = textwrap.wrap(status, 134, break_long_words=False)
    if len(status_lines) > 1:
        raise ValueError('Status does not fit')
    d.text((24, 1366), status, font=FONT, fill='#86EFAC' if status.startswith(('OK', 'PASS')) else '#FDE68A')
    d.text((24, 1410), note, font=SMALL, fill='#A5B4C8')
    return canvas


def caption_at(events, seconds, fallback):
    found = [e for e in events if e['seconds'] <= seconds]
    return found[-1] if found else fallback


def config(app):
    if app == 'capcut':
        folder = ROOT / 'capcut-cli/capcut-analysis/recorded-real-media-20261014-wgc'
        proof = read(ROOT / 'capcut-cli/evidence/recorded-real-media-20261014.json')
        packaging = read(folder / 'recording-verification.json')
        timeline = read(folder / 'capcut-from-blank-recording.timeline.json')
        source = folder / 'capcut-from-blank-recording.mp4'; result = folder / 'water-science-final.mp4'
        assert proof['passed'] and packaging['passed'] and timeline['recorderError'] is None
        assert sha(source) == packaging['files']['raw']['sha256']
        assert sha(result) == proof['deliverables']['water-science-fresh-subtitles-20261014.mp4']['sha256']
        rawframes = timeline['frames']; assert rawframes == 3221
        names = ['CREATE AN EMPTY PROJECT', 'IMPORT REAL FOOTAGE', 'TRIM THE NATIVE TIMELINE',
                 'TRANSCRIBE SPEECH LOCALLY', 'GENERATE FRESH CHINESE TRANSLATION', 'BUILD JSON / SRT CAPTIONS',
                 'ADD BACKGROUND MUSIC', 'IMPORT EDITABLE CAPTIONS', 'EXPORT THROUGH CAPCUT',
                 'SAVE, REOPEN AND VERIFY', 'PLAY THE NATIVE EXPORT WITH AUDIO']
        chapters = [{'seconds': 0, 'title': 'INITIALIZE THE CLI WORKFLOW'}] + [
            dict(seconds=row['seconds'], title=title) for row, title in zip(proof['recording']['chapters'], names)]
        events = [e for e in timeline['events'] if 'command' in e and 'status' in e and 'snapshot' not in e]
        fallback = dict(command='CLI workflow initializes: project -> media -> edit -> captions/music -> native export', status='Recorded application capture; no mouse or keyboard editing')
        def live(t):
            e = caption_at(events, t, fallback)
            h = caption_at(chapters, t, chapters[0])['title']
            return h, e['command'], e['status'], 'Actual recorded CLI command log | Local ASR + agent translation | Original footage at 1x'
        def playback(t):
            return ('RESULT PLAYBACK / NATIVE CAPCUT EXPORT',
                    'Native output: water-science-final.mp4\n33.7 s | 1920 x 1080 | 30 fps | H.264 + AAC\n3 video clips + music + 16 fresh bilingual captions + source credit',
                    'OK | 26 native/media checks passed in the recorded run | Original speech and music preserved',
                    'Recorded result, not another editing command | NASA footage / Fluidscape - Kevin MacLeod (CC BY 4.0)')
        return dict(name='CapCut native editing', segments=[
            dict(path=source, width=1920, cropHeight=1134, fps=15, frames=rawframes, captions=live),
            dict(path=result, width=1920, cropHeight=1080, fps=30, frames=1011, captions=playback)],
            chapters=chapters, audio=result, audioStart=rawframes/15, nativeChecks=26,
            evidence='capcut-cli/evidence/recorded-real-media-20261014.json', commandEvents=events,
            sampleTimes=[0, 8, 17, 40, 59, 79, 100, 129, 135, 155, 178, 193, 211, 232])
    folder = ROOT / 'axure-cli/outputs/login-20261013-191733'
    proof = read(folder / 'recording-verification.json'); native = read(folder / 'acceptance.json')
    browser = read(folder / 'browser-acceptance.json'); journal = read(folder / 'recording-timeline.json')
    assert proof['passed'] and native['passed'] and browser['passed']
    assert sha(Path(proof['path'])) == proof['sha256']
    parts = [folder / 'native-part-1.mp4', folder / 'native-part-2.mp4', Path(browser['video'])]
    # The old browser MP4's subtitles extend into its image area. Reuse the
    # original timestamped CDP JPEG frames instead of covering recorded pixels.
    frame_dir=Path(browser['frameCache']); frame_list=frame_dir/'frames.txt'
    images=sorted(frame_dir.glob('*.jpg'))
    if len(images)!=browser['captureFrames']: raise ValueError('Missing original browser frames')
    clean=CACHE/'axure'/'browser-unlabelled.mp4'
    if not clean.exists():
        run(['-loglevel','error','-n','-f','concat','-safe','0','-i',str(frame_list),
             '-vf','setsar=1','-r','15','-c:v','libx264','-preset','veryfast','-crf','18',
             '-pix_fmt','yuv420p',str(clean)],capture_output=True,check=True)
    parts[2]=clean
    frame_counts = [1037, 194, 352]
    starts = [0, frame_counts[0]/15, sum(frame_counts[:2])/15]
    titles = ['BUILD AN INTERACTIVE LOGIN FORM', 'COLD REOPEN AND NATIVE HTML EXPORT', 'VERIFY THE EXPORTED HTML']
    events_by_part = [[e for e in journal['steps'] if e['part'] == i] for i in (1,2)]
    captions = []
    for i in (0,1):
        def native_caption(t, i=i):
            e = caption_at(events_by_part[i], t, dict(caption='Native editor session initializes'))
            return (titles[i], e['caption'], 'RECORDED | Native CLI build and persistence checks: 29/29 passed',
                    'Actual recorded CLI command log | Original application pixels | Original footage at 1x')
        captions.append(native_caption)
    def browser_caption(t):
        e = caption_at(browser['captions'], t, dict(text='Browser verification initializes'))
        return (titles[2], 'Verification driver: node axure-cli/verify_login.mjs\n\n' + e['text'],
                'RECORDED | 14/14 browser checks passed | Native HTML unchanged | Local demo credentials only',
                'Real browser capture | Input/change events and keyboard Enter activate native rules | No mouse events')
    captions.append(browser_caption)
    return dict(name='Axure RP native prototyping', segments=[dict(path=path, width=(1280 if i==2 else 1920),
         cropHeight=(900 if i==2 else 1166), fps=15, frames=count, captions=callback,
         **({'origin':'Original CDP JPEG captures, replayed with their original durations',
             'captureFrameCount':len(images),'captureTimelineSha256':sha(frame_list),
             'captureImagesSha256':hashlib.sha256(''.join(sha(p) for p in images).encode('ascii')).hexdigest()} if i==2 else {}))
         for i,(path,count,callback) in enumerate(zip(parts,frame_counts,captions))],
         chapters=[dict(seconds=s,title=t) for s,t in zip(starts,titles)], nativeChecks=29, browserChecks=14,
         evidence='axure-cli/evidence/login-recording.json', commandEvents=journal['steps'],
         sampleTimes=[0,13,28,36,43,56,65,73,79,85,87,93,100,104])


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--app', choices=['capcut','axure','shapr3d'], required=True)
    app=p.parse_args().app; work=CACHE/app; work.mkdir(parents=True,exist_ok=True); (CACHE/'temp').mkdir(exist_ok=True)
    assets=ROOT/(app+'-cli')/'assets'; assets.mkdir(exist_ok=True)
    output=assets/(app+'-cli-demo.mp4')
    if output.exists(): raise FileExistsError(output)
    if app=='shapr3d':
        source=ROOT/'shapr3d-cli/exports/shapr3d-cli-demo-english-20261014.mp4'
        proof=read(ROOT/'shapr3d-cli/outputs/presentation-english-20261014/verification.json')
        assert proof['passed'] and sha(source)==proof['output']['sha256']
        shutil.copyfile(source,output)
        conf=dict(chapters=[dict(seconds=p['sourceSeconds'],title=p['title']) for p in read(ROOT/'shapr3d-cli/outputs/presentation-english-20261014/chapters.json')['phases']]+[dict(seconds=49,title='INDEPENDENT GEOMETRY VERIFICATION')],
             sampleTimes=[0,4,9,13,18,23,28,31,35,39,43,47,53],evidence='shapr3d-cli/evidence/recorded-demo-english-20261014.json',nativeChecks=78)
        sources=[dict(path=str(source.relative_to(ROOT)).replace('\\','/'),sha256=sha(source),frames=1680)]
        frames, expected_seconds=1680,56
        provenance='Reuses accepted English edition. CLI equivalents from verified native requests, not a new execution.'
    else:
        conf=config(app); sources=[]; total_frames=0
        for seg in conf['segments']:
            # Fit the old software area, excluding its old caption footer.
            scale=min(1920/seg['width'],TOP/seg['cropHeight'])
            seg['dest']=[round(seg['width']*scale),round(seg['cropHeight']*scale)]
            source_path=(str(seg['path'].relative_to(ROOT)).replace('\\','/') if seg['path'].is_relative_to(ROOT)
                         else 'local original browser capture frames / derived unlabelled replay')
            sources.append(dict(path=source_path,sha256=sha(seg['path']),
                 frames=seg['frames'],fps=seg['fps'],cropHeight=seg['cropHeight'],destSize=seg['dest'],
                 **{k:seg[k] for k in ('origin','captureFrameCount','captureTimelineSha256','captureImagesSha256') if k in seg}))
            total_frames += seg['frames']*(30//seg['fps'])
        expected_seconds=total_frames/30
        picture=work/'picture.mp4'
        if picture.exists(): raise FileExistsError(picture)
        log=(work/'encode.log').open('wb')
        encoder=subprocess.Popen([str(FF),'-hide_banner','-loglevel','warning','-n','-f','rawvideo','-pix_fmt','rgb24',
             '-s','1920x1440','-r','30','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(picture)],stdin=subprocess.PIPE,stdout=log,stderr=log,
             env=ENV,creationflags=subprocess.CREATE_NO_WINDOW)
        elapsed=0; frames=0
        try:
            for si,seg in enumerate(conf['segments']):
                width,height=seg['dest']; crop=f'crop={seg["width"]}:{seg["cropHeight"]}:0:0,scale={width}:{height},setsar=1'
                decoder=subprocess.Popen([str(FF),'-hide_banner','-loglevel','error','-i',str(seg['path']),'-vf',crop,
                     '-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=log,env=ENV,creationflags=subprocess.CREATE_NO_WINDOW)
                count=0
                try:
                    while True:
                        raw=exact(decoder.stdout,width*height*3)
                        if not raw: break
                        if len(raw)!=width*height*3: raise RuntimeError('Partial decoded frame')
                        t=count/seg['fps']; title,command,status,note=seg['captions'](t)
                        canvas=footer(conf['name'],elapsed+t,title,command,status,note)
                        canvas.paste(Image.frombytes('RGB',(width,height),raw),((1920-width)//2,0))
                        pixels=canvas.tobytes()
                        for _ in range(30//seg['fps']): encoder.stdin.write(pixels); frames+=1
                        count+=1
                finally:
                    decoder.stdout.close()
                    if decoder.poll() is None and count!=seg['frames']: decoder.terminate()
                    rc=decoder.wait()
                if rc or count!=seg['frames']: raise RuntimeError(f'Decode mismatch: {count}, expected {seg["frames"]}')
                elapsed+=count/seg['fps']
                print(json.dumps(dict(app=app,part=si+1,decodedFrames=count)),flush=True)
        finally:
            encoder.stdin.close(); encoder.wait(); log.close()
        if encoder.returncode or frames!=total_frames: raise RuntimeError('Encoding failed')
        if conf.get('audio'):
            delay=round(conf['audioStart']*48000)
            filt=f'[1:a]aresample=48000,adelay={delay}S:all=1,apad,atrim=duration={expected_seconds}[a]'
            run(['-loglevel','error','-n','-i',str(picture),'-i',str(conf['audio']),'-filter_complex',filt,
                 '-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)],check=True)
        else: shutil.copyfile(picture,output)
        provenance='Reuses original chronological software captures; caption footer rebuilt from original timed command journals. No native edits rerun.'
        write(work/'command-events.json',conf['commandEvents'])
    decoded=run(['-loglevel','error','-xerror','-i',str(output),'-progress','pipe:1','-f','null','-'],capture_output=True,check=True)
    (work/'decode.log').write_bytes(decoded.stdout+decoded.stderr)
    actual_frames=int(re.findall(rb'frame=(\d+)',decoded.stdout)[-1]); actual_seconds=int(re.findall(rb'out_time_us=(\d+)',decoded.stdout)[-1])/1e6
    assert actual_frames==frames and abs(actual_seconds-expected_seconds)<.1
    samples=[]
    for i,t in enumerate(conf['sampleTimes']):
        path=work/f'frame-{i:02d}.png'
        run(['-loglevel','error','-y','-ss',str(t),'-i',str(output),'-frames:v','1',str(path)],capture_output=True,check=True)
        samples.append(dict(seconds=t,path=str(path)))
    poster_at={'capcut':211,'axure':56,'shapr3d':47}[app]
    run(['-loglevel','error','-y','-ss',str(poster_at),'-i',str(output),'-frames:v','1','-vf','scale=960:720','-q:v','3',
         str(assets/(app+'-cli-demo.jpg'))],capture_output=True,check=True)
    sheet=Image.new('RGB',(1920,((len(samples)+2)//3)*507),'#111827'); drawing=ImageDraw.Draw(sheet)
    for i,s in enumerate(samples):
        im=Image.open(s['path']);im.thumbnail((640,480));x=i%3*640;y=i//3*507;sheet.paste(im,(x,y+26));drawing.text((x+8,y+4),f'{s["seconds"]:.2f}s',fill='white')
    sheet.save(work/'contact-sheet.jpg',quality=92)
    report=dict(app=app,passed=True,presentationDate='2026-10-14',video=str(output.relative_to(ROOT)).replace('\\','/'),
         poster=str((assets/(app+'-cli-demo.jpg')).relative_to(ROOT)).replace('\\','/'),sha256=sha(output),bytes=output.stat().st_size,
         width=1920,height=1440,fps=30,frames=actual_frames,durationSeconds=expected_seconds,
         chapters=conf['chapters'],sources=sources,provenance=provenance,sourceEvidence=conf['evidence'],
         nativeChecks=conf['nativeChecks'],browserChecks=conf.get('browserChecks'),
         noMouseInput=True,newNativeOperationsPerformed=False,fullDecodePassed=True,visualReview='pending',
         style=dict(intro=False,language='English overlays; original app/content language retained',background='#111827',
                    font='Consolas',commandFontPx=23,headerFontPx=26,appAreaHeight=TOP),sampleFrames=samples)
    write(work/'report.json',report)
    print(json.dumps(dict(app=app,output=str(output),seconds=expected_seconds,frames=actual_frames,bytes=report['bytes'])),flush=True)


if __name__=='__main__': main()
