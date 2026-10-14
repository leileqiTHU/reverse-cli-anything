// Appended to capcut_store_agent.js; native Qt model access, without input events.
const exportQt={
 children:nf(qtExport('?children@QObject@@QEBAAEBV?$QList@PEAVQObject@@@@XZ',0x67e0),'pointer',['pointer']),
 className:nf(qtExport('?className@QMetaObject@@QEBAPEBDXZ',0xa5360),'pointer',['pointer']),
 property:nf(qtExport('?property@QObject@@QEBA?AVQVariant@@PEBD@Z',0xdf960),'pointer',['pointer','pointer','pointer']),
 variantString:nf(qtExport('?toString@QVariant@@QEBA?AVQString@@XZ',0xf4710),'pointer',['pointer','pointer']),
 variantDtor:nf(qtExport('??1QVariant@@QEAA@XZ',0xf0af0),'void',['pointer']),
 stringDtor:nf(qtExport('??1QString@@QEAA@XZ',0x4000),'void',['pointer'])
};
function exportQString(p){const n=p.add(16).readS64().toNumber();if(n<0||n>32768)throw Error('Export QString bounds');return n?p.add(8).readPointer().readUtf16String(n):'';}
function exportProperty(obj,key,type){
 const variant=Memory.alloc(32),value=Memory.alloc(24);
 try{exportQt.property(obj,variant,Memory.allocUtf8String(key));
  if(type===11){
   const list=nf(qt.getExportByName('?constData@QVariant@@QEBAPEBXXZ'),'pointer',['pointer'])(variant);
   const count=list.add(16).readS64().toNumber(),data=list.add(8).readPointer();if(count<0||count>1000)throw Error('QStringList bounds');
   return Array.from({length:count},(_,i)=>exportQString(data.add(i*24)));
  }
  exportQt.variantString(variant,value);return exportQString(value);}
 finally{exportQt.stringDtor(value);exportQt.variantDtor(variant);}
}
function exportMeta(obj){return nf(obj.readPointer().readPointer(),'pointer',['pointer'])(obj);}
function exportClass(obj){return exportQt.className(exportMeta(obj)).readUtf8String();}
function exportMetaRows(obj){
 const rows=[];let meta=exportMeta(obj);
 for(let depth=0;!meta.isNull()&&depth<20;depth++,meta=meta.readPointer()){
  const strings=meta.add(16).readPointer(),data=meta.add(24).readPointer();
  if(strings.isNull()||data.isNull())break;
  const cls=exportQt.className(meta).readUtf8String();
  if(!/Export|TitleBar/.test(cls))continue;
  const get=index=>{if(index>16384)throw Error('Meta string index');const s=strings.add(index*8),n=s.add(4).readU32();if(n>4096)throw Error('Meta string bounds');return strings.add(s.readU32()).readUtf8String(n);};
  const row={className:cls,methods:[],properties:{}};
  const count=data.add(16).readU32(),off=data.add(20).readU32();
  if(count>2048||off>65536)throw Error('Meta methods bounds');
  for(let i=0;i<count;i++){
   const m=data.add(off*4+i*24);row.methods.push({name:get(m.readU32()),argc:m.add(4).readU32(),flags:m.add(16).readU32()});
  }
  const pc=data.add(24).readU32(),po=data.add(28).readU32();
  if(pc>2048||po>65536)throw Error('Meta properties bounds');
  for(let i=0;i<pc;i++){
   const p=data.add(po*4+i*20),name=get(p.readU32());
   row.properties[name]={value:exportProperty(obj,name,p.add(4).readU32()),type:p.add(4).readU32(),flags:p.add(8).readU32()};
  }
  rows.push(row);
 }
 return rows;
}
function exportObjects(){
 const gui=Process.getModuleByName('Qt6Gui.dll');
 if(normalize(gui.path)!==normalize(DIRECTORY+'/Qt6Gui.dll'))throw Error('Qt GUI path mismatch');
 const top=nf(gui.getExportByName('?topLevelWindows@QGuiApplication@@SA?AV?$QList@PEAVQWindow@@@@XZ'),'pointer',['pointer']);
 const quick=Process.getModuleByName('Qt6Quick.dll');
 if(normalize(quick.path)!==normalize(DIRECTORY+'/Qt6Quick.dll')||!quick.getExportByName('?childItems@QQuickItem@@QEBA?AV?$QList@PEAVQQuickItem@@@@XZ').equals(quick.base.add(0x4e410)))throw Error('QQuickItem ABI mismatch');
 const inherits=nf(qtExport('?inherits@QObject@@QEBA_NPEBD@Z',0x7be0),'bool',['pointer','pointer']);
 const quickName=Memory.allocUtf8String('QQuickItem');
 const list=Memory.alloc(24),queue=[],seen=new Set(),found=[],roots=[];
 try{
  top(list);const n=list.add(16).readS64().toNumber(),data=list.add(8).readPointer();
  if(n<0||n>128)throw Error('Top-level bounds');
  for(let i=0;i<n;i++){
   const obj=data.add(i*8).readPointer();
   roots.push({obj,className:exportClass(obj),title:exportProperty(obj,'title'),visible:exportProperty(obj,'visible')==='true'});
  }
 }finally{
  const owner=list.readPointer();if(!owner.isNull()){
   if(owner.readS32()!==1)throw Error('Unexpected shared QList');
   nf(qtExport('?deallocate@QArrayData@@SAXPEAU1@_J1@Z',0x188680),'void',['pointer','int64','int64'])(owner,8,8);
  }
 }
 const exportRoots=roots.filter(row=>row.visible&&(/ExportWindow/.test(row.className)));
 for(const row of (exportRoots.length?exportRoots:roots))queue.push(row.obj);
 while(queue.length){
  const obj=queue.shift();if(obj.isNull()||seen.has(obj.toString()))continue;
  if(seen.size>25000)throw Error('QObject scan bounds');seen.add(obj.toString());
  const cls=exportClass(obj);
  if(/Export.*ViewModel|MainWindowStyleTitleBarViewModel/.test(cls))found.push({obj,className:cls});
  const children=exportQt.children(obj),n=children.add(16).readS64().toNumber(),data=children.add(8).readPointer();
  if(n<0||n>20000)throw Error('Child-list bounds');
  for(let i=0;i<n;i++)queue.push(data.add(i*8).readPointer());
  // Qt6Quick!childItems disassembly: borrowed list at QObjectPrivate+0x120.
  // Read it on the application thread, without making a reference-counted copy.
  if(exportRoots.length&&inherits(obj,quickName)){
   const visual=obj.add(8).readPointer().add(0x120),count=visual.add(16).readS64().toNumber(),items=visual.add(8).readPointer();
   if(count<0||count>20000)throw Error('Visual child-list bounds');
   for(let i=0;i<count;i++)queue.push(items.add(i*8).readPointer());
  }
 }
 return {found,scanned:seen.size,roots:roots.map(row=>({pointer:row.obj.toString(),className:row.className,title:row.title,visible:row.visible}))};
}
rpc.exports.exportinspect=function(req){return onApplicationThread(req,state=>{
 const project=currentProject(state);
 if(!project||project.id.toLowerCase()!==req.project_id.toLowerCase())throw Error('Current project changed');
 const inventory=exportObjects();
 return {project,roots:inventory.roots,scanned:inventory.scanned,models:inventory.found.map(row=>({pointer:row.obj.toString(),className:row.className,meta:exportMetaRows(row.obj)}))};
});};
function exportUnique(rows,cls){const matches=rows.filter(row=>row.className===cls);if(matches.length!==1)throw Error('Expected exactly one '+cls+', got '+matches.length);return matches[0].obj;}
function exportInvoke(obj,cls,method,parameters=[],result=null){
 let meta=exportMeta(obj);
 while(!meta.isNull()&&exportQt.className(meta).readUtf8String()!==cls)meta=meta.readPointer();
 if(meta.isNull())throw Error('Expected export model metadata');
 const strings=meta.add(16).readPointer(),data=meta.add(24).readPointer();
 const count=data.add(16).readU32(),off=data.add(20).readU32(),matches=[];
 for(let i=0;i<count;i++){
  const m=data.add(off*4+i*24),s=strings.add(m.readU32()*8),name=strings.add(s.readU32()).readUtf8String(s.add(4).readU32());
  if(name===method&&m.add(4).readU32()===parameters.length)matches.push(i);
 }
 if(matches.length!==1)throw Error('Expected unique native method: '+method);
 const dispatcher=meta.add(32).readPointer();
 if(!Process.findModuleByAddress(dispatcher)?.base.equals(frontend.base))throw Error('Export method outside pinned frontend');
 const args=Memory.alloc(8*(parameters.length+1));args.writePointer(result||ptr(0));
 parameters.forEach((p,i)=>args.add((i+1)*8).writePointer(p));
 nf(dispatcher,'void',['pointer','int','int','pointer'])(obj,0,matches[0],args);
 return {method,index:matches[0],dispatcher:dispatcher.sub(frontend.base).toString()};
}
function exportInvokeZero(obj,cls,method){return exportInvoke(obj,cls,method);}
function exportInvokeInt(obj,method,value){const v=Memory.alloc(4);v.writeS32(value);return exportInvoke(obj,exportClass(obj),method,[v]);}
function exportReadMethodString(obj,method){const out=Memory.alloc(24);try{exportInvoke(obj,exportClass(obj),method,[],out);return exportQString(out);}finally{exportQt.stringDtor(out);}}
function exportReadMethodInt(obj,method){const out=Memory.alloc(4);exportInvoke(obj,exportClass(obj),method,[],out);return out.readS32();}
function exportSetString(obj,key,bytes){
 const data=input(bytes),str=Memory.alloc(24),variant=Memory.alloc(32);
 try{
  nf(qtExport('?fromUtf8@QString@@SA?AV1@PEBD_J@Z',0x78f0),'pointer',['pointer','pointer','int64'])(str,data.data,bytes.length);
  nf(qtExport('??0QVariant@@QEAA@AEBVQString@@@Z',0xf06e0),'pointer',['pointer','pointer'])(variant,str);
  if(!nf(qtExport('?setProperty@QObject@@QEAA_NPEBDAEBVQVariant@@@Z',0xe1ae0),'bool',['pointer','pointer','pointer'])(obj,Memory.allocUtf8String(key),variant))throw Error('Cannot write native export property '+key);
  if(exportProperty(obj,key)!==data.text)throw Error('Export property readback mismatch: '+key);
 }finally{exportQt.variantDtor(variant);exportQt.stringDtor(str);}
}
function exportProjectGuard(req,state){
 const project=currentProject(state);
 if(!project||project.id.toLowerCase()!==req.project_id.toLowerCase())throw Error('Current project changed');
 return project;
}
rpc.exports.exportconfigure=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);
 const rows=exportObjects().found,window=exportUnique(rows,'ExportWindowViewModel');
 if(exportProperty(window,'uiStage')!=='HOME')throw Error('Export is not in its settings stage');
 const file=exportUnique(rows,'ExportFileSelectorPanelViewModel'),video=exportUnique(rows,'ExportVideoOptionsPanelViewModel');
 const bottom=exportUnique(rows,'ExportHomeBottomViewModel');
 const timeline=exportReadMethodString(file,'getTimelineName');
 if(timeline!==req.timeline_name)throw Error('Export model timeline differs from the requested timeline: '+timeline);
 if(exportProperty(file,'exportWithDir')!=='false'||exportProperty(bottom,'videoChecked')!=='true'||
    ['audioChecked','gifChecked','subtitleChecked','isUploadToEnterprise','preparing','isTryExporting'].some(k=>exportProperty(bottom,k)!=='false'))throw Error('Export is busy or has unsupported targets');
 const listIndex=(key,predicate)=>{const list=exportProperty(video,key,11),idx=list.findIndex(predicate);if(idx<0)throw Error('Requested export setting unavailable: '+key);return idx;};
 const resolution=listIndex('resolutionStringList',s=>s.toUpperCase()===req.resolution_label.toUpperCase());
 exportInvokeInt(video,'setResolutionIndex',resolution);
 const encoder=listIndex('encoderList',s=>s==='H.264');
 exportInvokeInt(video,'setEncoderIndex',encoder);
 const format=listIndex('formatList',s=>s.toLowerCase()==='mp4');
 exportInvokeInt(video,'setFormat',format);
 const fps=listIndex('frameRateList',s=>Math.abs(parseFloat(s)-req.fps)<.001);
 exportInvokeInt(video,'setFrameRate',fps);
 // Persist the stable user-selected directory, never a disposable staging path.
 exportSetString(file,'selectedExportPath',req.output_parent_bytes);
 if(req.action==='export')exportInvokeZero(file,'ExportFileSelectorPanelViewModel','saveExportPath');
 const savedDefaultDirectory=exportProperty(file,'selectedExportPath');
 exportSetString(file,'selectedExportPath',req.output_dir_bytes);
 exportSetString(file,'selectedExportTitle',req.output_title_bytes);
 if(exportReadMethodInt(video,'getEncoderIndex')!==encoder||exportReadMethodInt(video,'getFormatIndex')!==format||
    exportReadMethodInt(video,'defaultFrameRateIndex')!==fps||Number(exportProperty(video,'resolutionIndex'))!==resolution||exportProperty(file,'exportFileFormat').toLowerCase()!=='mp4')throw Error('Native export setting readback mismatch');
 return {timeline,stage:'HOME',directory:exportProperty(file,'selectedExportPath'),savedDefaultDirectory:req.action==='export'?savedDefaultDirectory:null,title:exportProperty(file,'selectedExportTitle'),
  format:'mp4',encoder:'H.264',fps:req.fps,resolution:req.resolution_label,info:exportProperty(bottom,'exportFileInfo')};
});};
rpc.exports.exportbegin=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);
 const rows=exportObjects().found,window=exportUnique(rows,'ExportWindowViewModel'),file=exportUnique(rows,'ExportFileSelectorPanelViewModel');
 if(exportProperty(window,'uiStage')!=='HOME'||exportReadMethodString(file,'getTimelineName')!==req.timeline_name)throw Error('Export target/stage changed');
 const output=exportProperty(file,'selectedExportPath').replace(/\\/g,'/')+'/'+exportProperty(file,'selectedExportTitle')+'.'+exportProperty(file,'exportFileFormat');
 if(normalize(output)!==normalize(req.stage_output))throw Error('Export output path changed');
 const video=exportUnique(rows,'ExportVideoOptionsPanelViewModel'),bottom=exportUnique(rows,'ExportHomeBottomViewModel');
 const encoders=exportProperty(video,'encoderList',11),formats=exportProperty(video,'formatList',11),fps=exportProperty(video,'frameRateList',11),res=exportProperty(video,'resolutionStringList',11);
 if(encoders[exportReadMethodInt(video,'getEncoderIndex')]!=='H.264'||formats[exportReadMethodInt(video,'getFormatIndex')].toLowerCase()!=='mp4'||
    Math.abs(parseFloat(fps[exportReadMethodInt(video,'defaultFrameRateIndex')])-req.fps)>.001||res[Number(exportProperty(video,'resolutionIndex'))].toUpperCase()!==req.resolution_label.toUpperCase())throw Error('Export settings changed before start');
 const targetState={exportWithDir:exportProperty(file,'exportWithDir')};
 for(const key of ['videoChecked','audioChecked','gifChecked','subtitleChecked','isUploadToEnterprise','preparing','isTryExporting'])targetState[key]=exportProperty(bottom,key);
 if(targetState.exportWithDir!=='false'||targetState.videoChecked!=='true'||
    ['audioChecked','gifChecked','subtitleChecked','isUploadToEnterprise','isTryExporting'].some(k=>targetState[k]!=='false'))throw Error('Export target selection changed: '+JSON.stringify(targetState));
 // Preparation may restart between the status read and this UI-thread callback.
 // No compile call has happened in this branch, so the caller may safely wait.
 if(targetState.preparing==='true')return {started:false,reason:'preparing'};
 if(targetState.preparing!=='false')throw Error('Unknown export preparation state');
 return {started:true,native:exportInvokeZero(exportUnique(rows,'ExportHomeBottomViewModel'),'ExportHomeBottomViewModel','compileClick')};
});};
rpc.exports.exportclose=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);const inventory=exportObjects();
 const window=exportUnique(inventory.found,'ExportWindowViewModel'),stage=exportProperty(window,'uiStage');
 if(!['HOME','FINISH'].includes(stage))throw Error('Cannot close an active export');
 const roots=inventory.roots.filter(row=>row.visible&&/^ExportWindow_QMLTYPE_/.test(row.className));
 if(roots.length!==1)throw Error('Export window identity is ambiguous');
 const gui=Process.getModuleByName('Qt6Gui.dll');
 return {stage,closeAccepted:nf(gui.getExportByName('?close@QWindow@@QEAA_NXZ'),'bool',['pointer'])(ptr(roots[0].pointer))};
});};
rpc.exports.exportcancel=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);const rows=exportObjects().found;
 const window=exportUnique(rows,'ExportWindowViewModel');
 if(exportProperty(window,'uiStage')!=='COMPILING')throw Error('No active export to cancel');
 return exportInvokeZero(exportUnique(rows,'ExportCompileBottomViewModel'),'ExportCompileBottomViewModel','cancel');
});};
rpc.exports.exportstatus=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);const rows=exportObjects().found;
 const windows=rows.filter(row=>row.className==='ExportWindowViewModel');
 const result={stage:windows.length===1?exportProperty(windows[0].obj,'uiStage'):null};
 const home=rows.filter(row=>row.className==='ExportHomeBottomViewModel');
 if(home.length===1)for(const key of ['preparing','isTryExporting','videoChecked','audioChecked','gifChecked','subtitleChecked'])result[key]=exportProperty(home[0].obj,key);
 for(const cls of ['ExportCompileBottomViewModel','ExportCompileRightPanelViewModel']){
  const matches=rows.filter(row=>row.className===cls);
  if(matches.length===1)for(const key of cls==='ExportCompileBottomViewModel'?['progress','exportTaskFailed','inBgExportPending','progressBlocked','exportedVideoDurationText']:['exportFail','exportPending'])result[key]=exportProperty(matches[0].obj,key);
 }
 return result;
});};
rpc.exports.exportopen=function(req){return onApplicationThread(req,state=>{
 const project=currentProject(state);
 if(!project||project.id.toLowerCase()!==req.project_id.toLowerCase())throw Error('Current project changed');
 const rows=exportObjects().found;
 const existing=rows.filter(row=>row.className==='ExportWindowViewModel');
 if(existing.length)throw Error('An export panel is already open; close it before starting a separate CLI export');
 const vm=editorWindow(windowController());
 if(vm.isNull()||vm.add(0x31).readU8()!==1||vm.add(0x30).readU8()!==0||vm.add(0x71).readU8()!==0)throw Error('Editor is not ready');
 if(nf(frontend.base.add(0x4f3b980),'bool',['pointer'])(vm))throw Error('A modal window blocks export');
 const obj=exportUnique(rows,'MainWindowStyleTitleBarViewModel');
 return {project,opened:exportInvokeZero(obj,'MainWindowStyleTitleBarViewModel','openExportWindow')};
});};

