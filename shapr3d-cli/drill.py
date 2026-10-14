"""Journalled CLI for a native circular cut in the currently visible XY plate.

prepare makes a native archive/STL backup and imports a 2D circle; preview starts
the native tool and selects its region; cut sets depth; finish commits/exports.
No document database writes, external CAD solid construction, or UI input.
"""
import argparse, hashlib, json, math, os, sys, time, uuid
from pathlib import Path
from pilot import save, validate_request

def rpc(session, request):
    request=validate_request(dict(request))
    state=json.loads((session/'host.json').read_text(encoding='utf-8'))
    if state.get('status')!='ready':raise ValueError('Bridge is not ready')
    key=f'{time.time_ns()}-{uuid.uuid4().hex[:8]}'
    save(session/(key+'.request.json'),request)
    result_path=session/(key+'.result.json');end=time.monotonic()+180
    while not result_path.exists() and time.monotonic()<end:time.sleep(.1)
    if not result_path.exists():raise TimeoutError(f'Outcome unknown; inspect {key}, do not replay')
    result=json.loads(result_path.read_text(encoding='utf-8'))
    if not result.get('ok'):raise RuntimeError(result.get('error',result))
    return result['result'],str(result_path)

def call(job, request):
    job['pending']=request;save(Path(job['job']),job)
    result,receipt=rpc(Path(job['session']),request)
    job['receipts'].append({'operation':request['operation'],'receipt':receipt,'result':result})
    job.pop('pending',None);save(Path(job['job']),job)
    return result

def circle_dxf(path,x,y,z,r):
    pairs=[0,'SECTION',2,'HEADER',9,'$ACADVER',1,'AC1009',9,'$INSUNITS',70,4,
           0,'ENDSEC',0,'SECTION',2,'ENTITIES',0,'CIRCLE',8,'reverse_cli_hole',
           10,x,20,y,30,z,40,r,0,'ENDSEC',0,'EOF']
    path.write_text('\n'.join(map(str,pairs))+'\n',encoding='ascii')

