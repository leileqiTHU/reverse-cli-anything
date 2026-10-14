// Read-only, bounded evidence hooks. Parent runner controls attachment and export.
// No native export is invoked here. RVAs apply only to the pinned 9.5.0.4050 DLL.
const exportVe = Process.getModuleByName('videoeditor.dll');
const exportFrontend = Process.getModuleByName('VECreator.dll');
const exportHooks = [];
let exportCount = 0, exportActive = false, expectedPath = null, observedSid = null, observedPath = null, observedResponse = null;
function exportPath(value) {return value.replace(/[\\/]+/g,'/').toLowerCase();}
function exportExpectedOutput(value) {
  const candidate=exportPath(value),directory=expectedPath.slice(0,expectedPath.lastIndexOf('/')+1);
  return candidate===expectedPath || (candidate.startsWith(directory) && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\.mp4$/.test(candidate.slice(directory.length)));
}
function exportString(p) {
  const n=p.add(16).readU64().toNumber(), cap=p.add(24).readU64().toNumber();
  if(n>4096 || cap<n) throw Error('Invalid native export string');
  return (cap<16?p:p.readPointer()).readUtf8String(n);
}
function exportEmit(kind, details) {
  if(exportCount++>=300 && kind==='progress') return;
  send({event:'export-engine-observe',kind,pid:Process.id,threadId:Process.getCurrentThreadId(),...details});
}
function exportSafe(kind, fn) {try {fn();} catch(e) {exportEmit(kind+'-read-error',{error:String(e)});}}
rpc.exports = {
  start(output) {
    expectedPath = exportPath(output);
    if(exportHooks.length) throw Error('Observer already started');
    const ex=exportVe.getExportByName('?exportStart@ExportClient@@SAXV?$shared_ptr@UExportStartReqStruct@lyra@@@std@@AEBV?$function@$$A6AXV?$shared_ptr@URespStruct@lyra@@@std@@@Z@3@_NJ@Z');
    if(!ex.equals(exportVe.base.add(0x17170b0))) throw Error('Export entry ABI mismatch');
    exportHooks.push(Interceptor.attach(ex,{onEnter(args) {exportSafe('start',()=>{
      const q=args[0].readPointer();
      if(!q.readPointer().equals(exportVe.base.add(0x30368a0)) && !q.readPointer().equals(exportFrontend.base.add(0xc8f4f50))) {
        const table=q.readPointer(),mod=Process.findModuleByAddress(table);
        exportEmit('request-type',{request:q.toString(),table:table.toString(),module:mod&&mod.name,rva:mod&&table.sub(mod.base).toString()});
        throw Error('Unrecognized native ExportStartReqStruct vtable');
      }
      const nativeOutput=exportString(q.add(0x58));
      exportEmit('start-candidate',{output:nativeOutput,expectedOutput:expectedPath,sid:args[3].toInt32()});
      if(!exportExpectedOutput(nativeOutput))return;
      if(observedPath!==null)throw Error('Multiple engine requests target the private export directory');
      const c=q.add(0x78);exportActive=true;observedSid=args[3].toInt32();observedPath=exportPath(nativeOutput);
      exportEmit('start',{sid:args[3].toInt32(),request:q.toString(),output:exportString(q.add(0x58)),
        source:exportString(q.add(0x440)),mode:q.add(0x460).readS32(),
        width:c.add(0x47).readS32(),height:c.add(0x4b).readS32(),fps:c.add(0x52).readDouble(),
        bitrate:c.add(0x66).readS64().toString(),start:c.add(0x168).readS64().toString(),end:c.add(0x170).readS64().toString()});
    });}}));
    // ExportService's startup helper receives the exact path and callback objects.
    // Bind the shared response object: background preview exports can share a SID.
    exportHooks.push(Interceptor.attach(exportVe.base.add(0x1ea8330),{onEnter(args) {if(exportActive) exportSafe('bind',()=>{
      if(exportPath(exportString(args[1]))!==observedPath)return;
      const callback=args[4].add(0x38).readPointer();
      if(callback.isNull()||!callback.readPointer().equals(exportVe.base.add(0x31b1e48)))throw Error('Export completion callback ABI mismatch');
      if(callback.add(0x58).readS32()!==observedSid)throw Error('Export callback session mismatch');
      observedResponse=callback.add(0x48).readPointer().toString();
      exportEmit('bound',{response:observedResponse,sid:observedSid,output:observedPath});
    });}}));
    exportHooks.push(Interceptor.attach(exportVe.base.add(0x1eabc40),{onEnter(args) {if(exportActive) exportSafe('progress',()=>{
      if(args[0].add(0x48).readPointer().toString()!==observedResponse)return;
      exportEmit('progress',{response:args[0].add(0x48).readPointer().toString(),progress:args[1].readDouble()});
    });}}));
    exportHooks.push(Interceptor.attach(exportVe.base.add(0x1eaba40),{onEnter(args) {if(exportActive) exportSafe('complete',()=>{
      if(args[0].add(0x58).readS32()!==observedSid||args[0].add(0x48).readPointer().toString()!==observedResponse)return;
      const error=args[2].readPointer();
      exportEmit('complete',{sid:args[0].add(0x58).readS32(),response:args[0].add(0x48).readPointer().toString(),
        success:args[1].readU8()!==0,error:error.isNull()?null:{code:error.add(8).readS64().toString(),message:exportString(error.add(0x10))}});
      exportActive=false;
    });}}));
    Interceptor.flush();
    return {ready:true,pid:Process.id,module:exportVe.path,readOnly:true};
  },
  stop() { for(const h of exportHooks) h.detach();exportHooks.length=0;exportActive=false;return {events:exportCount}; }
};
