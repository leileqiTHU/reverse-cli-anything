"""Explicit native regression on installed, activated applications. No mouse input.

CapCut/Axure create independent test documents and restore the previous document.
Shapr3D backs up the existing verified demo plate, makes/restores one native cut edit.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from reverse_cli import config
from reverse_cli.journal import write,now

ROOT=config.ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',choices=['capcut','axure','shapr3d']);p.add_argument('--pid',type=int);p.add_argument('--session',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume-capcut',type=Path,help='Explicit prior regression directory whose successful workflow is resumed after verified recovery')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    report={'schemaVersion':1,'adapter':a.app,'startedAt':now(),'passed':False,'mouseClicks':0,'checks':[],'commands':[],'output':str(out)}
    def save():write(out/'regression.json',report)
    def check(name,ok,detail=None):
        report['checks'].append({'name':name,'passed':bool(ok),'detail':detail});save()
        if not ok:raise AssertionError(name)
    def call(*argv,identity=None):
        identity=identity or a.app+'-native-'+uuid.uuid4().hex
        proc=subprocess.run([sys.executable,'-B',str(ROOT/'reverse-cli.py'),'run',a.app,'--operation-id',identity,'--',*map(str,argv)],capture_output=True,text=True,encoding='utf-8',timeout=380,env=config.child_env(a.app))
        result=json.loads(proc.stdout);report['commands'].append({'argv':list(map(str,argv)),'response':result});save()
        if not result.get('ok'):raise RuntimeError(json.dumps(result,ensure_ascii=False))
        return result.get('response',result.get('recordedResponse'))
    def subscript(command,env=None):
        proc=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=600,env=env or config.child_env(a.app))
        log=out/('script-'+str(len(report['checks']))+'.log');log.write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
        check('script '+Path(command[2] if len(command)>2 and command[1]=='-B' else command[1]).name,proc.returncode==0,str(log))
    try:
        if a.app=='axure':
            before=call('status')['result'];original=before['project']['file']
            check('original document saved',not before['project']['dirty'])
            env=config.child_env('axure');env.update(REVERSE_CLI_ACCEPTANCE_GATEWAY='1',AXURE_EVIDENCE_OUTPUT=str(out/'native.json'))
            try:
                subscript([sys.executable,'-B',str(ROOT/'axure-cli/acceptance_login.py')],env)
                native=json.loads((out/'native.json').read_text(encoding='utf-8'))
                check('native login acceptance',native['passed'],len(native['checks']))
                env.update(AXURE_NATIVE_EVIDENCE=str(out/'native.json'),AXURE_BROWSER_EVIDENCE=str(out/'browser.json'))
                subscript(['node',str(ROOT/'axure-cli/verify_login.mjs')],env)
                browser=json.loads((out/'browser.json').read_text(encoding='utf-8'));check('native HTML interaction acceptance',browser['passed'],len(browser['checks']))
                check('shared receipts cover successful native calls',all(c['commonReceipt'] for c in native['commands'] if c['response']['ok']))
                report['nativeChecks']=len(native['checks']);report['browserChecks']=len(browser['checks']);report['artifacts']=[native['project'],native['htmlPage']]
            finally:
                if original and Path(original).is_file():call('project','open','--path',original)
            check('original project restored',call('status')['result']['project']['file']==original)
        elif a.app=='capcut':
            state=call('project','list','--pid',a.pid)['result'];write(out/'original-state.json',state)
            original=state.get('currentProject');report['originalProject']=original;save()
            if a.resume_capcut:
                prior=json.loads((a.resume_capcut/'regression.json').read_text(encoding='utf-8'))
                original=prior['originalProject'];report['originalProject']=original;report['resumedFrom']=str(a.resume_capcut.resolve());save()
            elif original:call('project','close','--pid',a.pid,'--project-id',original['id'])
            env=config.child_env('capcut');env['REVERSE_CLI_ACCEPTANCE_GATEWAY']='1'
            try:
                workflow=(a.resume_capcut if a.resume_capcut else out)/'workflow.json'
                if not a.resume_capcut:
                    subscript([sys.executable,'-B',str(ROOT/'capcut-cli/tests/verify_cli_workflow.py'),'--pid',str(a.pid),'--name','reverse-cli 0.2 '+uuid.uuid4().hex[:8],'--report',str(workflow)],env)
                w=json.loads(workflow.read_text(encoding='utf-8'));check('existing CLI workflow and reopen',w['ok'] and w['persistenceAfterReopenVerified'],len(w['steps']))
                if a.resume_capcut:
                    check('resume targets the existing dedicated test project',state['currentProject']['id'].upper()==w['projectId'].upper())
                project=w['projectPath'];timeline=w['editTimelineId']
                def edit(action,*args,identity=None):return call('--timeout','180','editor',action,'--pid',a.pid,'--project',project,'--timeline',timeline,*args,identity=identity)['result']
                before=edit('inspect');segment=before['clips'][0]['id']
                audio=out/'tone.wav'
                with wave.open(str(audio),'wb') as wav:
                    wav.setparams((1,2,48000,0,'NONE','not compressed'));wav.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*440*i/48000))) for i in range(96000)))
                edit('add-audio','--input',audio,'--duration-us',2000000,'--gain-db',-12)
                srt=out/'captions.srt';srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nNative CLI regression\n\n2\n00:00:01,000 --> 00:00:02,000\n中文回归验证\n',encoding='utf-8')
                edit('captions-import','--input',srt)
                patch=out/'patch.json';write(patch,{'transform':{'scaleX':.9,'scaleY':.9,'xRatio':.05,'yRatio':0}})
                identity='capcut-native-property-'+uuid.uuid4().hex
                edit('set-clip','--segment',segment,'--patch',patch,identity=identity)
                stable=edit('inspect')
                edit('set-clip','--segment',segment,'--patch',patch,identity=identity)
                check('duplicate shared operation leaves native items unchanged',edit('inspect')['items']==stable['items'])
                # Reopen the saved document before rendering, so native caption
                # track initialization is included in the render baseline.
                call('project','close','--pid',a.pid,'--project',project)
                project=call('project','open','--pid',a.pid,'--project-id',w['projectId'])['result']['projectPath']
                edit('switch-timeline')
                check('edited items persist before render',edit('inspect')['items']==stable['items'])
                edit('frame','--at-us',500000,'--output',out/'native-frame.png')
                edit('preview','--start-us',0,'--end-us',1000000,'--output',out/'native-preview.mp4')
                exported=edit('export','--output',out/'native-final.mp4');write(out/'export.json',exported)
                check('native export exists after adapter decode validation',(out/'native-final.mp4').stat().st_size>0)
                subscript([sys.executable,'-B',str(ROOT/'tools/verify-capcut-fixture.py'),str(out/'native-final.mp4'),'--report',str(out/'fixture.json')])
                call('project','close','--pid',a.pid,'--project',project)
                project=call('project','open','--pid',a.pid,'--project-id',w['projectId'])['result']['projectPath']
                edit('switch-timeline');check('audio captions properties survive reopen',edit('inspect')['items']==stable['items'])
                report['nativeWorkflowSteps']=len(w['steps']);report['artifacts']=[str(out/'native-final.mp4'),str(out/'native-frame.png'),str(out/'native-preview.mp4')]
            finally:
                current=call('project','list','--pid',a.pid)['result'].get('currentProject')
                if current:call('project','close','--pid',a.pid,'--project-id',current['id'])
                if original:call('project','open','--pid',a.pid,'--project-id',original['id'])
        else:
            if not a.session:raise ValueError('Shapr3D regression requires an explicit live pilot session')
            def shapr(operation,**args):return call('call','--session',a.session,'--json',json.dumps(dict(operation=operation,**args),ensure_ascii=False))['result']
            history=shapr('history')['history'];write(out/'history-before.json',history)
            candidates=[(s,q) for s in history for q in s.get('parameters',[]) if q.get('numericType')==0 and q.get('numericValue')==-.008]
            check('verified demo has one -8 mm through-cut',len(candidates)==1 and not any(s.get('hasError') for s in history))
            step,param=candidates[0];native=(Path(os.environ['LOCALAPPDATA'])/'Packages/Shapr3D.Shapr3D_dvv5p1vgwv6mp/LocalState').resolve()/('reverse-cli-regression-'+uuid.uuid4().hex)
            check('native staging remains on D',native.drive.upper()=='D:');native.mkdir()
            def export(name):
                for operation,suffix in [('export-shapr','.shapr'),('export-stl','.stl')]:
                    shapr(operation,directory=str(native),name=name);(out/(name+suffix)).write_bytes((native/(name+suffix)).read_bytes())
            export('before')
            sys.path.insert(0,str(ROOT/'shapr3d-cli'))
            from verify_drilled_plate import verify
            from verify_plate import read_stl
            baseline=ROOT/'shapr3d-cli/outputs/full-build-visible-20261013/drill/before.stl'
            original=verify(out/'before.stl',before=baseline);write(out/'geometry-before.json',original);check('original three-hole geometry',original['passed'],len(original['checks']))
            try:
                shapr('history-set',step=step['name'],parameter=param['label'],expression='-4 mm')
                changed=shapr('history')['history'];check('native cut distance changed',any(q.get('expression')=='-4 mm' for s in changed for q in s.get('parameters',[])))
                export('edited')
                blind=verify(out/'edited.stl',before=baseline);write(out/'geometry-edited.json',blind)
                check('independent verifier detects changed non-through hole',not blind['passed'])
                check('exported native geometry changed',hashlib.sha256((out/'edited.stl').read_bytes()).digest()!=hashlib.sha256((out/'before.stl').read_bytes()).digest())
            finally:
                shapr('history-set',step=step['name'],parameter=param['label'],expression=param['expression'])
            export('restored')
            final=verify(out/'restored.stl',before=baseline);write(out/'geometry-restored.json',final)
            check('restored geometry acceptance',final['passed'],len(final['checks']))
            check('restored STL byte-identical to backup',(out/'restored.stl').read_bytes()==(out/'before.stl').read_bytes())
            check('native history restored',shapr('history')['history']==history)
            report['geometryChecks']=len(final['checks']);report['artifacts']=[str(out/'restored.stl'),str(out/'restored.shapr')]
            report['limits']=['Current visible plate only; no fresh same-session or cold-reopen claim.']
        report['passed']=True
    except Exception as error:report['error']=str(error)
    finally:report['finishedAt']=now();save()
    print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'output':str(out),'error':report.get('error')},ensure_ascii=False))
    return 0 if report['passed'] else 2
if __name__=='__main__':raise SystemExit(main())