def copy_export(job,name,suffix):
    src=Path(job['nativeDirectory'])/(name+suffix)
    dst=Path(job['output'])/(name+suffix)
    if dst.exists():raise ValueError('Output already exists')
    data=src.read_bytes();dst.write_bytes(data)
    return {'path':str(dst),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def prepare(a):
    for v in (a.x,a.y,a.top,a.diameter,a.depth):
        if not math.isfinite(v) or abs(v)>100:raise ValueError('Coordinates/lengths must be finite and within 100 mm')
    if a.diameter<=0 or a.top<=0 or a.depth<=a.top:raise ValueError('Require positive diameter, positive top Z, and through depth greater than top Z')
    if abs(a.x)+a.diameter/2>=40 or abs(a.y)+a.diameter/2>=20 or any(math.hypot(a.x-h,a.y)<=a.diameter/2+3 for h in (-30,30)):
        raise ValueError('Hole must lie inside the 80 x 40 plate and clear its original mounting holes')
    out=a.output.resolve();session=a.session.resolve()
    if out.drive.upper()!='D:' or session.drive.upper()!='D:':raise ValueError('Output and session must be on D:')
    out.mkdir(parents=True,exist_ok=False)
    local=(Path(os.environ['LOCALAPPDATA'])/'Packages/Shapr3D.Shapr3D_dvv5p1vgwv6mp/LocalState').resolve()
    if local.drive.upper()!='D:':raise ValueError('This adapter requires D-backed LocalState')
    native=local/('reverse-cli-drill-'+uuid.uuid4().hex[:12]);native.mkdir()
    job={'job':str(out/'job.json'),'session':str(session),'output':str(out),'nativeDirectory':str(native),
         'xMm':a.x,'yMm':a.y,'topMm':a.top,'diameterMm':a.diameter,'depthMm':a.depth,'phase':'preparing','receipts':[]}
    save(Path(job['job']),job)
    status=call(job,{'operation':'visible-status'})
    if 'EditorPage' not in status['pageType'] or status['state']['activeEditor']!=1 or status['state']['isViewOnly']:
        raise ValueError('Require an editable foreground project')
    history=call(job,{'operation':'history'})['history']
    if any(s.get('hasError') for s in history):raise ValueError('Existing history has errors')
    job['historyBefore']=history
    for op,name,suffix in [('export-shapr','before','.shapr'),('export-stl','before','.stl')]:
        call(job,{'operation':op,'directory':str(native),'name':name})
        job['before'+suffix]=copy_export(job,name,suffix)
    from verify_plate import verify, read_stl
    report=verify(out/'before.stl',length=80,width=40,thickness=a.top,pitch=60,diameter=6)
    save(out/'verification-before.json',report)
    if not report['passed']:raise ValueError('Current solid is not the expected two-hole plate; nothing imported')
    triangles,_=read_stl(out/'before.stl');points=[v for t in triangles for v in t]
    bounds=[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]
    expected=[[-40,40],[-20,20],[0,a.top]]
    if any(abs(bounds[i][j]-expected[i][j])>.1 for i in range(3) for j in range(2)):
        raise ValueError('Pilot requires the plate centered on world XY with its bottom at Z=0; nothing imported')
    # Exit active sketching normally; unavailable means already outside sketch mode.
    state=call(job,{'operation':'model-command','name':'exit-sketch','check':True})
    if state['allowed'] and not state['blocked']:call(job,{'operation':'model-command','name':'exit-sketch'})
    sketch=native/'drill-circle.dxf';circle_dxf(sketch,a.x,a.y,a.top,a.diameter/2)
    call(job,{'operation':'import-native','path':str(sketch),'name':sketch.name})
    job['phase']='prepared';save(Path(job['job']),job)
    return job

def stage(a):
    job=json.loads(a.job.read_text(encoding='utf-8'))
    if job.get('pending'):raise ValueError('A previous outcome is unknown; inspect pending receipt before proceeding')
    if a.mode=='preview':
        if job['phase'] not in ('prepared','tool-started'):raise ValueError('Expected prepared job')
        if job['phase']=='prepared':
            call(job,{'operation':'model-tool-start','tool':'extrude'})
            job['phase']='tool-started';save(Path(job['job']),job)
        center=call(job,{'operation':'model-pick','xMm':job['xMm'],'yMm':job['yMm']})['rows']
        outside=call(job,{'operation':'model-pick','xMm':job['xMm']+job['diameterMm']/2+.5,'yMm':job['yMm']})['rows']
        outside_ids={r['rawID'] for r in outside}
        candidates=[r for r in center if r['present'] and r['rawID'] not in outside_ids]
        if len(candidates)!=1:raise ValueError('Circle region cannot be uniquely isolated from outside probe')
        call(job,{'operation':'model-pick','xMm':job['xMm'],'yMm':job['yMm'],'select':True,'expectedRawID':candidates[0]['rawID']})
        job['phase']='selected'
    elif a.mode=='cut':
        if job['phase'] not in ('selected','cut-preview'):raise ValueError('Expected selected native region')
        depth=a.depth if a.depth is not None else job['depthMm']
        if not math.isfinite(depth) or depth<=0 or depth>job['depthMm']:raise ValueError('Depth exceeds prepared bound')
        if job['phase']=='cut-preview' and not job.get('cutStep'):
            # The tool rebuilds annotation IDs after the first preview. Commit
            # the new feature and refine its stable native history parameter.
            call(job,{'operation':'model-tool-finish'})
            rows=call(job,{'operation':'history'})['history'][len(job['historyBefore']):]
            candidates=[(s,p) for s in rows for p in s.get('parameters',[]) if p.get('valueType')==1 and p.get('numericType')==0 and abs(p.get('numericValue',1)+job['previewDepthMm']/1000)<1e-9]
            if len(candidates)!=1:raise ValueError('Cannot uniquely identify the committed cut distance')
            job['cutStep']=candidates[0][0]['name'];job['cutParameter']=candidates[0][1]['label'];save(Path(job['job']),job)
        if job.get('cutStep'):
            call(job,{'operation':'history-set','step':job['cutStep'],'parameter':job['cutParameter'],'expression':f'{-depth:g} mm'})
        else:
            call(job,{'operation':'model-set-distance','expression':f'{-depth:g} mm'})
        job['previewDepthMm']=depth;job['phase']='cut-preview'
    elif a.mode=='finish':
        if job['phase']!='cut-preview' or job['previewDepthMm']!=job['depthMm']:raise ValueError('Through cut preview required')
        if not job.get('cutStep'):call(job,{'operation':'model-tool-finish'})
        job['historyAfter']=call(job,{'operation':'history'})['history']
        if any(s.get('hasError') for s in job['historyAfter']):raise ValueError('Native history has errors')
        for op,name,suffix in [('export-stl','after','.stl'),('export-shapr','after','.shapr')]:
            call(job,{'operation':op,'directory':job['nativeDirectory'],'name':name})
            job['after'+suffix]=copy_export(job,name,suffix)
        job['phase']='committed-exported'
    save(Path(job['job']),job);return job

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    for mode in ('prepare','run'):
        q=s.add_parser(mode);q.add_argument('--session',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
        for flag,default in [('x',0),('y',0),('top',6),('diameter',8),('depth',8)]:q.add_argument('--'+flag,type=float,default=default)
        if mode=='run':q.add_argument('--pause-seconds',type=float,default=2)
    for mode in ('preview','cut','finish'):
        q=s.add_parser(mode);q.add_argument('--job',type=Path,required=True)
        if mode=='cut':q.add_argument('--depth',type=float)
    a=p.parse_args()
    if a.mode=='run':
        if not math.isfinite(a.pause_seconds) or not 0<=a.pause_seconds<=10:raise ValueError('Pause must be 0..10 seconds')
        job=prepare(a);print(json.dumps({'phase':'prepared','job':job['job']}),flush=True);time.sleep(a.pause_seconds)
        j=Path(job['job']);job=stage(argparse.Namespace(mode='preview',job=j));time.sleep(a.pause_seconds)
        for depth in sorted(set([min(2,a.depth),min(4,a.depth),a.depth])):
            job=stage(argparse.Namespace(mode='cut',job=j,depth=depth));print(json.dumps({'phase':job['phase'],'depthMm':depth}),flush=True);time.sleep(a.pause_seconds)
        job=stage(argparse.Namespace(mode='finish',job=j))
    else:job=prepare(a) if a.mode=='prepare' else stage(a)
    print(json.dumps({'ok':True,'phase':job['phase'],'job':job['job'],'geometryVerified':False},ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except Exception as e:print(json.dumps({'ok':False,'error':str(e),'retry':'Inspect job.json and native state; do not replay mutations blindly'},ensure_ascii=False));sys.exit(2)
