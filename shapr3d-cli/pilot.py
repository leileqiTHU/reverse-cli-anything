"""Local pilot harness: serialized JSON queue, no network listener or UI input."""
import argparse,json,math,os,re,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from reverse_cli.config import native_tools
for dependency in reversed(native_tools('shapr3d')):sys.path.insert(0,dependency)
sys.path.insert(0,str(ROOT/'shapr3d-cli'))
from shapr_agent import validate_target
OPERATIONS={'inspect','history','create-project','import-native','history-set','export-stl','export-shapr','project-close','project-reopen','session-close','model-select-sketch','model-annotations','model-tool-start','model-tool-finish','model-pick','model-set-distance','model-screenshot'}
OPERATIONS.update({'visible-status','model-command'})
OPERATIONS.add('model-clear-demo')

def validate_request(request):
    if not isinstance(request,dict) or request.get('operation') not in OPERATIONS:
        raise ValueError('Unknown pilot operation')
    op=request['operation']
    if op=='model-clear-demo':
        backup=Path(request['backup']).resolve(strict=True)
        if backup.drive.upper()!='D:' or backup.suffix.lower()!='.shapr' or backup.stat().st_size<1024:raise ValueError('Demo reset requires a nonempty native project archive on D:')
        if request.get('confirm')!='replace-backed-up-demo-plate' or not isinstance(request.get('expectedHistory'),list) or not 1<=len(request['expectedHistory'])<=8:raise ValueError('Explicit demo reset and exact small history snapshot required')
    if op=='model-command':
        if request.get('name') not in ('exit-sketch','deselect','default-view','zoom-fit','undo'):raise ValueError('Unsupported model command')
        if 'check' in request and not isinstance(request['check'],bool):raise ValueError('check must be boolean')
    if op=='import-native':
        path=Path(request['path']).resolve(strict=True)
        if path.suffix.lower() not in ('.shapr','.dxf') or not path.is_file():raise ValueError('Pilot import supports an existing .shapr or .dxf file')
        request['path']=str(path);request['name']=path.name
    if op=='history-set':
        for key in ('step','parameter','expression'):
            if not isinstance(request.get(key),str) or not request[key]:raise ValueError(f'Missing {key}')
    if op in ('export-stl','export-shapr'):
        directory=Path(request['directory']).resolve()
        name=request['name']
        if directory.drive.upper()!='D:' or not directory.is_dir():raise ValueError('Export requires an existing D: directory')
        if not isinstance(name,str) or not name or any(c in name for c in '\\/:*?\"<>|') or name.endswith(('.', ' ')):raise ValueError('Invalid export basename')
        suffix='.stl' if op=='export-stl' else '.shapr'
        if name.lower().endswith(suffix):raise ValueError('Use a basename without the extension; native exporter appends it')
        if (directory/(name+suffix)).exists():raise ValueError('Export destination already exists')
        request['directory']=str(directory)
    if op=='model-tool-start' and request.get('tool') not in ('extrude','move-rotate'):
        raise ValueError('Supported tools: extrude, move-rotate')
    if op=='model-set-distance':
        expression=request.get('expression','')
        if not isinstance(expression,str) or not re.fullmatch(r'[-+]?\d+(?:\.\d+)? mm',expression) or len(expression)>15 or abs(float(expression[:-3]))>100:
            raise ValueError('Pilot requires an explicit mm expression within +/-100 mm')
    if op=='model-pick':
        for key in ('xMm','yMm'):
            if key in request and (not isinstance(request[key],(int,float)) or not math.isfinite(request[key]) or abs(request[key])>100):raise ValueError('Coordinates must be finite and within 100 mm')
        if 'expectedRawID' in request and (not isinstance(request['expectedRawID'],str) or not re.fullmatch(r'\d{1,20}',request['expectedRawID']) or int(request['expectedRawID'])>=2**64):raise ValueError('Expected a uint64 decimal native ID from a recent pick')
        for key in ('nearMm','farMm'):
            if key in request and (not isinstance(request[key],list) or len(request[key])!=3 or any(not isinstance(v,(float,int)) or not math.isfinite(v) or abs(v)>100 for v in request[key])):
                raise ValueError('World ray requires three finite coordinates within +/-100 mm')
        for key in ('select','additive'):
            if key in request and not isinstance(request[key],bool):raise ValueError('Selection flags must be boolean')
    if op=='model-screenshot':
        path=Path(request['path']).absolute()
        local=Path(os.environ['LOCALAPPDATA'])/'Packages/Shapr3D.Shapr3D_dvv5p1vgwv6mp/LocalState'
        resolved=path.resolve(strict=True)
        if resolved.drive.upper()!='D:' or not resolved.is_relative_to(local.resolve()) or resolved.suffix.lower()!='.png' or resolved.stat().st_size!=0:
            raise ValueError('Screenshot requires an empty reserved PNG in D-backed Shapr3D LocalState')
        # WinRT requires the package's logical path even when the bytes live on D:.
        request['path']=str(local/resolved.relative_to(local.resolve()))
    return request

