// Normal command dispatch only; never injects mouse/keyboard events.
extensions.set('model-command',async(req,o)=>{
 const commands={'exit-sketch':77,'deselect':43,'default-view':31,'zoom-fit':292,'undo':277};
 if(!(req.name in commands))throw new Error('Unsupported model command');
 let store,ctx,allowed=null,blocked;
 const can=delegate('70584c5e-c66a-5a3c-ab58-1f0614e6f485',['uchar'],v=>allowed=!!v);
 await onUI(()=>{
  if(numberResult(o.editor,8)!==1||numberResult(o.model,41,'bool'))throw new Error('An editable model must be open');
  store=pointerResult(o.app,23);ctx=pointerResult(factory('Shapr.CommonApp.MTCommandContext',COM.contextFactory),6,['int'],[0]);
  if(numberResult(ctx,8,'bool'))throw new Error('Unexpected bypass context');
  const out=alloc(1);check(call(store,14,['int','pointer'],[commands[req.name],out]),'IsCommandBlocked');blocked=!!out.readU8();
  check(call(store,7,['int','pointer','pointer'],[commands[req.name],ctx,can.pointer]),'CanPerform');
 });
 const end=Date.now()+15000;while(allowed===null&&Date.now()<end)await delay(20);
 if(allowed===null)throw new Error('Command availability timeout');
 if(!req.check){if(!allowed||blocked)throw new Error('Command unavailable');await onUI(()=>check(call(store,6,['int','pointer'],[commands[req.name],ctx]),'PerformActionOfCommand'));await delay(350);}
 return {name:req.name,allowed,blocked,submitted:!req.check};
});

// Deliberate demo reset, protected by a caller-supplied exact history snapshot.
// The CLI host separately requires a nonempty native archive backup on D:.
extensions.set('model-clear-demo',async(req,o)=>{
 await ensureModelMutation(o);
 if(req.confirm!=='replace-backed-up-demo-plate')throw new Error('Explicit demo reset required');
 let ui;
 await onUI(()=>{ui=pointerResult(factory('Shapr.CommonApp.MTDesignHistoryStepsListUI',COM.historyFactory),6,['pointer'],[pointerResult(o.model,14)]);});await delay(150);
 await onUI(()=>{
  const before=historyRows(ui);
  if(!before.length||before.length>8||JSON.stringify(before)!==JSON.stringify(req.expectedHistory))throw new Error('Current history differs from backed-up demo snapshot');
  const ids=arrayResult(ui,22).map(c=>pointerResult(c,6)),arr=alloc(ids.length*8);ids.forEach((p,i)=>arr.add(i*8).writePointer(p));
  check(call(ui,34,['uint','pointer'],[ids.length,arr]),'DeleteSteps on backed-up demo');
 });
 const end=Date.now()+15000;while(Date.now()<end){await delay(50);const rows=await onUI(()=>historyRows(ui));if(!rows.length)return {remaining:0,completed:true};}
 throw new Error('Demo reset outcome unknown; inspect before retrying');
});