// The FINISH page starts an unsolicited AI-crop preview on horizontal videos.
// Its WithoutText method sets text-track attribute bit 2 (hidden) in the source
// draft. Suppress that secondary action only while this script owns an export
// window. No application bytes, feature flags or export permissions are changed.
let exportCropGuard=null;
rpc.exports.exportguardinstall=function(req){return onApplicationThread(req,state=>{
 exportProjectGuard(req,state);
 if(exportCropGuard!==null)throw Error('Export crop guard already installed');
 const window=exportUnique(exportObjects().found,'ExportWindowViewModel');
 if(exportProperty(window,'uiStage')!=='HOME')throw Error('Crop guard requires owned export settings');
 const address=frontend.base.add(0x3e8bfd0);
 const expected='48895c2410488974241848897c2420554154415541564157488dac2410fcffff';
 const actual=Array.from(new Uint8Array(address.readByteArray(expected.length/2))).map(b=>b.toString(16).padStart(2,'0')).join('');
 if(actual!==expected)throw Error('Unsupported export AI-crop entry bytes');
 const original=nf(address,'void',['pointer']),ownerThread=Process.getCurrentThreadId();
 const guard={address,ownerThread,suppressed:0,callback:null};
 guard.callback=new NativeCallback(function(self){
  let sameProject=false;
  if(Process.getCurrentThreadId()===ownerThread){
   try{const project=currentProject(state);sameProject=project!==null&&project.id.toLowerCase()===req.project_id.toLowerCase();}catch(error){sameProject=false;}
  }
  const suppress=exportCropGuard===guard&&Process.getCurrentThreadId()===ownerThread&&sameProject;
  send({event:'export-postprocess-observed',threadId:Process.getCurrentThreadId(),ownerThread,passThrough:!suppress});
  if(suppress){
   guard.suppressed++;
   send({event:'export-postprocess-suppressed',kind:'automatic-ai-crop-without-text',projectId:req.project_id,sid:req.expected_editor_sid});
   return;
  }
  original(self);
 },'void',['pointer']);
 exportCropGuard=guard;Interceptor.replace(address,guard.callback);Interceptor.flush();
 return {installed:true,entryRva:'0x3e8bfd0',ownerThread,scope:'owned export window, bound project and application thread',projectId:req.project_id};
});};
rpc.exports.exportguardremove=function(){
 const guard=exportCropGuard;
 if(guard===null)return {removed:false,suppressed:0};
 Interceptor.revert(guard.address);Interceptor.flush();exportCropGuard=null;
 return {removed:true,suppressed:guard.suppressed};
};