def save(path,obj):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def host(pid,folder):
    import frida
    target=validate_target(pid);session=frida.attach(pid)
    script=session.create_script((ROOT/'shapr3d-cli/native_bridge.js').read_text(encoding='utf-8'))
    script.on('message',lambda m,d:print(json.dumps(m),flush=True))
    script.load()
    script.exports_sync.extend((ROOT/'shapr3d-cli/operations.js').read_text(encoding='utf-8'))
    for extension in ('frontend.js','visible_modeling.js','modeling.js','native_screenshot.js','native_archive.js'):
        script.exports_sync.extend((ROOT/'shapr3d-cli'/extension).read_text(encoding='utf-8'))
    save(folder/'host.json',{'pid':os.getpid(),'target':target,'status':'ready'})
    try:
        while True:
            pending=sorted(folder.glob('*.request.json'))
            for path in pending:
                out=path.with_name(path.name.replace('.request.json','.result.json'))
                if out.exists():continue
                request=json.loads(path.read_text(encoding='utf-8'))
                try:
                    request=validate_request(request)
                    if request['operation']=='session-close':
                        result=script.exports_sync.close()
                    else:result=script.exports_sync.run(request)
                    save(out,{'ok':True,'request':request,'result':result})
                    if request['operation']=='session-close' and result['safeToDetach']:return
                except Exception as e:save(out,{'ok':False,'request':request,'error':str(e)})
            time.sleep(0.05)
    finally:
        state=script.exports_sync.lifecycle()
        if not state['safeToDetach']:
            save(folder/'host.json',{'pid':os.getpid(),'status':'retaining-native-callbacks','lifecycle':state})
            while not script.exports_sync.close()['safeToDetach']:time.sleep(1)
        script.unload();session.detach()
        save(folder/'host.json',{'pid':os.getpid(),'status':'closed'})

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['start','host','call']);p.add_argument('--pid',type=int);p.add_argument('--session',type=Path);p.add_argument('--json');a=p.parse_args()
    folder=(a.session or ROOT/'shapr3d-cli/.runtime/sessions'/uuid.uuid4().hex).resolve()
    if folder.drive.upper()!='D:':raise ValueError('Session storage must be on D:')
    if a.mode=='start':
        validate_target(a.pid);folder.mkdir(parents=True,exist_ok=False)
        with (folder/'host.log').open('w',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,'-B',__file__,'host','--pid',str(a.pid),'--session',str(folder)],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        end=time.monotonic()+10
        while not (folder/'host.json').exists() and time.monotonic()<end:time.sleep(.1)
        ready=(folder/'host.json').exists()
        print(json.dumps({'session':str(folder),'hostPid':proc.pid,'ready':ready}))
        return 0 if ready else 2
    elif a.mode=='host':host(a.pid,folder)
    else:
        request=validate_request(json.loads(a.json));key=f'{time.time_ns()}-{uuid.uuid4().hex[:8]}'
        host_state=json.loads((folder/'host.json').read_text(encoding='utf-8'))
        if host_state.get('status')!='ready':raise ValueError('Session is not ready')
        save(folder/(key+'.request.json'),request);out=folder/(key+'.result.json');end=time.monotonic()+180
        while not out.exists() and time.monotonic()<end:time.sleep(.1)
        if not out.exists():raise TimeoutError(f'Request still pending: {key}; do not resubmit blindly')
        result=json.loads(out.read_text(encoding='utf-8'));result['receipt']=str(out)
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result['ok'] else 2
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError,TimeoutError) as exc:
        print(json.dumps({'ok':False,'status':'not-submitted-or-unknown','error':str(exc)},ensure_ascii=False));raise SystemExit(2)
