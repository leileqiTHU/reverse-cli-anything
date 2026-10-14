"""Additive shared CLI: legacy responses are preserved inside the execution envelope."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from . import config
from .catalog import command, load, mutates, preflight
from . import registry
from .journal import Journal, classify, digest, now, operation_id, write, refresh, resolve

def run(app, argv, identity=None, timeout=360):
    if not argv:raise ValueError('Pass adapter arguments after --')
    if not 1<=timeout<=1800:raise ValueError('timeout must be between 1 and 1800 seconds')
    identity=operation_id(identity);journal=Journal(config.directory('state'));entry=registry.find(app)
    request={'adapter':app,'argv':argv,'python':config.python(),'targetConfiguration':{'app':str(config.app_path(app))}}
    # Bind input-file contents, not just filenames; output/project paths are not inputs here.
    inputs={}
    for i,arg in enumerate(argv[:-1]):
        if arg in ('--input','--spec','--patch','--style'):
            p=Path(argv[i+1])
            if p.is_file():
                import hashlib
                inputs[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    request['inputHashes']=inputs;signature=digest(request)
    if journal.path(identity).exists():
        old=journal.get(identity)
        if old['requestDigest']!=signature:raise ValueError('operation-id was already used with different arguments or input contents')
        return {'ok':old.get('ok',False),'operationId':identity,'state':old['state'],'recordedResponse':old.get('response'),
                'replayed':True,'freshStateVerified':False,'receipt':str(journal.path(identity)),
                'message':'Retained receipt only; no command was resubmitted. Inspect the application for current state.'}
    record={'schemaVersion':1,'operationId':identity,'adapter':app,'request':request,'requestDigest':signature,
            'createdAt':now(),'updatedAt':now(),'state':'not-submitted','ok':False,'ownerPid':os.getpid(),
            'childPid':None,'tool':None,'mutation':False,'response':None,'exitCode':None,
            'nativeEvidence':[],'verification':{'nativeState':False,'persistence':False,'artifact':False}}
    path=journal.reserve(record);lock=None;child=None
    try:
        try:
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                tool,args=preflight(app,argv)
        except SystemExit as e:raise ValueError('Invalid adapter arguments; use tools describe or adapter help') from e
        record.update(tool=tool,mutation=mutates(app,tool))
        if record['mutation']:lock=journal.acquire(app,identity)
        work=config.directory('cache')/'operations'/identity;work.mkdir(parents=True,exist_ok=False)
        record['logs']=str(work);record['lock']=str(lock) if lock else None
        env=config.child_env(app)
        argv=registry.invoke(entry,'prepare',argv,identity,default=argv)
        # Mark uncertainty before crossing the process boundary.
        record.update(state='running',updatedAt=now());write(path,record)
        with (work/'stdout.log').open('wb') as out,(work/'stderr.log').open('wb') as err:
            child=subprocess.Popen([config.python(),'-B',str(registry.reference(entry,'entrypoint')),*argv],stdout=out,stderr=err,cwd=entry['_root'],env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            record['childPid']=child.pid;write(path,record)
            try:code=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record.update(state='unknown',error='Deadline exceeded. Child is retained; timeout does not cancel native work.')
                code=None
        if code is not None:
            record['exitCode']=code
            raw=(work/'stdout.log').read_text(encoding='utf-8-sig')
            try:response=json.loads(raw)
            except (ValueError,TypeError):response={'ok':False,'error':'Adapter did not return a JSON response; inspect logs'}
            record.update(response=response,ok=response.get('ok') is True and code==0,state=classify(response,code,record['mutation']))
            if registry.invoke(entry,'successful',tool,response,code,default=False):
                record.update(ok=True,state='completed')
            for owner in (response,response.get('result',{}),response.get('error',{})):
                if isinstance(owner,dict):
                    for key in ('logs','receipt','journal','recoveryFile'):
                        if isinstance(owner.get(key),str):record['nativeEvidence'].append({'kind':key,'path':owner[key]})
            record['nativeEvidence']+=registry.invoke(entry,'evidence',response,default=[])
    except Exception as error:
        record.update(error=str(error),ok=False)
        if record['state']=='running':record['state']='unknown' if child is not None else 'not-submitted'
    finally:
        record['updatedAt']=now();write(path,record)
        if lock and record['state'] not in ('unknown','partially-applied'):
            lock.unlink(missing_ok=True)
    return {'ok':record['ok'],'operationId':identity,'state':record['state'],'response':record['response'],
            'receipt':str(path),'replayed':False,**({'error':record['error']} if 'error' in record else {})}

def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    raw=list(sys.argv[1:] if argv is None else argv)
    forwarded=[]
    if raw[:1]==['run'] and '--' in raw:
        boundary=raw.index('--');forwarded=raw[boundary+1:];raw=raw[:boundary]
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    ls=subs.add_parser('list');ls.add_argument('--examples',action='store_true')
    d=subs.add_parser('doctor');d.add_argument('adapter',nargs='?');d.add_argument('--pid',type=int)
    t=subs.add_parser('tools');t.add_argument('adapter');t.add_argument('--name')
    r=subs.add_parser('run');r.add_argument('adapter');r.add_argument('--operation-id');r.add_argument('--timeout',type=float,default=360)
    c=subs.add_parser('call');c.add_argument('adapter');c.add_argument('tool');c.add_argument('--args',required=True,help='JSON object or @file');c.add_argument('--operation-id');c.add_argument('--timeout',type=float,default=360)
    reg=subs.add_parser('register');reg.add_argument('manifest',type=Path)
    init=subs.add_parser('init');init.add_argument('adapter');init.add_argument('--output',type=Path,required=True)
    ac=subs.add_parser('acceptance');ac.add_argument('report',type=Path)
    o=subs.add_parser('operation');o.add_argument('action',choices=['get','list','refresh','resolve']);o.add_argument('id',nargs='?');o.add_argument('--adapter')
    o.add_argument('--evidence',type=Path)
    try:
        a=parser.parse_args(raw)
        if a.command=='list':result={'ok':True,'adapters':[registry.public(e) for e in registry.entries(examples=a.examples)],'includesExamples':a.examples}
        elif a.command=='register':result={'ok':True,'adapter':registry.public(registry.register(a.manifest))}
        elif a.command=='init':
            from .scaffold import create
            result=create(a.adapter,a.output)
        elif a.command=='acceptance':
            from .acceptance import inspect
            result=inspect(a.report)
        elif a.command=='doctor':
            from .doctor import inspect
            result=inspect(a.adapter,a.pid)
        elif a.command=='tools':
            catalog=load(a.adapter);result={'ok':True,'result':next(t for t in catalog['tools'] if t['name']==a.name) if a.name else catalog}
        elif a.command=='operation':
            journal=Journal(config.directory('state'))
            if a.action=='resolve':
                if not a.id or not a.evidence:raise ValueError('operation resolve requires ID and --evidence')
                result={'ok':True,'result':resolve(journal,a.id,a.evidence)}
            elif a.action in ('get','refresh'):
                if not a.id:raise ValueError('operation get/refresh requires an ID')
                result={'ok':True,'result':journal.get(a.id) if a.action=='get' else refresh(journal,a.id)}
            else:
                records=[journal.get(p.stem) for p in (journal.root/'operations').glob('*.json')]
                result={'ok':True,'result':[{k:r.get(k) for k in ('operationId','adapter','tool','state','ok','updatedAt')} for r in sorted(records,key=lambda r:r['createdAt'],reverse=True) if not a.adapter or r['adapter']==a.adapter]}
        elif a.command=='call':
            raw=Path(a.args[1:]).read_text(encoding='utf-8-sig') if a.args.startswith('@') else a.args
            result=run(a.adapter,command(a.adapter,a.tool,json.loads(raw)),a.operation_id,a.timeout)
        else:
            result=run(a.adapter,forwarded,a.operation_id,a.timeout)
        print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 2
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error),'kind':type(error).__name__},ensure_ascii=False));return 2
