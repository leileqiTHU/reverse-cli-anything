// Version-pinned, exercised native modeling pilot. No fixture clearing or UI input.
extensions.set('model-tool-start',async(req,o)=>{
 await ensureModelMutation(o);
 const allowedTools={extrude:220,'move-rotate':236};if(!(req.tool in allowedTools))throw new Error('Unsupported tool');
 req={...req,command:allowedTools[req.tool],perform:true};
 let store,ctx,allowed=null,blocked;
 const can=delegate('70584c5e-c66a-5a3c-ab58-1f0614e6f485',['uchar'],x=>allowed=!!x);
 await onUI(()=>{
  store=pointerResult(o.app,23);ctx=pointerResult(factory('Shapr.CommonApp.MTCommandContext',COM.contextFactory),6,['int'],[0]);
  if(numberResult(ctx,8,'bool'))throw new Error('Unexpected bypass context');
  const out=alloc(1);check(call(store,14,['int','pointer'],[req.command,out]),'blocked');blocked=!!out.readU8();
  check(call(store,7,['int','pointer','pointer'],[req.command,ctx,can.pointer]),'can');
 });const end=Date.now()+15000;while(allowed===null&&Date.now()<end)await delay(20);if(allowed===null)throw new Error("availability timeout");
 if(req.perform){if(!allowed||blocked)throw new Error('Unavailable');await onUI(()=>check(call(store,6,['int','pointer'],[req.command,ctx]),'perform'));}
 return {allowed,blocked,performed:!!req.perform};
});

