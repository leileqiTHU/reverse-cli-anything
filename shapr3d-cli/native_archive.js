extensions.set('export-shapr',async(req,o)=>{
 await ensureModelMutation(o);
 let result=null;const d=delegate('f02e8944-5490-5cf3-b426-61cc5107adad',['pointer','pointer'],(path,error)=>result={path:text(path),error:text(error)});
 await onUI(()=>{
  const opts=pointerResult(factory('Shapr.Kernel.MTExportOptions','70f4fc6a-3855-50b4-bffd-9466cd8e2300'),6,['int'],[0]);
  check(call(opts,9,['pointer'],[hstr(req.name)]),'Shapr filename');
  check(call(pointerResult(o.app,30),6,['pointer','pointer','pointer','pointer','pointer'],[hstr(req.directory),opts,nullp,nullp,d.pointer]),'Export native project archive');
 });
 const end=Date.now()+60000;while(result===null&&Date.now()<end)await delay(25);
 if(result===null)throw new Error('Native archive export timeout');if(result.error)throw new Error(result.error);
 return {...result,format:'Shapr'};
});
