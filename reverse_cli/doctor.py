"""Core diagnostics work with zero adapters and never start a target application."""
import json
import os
import subprocess
import sys
from . import config, registry

def inventory():
    if os.name!='nt':return []
    code="Get-CimInstance Win32_Process | Select-Object ProcessId,Name,ExecutablePath,CreationDate | ConvertTo-Json -Compress"
    proc=subprocess.run(['powershell.exe','-NoProfile','-Command',code],capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode:raise RuntimeError('Process inventory failed: '+proc.stderr)
    data=json.loads(proc.stdout or '[]')
    return data if isinstance(data,list) else [data]

def inspect(app=None,pid=None):
    checks=[]
    def add(name,ok,detail,required=True):checks.append(dict(name=name,passed=bool(ok),required=required,detail=detail))
    try:
        result=subprocess.run([config.python(),'-B','-c','import sys,json;print(json.dumps(list(sys.version_info[:3])))'],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        version=json.loads(result.stdout);valid=result.returncode==0 and tuple(version)>=(3,11)
    except (OSError,ValueError,subprocess.TimeoutExpired):version=None;valid=False
    add('python',valid,{'executable':config.python(),'version':version,'doctorInterpreter':sys.executable})
    for kind in ('cache','state','output'):
        path=config.directory(kind);parent=path
        while not parent.exists() and parent!=parent.parent:parent=parent.parent
        add(kind+'-directory',parent.is_dir() and os.access(parent,os.W_OK),{'path':str(path),'writeProbePerformed':False})
    try:installed=registry.entries();add('registry',True,{'registeredAdapters':len(installed),'emptyRegistrySupported':True})
    except (OSError,ValueError,KeyError) as error:add('registry',False,str(error))
    if app:
        entry=registry.find(app)
        checks+=registry.invoke(entry,'doctor_checks',pid,inventory,default=[])
        add('entrypoint',registry.reference(entry,'entrypoint').is_file(),entry['entrypoint'])
    return {'ok':all(c['passed'] for c in checks if c['required']),'adapter':app,'scope':'adapter' if app else 'core','checks':checks,'nativeReadiness':'not-probed','notes':['Core setup requires no target application or showcase dependency.','Doctor does not establish activation, editable state or native execution.']}
