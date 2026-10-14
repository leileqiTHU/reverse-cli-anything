"""Record a real, visible native plate build from an empty backed-up demo project.

Requires explicit --replace-current-demo, verified screen capture coordinates,
and the version-pinned public pilot session. No mouse or keyboard input.
"""
import argparse, json, os, subprocess, sys, time, uuid
from pathlib import Path
import drill
from pilot import save

def outline(path):
    p=[0,'SECTION',2,'HEADER',9,'$ACADVER',1,'AC1009',9,'$INSUNITS',70,4,0,'ENDSEC',0,'SECTION',2,'ENTITIES']
    vertices=[(-40,-20),(40,-20),(40,20),(-40,20)]
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):p += [0,'LINE',8,'0',10,a[0],20,a[1],30,0,11,b[0],21,b[1],31,0]
    for x in (-25,25):p += [0,'CIRCLE',8,'0',10,x,20,0,30,0,40,3]
    p += [0,'ENDSEC',0,'EOF'];path.write_text('\n'.join(map(str,p))+'\n',encoding='ascii')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True);p.add_argument('--replace-current-demo',action='store_true',required=True)
    p.add_argument('--baseline-two-hole',type=Path,required=True,help='Previously verified native STL before the central hole')
    for k in ('capture-x','capture-y','capture-width','capture-height'):p.add_argument('--'+k,type=int,required=True)
    a=p.parse_args();out=a.output.resolve()
    if out.drive.upper()!='D:':raise ValueError('D: output required')
    a.ffmpeg=a.ffmpeg.resolve(strict=True);a.baseline_two_hole=a.baseline_two_hole.resolve(strict=True)
    if min(a.capture_x,a.capture_y)<0 or not 64<=a.capture_width<=8192 or not 64<=a.capture_height<=8192:raise ValueError('Expected observed desktop capture bounds')
    out.mkdir(parents=True,exist_ok=False)
    native=(Path(os.environ['LOCALAPPDATA'])/'Packages/Shapr3D.Shapr3D_dvv5p1vgwv6mp/LocalState').resolve()/('reverse-cli-full-'+uuid.uuid4().hex[:12]);native.mkdir()
    job={'job':str(out/'job.json'),'session':str(a.session.resolve()),'output':str(out),'nativeDirectory':str(native),'receipts':[],'phase':'backup'}
    save(Path(job['job']),job);call=lambda request:drill.call(job,request)
    state=call({'operation':'visible-status'})
    if 'EditorPage' not in state['pageType'] or state['state']['isViewOnly']:raise ValueError('An editable demo must be open')
    previous=call({'operation':'history'})['history']
    for operation,name,suffix in [('export-shapr','previous-demo','.shapr'),('export-stl','previous-demo','.stl')]:
        call({'operation':operation,'directory':str(native),'name':name});drill.copy_export(job,name,suffix)
    # Match this task's known three-hole plate independently before resetting it.
    from verify_drilled_plate import verify as verify_three
    previous_report=verify_three(out/'previous-demo.stl',before=a.baseline_two_hole,length=80,width=40,thickness=6,pitch=60,existing_diameter=6,new_diameter=8)
    save(out/'previous-demo-verification.json',previous_report)
    if not previous_report['passed']:raise ValueError('Current solid is not the backed-up demonstration plate')
    call({'operation':'model-clear-demo','expectedHistory':previous,'backup':str(out/'previous-demo.shapr'),'confirm':'replace-backed-up-demo-plate'})
    job['phase']='empty';save(Path(job['job']),job)
    log=(out/'recording.log').open('w',encoding='utf-8')
    capture=f'ddagrab=framerate=15:draw_mouse=0:offset_x={a.capture_x}:offset_y={a.capture_y}:video_size={a.capture_width}x{a.capture_height}'
    command=[str(a.ffmpeg.resolve()),'-hide_banner','-loglevel','warning','-n','-f','lavfi','-i',capture,
             '-vf','hwdownload,format=bgra,scale=1026:802','-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'full-build.mp4')]
    recording=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    start=time.monotonic();job['recording']={'file':str(out/'full-build.mp4'),'capture':'DXGI Desktop Duplication, observed Shapr3D bounds','fps':15,'events':[]}
    def show(phase):
        event={'phase':phase,'seconds':round(time.monotonic()-start,3)};job['recording']['events'].append(event);save(Path(job['job']),job);print(json.dumps(event),flush=True);time.sleep(3)
        if recording.poll() is not None:raise RuntimeError('Recorder stopped unexpectedly; inspect recording.log')
    try:
        show('empty-model')
        sketch=native/'plate-outline.dxf';outline(sketch)
        call({'operation':'import-native','path':str(sketch),'name':sketch.name});show('rectangle-and-two-circles')
        call({'operation':'model-tool-start','tool':'extrude'});call({'operation':'model-pick','xMm':0,'yMm':0,'select':True})
        call({'operation':'model-set-distance','expression':'4 mm'});show('native-extrude-4mm')
        call({'operation':'model-tool-finish'})
        rows=call({'operation':'history'})['history']
        candidates=[(s,q) for s in rows for q in s.get('parameters',[]) if q.get('numericType')==0 and q.get('numericValue')==.004]
        if len(candidates)!=1:raise ValueError('Cannot identify plate thickness parameter')
        call({'operation':'history-set','step':candidates[0][0]['name'],'parameter':candidates[0][1]['label'],'expression':'6 mm'});show('thickness-6mm')
        for side in (1,-1):
            call({'operation':'model-tool-start','tool':'move-rotate'})
            call({'operation':'model-pick','nearMm':[25*side,0,3],'farMm':[35*side,0,3],'select':True})
            call({'operation':'model-set-distance','expression':f'{5*side} mm'})
            call({'operation':'model-tool-finish'});show('right-hole-moved' if side==1 else 'mounting-hole-pitch-60mm')
        job['phase']='plate-created';save(Path(job['job']),job)
        d=drill.prepare(argparse.Namespace(session=a.session,output=out/'drill',x=0,y=0,top=6,diameter=8,depth=8));show('new-center-circle')
        drill_job=Path(d['job']);drill.stage(argparse.Namespace(mode='preview',job=drill_job));show('center-region-selected')
        for depth in (2,4,8):
            drill.stage(argparse.Namespace(mode='cut',job=drill_job,depth=depth));show(f'center-cut-{depth}mm')
        drill.stage(argparse.Namespace(mode='finish',job=drill_job));show('native-export-complete')
        job['phase']='completed';save(Path(job['job']),job)
    finally:
        if recording.poll() is None:
            recording.stdin.write(b'q\n');recording.stdin.flush();recording.wait(timeout=20)
        log.close();job['recording']['exitCode']=recording.returncode;save(Path(job['job']),job)
    if recording.returncode!=0:raise RuntimeError('Recorder failed; do not treat the video as accepted')
    print(json.dumps({'completed':True,'recording':str(out/'full-build.mp4'),'job':job['job']}),flush=True)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except Exception as e:print(json.dumps({'ok':False,'error':str(e),'warning':'Do not retry automatically; inspect the journal and current model'}),flush=True);sys.exit(2)
