async function screenshotAwait(op,timeout=30000){
 const info=await onUI(()=>query(op,'00000036-0000-0000-c000-000000000046'));
 const end=Date.now()+timeout;
 while(Date.now()<end){const s=await onUI(()=>numberResult(info,7));if(s===1)return;if(s===2||s===3)throw new Error('Screenshot async failed: '+s+', HRESULT '+await onUI(()=>numberResult(info,8)));await delay(40);}
 throw new Error('Screenshot async timeout; outcome unknown');
}
extensions.set('model-screenshot',async(req,o)=>{
 if(projectToken.isNull()||!req.path.endsWith('.png'))throw new Error('Expected owned model and PNG path');
 let shots=null;
 const d=delegate('39e2a886-b1ed-53d6-b968-587e2ef2535c',['uint','pointer'],(n,a)=>{
  if(n!==1)throw new Error('Expected one screenshot');
  const p=a.readPointer();check(call(p,1),'Screenshot AddRef');shots=[own(p)];
 });
 await onUI(()=>{
  if(numberResult(o.editor,8)!==1)throw new Error('Model is not active');
  const config=alloc(20),themes=alloc(4);config.writeFloat(1280);config.add(4).writeFloat(960);
  for(const offset of [8,11,12,13,14,15,16,17])config.add(offset).writeU8(1);
  check(call(o.editor,20,['pointer','uint','pointer','pointer'],[config,1,themes,d.pointer]),'CreateScreenshots');
 });
 const end=Date.now()+30000;while(shots===null&&Date.now()<end&&!d.error)await delay(30);
 if(d.error)throw new Error(d.error);if(!shots)throw new Error('Native screenshot callback timeout');
 if(await onUI(()=>numberResult(shots[0],7,'bool')))throw new Error('Native screenshot is empty');
 const getFile=await onUI(()=>pointerResult(factory('Windows.Storage.StorageFile','5984c710-daf2-43c8-8bb4-a4d3eacfd03f'),6,['pointer'],[hstr(req.path)]));
 await screenshotAwait(getFile);const file=await onUI(()=>pointerResult(getFile,8));
 const save=await onUI(()=>pointerResult(shots[0],8,['pointer','pointer'],[file,nullp]));await screenshotAwait(save);
 await onUI(()=>check(call(save,8),'PNG save GetResults'));
 return {path:req.path,renderedBy:'Shapr3D native model renderer',isApplicationWindowScreenshot:false,theme:0,requestedSize:[1280,960]};
});
