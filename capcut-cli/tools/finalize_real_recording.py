"""Keep the uncut command recording and append a labelled native-export playback.

This only packages the demonstration. water-science-final.mp4 remains the
original CapCut-produced video; FFmpeg is not used to replace native editing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from media_acceptance import FFMPEG, ENV, metadata

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args(); out=args.run_dir.resolve()
    raw=out/'capcut-from-blank-recording.mp4'
    final=out/'water-science-final.mp4'
    output=out/'capcut-cli-complete-demo.mp4'
    timeline=json.loads(raw.with_suffix('.timeline.json').read_text(encoding='utf8'))
    duration=timeline['frames']/15
    (out/'result-caption.txt').write_text('RESULT PLAYBACK | CapCut native MP4 with original speech and music\n33.7 seconds | 1080p / 30 fps | Fresh speech recognition and fresh Chinese subtitles',encoding='utf8')
    vf=(f'[0:v]fps=30,setsar=1,setpts=PTS-STARTPTS[v0];'
        f'anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a0];'
        "[1:v]pad=1920:1440:0:27:color=0x111827,setsar=1,"
        "drawtext=fontfile='C\\:/Windows/Fonts/consola.ttf':textfile=result-caption.txt:fontcolor=white:fontsize=25:x=24:y=1160:line_spacing=16,"
        'setpts=PTS-STARTPTS[v1];[1:a]atrim=duration=33.7,asetpts=PTS-STARTPTS[a1];'
        '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]')
    cmd=[str(FFMPEG),'-hide_banner','-loglevel','warning','-n','-i',str(raw),'-i',str(final),
         '-filter_complex',vf,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','20',
         '-r','30','-fps_mode','cfr','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)]
    with (out/'recording-package.log').open('wb') as log:
        subprocess.run(cmd,cwd=out,stdout=log,stderr=log,env=ENV,check=True)
    def decode(path):
        p=subprocess.run([str(FFMPEG),'-hide_banner','-xerror','-err_detect','explode','-i',str(path),
             '-map','0:v:0','-map','0:a?','-f','null','-'],capture_output=True,env=ENV,check=True)
        log=p.stderr.decode('utf8',errors='replace')
        (out/(path.stem+'-decode.log')).write_text(log,encoding='utf8')
        counts=re.findall(r'frame=\s*(\d+)',log)
        return int(counts[-1])
    raw_count,combined_count=decode(raw),decode(output)
    expected=raw_count*2+1011
    checks={'rawRecordingFullyDecoded':raw_count==timeline['frames'],
            'completeDemoFullyDecoded':combined_count==expected,
            'originalCaptureNotAccelerated':abs(metadata(raw)['containerDurationSeconds']-duration)<.08,
            'nativeResultPlaybackAppended':abs(metadata(output)['containerDurationSeconds']-(duration+33.7))<.08,
            'recordingHasNoCaptureError':timeline['recorderError'] is None,
            'noMouseOrKeyboardEventsSent':timeline['mouseEventsSent']==0 and timeline['keyboardEventsSent']==0}
    files={}
    for name,path in [('raw',raw),('completeDemo',output),('nativeExport',final)]:
        files[name]={'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**metadata(path)}
    report={'passed':all(checks.values()),'checks':checks,'files':files,'rawFrames':raw_count,'demoFrames':combined_count,
            'resultPlaybackStartsSeconds':duration,'resultPlaybackDurationSeconds':33.7,
            'note':'Uncut actual application capture with live CLI footer; fresh-agent translation wait is retained. Separate labelled result playback appended with original audio. Process capture itself has no microphone/system audio.'}
    (out/'recording-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    events=timeline['events']
    samples={'empty-project':next(e['seconds']+1 for e in events if 'editor inspect' in e.get('command','')),
             'subtitle-generation':next(e['seconds']+1 for e in events if 'AGENT TASK' in e.get('command','')),
             'native-export':max(e['seconds'] for e in events if 'editor export' in e.get('command','')),
             'accepted-editor':duration-2,'result-playback':duration+17}
    for name,at in samples.items():
        subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-n','-ss',str(at),'-i',str(output),
            '-frames:v','1',str(out/(name+'.png'))],check=True,env=ENV)
    print(json.dumps({'passed':report['passed'],'checks':checks,'durationSeconds':metadata(output)['containerDurationSeconds'],
                      'output':str(output),'frames':combined_count}),flush=True)
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
