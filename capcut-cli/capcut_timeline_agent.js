// Version-pinned frontend timeline switch adapter. Script loading is inert.
'use strict';
const HASHES={
 'videoeditor.dll':'029986c9a26f3db4222402d00283cc610c81247b50ee9827e281daf626426b90',
 'lyra_cli_client.dll':'1760a1d8752c2cba1c3ea572f3c1ec0ce4e8ca0da90b0bb8032d297804bcde97',
 'VECreator.dll':'576bc1f51c0e81d50369e2ee69c157389a310151f1e75ea79813d9753be2db77',
 'Qt6Core.dll':'88f0da8219ab163c2949cb862fc00356e9c96df3bd4a0013bde14aa285bbc925'
};
const DIRECTORY='D:/Apps/CapCut2/CapCut/9.5.0.4050';
const frontend=Process.getModuleByName('VECreator.dll'),ve=Process.getModuleByName('videoeditor.dll');
const lyra=Process.getModuleByName('lyra_cli_client.dll'),qt=Process.getModuleByName('Qt6Core.dll');
const nf=(p,r,a)=>new NativeFunction(p,r,a,{abi:'win64',exceptions:'propagate'});
const norm=s=>s.replace(/\\/g,'/').replace(/\/$/,'').toLowerCase();
const sameId=(a,b)=>typeof a==='string'&&typeof b==='string'&&a.toLowerCase()===b.toLowerCase();
const uuid=s=>typeof s==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
let pending=null,attempted=false;
function qs(p){const n=p.add(16).readS64().toNumber();if(n<0||n>1024)throw Error('QString bounds');return n?p.add(8).readPointer().readUtf16String(n):'';}
function str(p){const n=p.add(16).readU64().toNumber(),c=p.add(24).readU64().toNumber();if(n>32768||c<n||c>0x7fffffff)throw Error('Native string bounds');return n?(c<16?p:p.readPointer()).readUtf8String(n):'';}
function qtExport(name,rva){const p=qt.getExportByName(name);if(!p.equals(qt.base.add(rva)))throw Error('Qt ABI mismatch');return p;}
const release=nf(lyra.base.add(0x193a0),'void',['pointer']);
const acquire=nf(ve.base.add(0xbf440),'pointer',['pointer','pointer']);
function releaseShared(p){const c=p.add(8).readPointer();if(!c.isNull())release(c);}
function sessionGuard(req){
 const server=ve.base.add(0x4243ca8),head=server.add(8).readPointer(),ready=[],seen=new Set();
 if(head.isNull())throw Error('No session registry');
 let node=head.readPointer();
 while(!node.equals(head)){
  if(node.isNull()||seen.size>=128||seen.has(node.toString()))throw Error('Session registry bounds');seen.add(node.toString());
  const sid=node.add(16).readS32(),s=node.add(24).readPointer();
  if(!s.isNull()&&sid>0&&s.add(16).readS32()===sid&&str(s.add(0x140))==='edit'&&!s.add(0x38).readPointer().isNull()&&s.add(0xf8).readU8()===1)ready.push(sid);
  node=node.readPointer();
 }
 if(ready.length!==1||ready[0]!==req.expectedSid)throw Error('Unique ready editor session changed');
 return ready[0];
}
function guard(req){
 if(!req||req.pid!==Process.id||Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Fresh x64 PID required');
 for(const m of[frontend,ve,lyra,qt])if(norm(m.path)!==norm(DIRECTORY+'/'+m.name)||req.verifiedHashes?.[m.name]!==HASHES[m.name])throw Error('Module path/hash verification required: '+m.name);
 if(!uuid(req.expectedProjectId)||!uuid(req.expectedActiveDraftUUID)||!Number.isInteger(req.expectedSid)||!/^d:[\\/]/i.test(req.expectedProjectPath||''))throw Error('Expected project, active timeline, SID and D: path required');
 const controller=frontend.base.add(0xe3aa7f0).readPointer();
 if(controller.isNull()||!controller.readPointer().equals(frontend.base.add(0xc92dcc8)))throw Error('Native window controller unavailable');
 const vm=controller.add(0x28).readPointer();
 if(vm.isNull()||!vm.readPointer().equals(frontend.base.add(0xc9312d0)))throw Error('An editor window is required');
 const app=qt.base.add(0x4d7580).readPointer();if(app.isNull())throw Error('No Qt application');
 return{controller,vm,app,sid:sessionGuard(req)};
}
function currentProject(){
 const p=Memory.alloc(16),s=Memory.alloc(16),pack=Memory.alloc(104);
 for(const o of[8,40,72])pack.add(o+24).writeU64(15);
 try{
  nf(frontend.base.add(0x4906390),'pointer',['pointer','pointer'])(frontend.base.add(0xe39e780),p);
  if(p.readPointer().isNull()||p.add(8).readPointer().isNull())throw Error('No current native project');
  nf(frontend.base.add(0x25d71e0),'pointer',['pointer','pointer'])(p.readPointer(),s);
  const store=s.readPointer(),control=s.add(8).readPointer();
  if(store.isNull()||control.isNull()||!store.readPointer().equals(store)||!store.add(8).readPointer().equals(control))throw Error('Store identity changed');
  for(const[rva,o]of[[0x1303e70,8],[0x13040b0,40],[0x1303e10,72]])nf(ve.base.add(rva),'pointer',['pointer','pointer'])(store,pack.add(o));
  return{id:str(pack.add(8)),name:str(pack.add(40)),path:str(pack.add(72))};
 }finally{nf(lyra.base.add(0x15b30),'void',['pointer'])(pack);releaseShared(s);releaseShared(p);}
}
function onUi(req, fn) {
  if (pending !== null) throw Error('A native operation is already queued');
  const initial = guard(req);
  const notify = qtExport('?notifyInternal2@QCoreApplication@@CA_NPEAVQObject@@PEAVQEvent@@@Z', 0x9ccd0);
  const eventCtor = nf(qtExport('??0QEvent@@QEAA@W4Type@0@@Z', 0xa2320), 'pointer', ['pointer', 'int']);
  const eventDtor = nf(qtExport('??1QEvent@@UEAA@XZ', 0xa2400), 'void', ['pointer']);
  const cloneEvent = nf(qtExport('?clone@QEvent@@UEBAPEAV1@XZ', 0xa2430), 'pointer', ['pointer']);
  const postEvent = nf(qtExport('?postEvent@QCoreApplication@@SAXPEAVQObject@@PEAVQEvent@@H@Z', 0x9cf10), 'void', ['pointer', 'pointer', 'int']);
  const objectThread = nf(qtExport('?thread@QObject@@QEBAPEAVQThread@@XZ', 0xe23e0), 'pointer', ['pointer']);
  const currentThread = nf(qtExport('?currentThread@QThread@@SAPEAV1@XZ', 0x1772c0), 'pointer', []);
  return new Promise((resolve, reject) => {
    let claimed = false, hook = null, timer = null, event = null, posted = false;
    const unhook = () => {if (hook !== null) {hook.detach(); hook = null;} if (timer !== null) {clearTimeout(timer); timer = null;}};
    const cleanup = () => {
      unhook(); pending = null;
      if (event !== null && !event.isNull() && !posted) {
        // QEvent::clone allocates on Qt's native heap. Its scalar-deleting
        // destructor frees an unposted clone; Qt owns every posted event.
        nf(qt.base.add(0x58f0), 'pointer', ['pointer', 'uint'])(event, 1); event = null;
      }
    };
    pending = {cancel() {if (!claimed) {claimed = true; cleanup(); reject(Error('Cancelled before native operation'));}}};
    try {
      // Use a native-owned, no-op QEvent::None addressed only to qApp. The
      // exact event pointer prevents unrelated UI callbacks from selecting
      // the scheduling point. An entry-only hook never leaves return hooks
      // outstanding in worker dispatchers or nested/modal event loops.
      const temporary = Memory.alloc(16);
      eventCtor(temporary, 0);
      try {event = cloneEvent(temporary);} finally {eventDtor(temporary);}
      if (event.isNull() || !event.readPointer().equals(qt.base.add(0x31e0e8)) ||
          !event.readPointer().readPointer().equals(qt.base.add(0x58f0)) || event.add(8).readU16() !== 0) throw Error('Native scheduling-event ABI mismatch');
      hook = Interceptor.attach(notify, {onEnter(args) {
        if (claimed || !args[0].equals(initial.app) || !args[1].equals(event)) return;
        claimed = true;
        unhook();
        try {
          if (!qt.base.add(0x4d7580).readPointer().equals(initial.app)) throw Error('Qt application changed');
          if (!currentThread().equals(objectThread(initial.app))) throw Error('Scheduling event reached the wrong Qt thread');
          const state = guard(req);
          if (!state.app.equals(initial.app) || !state.vm.equals(initial.vm) || state.sid !== initial.sid) throw Error('Editor/project session changed while queued');
          const project = currentProject();
          if (!sameId(project.id, req.expectedProjectId) || norm(project.path) !== norm(req.expectedProjectPath)) throw Error('Current project identity changed');
          const result = fn(state, project); cleanup(); setImmediate(() => resolve(result));
        } catch (e) {cleanup(); setImmediate(() => reject(e));}
      }});
      timer = setTimeout(() => {if (!claimed) {claimed = true; cleanup(); reject(Error('No Qt application scheduling event within 15 seconds; no operation attempted'));}}, 15000);
      Interceptor.flush();
      posted = true;
      postEvent(initial.app, event, 0);
    } catch (e) {cleanup(); reject(e);}
  });
}
function withModel(req,fn,diagnostic=false,discoverActive=false){
 // This is the native model registration list, not a heap/object graph scan.
 // Constructor df8040 and destructor df87f0 use the same mutex and node format.
 const registry=frontend.base.add(0xe2ce790).readPointer();
 if(registry.isNull()||registry.compare(ptr('0x10000'))<0)throw Error('Model registry unavailable');
 const mutex=registry.add(0x98),msvc=Process.getModuleByName('msvcp140.dll');
 const tryLock=nf(msvc.getExportByName('_Mtx_trylock'),'int',['pointer']);
 const unlock=nf(frontend.base.add(0x68d8fc1),'int',['pointer']);
 const owned=[],records=[];let registryCount=0,modelCount=0,initialMain=false;
 const allowInitialMain=uuid(req.expectedMainTimelineId)&&sameId(req.expectedMainTimelineId,req.expectedActiveDraftUUID);
 try{
  if(tryLock(mutex)!==0)throw Error('Native model registry busy; no operation attempted');
  try{
   if(registry.add(0x90).readS32()!==0)throw Error('Native model registry is dispatching');
   const head=registry.add(0x40).readPointer(),count=registry.add(0x48).readU64().toNumber();
   registryCount=count;
   if(head.isNull()||count<1||count>2048)throw Error('Model registry bounds');
   let node=head.readPointer(),previous=head;
   for(let i=0;i<count;i++){
    if(node.isNull()||node.equals(head)||!node.add(8).readPointer().equals(previous))throw Error('Model registry links changed');
    const sub=node.add(16).readPointer();
    if(diagnostic){
     const row={index:i,payload:sub.toString()};
     try{
      const vt=sub.readPointer();row.vtable=vt.toString();
      if(vt.compare(frontend.base)>=0&&vt.compare(frontend.base.add(frontend.size))<0){
       row.vtableRva=vt.sub(frontend.base).toString();
       const col=vt.sub(8).readPointer();
       if(col.compare(frontend.base)>=0&&col.compare(frontend.base.add(frontend.size-24))<0&&col.readU32()===1){
        row.baseOffset=col.add(4).readU32();const td=col.add(12).readU32();
        if(td<frontend.size-208){const data=new Uint8Array(frontend.base.add(td+16).readByteArray(192));let name='';for(const b of data){if(b===0)break;name+=String.fromCharCode(b);}row.type=name;}
       }
      }
      if(vt.equals(frontend.base.add(0xa6ed4b8))){
       const model=sub.sub(0x30);row.model=model.toString();row.primaryVtableRva=model.readPointer().sub(frontend.base).toString();row.current=qs(model.add(0x108));row.weakSelf=model.add(0x38).readPointer().toString();row.control=model.add(0x40).readPointer().toString();row.context=model.add(0x18).readPointer().toString();
       row.dependencies=[0x58,0x68,0x78,0x88,0x98,0x120].map(o=>({offset:'0x'+o.toString(16),pointer:model.add(o).readPointer().toString()}));
       const begin=model.add(0x130).readPointer(),end=model.add(0x138).readPointer(),length=end.sub(begin).toInt32();
       row.timelineVector={begin:begin.toString(),end:end.toString(),bytes:length,entries:[]};
       if(length>=0&&length<=16*64&&length%16===0){
        for(let j=0;j<Math.min(length/16,8);j++){
         const entry=begin.add(j*16),timeline=entry.readPointer(),control=entry.add(8).readPointer(),item={index:j,pointer:timeline.toString(),control:control.toString()};
         if(!timeline.isNull()){
          const tvt=timeline.readPointer();item.vtableRva=tvt.sub(frontend.base).toString();
          item.virtuals=[0x68,0x70,0x78,0x80,0x98].map(o=>({slot:'0x'+o.toString(16),rva:tvt.add(o).readPointer().sub(frontend.base).toString()}));
          if(tvt.equals(frontend.base.add(0xa6f7390))){
           item.id=qs(timeline.add(0x5f0));item.nativeTimelineId=timeline.add(0x5ec).readS32();item.lazyTouched=timeline.add(0x621).readU8();
           item.cachedMainDraft=timeline.add(0x80).readPointer().toString();
           item.playbackProvider=[0,8,16,24,32,40,48].map(o=>timeline.add(0x1d8+o).readPointer().toString());
           const backend=timeline.add(0x38).readPointer();item.projectBackend=backend.toString();
           if(!backend.isNull()){const bvt=backend.readPointer();item.backendVtableRva=bvt.sub(frontend.base).toString();item.backendGetters=[0xa0,0xa8].map(o=>({slot:'0x'+o.toString(16),rva:bvt.add(o).readPointer().sub(frontend.base).toString()}));}
          }
          item.bytes=Array.from(new Uint8Array(timeline.readByteArray(0x640))).map(b=>b.toString(16).padStart(2,'0')).join('');
         }
         row.timelineVector.entries.push(item);
        }
       }
      }
     }catch(e){row.error=String(e);}
     records.push(row);
    }
    if(!sub.isNull()&&sub.readPointer().equals(frontend.base.add(0xa6ed4b8))){
     modelCount++;
     const model=sub.sub(0x30),control=model.add(0x40).readPointer();
     if(!model.readPointer().equals(frontend.base.add(0xa6ed348))||!model.add(0x38).readPointer().equals(model)||control.isNull()||control.add(8).readS32()<1)throw Error('Timeline model ownership mismatch');
     const current=qs(model.add(0x108));
     if(discoverActive||sameId(current,req.expectedActiveDraftUUID)||(current===''&&allowInitialMain)){
      if(current==='')initialMain=true;
      const shared=Memory.alloc(16);acquire(model.add(0x38),shared);owned.push(shared);
      if(!shared.readPointer().equals(model)||!shared.add(8).readPointer().equals(control))throw Error('Timeline strong reference mismatch');
     }
    }
    previous=node;node=node.readPointer();
   }
   if(!node.equals(head)||!head.add(8).readPointer().equals(previous))throw Error('Model registry size changed');
  }finally{unlock(mutex);}
  if(diagnostic)return{pid:Process.id,threadId:Process.getCurrentThreadId(),registry:registry.toString(),count:registryCount,expectedActiveDraftUUID:req.expectedActiveDraftUUID,matches:owned.length,modelCount,records};
  if(owned.length!==1)throw Error('Expected exactly one live timeline model matching the active draft; found '+owned.length);
  // A freshly opened project's frontend current QString is observed empty
  // before its first tab switch. Accept that state only for the separately
  // verified native main draft, and only when this is the sole live model.
  if((initialMain||discoverActive)&&modelCount!==1)throw Error('Frontend timeline model is ambiguous');
  return fn(owned[0].readPointer(),{initialMain,observedCurrent:qs(owned[0].readPointer().add(0x108))});
 }finally{for(const shared of owned)releaseShared(shared);}
}
function inspectModel(model,project,sid,req,modelState){const current=qs(model.add(0x108));return{backend:'capcut-native-frontend-timeline',pid:Process.id,sid,threadId:Process.getCurrentThreadId(),project,activeDraftUUID:current||(modelState.initialMain?req.expectedMainTimelineId:''),frontendActiveDraftUUID:current,initialMainRepresentation:modelState.initialMain&&current===''};}
function readiness(model,req,readDraft=false){
 const begin=model.add(0x130).readPointer(),end=model.add(0x138).readPointer(),size=end.sub(begin).toInt32();
 if(size<16||size>64*16||size%16)throw Error('Timeline model vector bounds');
 const controller=frontend.base.add(0xe3aa7f0).readPointer(),vm=controller.add(0x28).readPointer();
 const result={ready:false,managerInitialized:model.add(0x188).readU8()===1,frontendRequestedUUID:qs(model.add(0x108)),windowLoaded:vm.add(0x31).readU8()===1,inputBlocked:vm.add(0x30).readU8()!==0,closing:vm.add(0x71).readU8()!==0,timelines:[]};
 for(let i=0;i<size/16;i++){
  const t=begin.add(i*16).readPointer(),control=begin.add(i*16+8).readPointer();
  if(t.isNull()||control.isNull()||!t.readPointer().equals(frontend.base.add(0xa6f7390)))throw Error('Timeline item ABI mismatch');
  const id=qs(t.add(0x5f0));if(!uuid(id))throw Error('Timeline item UUID invalid');
  const row={id,nativeTimelineId:t.add(0x5ec).readS32(),selected:t.equals(model.add(0x120).readPointer()),mainDraftPresent:!t.add(0x80).readPointer().isNull(),canvasRequested:t.add(0x621).readU8()!==0};
  const owner=t.add(0x1e0).readPointer(),cached=t.add(0x1f0).readPointer();
  row.canvasOwnerStrong=owner.isNull()?0:owner.add(8).readS32();row.canvasCachedStrong=cached.isNull()?0:cached.add(8).readS32();
  if(readDraft&&sameId(id,req.targetDraftUUID)){
   const backend=t.add(0x38).readPointer();
   if(backend.isNull()||!backend.readPointer().equals(frontend.base.add(0xcb2d610))||!backend.equals(model.add(0x88).readPointer()))throw Error('Target project backend identity changed');
   const draft=Memory.alloc(16);
   try{
    // Existing normal getter: backend.getVEDraft(UUID), shared ownership only.
    nf(frontend.base.add(0x24b0d70),'pointer',['pointer','pointer'])(t,draft);
    const p=draft.readPointer(),c=draft.add(8).readPointer();row.nativeDraft={present:!p.isNull(),owned:!c.isNull()};
    if(!p.isNull()){
     const vt=p.readPointer();row.nativeDraft.vtableRelativeToVE=vt.sub(ve.base).toString();
     if(vt.equals(ve.base.add(0x2f59818)))row.nativeDraft.uuid=str(p.add(8));
    }
   }finally{releaseShared(draft);}
  }
  result.timelines.push(row);
  if(row.selected)result.activeDraftUUID=id;
  if(sameId(id,req.targetDraftUUID))result.targetState=row;
 }
 const target=result.targetState;
 result.ready=!!(target&&target.selected&&target.nativeTimelineId>=0&&target.mainDraftPresent&&target.canvasOwnerStrong>0&&target.canvasCachedStrong>0&&target.canvasRequested&&result.managerInitialized&&result.windowLoaded&&!result.inputBlocked&&!result.closing&&sameId(result.activeDraftUUID,req.targetDraftUUID));
 return result;
}
rpc.exports={
 activereadiness(req){
  if(!req||!uuid(req.expectedMainTimelineId))throw Error('Verified main timeline UUID required');
  // Only the ordinary identity guard needs a UUID before model discovery.
  // This value is not used to select a model or assumed to be active.
  const checked={...req,expectedActiveDraftUUID:req.expectedMainTimelineId};
  return onUi(checked,()=>withModel(checked,model=>{
   const selected=model.add(0x120).readPointer(),control=model.add(0x128).readPointer();
   if(selected.isNull()||control.isNull())return{ready:false,activeDraftUUID:null,reason:'No selected timeline model'};
   if(control.add(8).readS32()<1||!selected.readPointer().equals(frontend.base.add(0xa6f7390)))throw Error('Selected timeline ownership/ABI mismatch');
   const active=qs(selected.add(0x5f0));
   if(!uuid(active))throw Error('Selected timeline UUID invalid');
   const result=readiness(model,{...checked,targetDraftUUID:active});
   // During an asynchronous switch, +108 already names the requested target
   // while +120 can still identify the old, fully loaded timeline. Reject that
   // interval rather than incorrectly authorizing a full native snapshot.
   const requested=result.frontendRequestedUUID;
   result.requestMatchesSelected=sameId(requested,active)||(requested===''&&sameId(active,req.expectedMainTimelineId));
   result.ready=result.ready&&result.requestMatchesSelected;
   return result;
  },false,true));
 },
 readiness(req){if(!uuid(req.targetDraftUUID))throw Error('Target UUID required');return onUi(req,()=>withModel(req,model=>readiness(model,req)));},
 draftreadiness(req){if(!uuid(req.targetDraftUUID))throw Error('Target UUID required');return onUi(req,()=>withModel(req,model=>readiness(model,req,true)));},
 diagnose(req){return onUi(req,state=>({...withModel(req,()=>null,true),windowContext:state.vm.add(0x20).readPointer().toString()}));},
 inspect(req){return onUi(req,(state,project)=>withModel(req,(model,modelState)=>inspectModel(model,project,state.sid,req,modelState)));},
 switchtimeline(req){
  if(attempted)throw Error('One switch attempt per agent instance');
  if(!uuid(req.targetDraftUUID))throw Error('Target timeline UUID required');
  return onUi(req,(state,project)=>withModel(req,(model,modelState)=>{
   const frontendBefore=qs(model.add(0x108)),before=frontendBefore||(modelState.initialMain?req.expectedMainTimelineId:'');
   if(!sameId(before,req.expectedActiveDraftUUID))throw Error('Active timeline changed');
   if(sameId(before,req.targetDraftUUID))return{...inspectModel(model,project,state.sid,req,modelState),before,frontendBefore,after:before,changed:false};
   const target=Memory.alloc(24),utf8=Memory.allocUtf8String(req.targetDraftUUID);
   const ctor=nf(qtExport('??0QString@@QEAA@PEBD@Z',0x3b20),'pointer',['pointer','pointer']);
   const dtor=nf(qtExport('??1QString@@QEAA@XZ',0x4000),'void',['pointer']);
   ctor(target,utf8);
   try{
    if(qs(target)!==req.targetDraftUUID)throw Error('Native QString construction mismatch');
    attempted=true;
    send({event:'native-timeline-switch',stage:'native-enter',pid:Process.id,sid:state.sid,before,target:req.targetDraftUUID});
    const accepted=nf(frontend.base.add(0x24810d0),'bool',['pointer','pointer'])(model,target);
    const after=qs(model.add(0x108));
    if(!accepted||!sameId(after,req.targetDraftUUID))throw Error('Native frontend did not confirm requested timeline');
    return{...inspectModel(model,project,state.sid,req,modelState),before,frontendBefore,after,changed:true,nativeAccepted:accepted};
   }finally{dtor(target);}
  }));
 },
 cancel(){if(pending)pending.cancel();return{attempted};}
};
