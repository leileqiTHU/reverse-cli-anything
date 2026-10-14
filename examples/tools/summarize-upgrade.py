"""Curate this dated regression from actual local reports; never create missing passes."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from reverse_cli.config import ROOT
from reverse_cli.catalog import preflight,load
from reverse_cli.journal import now,write

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p):
    p=Path(p).resolve();return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.name

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'outputs/upgrade-20261014');p.add_argument('--capcut',default='capcut-clean-session');a=p.parse_args();base=a.source.resolve()
    reports={'capcut':base/a.capcut/'regression.json','axure':base/'axure-final/regression.json','shapr3d':base/'shapr3d/regression.json'}
    summary={'schemaVersion':1,'passed':False,'date':'2026-10-14','generatedAt':now(),'mouseClicks':0,'adapters':{},'tests':{},'limits':['Current command execution is not exhaustive parameter coverage. Historical and untested commands are separated.','Shared receipt completion is not independent native state/persistence/artifact proof.','Existing interpreter installation on C: was reused; new dependencies, caches, outputs and native staging used D:.']}
    for app,path in reports.items():
        r=read(path);assert r['passed'],str(path)+' has not passed'
        commands=list(r['commands']);extra=[]
        if app=='capcut':
            workflow=path.parent/'workflow.json';w=read(workflow);assert w['ok'] and w['persistenceAfterReopenVerified'];extra.append(workflow)
            commands+=w['steps'];fixture=path.parent/'fixture.json';f=read(fixture);assert f['passed'];extra.append(fixture)
            counts={'workflowSteps':len(w['steps']),'fixtureAssertions':len(f['checks'])}
        elif app=='axure':
            native=path.parent/'native.json';browser=path.parent/'browser.json';n=read(native);b=read(browser);assert n['passed'] and b['passed'];commands+=n['commands'];extra+=[native,browser]
            counts={'nativeAssertions':len(n['checks']),'browserAssertions':len(b['checks'])}
        else:
            geometry=path.parent/'geometry-restored.json';g=read(geometry);assert g['passed'];extra.append(geometry);counts={'geometryAssertions':len(g['checks'])}
        executed=set();receipts=[]
        for c in commands:
            response=c.get('response',{});argv=c.get('argv',c.get('command'))
            if not argv or response.get('ok') is not True:continue
            # Historical requests must not be re-preflighted against today's
            # filesystem (for example the export destination now exists).
            tool=json.loads(argv[argv.index('--json')+1])['operation'] if app=='shapr3d' and '--json' in argv else preflight(app,argv)[0]
            assert tool in {t['name'] for t in load(app)['tools']}
            executed.add(tool)
            receipt=response.get('receipt',c.get('commonReceipt'))
            if isinstance(receipt,dict):receipt=receipt.get('receipt')
            if isinstance(receipt,str) and Path(receipt).is_file():receipts.append({'path':relative(receipt),'sha256':digest(Path(receipt))})
        artifacts=[]
        for item in r.get('artifacts',[]):
            file=Path(item);assert file.is_file();artifacts.append({'path':relative(file),'bytes':file.stat().st_size,'sha256':digest(file)})
        summary['adapters'][app]={'passed':True,'executedTools':sorted(executed),'orchestrationAssertions':len(r['checks']),**counts,'checks':[{'name':c['name'],'passed':c['passed']} for c in r['checks']],'reports':[{'path':relative(f),'sha256':digest(f)} for f in [path,*extra]],'artifacts':artifacts,'receiptCount':len(receipts),'receiptReferences':receipts,'limits':r.get('limits',[])}
    for name in ('shared','capcut'):
        r=read(base/(name+'-tests.json'));assert r['passed'];summary['tests'][name]={'run':r['run'],'passed':r['passedTests'],'skipped':r['skipped'],'reportSha256':digest(base/(name+'-tests.json'))}
    smoke=read(base/'portable-smoke.json');assert smoke['passed'];summary['portableSmoke']={'passed':True,'checks':len(smoke['checks']),'scope':smoke['scope']}
    summary['doctors']={}
    for app in reports:
        d=read(base/('doctor-'+app+'.json'));assert d['ok'];summary['doctors'][app]={'passed':True,'checks':len(d['checks']),'nativeReadiness':d['nativeReadiness']}
    summary['incidents']=[
      {'adapter':'axure','finding':'Cold launch readiness could outlast a three-second status wait. Repeated only read-only readiness probes; exact late request journal resolved the earlier unknown result.'},
      {'adapter':'capcut','finding':'One add-audio worker timeout occurred before mutation submission: worker exited, native write journal absent and fresh state unchanged. Retained failed receipt and verified resolution; no blind replay.'},
      {'adapter':'capcut','finding':'Native export FINISH-page automatic AI crop hid text tracks. Exact content guard rejected the first output. An intermediate completed render lacked captions and failed independent fixture acceptance. Scoped project/thread-bound suppression now prevents the secondary crop, with actual suppression events and visible EN/ZH subtitles in the final regression.'},
      {'adapter':'capcut','finding':'An older background crop export blocked a later request. Native cancel did not confirm completion. Backed up the dedicated test draft, restarted the application and retained unknown/failure evidence. Fresh full regression passed; original user project was reopened.'}
    ]
    summary['passed']=True;summary_path='evidence/upgrade-20261014.json';write(ROOT/summary_path,summary)
    registry=read(ROOT/'examples/registry.json')
    historical={'shapr3d':{'create-project','import-native','project-close','project-reopen','inspect','session-close'}}
    historical_paths={'shapr3d':'shapr3d-cli/evidence/native-model-proof-20261013.json'}
    checks=[('environment','Pinned build, explicit paths, process and doctor; activation/editability checked separately.'),('request','Correct identity and units; malformed requests rejected; JSON results and legacy compatibility retained.'),('receipt','Operation state, ID/input collision, write serialization, timeout, late completion and no automatic mutation replay.'),('native-state','Inspect actual before/after objects and preserve unrelated content.'),('persistence','Save convergence and explicitly scoped reopen; distinguish same-session from cold startup.'),('artifact','Native output and independent media/browser/geometry validation; absence of overwrite.'),('restoration','Retain failures, restore previous user project or verified model parameters; no mouse input.')]
    for entry in registry['adapters']:
        app=entry['id'];current=set(summary['adapters'][app]['executedTools']);tools=[]
        for tool in load(app)['tools']:
            name=tool['name'];coverage='current-native' if name in current else 'historical-workflow' if name in historical.get(app,set()) else 'not-run'
            refs=[summary_path] if coverage=='current-native' else [historical_paths[app]] if coverage=='historical-workflow' else []
            scope='Exact command executed in the dated bounded workflow; not every argument combination.' if coverage=='current-native' else 'Earlier native session lifecycle proof only; not rerun during this upgrade.' if coverage=='historical-workflow' else 'No current native acceptance claim; see schema, adapter guide and offline tests.'
            tools.append({'name':name,'coverage':coverage,'evidence':refs,'scope':scope})
        write(ROOT/'acceptance'/(app+'.json'),{'schemaVersion':1,'adapter':app,'build':entry['testedBuilds'][0],'checklist':[{'id':key,'assertion':value} for key,value in checks],'tools':tools})
    print(json.dumps({'passed':True,'summary':summary_path,'executedTools':{app:len(r['executedTools']) for app,r in summary['adapters'].items()}}))
if __name__=='__main__':main()
