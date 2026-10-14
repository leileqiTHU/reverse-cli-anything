"""Read-only environment checks: no app launch, attachment, login or project changes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from reverse_cli import config
from examples.legacy_catalog import module

def inspect(app, pid=None, inventory=None):
    checks=[]
    def add(name,ok,detail,required=True):checks.append(dict(name=name,passed=bool(ok),required=required,detail=detail))
    add('platform',os.name=='nt' and platform.machine().lower() in ('amd64','x86_64'),'Windows x64 required for native adapters')
    try:
        probe=subprocess.run([config.python(),'-B','-c','import sys,json;print(json.dumps(list(sys.version_info[:3])))'],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        version=json.loads(probe.stdout);valid=probe.returncode==0 and tuple(version)>=(3,11)
    except (OSError,ValueError,subprocess.TimeoutExpired):version=None;valid=False
    add('python',valid,{'executable':config.python(),'version':version,'doctorInterpreter':sys.executable})
    processes=inventory();name={'capcut':'CapCut.exe','axure':'AxureRP11.exe','shapr3d':'Shapr3D.exe'}[app]
    candidates=[p for p in processes if p['Name'].lower()==name.lower() and (pid is None or p['ProcessId']==pid)]
    add('process',bool(candidates),candidates,pid is not None)
    path=config.app_path(app)
    explicit=config.value({'capcut':'capcutDir','axure':'axureApp','shapr3d':'shapr3dApp'}[app],{'capcut':'CAPCUT_DIR','axure':'AXURE_APP','shapr3d':'SHAPR3D_APP'}[app])
    if candidates and not explicit and (path is None or not path.exists()):
        path=Path(candidates[0]['ExecutablePath']);path=path.parent if app=='capcut' else path
    if app=='capcut':
        sys.path.insert(0,str(config.ROOT/'capcut-cli'))
        from capcut_store_worker import STORE_PINS
        pins=STORE_PINS
        base=path
    elif app=='axure':
        pins={'AxureRP11.dll':module(app).HASH};base=path.parent
    else:
        # Constants are read from the adapter; this does not invoke native code.
        sys.path.insert(0,str(config.ROOT/'shapr3d-cli'))
        from shapr_agent import HASHES
        pins=HASHES;base=path.parent if path else None
    for filename,expected in pins.items():
        file=base/filename if base else None
        actual=hashlib.sha256(file.read_bytes()).hexdigest() if file and file.is_file() else None
        add('module:'+filename,actual==expected,{'path':str(file) if file else None,'expectedSha256':expected,'actualSha256':actual})
    paths=config.native_tools(app)
    old=list(sys.path)
    try:
        sys.path[:0]=paths
        if app in ('capcut','shapr3d'):add('frida',importlib.util.find_spec('frida') is not None,paths)
    finally:sys.path[:]=old
    if app=='capcut':
        f=config.ffmpeg(app);add('ffmpeg',f is not None and f.is_file(),str(f))
    if app=='axure':
        build=config.ROOT/'axure-cli/.runtime/bridge-build.json'
        add('bridge-build',build.is_file(),str(build))
        endpoint=config.ROOT/'axure-cli/.runtime/endpoint.json'
        ep=json.loads(endpoint.read_text(encoding='utf-8-sig')) if endpoint.is_file() else {}
        add('bridge-process',any(p['ProcessId']==ep.get('pid') for p in candidates),ep,False)
    for kind in ('cache','state','output'):
        p=config.directory(kind);existing=p
        while not existing.exists() and existing!=existing.parent:existing=existing.parent
        add(kind+'-directory',existing.is_dir() and os.access(existing,os.W_OK),{'path':str(p),'nearestExistingParent':str(existing),'writeProbePerformed':False})
    ok=all(c['passed'] for c in checks if c['required'])
    return {'ok':ok,'adapter':app,'checks':checks,'nativeReadiness':'not-probed','notes':['Doctor does not prove login, editable project state or native execution. Use the adapter status/inspect command next.','No installation, cache migration or application mutation performed.']}
