"""Check curated recordings against their original image areas and audio."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('D:/Caches/reverse-cli/showcase-20261014')
FF=ROOT/'capcut-cli/.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'


def run(args):
    return subprocess.run([str(FF),'-hide_banner',*args],capture_output=True,check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW)


def pcm(path,start,duration):
    b=run(['-loglevel','error','-ss',str(start),'-i',str(path),'-t',str(duration),
           '-vn','-ac','1','-ar','16000','-f','f32le','-']).stdout
    return np.frombuffer(b,dtype='<f4').astype(np.float64)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',choices=['capcut','axure','shapr3d'],required=True)
    app=p.parse_args().app;work=CACHE/app;rp=work/'report.json';report=json.loads(rp.read_text(encoding='utf-8'))
    output=ROOT/report['video'];checks={};comparisons=[]
    checks['outputHashMatches']=hashlib.sha256(output.read_bytes()).hexdigest()==report['sha256']
    if app=='shapr3d':
        checks['exactAcceptedEditionCopy']=hashlib.sha256((ROOT/report['sources'][0]['path']).read_bytes()).hexdigest()==report['sha256']
    else:
        start=0
        for i,source in enumerate(report['sources']):
            path=(CACHE/'axure/browser-unlabelled.mp4') if source.get('origin') else ROOT/source['path']
            checks[f'sourceHash{i}']=hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
            w,h=source['destSize'];x=(1920-w)//2;fps=source['fps'];duration=source['frames']/fps
            source_width=1280 if source.get('origin') else 1920
            # yuv444p permits the exact odd-width/odd-offset crop before the
            # common 4:2:0 comparison, avoiding silently rounded crop bounds.
            filt=(f'[0:v]trim=start={start}:end={start+duration},setpts=PTS-STARTPTS,fps={fps},'
                  f'format=yuv444p,crop={w}:{h}:{x}:0,format=yuv420p,settb=AVTB[out];'
                  f'[1:v]crop={source_width}:{source["cropHeight"]}:0:0,scale={w}:{h},setsar=1,'
                  f'fps={fps},setpts=PTS-STARTPTS,format=yuv420p,settb=AVTB[src];[out][src]ssim')
            r=run(['-filter_complex_threads','2','-i',str(output),'-i',str(path),'-filter_complex',filt,'-an','-f','null','-'])
            (work/f'image-comparison-{i}.log').write_bytes(r.stderr)
            score=float(re.search(rb'All:(\d+\.\d+)',r.stderr).group(1))
            comparisons.append(dict(part=i+1,ssim=score,seconds=duration,passed=score>.985))
            checks[f'imageAreaPreserved{i}']=score>.985;start+=duration
    if app=='capcut':
        source=ROOT/report['sources'][1]['path'];at=report['sources'][0]['frames']/report['sources'][0]['fps']
        before=pcm(output,0,at-.05);original=pcm(source,0,33.7);played=pcm(output,at,33.7)
        n=min(len(original),len(played));a=original[64:n-64]
        choices=[(float(np.corrcoef(a,played[64+shift:n-64+shift])[0,1]),shift) for shift in range(-32,33)]
        corr,shift=max(choices)
        silence_peak=float(np.max(np.abs(before)));rms=float(np.sqrt(np.mean(played**2)))
        checks.update(commandFootageSilent=silence_peak<.0001,nativePlaybackAudible=rms>.001,
                      nativeAudioPreserved=corr>.99)
        report['audioVerification']=dict(silentPortionPeak=silence_peak,playbackRms=rms,
                                         nativeCorrelation=corr,alignmentSamplesAt16kHz=shift,
                                         nativePlaybackStartsSeconds=at)
    report['presentationChecks']=checks;report['imageComparisons']=comparisons
    report['passed']=report['passed'] and all(checks.values())
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(app=app,passed=report['passed'],checks=checks,imageComparisons=comparisons,
                         audioVerification=report.get('audioVerification'))))
    if not report['passed']:raise SystemExit(2)


if __name__=='__main__':main()
