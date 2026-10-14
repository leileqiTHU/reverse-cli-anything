'use strict';
const nullp=ptr(0), keep=[], held=[], delegates=[];
const COM={
 appStatic:'bf001fc6-3261-5c95-b4ff-0030969becf4', app:'2a6abb39-9b44-5dca-b172-274312321a05',
 contextFactory:'61a62968-50b7-55fe-a063-827b7d0ec437', historyFactory:'7df12128-1127-59c8-bd65-5b1d26be217e',
 coreApp:'1ada0e3e-e4a2-4123-b451-dc96bf800419', coreView2:'68eb7adf-917f-48eb-9aeb-7de53e086ab1',
 dispatchedHandler:'d1f276c4-98d8-4636-bf49-eb79507548e9', unknown:'00000000-0000-0000-c000-000000000046',agile:'94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90'
};
function native(name,ret,args){return new NativeFunction(Module.getGlobalExportByName(name),ret,args);}
const createString=native('WindowsCreateString','int',['pointer','uint','pointer']);
const deleteString=native('WindowsDeleteString','int',['pointer']);
const stringBuffer=native('WindowsGetStringRawBuffer','pointer',['pointer','pointer']);
const getFactory=native('RoGetActivationFactory','int',['pointer','pointer','pointer']);
const initialize=native('RoInitialize','int',['uint']);
const uninitialize=native('RoUninitialize','void',[]);
const free=native('CoTaskMemFree','void',['pointer']);
function check(hr,label){if(hr<0)throw new Error(label+': HRESULT 0x'+(hr>>>0).toString(16));}
function alloc(n){const p=Memory.alloc(n);keep.push(p);return p;}
function guid(s){const a=s.split('-'),p=alloc(16);p.writeU32(parseInt(a[0],16));p.add(4).writeU16(parseInt(a[1],16));p.add(6).writeU16(parseInt(a[2],16));const tail=a[3]+a[4];for(let i=0;i<8;i++)p.add(8+i).writeU8(parseInt(tail.slice(i*2,i*2+2),16));return p;}
function bytes(p,n){return Array.from(new Uint8Array(p.readByteArray(n))).map(b=>b.toString(16).padStart(2,'0')).join('');}
function hstr(s){const out=alloc(8),raw=Memory.allocUtf16String(s);keep.push(raw);check(createString(raw,s.length,out),'WindowsCreateString');const h=out.readPointer();keep.push({hstring:h});return h;}
function text(h){if(h.isNull())return '';const n=alloc(4),p=stringBuffer(h,n);return p.readUtf16String(n.readU32());}
function call(p,slot,types=[],args=[]){if(p.isNull())throw new Error('Null interface slot '+slot);return new NativeFunction(p.readPointer().add(slot*8).readPointer(),'int',['pointer',...types])(p,...args);}
function own(p){if(!p.isNull())held.push(p);return p;}
function pointerResult(p,slot,types=[],args=[]){const out=alloc(8);check(call(p,slot,[...types,'pointer'],[...args,out]),'slot '+slot);return own(out.readPointer());}
function numberResult(p,slot,type='int'){const out=alloc(8);check(call(p,slot,['pointer'],[out]),'slot '+slot);return type==='double'?out.readDouble():type==='bool'?!!out.readU8():out.readS32();}
function textResult(p,slot,types=[],args=[]){const out=alloc(8);check(call(p,slot,[...types,'pointer'],[...args,out]),'slot '+slot);const h=out.readPointer();try{return text(h);}finally{deleteString(h);}}
function arrayResult(p,slot){const count=alloc(4),out=alloc(8);check(call(p,slot,['pointer','pointer'],[count,out]),'array slot '+slot);const n=count.readU32(),a=out.readPointer();if(n>10000)throw new Error('Array bound exceeded');const result=[];for(let i=0;i<n;i++)result.push(own(a.add(i*8).readPointer()));if(!a.isNull())free(a);return result;}
function query(p,iid){const out=alloc(8);check(call(p,0,['pointer','pointer'],[guid(iid),out]),'QI '+iid);return own(out.readPointer());}
function factory(name,iid){const out=alloc(8);check(getFactory(hstr(name),guid(iid),out),'Factory '+name);return own(out.readPointer());}
function describe(p){if(p.isNull())return {null:true};const v=p.readPointer(),m=Process.findModuleByAddress(v);return {runtimeClass:textResult(p,4),vtableModule:m?.name,vtableRva:m?v.sub(m.base).toString():null};}
function release(p){return new NativeFunction(p.readPointer().add(16).readPointer(),'uint',['pointer'])(p);}
function delay(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
function delegate(iid,types,body){
 const state={refs:1,invocations:0,error:null};const obj=alloc(8),vt=alloc(32);obj.writePointer(vt);
 const ids=[iid,COM.unknown,COM.agile].map(s=>bytes(guid(s),16));
 const callbacks=[
  new NativeCallback((self,id,out)=>{if(ids.includes(bytes(id,16))){out.writePointer(obj);state.refs++;return 0;}out.writePointer(nullp);return -2147467262;},'int',['pointer','pointer','pointer']),
  new NativeCallback(()=>++state.refs,'uint',['pointer']),
  new NativeCallback(()=>--state.refs,'uint',['pointer']),
  new NativeCallback((self,...args)=>{state.invocations++;try{body(...args);}catch(e){state.error=String(e);}return 0;},'int',['pointer',...types])
 ];callbacks.forEach((p,i)=>vt.add(i*8).writePointer(p));keep.push(...callbacks);state.pointer=obj;delegates.push(state);return state;
}
let dispatcher=nullp;
let projectToken=nullp;
const extensions=new Map();
// Native subscriptions must have a matching teardown before the script unloads.
const cleanupHooks=new Map();
function setupDispatcher(){const f=factory('Windows.ApplicationModel.Core.CoreApplication',COM.coreApp);const view=pointerResult(f,8);const view2=query(view,COM.coreView2);dispatcher=pointerResult(view2,6);}
async function onUI(work){
 let value,error,done=false;
 const d=delegate(COM.dispatchedHandler,[],()=>{try{value=work();}catch(e){error=e;}done=true;});
 const out=alloc(8);
 check(call(dispatcher,8,['int','pointer','pointer'],[0,d.pointer,out]),'CoreDispatcher.RunAsync');
 // The dispatcher owns the scheduled work. Drop our IAsyncAction reference so
 // it cannot keep the callback alive after completion.
 const asyncAction=out.readPointer();if(!asyncAction.isNull())release(asyncAction);
 const end=Date.now()+15000;
 while(!done && Date.now()<end)await delay(20);
 if(!done)throw new Error('UI dispatch timeout; outcome unknown');
 while(d.refs>1 && Date.now()<end)await delay(10);
 if(d.refs>1)throw new Error('UI callback is still retained');
 if(d.error)throw new Error(d.error);
 if(error)throw error;
 return value;
}
function appObjects(){const f=factory('Shapr.CommonAppWin.MTShaprApp',COM.appStatic);const app=pointerResult(f,8);if(app.isNull())throw new Error('Shapr3D is not initialized');const editor=pointerResult(app,29),model=pointerResult(editor,7);return {f,app,editor,model};}
function inspect(o){return {pid:Process.id,gitCommit:textResult(o.f,9),app:describe(o.app),editor:describe(o.editor),activeEditor:numberResult(o.editor,8),model:describe(o.model),gridDensity:numberResult(o.model,39,'double'),isViewOnly:numberResult(o.model,41,'bool'),gridScaleText:textResult(o.model,38),uiThreadId:Process.getCurrentThreadId()};}
// Read the real XAML page through documented WinRT interface layouts recovered
// from this pinned application. No UI Automation input or synthetic navigation.
function frontendPageType(){
 const window=pointerResult(factory('Windows.UI.Xaml.Window','93328409-4ea1-4afa-83dc-0c4e73e88bb1'),6);
 const frame=pointerResult(query(window,'3276167d-c9f6-462d-9de2-ae4c1fd8c2e5'),8);
 const page=pointerResult(query(frame,'a26dd1dc-cd44-435c-be94-01d6241c231c'),6);
 const type=alloc(16);check(call(query(page,'7c925755-3e48-42b4-8677-76372267033f'),9,['pointer'],[type]),'Actual page type');
 const hs=type.readPointer();try{return text(hs);}finally{deleteString(hs);}
}
async function ensureModelMutation(o){
 // The retained token supports the older backend-only pilot. A normal open
 // frontend already owns its access token; this adapter must not fabricate one.
 if(!projectToken.isNull())return;
 await onUI(()=>{
  if(numberResult(o.editor,8)!==1||numberResult(o.model,41,'bool')||!frontendPageType().startsWith('Shapr3D.Editor.EditorPage,'))
   throw new Error('An editable native project must be open in the frontend');
 });
}

function historyRows(ui){
 return arrayResult(ui,22).map((container,index)=>{
  const step=pointerResult(container,8);if(step.isNull())return {index,hidden:true};
  return {index,name:textResult(step,7),hasError:numberResult(step,9,'bool'),parameters:arrayResult(step,13).map(param=>{
   const id=pointerResult(param,6),def=pointerResult(param,7),info=pointerResult(def,10),type=numberResult(info,6);
   const row={hash:numberResult(id,7),label:textResult(def,6),hasValue:numberResult(param,11,'bool'),valueType:type};
   if(row.hasValue){
    if(type===0)row.selection=textResult(param,13);
    else if(type===1){
     row.isExpression=numberResult(param,12,'bool');row.numericType=numberResult(pointerResult(info,8),6);
     if(row.isExpression){
      const expression=alloc(16);check(call(param,18,['pointer'],[expression]),'ExpressionValue');
      const hs=expression.readPointer(),value=own(expression.add(8).readPointer());
      try{row.expression=text(hs);}finally{deleteString(hs);}
      row.numericValue=value.isNull()?null:numberResult(value,6,'double');
     }else row.numericValue=numberResult(param,14,'double');
    }
    else if(type===2)row.choice=numberResult(param,15);
    else if(type===3)row.booleanValue=numberResult(param,16,'bool');
    else if(type===4)row.vertex=textResult(param,17);
   }
   return row;
  })};
 });
}
async function operation(request){
 let o;
 await onUI(()=>{o=appObjects();});
 if(extensions.has(request.operation))return await extensions.get(request.operation)(request,o);
 if(request.operation==='inspect')return await onUI(()=>inspect(o));
 if(request.operation==='create-project'){
  if(!projectToken.isNull())throw new Error('Session already owns a test project');
  let hook;
  await onUI(()=>{
   const controller=pointerResult(o.app,31);
   hook=Interceptor.attach(controller.readPointer().add(9*8).readPointer(),{onEnter(args){
    if(projectToken.isNull()&&!args[1].isNull())projectToken=query(args[1],'7c863a53-2ef1-513e-9519-5b44fdaade07');
   }});
  });
  try{
   const submitted=await operation({operation:'command',name:'NewProject'});
   const end=Date.now()+15000;while(projectToken.isNull()&&Date.now()<end)await delay(20);
   if(projectToken.isNull())throw new Error('NewProject did not reach native CreateProject');
   return await onUI(()=>({submitted,projectTokenCaptured:true,accessMode:numberResult(projectToken,6),state:inspect(o)}));
  }finally{hook.detach();}
 }
 if(request.operation==='history'){
  let ui;
  await onUI(()=>{const manager=pointerResult(o.model,14),f=factory('Shapr.CommonApp.MTDesignHistoryStepsListUI',COM.historyFactory);ui=pointerResult(f,6,['pointer'],[manager]);});
  await delay(150);
  return await onUI(()=>({state:inspect(o),history:historyRows(ui)}));
 }
 if(request.operation==='command'||request.operation==='command-check'){
  const commands={NewProject:100,CloseProject:3,Undo:277,Redo:119};
  if(!(request.name in commands))throw new Error('Command is not in allowlist');
  let store,ctx,allowed=null,blocked;
  const can=delegate('70584c5e-c66a-5a3c-ab58-1f0614e6f485',['uchar'],value=>{allowed=!!value;});
  await onUI(()=>{
   store=pointerResult(o.app,23);const f=factory('Shapr.CommonApp.MTCommandContext',COM.contextFactory);ctx=pointerResult(f,6,['int'],[0]);
   if(numberResult(ctx,8,'bool'))throw new Error('Unexpected authorization-bypass context');
   const out=alloc(1);check(call(store,14,['int','pointer'],[commands[request.name],out]),'IsCommandBlocked');blocked=!!out.readU8();
   check(call(store,7,['int','pointer','pointer'],[commands[request.name],ctx,can.pointer]),'CanPerform');
  });
  const end=Date.now()+15000;while(allowed===null&&Date.now()<end)await delay(20);
  if(allowed===null)throw new Error('Command availability timeout');
  if(request.operation==='command-check')return {command:request.name,allowed,blocked};
  if(!allowed||blocked)throw new Error('Command unavailable in current app state');
  return await onUI(()=>{
   check(call(store,6,['int','pointer'],[commands[request.name],ctx]),'PerformActionOfCommand');
   return {submitted:true,command:request.name,postconditionVerified:false};
  });
 }
 throw new Error('Unknown operation');
}
let initialized=false,closing=false,closed=false,closeError=null;
function lifecycle(){return {safeToDetach:closed,pendingCallbacks:delegates.filter(d=>d.refs>1).length,closing,closeError};}
rpc.exports={
 extend(source){if(closed)throw new Error('Bridge closed');eval(source);return [...extensions.keys()];},
 async run(request){
  if(closed||closing)throw new Error('Bridge closed');
  if(!initialized){const hr=initialize(1);check(hr,'RoInitialize');initialized=true;setupDispatcher();}
  const mark=held.length,delegateMark=delegates.length;
  try{return await operation(request);}
  finally{
   const deadline=Date.now()+15000;
   while(delegates.slice(delegateMark).some(d=>d.refs>1&&!d.persistent)&&Date.now()<deadline)await delay(20);
   if(delegates.slice(delegateMark).some(d=>d.refs>1&&!d.persistent))throw new Error('Operation callbacks retained; session must stay alive');
   // History UI objects register native observers. Destroy temporary helpers on
   // the UI thread before a later close/open can invalidate their workspace.
   await onUI(()=>{
    const persistent=[];
    while(held.length>mark){const p=held.pop();if(p.equals(projectToken))persistent.push(p);else release(p);}
    held.push(...persistent);
   });
  }
 },
 async close(){
  if(closed||closing)return lifecycle();
  closing=true;
  try{
   for(const [key,dispose] of cleanupHooks){await dispose();cleanupHooks.delete(key);}
   if(delegates.some(d=>d.refs>1))throw new Error('Native callbacks still retained after cleanup');
   const releaseOwned=()=>{while(held.length){const p=held.pop();if(!p.equals(dispatcher))release(p);}};
   if(!dispatcher.isNull())await onUI(releaseOwned);else releaseOwned();
   if(delegates.some(d=>d.refs>1))throw new Error('Cleanup callback retained');
   if(!dispatcher.isNull()){release(dispatcher);dispatcher=nullp;}
   for(const x of keep)if(x&&x.hstring)deleteString(x.hstring);
   if(initialized){uninitialize();initialized=false;}
   closed=true;
  }catch(e){closeError=String(e);}finally{closing=false;}
  return lifecycle();
 },
 lifecycle
};
