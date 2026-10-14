"""Version-pinned JSON CLI for the running Axure RP native editor (Windows)."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.runtime'
sys.path.insert(0,str(ROOT.parent))
from reverse_cli.config import app_path, directory
APP=app_path('axure')
HASH='dae5748f6be3e69c063ef117bab0b400586d94adf119f5a9ba260df59dc4e4a7'
VERSION='11.0.0.4150'

def alive(pid):
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.OpenProcess.restype=wintypes.HANDLE
 k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
 k.CloseHandle.argtypes=[wintypes.HANDLE]
 h=k.OpenProcess(0x1000,False,pid)
 if not h:return False
 try:
  code=wintypes.DWORD();return bool(k.GetExitCodeProcess(h,ctypes.byref(code))) and code.value==259
 finally:k.CloseHandle(h)

def endpoint():
 p=STATE/'endpoint.json'
 if not p.exists():raise RuntimeError('NO_BRIDGE: run launch first')
 data=json.loads(p.read_text(encoding='utf-8-sig'))
 if not alive(data['pid']):raise RuntimeError('APP_CLOSED: run launch first')
 return data

def request(payload,timeout=30):
 import msvcrt
 ep=endpoint();rid=str(uuid.uuid4());payload=dict(payload,requestId=rid)
 wire=(json.dumps(payload,ensure_ascii=False)+'\n').encode('utf-8')
 if len(wire)>250000:raise ValueError('Request exceeds 250 KB')
 deadline=time.monotonic()+timeout;f=None
 while time.monotonic()<deadline:
  try:f=open('\\\\.\\pipe\\'+ep['pipe'],'r+b',buffering=0);break
  except OSError:time.sleep(.05)
 if f is None:raise RuntimeError('BRIDGE_UNAVAILABLE: request was not sent')
 with f:
  f.write(wire)
  k=ctypes.WinDLL('kernel32',use_last_error=True)
  k.PeekNamedPipe.argtypes=[wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,wintypes.LPVOID,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]
  handle=wintypes.HANDLE(msvcrt.get_osfhandle(f.fileno()));line=bytearray()
  while time.monotonic()<deadline:
   available=wintypes.DWORD()
   if not k.PeekNamedPipe(handle,None,0,None,ctypes.byref(available),None):break
   if available.value:
    line.extend(f.read(available.value))
    if b'\n' in line:
     result=json.loads(line.split(b'\n',1)[0]);result['requestId']=rid;return result
   time.sleep(.03)
 if payload['op']=='project.close':
  for _ in range(20):
   if not alive(ep['pid']):return {'ok':True,'result':{'closed':True,'pid':ep['pid'],'verifiedProcessExit':True},'requestId':rid}
   time.sleep(.1)
 return {'ok':False,'error':'OUTCOME_UNKNOWN: request sent; do not replay automatically','requestId':rid,'journal':str(STATE/'requests'/f'{rid}.json')}

def launch(project=None,app=APP):
 app=Path(app).resolve()
 dll=app.with_suffix('.dll')
 if hashlib.sha256(dll.read_bytes()).hexdigest()!=HASH:raise RuntimeError('UNSUPPORTED_BUILD: application hash mismatch')
 build=STATE/'bridge-build.json'
 if not build.exists():raise RuntimeError('BUILD_REQUIRED: run pwsh -File axure-cli/build.ps1')
 try:old=endpoint()
 except RuntimeError:old=None
 if old:return {'ok':False,'error':'ALREADY_RUNNING: reuse the current bridge or close its project first','pid':old['pid']}
 hook=Path(json.loads(build.read_text(encoding='utf-8-sig'))['path'])
 if not hook.exists():raise RuntimeError('Bridge DLL missing; rebuild')
 env=os.environ.copy();env.update(DOTNET_STARTUP_HOOKS=str(hook),AXURE_CLI_STATE=str(STATE),TEMP=str(directory('cache')/'axure/temp'),TMP=str(directory('cache')/'axure/temp'))
 Path(env['TEMP']).mkdir(parents=True,exist_ok=True)
 args=[str(app)]
 if project:
  project=Path(project).resolve(strict=True);args.append(str(project))
 log=(STATE/'app-launch.log').open('ab')
 proc=subprocess.Popen(args,cwd=app.parent,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
 log.close()
 startup_deadline=time.monotonic()+45
 for _ in range(120):
  if time.monotonic()>=startup_deadline:break
  if proc.poll() is not None:raise RuntimeError(f'Application exited during startup ({proc.returncode}); see app-launch.log')
  try:
   e=endpoint()
   if e['pid']==proc.pid:
    out=request({'op':'status'},timeout=3)
    if out['ok']:return dict(out,launchedPid=proc.pid)
    # Only this read-only status probe may be repeated during startup. An expired
    # status wait does not justify launching another process or replaying edits.
    if not any(code in out.get('error','') for code in ('APP_STARTING','OUTCOME_UNKNOWN')):return dict(out,launchedPid=proc.pid)
  except (RuntimeError,OSError):pass
  time.sleep(.25)
 raise RuntimeError('APP_STARTING: launch did not reach ready state within the bounded startup wait')

def parser():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--timeout',type=float,default=60)
 sub=p.add_subparsers(dest='command',required=True)
 for cmd in ('status','inspect','undo','redo','capabilities'):sub.add_parser(cmd)
 l=sub.add_parser('launch');l.add_argument('--project');l.add_argument('--app',default=str(APP))
 w=sub.add_parser('widget').add_subparsers(dest='action',required=True)
 w.add_parser('list')
 c=w.add_parser('create');c.add_argument('--text',default='');c.add_argument('--name',default='Agent widget');c.add_argument('--kind',choices=('paragraph','button','input'),default='paragraph');c.add_argument('--password',action='store_true',default=None);c.add_argument('--placeholder')
 b=w.add_parser('bounds');b.add_argument('--id',required=True)
 for command in (c,b):
  for key in ('x','y','width','height'):command.add_argument('--'+key,type=float)
 t=w.add_parser('text');t.add_argument('--id',required=True);t.add_argument('--text',required=True)
 pa=sub.add_parser('page').add_subparsers(dest='action',required=True)
 pa.add_parser('list');pc=pa.add_parser('create');pc.add_argument('--name',required=True)
 po=pa.add_parser('open');po.add_argument('--id',required=True)
 ix=sub.add_parser('interaction').add_subparsers(dest='action',required=True)
 ig=ix.add_parser('get');ig.add_argument('--id',required=True)
 it=ix.add_parser('set');it.add_argument('--id',required=True);it.add_argument('--spec',required=True,help='UTF-8 JSON click specification')
 pr=sub.add_parser('project').add_subparsers(dest='action',required=True)
 for cmd in ('new','close','sitemap'):pr.add_parser(cmd)
 s=pr.add_parser('save');s.add_argument('--path')
 o=pr.add_parser('open');o.add_argument('--path',required=True)
 ex=sub.add_parser('export').add_subparsers(dest='action',required=True)
 h=ex.add_parser('html');h.add_argument('--output',required=True)
 se=sub.add_parser('settings').add_subparsers(dest='action',required=True)
 cache=se.add_parser('cache');cache.add_argument('--path',required=True)
 return p

def main():
 a=parser().parse_args()
 try:
  if a.command=='capabilities':out={'ok':True,'result':{'application':'Axure RP','version':VERSION,'sha256':HASH,'transport':'same-user named pipe and in-process .NET startup hook','commands':['launch','status','inspect','page create','page list','page open','widget list','widget create','widget text','widget bounds','interaction get','interaction set','undo','redo','project new','project open','project save','project close','project sitemap','export html','settings cache'],'widgetKinds':['paragraph','button','input'],'clickConditions':['widget equals','any','all'],'clickActions':['setText','navigate'],'limitations':['Windows x64 and one pinned build','desktop process required','current-page widgets only','interaction installation requires empty map','replacement text uses first-run formatting','normal application activation required']}}
  elif a.command=='launch':out=launch(a.project,a.app)
  else:
   payload={'op':a.command+('.'+a.action if hasattr(a,'action') else '')}
   for key in ('id','text','name','path','output','kind','password','placeholder','x','y','width','height'):
    value=getattr(a,key,None)
    if value is not None:payload[key]=str(Path(value).resolve()) if key in ('path','output') else value
   if hasattr(a,'spec'):payload['spec']=json.loads(Path(a.spec).read_text(encoding='utf-8-sig'))
   out=request(payload,a.timeout)
 except Exception as e:out={'ok':False,'error':str(e),'kind':type(e).__name__}
 print(json.dumps(out,ensure_ascii=False))
 return 0 if out['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
