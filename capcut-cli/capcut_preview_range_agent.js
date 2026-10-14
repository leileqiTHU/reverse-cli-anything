// Appended to capcut_timeline_agent.js. Native range access on the Qt UI thread.
function previewWithDraft(req,model,fn) {
 const selected=model.add(0x120).readPointer(),control=model.add(0x128).readPointer();
 if(selected.isNull()||control.isNull()||!selected.readPointer().equals(frontend.base.add(0xa6f7390))||
    !sameId(qs(selected.add(0x5f0)),req.targetDraftUUID))throw Error('Preview active timeline changed');
 const draft=Memory.alloc(16);
 try {
  nf(frontend.base.add(0x24b0d70),'pointer',['pointer','pointer'])(selected,draft);
  const p=draft.readPointer();
  if(p.isNull()||draft.add(8).readPointer().isNull()||!p.readPointer().equals(ve.base.add(0x2f59818))||!sameId(str(p.add(8)),req.targetDraftUUID))throw Error('Preview native draft identity mismatch');
  return fn(p);
 }finally{releaseShared(draft);}
}
function previewReadRange(req,model) {
 return previewWithDraft(req,model,draft=>{
  const config=nf(ve.base.add(0x2fea20),'pointer',['pointer'])(draft).readPointer();
  if(config.isNull())throw Error('Native draft config is missing');
  const range=nf(ve.base.add(0x122ae0),'pointer',['pointer'])(config).readPointer();
  if(range.isNull())return null;
  const start=nf(ve.base.add(0x100390),'pointer',['pointer'])(range).readS64().toNumber();
  const duration=nf(ve.base.add(0xff060),'pointer',['pointer'])(range).readS64().toNumber();
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(duration))throw Error('Native export range exceeds exact integer bounds');
  return {start,duration};
 });
}
rpc.exports.previewrange=req=>onUi(req,()=>withModel(req,model=>({range:previewReadRange(req,model),timelineId:req.targetDraftUUID})));
rpc.exports.previewsetrange=req=>onUi(req,()=>withModel(req,model=>{
 const ready=readiness(model,req);
 if(!ready.ready)throw Error('Native timeline is not ready for an export range change');
 const before=previewReadRange(req,model),expected=req.expectedRange,desired=req.desiredRange;
 const equal=(a,b)=>a===null?b===null:(b!==null&&a.start===b.start&&a.duration===b.duration);
 if(!equal(before,expected))throw Error('Export range changed concurrently; refusing to overwrite it');
 if(desired!==null&&(!Number.isSafeInteger(desired.start)||desired.start<0||!Number.isSafeInteger(desired.duration)||desired.duration<=0))throw Error('Invalid native export range');
 if(equal(before,desired))return {before,after:before,changed:false};
 const owned=Memory.alloc(16),response=Memory.alloc(16);
 let allocated=null,entered=false,returned=false;
 try{
  allocated=nf(frontend.base.add(0x68d98a0),'pointer',['uint64'])(0x118);
  if(allocated.isNull())throw Error('Native range allocation failed');
  nf(frontend.base.add(0x2501cd0),'pointer',['pointer'])(allocated);
  const request=allocated.add(0x10);
  owned.writePointer(request);owned.add(8).writePointer(allocated);
  if(!allocated.readPointer().equals(frontend.base.add(0xa6fde40))||!request.readPointer().equals(frontend.base.add(0xa6fdce8))||
     !request.add(0xe0).readPointer().equals(frontend.base.add(0xa6fdcd8))||request.add(0x48).readS32()!==-1||request.add(0x5c).readU8()!==1)throw Error('Native SetExportRange request constructor ABI mismatch');
  // Keep all normal constructor flags. Session::invoke resolves timeline id -1.
  // Negative start/duration uses the original handler's null-range branch.
  request.add(0xf8).writeS64(desired===null?-1:desired.start);
  request.add(0x100).writeS64(desired===null?-1:desired.duration);
  entered=true;
  nf(ve.base.add(0x17222e0),'pointer',['pointer','pointer','int'])(response,owned,req.expectedSid);
  returned=true;
  const result=response.readPointer();
  // This handler normally returns an empty shared_ptr. Getter readback is decisive.
  if(!result.isNull()&&result.add(0x4c).readS32()!==0)throw Error('Native range handler returned error '+result.add(0x4c).readS32());
  const after=previewReadRange(req,model);
  if(!equal(after,desired))throw Error('Native export range readback failed');
  return {before,after,changed:true,constructorFlagsPreserved:true};
 }finally{
  if(!entered&&allocated!==null&&!allocated.isNull())releaseShared(owned);
  if(returned)releaseShared(response);
 }
}));