extensions.set('model-select-sketch',async(req,o)=>{
 let result=null;const d=delegate('9607a29e-c47d-5653-b894-db449b6756ca',['uint64','uint','pointer','uint','pointer'],(folder,count,items,ni,indices)=>{
  const matches=[];for(let i=0;i<count;i++){const p=items.add(i*8).readPointer();if(numberResult(p,6)===2)matches.push(p);}
  if(matches.length!==1){result={error:'expected one sketch',count:matches.length};return;}
  const arr=alloc(8);arr.writePointer(matches[0]);check(call(o.model,26,['uint','pointer','uint64','uchar','uchar'],[1,arr,uint64(0),1,0]),'SelectItems');result={selected:textResult(matches[0],7)};
 });
 await onUI(()=>check(call(o.model,24,['uint64','pointer'],[uint64(0),d.pointer]),'RootFolderData'));
 const end=Date.now()+10000;while(result===null&&Date.now()<end)await delay(20);if(!result||result.error)throw new Error(JSON.stringify(result));return result;
});
extensions.set('model-annotations',async(req,o)=>onUI(()=>{
 const nativeEditor=o.model.add(0x10).readPointer(),host=nativeEditor.add(0x48).readPointer(),ui=host.add(0x650);
 const sentinel=ui.add(0x1b8).readPointer(),count=ui.add(0x1c0).readU64().toNumber();if(count>10000)throw new Error('Annotation count invalid');
 const rows=[];let p=sentinel.readPointer();for(let i=0;i<count&&!p.equals(sentinel);i++,p=p.readPointer()){
  const row={id:p.add(0x10).readU64().toString(),type:p.add(0x28).readU8()};
  rows.push(row);
 }
 return {available:ui.add(0x18).readU32(),hasNative:!ui.add(8).readPointer().isNull(),rows};
}));
extensions.set('model-set-distance',async(req,o)=>{
 await ensureModelMutation(o);
 if(!/^[-+]?\d+(?:\.\d+)? mm$/.test(req.expression))throw new Error('Expected explicit mm expression');
 const state=await extensions.get('model-annotations')(req,o);
 const candidates=state.rows.filter(r=>r.type===4);
 if(!(state.available&2)||candidates.length!==1)throw new Error('Expected one editable scalar or transform annotation: '+JSON.stringify(state));
 const id=candidates[0].id;
 await onUI(()=>{
  const ui=o.model.add(0x10).readPointer().add(0x48).readPointer().add(0x650),element=alloc(16),expression=alloc(32),callback=alloc(64);
  element.writeU64(uint64(id));element.add(8).writeU32(0);
  if(req.expression.length>15)throw new Error('Expression exceeds verified small-string layout');
  expression.writeUtf8String(req.expression);expression.add(16).writeU64(req.expression.length);expression.add(24).writeU64(15);
  // Verified native UI wrapper, preserving its normal queue and continuation.
  const fn=new NativeFunction(Process.getModuleByName('Shapr.Native.dll').base.add(0x657a30),'void',['pointer','pointer','pointer','int','pointer']);
  fn(ui,element,expression,0,callback);
 });
 await delay(500);return {submitted:true,id,expression:req.expression,annotations:await extensions.get('model-annotations')(req,o)};
});
extensions.set('model-tool-finish',async(req,o)=>{
 await ensureModelMutation(o);
 await onUI(()=>check(call(pointerResult(o.model,7),15),'FinishTool'));await delay(250);
 return {submitted:true,annotations:await extensions.get('model-annotations')(req,o)};
});
extensions.set('model-pick',async(req,o)=>{await ensureModelMutation(o);return onUI(()=>{
 const x=Number(req.xMm||0)/1000,y=Number(req.yMm||0)/1000;
 if(!Number.isFinite(x)||!Number.isFinite(y)||Math.abs(x)>0.1||Math.abs(y)>0.1)throw new Error('Bounded plate coordinate expected');
 const base=Process.getModuleByName('Shapr.Native.dll').base,ed=o.model.add(0x10).readPointer(),selectionController=ed.add(0x358).readPointer(),processor=selectionController.add(0x480).readPointer();
 if(processor.isNull())throw new Error('No native picker');
 const near=req.nearMm?req.nearMm.map(v=>Number(v)/1000):[x,y,0.1],far=req.farMm?req.farMm.map(v=>Number(v)/1000):[x,y,-0.1];
 if(near.length!==3||far.length!==3||[...near,...far].some(v=>!Number.isFinite(v)||Math.abs(v)>0.1))throw new Error('Bounded world ray expected');
 const distance=Math.hypot(...near.map((v,i)=>v-far[i]));if(distance<0.000001)throw new Error('Ray too short');
 const cone=alloc(80),out=alloc(24);[...near,...far,0.000001,0.000001,distance].forEach((v,i)=>cone.add(i*8).writeDouble(v));cone.add(72).writeU8(1);
 new NativeFunction(base.add(0x93be00),'pointer',['pointer','pointer','pointer'])(processor,out,cone);
 const begin=out.readPointer(),end=out.add(8).readPointer(),cap=out.add(16).readPointer(),size=end.sub(begin).toInt32(),capacity=cap.sub(begin).toInt32();
 if(size<0||size%120||size>12000||capacity<size||capacity>120000)throw new Error('Unexpected picker vector');
 const rows=[],bodies=[];
 try{
  for(let i=0;i<size/120;i++){
   const item=begin.add(i*120),optionalRay=alloc(128),body=alloc(16);Memory.copy(optionalRay,item,120);optionalRay.add(120).writeU8(1);
   new NativeFunction(base.add(0x860480),'pointer',['pointer','pointer','uchar'])(body,optionalRay,0);
   bodies.push(body);rows.push({index:i,kind:item.add(72).readU32(),present:!!body.add(12).readU8(),rawID:body.readU64().toString(),tag:body.add(8).readU32()});
  }
 }finally{if(!begin.isNull())new NativeFunction(base.add(0xbfa40),'void',['pointer','uint64'])(begin,uint64(capacity));}
 if(req.select){
  const matches=rows.filter(r=>r.present&&(req.expectedRawID===undefined||r.rawID===req.expectedRawID));
  if(matches.length!==1)throw new Error('Expected exactly one selectable native region');
  const selectedIndex=matches[0].index;
  const result=alloc(16),selection=ed.add(0x668).readPointer();
  const info=uint64(req.additive?'2':'8589934594'); // source2, mode0/add or mode2/replace.
  new NativeFunction(base.add(0xababa0),'pointer',['pointer','pointer','pointer','pointer','uint64','uchar'])(selection,result,cone,bodies[selectedIndex],info,0);
  const control=result.add(8).readPointer();if(!control.isNull())new NativeFunction(base.add(0xe02e0),'void',['pointer'])(control);
  result.writePointer(nullp);result.add(8).writePointer(nullp);
 }
 return {xMm:x*1000,yMm:y*1000,rows,selectionSubmitted:!!req.select};
});});
