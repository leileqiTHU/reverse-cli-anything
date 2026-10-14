"""Replay real-media native editing while continuously recording app + commands.

Stops for the live agent to author fresh bilingual captions from current ASR.
Never replays a failed/unknown mutation; receipts and native IDs remain on disk.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from window_recording import WindowRecorder

ROOT=Path(__file__).resolve().parents[1]
FFMPEG=ROOT/'.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
SPEECH_PYTHON=Path('D:/Apps/CapCutAgentSpeech/Scripts/python.exe')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--previous-run',type=Path,default=ROOT/'capcut-analysis/real-media-20261013')
    args=parser.parse_args()
    out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    cache=Path('D:/Caches/CapCutAgent/Temp'); cache.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TEMP=str(cache),TMP=str(cache),PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    sys.stdout.reconfigure(encoding='utf8')
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    def read(name):return json.loads((out/name).read_text(encoding='utf8'))
    def docs(project):
        return {p.parent.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in (Path(project)/'Timelines').glob('*/draft_content.json')}
    for name in ['edit-plan.json','caption-style.json','credit-style.json','credits.json','credits.txt']:
        shutil.copy2(args.previous_run/name,out/name)
    source=(args.previous_run/'assets/nasa-properties-of-water.mp4').resolve()
    music=(args.previous_run/'assets/Fluidscape.mp3').resolve()
    save('sources.json',{'video':str(source),'music':str(music),'previousFootageAndEditorialSelectionReused':True,
                         'oldEnglishCaptionsRead':False,'oldChineseCaptionsRead':False,
                         'subtitleWorkflow':'Fresh current rough-cut ASR, fresh live-agent Chinese translation, current word timing'})
    state={'pid':args.pid}; plan=read('edit-plan.json')
    recorder=WindowRecorder(args.pid,out/'capcut-from-blank-recording.mp4',FFMPEG,env)
    recording=False
    def run(label,argv,display=None):
        nonlocal recording
        if (out/(label+'.json')).exists():raise RuntimeError('Existing receipt; inspect before resuming')
        recorder.check()
        command=display or subprocess.list2cmdline(list(map(str,argv)))
        if recording:recorder.update('> '+command)
        began=time.monotonic()
        result=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,encoding='utf8',env=env)
        save(label+'-command.json',{'argv':list(map(str,argv)),'display':command,'exitCode':result.returncode,
                                  'seconds':time.monotonic()-began,'stderr':result.stderr})
        (out/(label+'.stdout.txt')).write_text(result.stdout,encoding='utf8')
        print(json.dumps({'step':label,'exitCode':result.returncode,'seconds':round(time.monotonic()-began,2)}),flush=True)
        if result.returncode:
            if recording:recorder.update('> '+command,'FAILED - saved receipt; inspect before any retry')
            raise RuntimeError(f'{label} failed; see output log')
        if recording:recorder.update('> '+command,'OK - process exited 0; response saved')
        return result
    def cli(label,*parts):
        argv=[sys.executable,'-B',ROOT/'capcut_agent.py','--timeout','240',*map(str,parts)]
        display=subprocess.list2cmdline(['python','-B','capcut_agent.py','--timeout','240',*map(str,parts)])
        response=run(label,argv,display)
        body=json.loads(response.stdout); save(label+'.json',body)
        if not body.get('ok'):raise RuntimeError(f'{label}: native ok=false')
        time.sleep(2)
        return body['result']
    def editor(label,action,*parts):
        return cli(label,'editor',action,'--pid',args.pid,'--project',state['projectPath'],
                   '--timeline',state['timelineId'],*parts)
    # Preserve the currently open project before starting the new-project demo.
    current=cli('01-original-project','project','list','--pid',args.pid)['currentProject']
    state['originalProject']=current
    if current:
        save('original-project-before.json',docs(current['path']))
        cli('02-close-original','project','close','--pid',args.pid,'--project-id',current['id'])
    else:save('original-project-before.json',{})
    try:
        recorder.start(); recording=True
        recorder.update('BEGIN | New empty project -> import -> trim -> fresh ASR/translation -> music/captions -> native MP4', 'Actual application pixels; no mouse or keyboard editing')
        time.sleep(3)
        name='NASA CLI Recording '+time.strftime('%Y%m%d-%H%M%S')
        created=cli('03-create','project','create','--pid',args.pid,'--name',name)
        state.update(projectId=created['projectId'],projectPath=created['projectPath'],timelineId=created['mainTimelineId'])
        save('project-state.json',state)
        empty=editor('03-empty','inspect'); assert empty['items']==[]
        cli('04-close-new','project','close','--pid',args.pid,'--project-id',state['projectId'])
        cli('05-import-video','project','import-media','--pid',args.pid,'--project-id',state['projectId'],'--input',source)
        opened=cli('06-open','project','open','--pid',args.pid,'--project-id',state['projectId'])
        state['projectPath']=opened['projectPath']; save('project-state.json',state)
        tl=editor('07-timeline','add-timeline','--name','Water Science - Fresh Captions')
        state['timelineId']=tl['timelineId']; save('project-state.json',state)
        editor('08-switch','switch-timeline'); assert editor('09-empty','inspect')['items']==[]
        position=0; clips=[]
        for i,segment in enumerate(plan['segments']):
            before=editor(f'20-{i}-before','inspect')['clips']
            added=editor(f'21-{i}-add','add-video','--input',source,'--start-us',position)
            new=[x for x in added['clips'] if x['id'] not in {c['id'] for c in before}]
            assert len(new)==1
            identity=new[0]['id']
            trimmed=editor(f'22-{i}-trim','trim','--segment',identity,'--in-us',position+segment['sourceInUs'],
                           '--out-us',position+segment['sourceOutUs'])
            clip=next(x for x in trimmed['clips'] if x['id']==identity)
            duration=segment['sourceOutUs']-segment['sourceInUs']
            assert clip['sourceUs']=={'start':segment['sourceInUs'],'duration':duration}
            assert clip['targetUs']=={'start':position,'duration':duration}
            clips.append(clip); position+=duration; save('native-clips.json',clips)
        save('clip-patch.json',plan['transform']['patch'])
        editor('24-transform','set-clip','--segment',clips[1]['id'],'--patch',out/'clip-patch.json',
               '--request-id',out.name+'-transform')
        # Fresh ASR is part of this recording, before music/subtitles are added.
        editor('24-rough-export','export','--output',out/'rough-cut.mp4','--width',1920,'--height',1080,'--fps',30)
        run('24-transcribe',[SPEECH_PYTHON,'-B',ROOT/'tools/transcribe_media.py','--input',out/'rough-cut.mp4','--output',out/'source-asr.json'])
        save('awaiting-fresh-translation.json',{'asr':str(out/'source-asr.json'),'write':str(out/'fresh-translations.json'),
             'instruction':'Current agent must freshly translate the new transcript and split at current word timestamps. Do not copy old captions.'})
        recorder.update('AGENT TASK: read this run\'s source-asr.json; freshly translate English into Chinese and align the current word timestamps.',
                        'Waiting for fresh-translations.json from the live agent; old captions are not loaded')
        print('AWAITING_FRESH_TRANSLATION '+str(out/'source-asr.json'),flush=True)
        deadline=time.monotonic()+900
        while not (out/'fresh-translations.json').exists():
            recorder.check()
            if time.monotonic()>deadline:raise TimeoutError('Fresh translation has not arrived')
            time.sleep(.5)
        run('24-assemble-captions',[sys.executable,'-B',ROOT/'tools/assemble_captions.py',
                                   '--input',out/'fresh-translations.json','--output',out/'captions.json'])
        save('captions-reference.json',read('fresh-translations.json'))
        # Remove MP3 cover art through ordinary audio decoding, then use CapCut's mixer.
        run('25-decode-music',[FFMPEG,'-hide_banner','-loglevel','error','-n','-i',music,'-t','90','-vn','-ar','48000','-ac','2',out/'music.wav'])
        editor('25-music','add-audio','--input',out/'music.wav','--start-us',0,'--source-in-us',20000000,
               '--duration-us',33700000,'--gain-db',-22,'--fade-in-us',1200000,'--fade-out-us',1600000,
               '--request-id',out.name+'-music')
        cues=read('captions.json')['cues']
        for i in range(0,len(cues),4):
            batch=f'captions-{i//4+1}.json';save(batch,{'timebase':'timeline_us','cues':cues[i:i+4]})
            editor(f'26-captions-{i//4+1}','captions-import','--input',out/batch,'--style',out/'caption-style.json',
                   '--request-id',out.name+f'-captions-{i//4+1}')
        editor('27-credit','captions-import','--input',out/'credits.json','--style',out/'credit-style.json',
               '--request-id',out.name+'-credit')
        editor('28-edited','inspect'); save('edited-drafts.json',docs(state['projectPath']))
        for i,second in enumerate(plan['previewSeconds']):
            editor(f'30-frame-{i}','frame','--at-us',second*1000000,'--short-side',540,'--output',out/f'native-{second}s.png')
        editor('31-export','export','--output',out/'water-science-final.mp4','--width',1920,'--height',1080,'--fps',30)
        editor('32-after-export','inspect')
        cli('40-close','project','close','--pid',args.pid,'--project-id',state['projectId'])
        opened=cli('41-reopen','project','open','--pid',args.pid,'--project-id',state['projectId'])
        state['projectPath']=opened['projectPath'];save('project-state.json',state)
        editor('42-switch','switch-timeline');editor('43-reopened','inspect')
        save('reopened-drafts.json',docs(state['projectPath']))
        save('original-project-after.json',docs(current['path']) if current else {})
        run('44-final-asr',[SPEECH_PYTHON,'-B',ROOT/'tools/transcribe_media.py','--input',out/'water-science-final.mp4','--output',out/'final-asr.json'])
        run('45-verify',[sys.executable,'-B',ROOT/'tools/verify_real_recording.py','--run-dir',out])
        verification=read('verification.json')
        assert verification['passed']
        recorder.update('ACCEPTED | Native export: water-science-final.mp4 | 33.7 seconds | 1920x1080 | 30 fps | H.264 + AAC',
                        f"OK - {len(verification['checks'])} checks passed; fresh captions, audio mix, full decode and save/reopen verified")
        time.sleep(5)
        save('run-complete.json',{'passed':True,'project':state,'finalVideo':str(out/'water-science-final.mp4')})
    except BaseException as exc:
        save('run-error.json',{'type':type(exc).__name__,'message':str(exc),'state':state,
                                'recovery':'Inspect native state and command receipts. Do not blindly rerun mutations.'})
        raise
    finally:
        if recording:recorder.stop()
    print('COMPLETE '+str(out),flush=True)

if __name__=='__main__':main()
