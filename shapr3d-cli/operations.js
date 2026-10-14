// Development operations loaded only by the local, user-owned pilot session.
extensions.set('onboarding-status',async(req,o)=>onUI(()=>{
 const handler=pointerResult(o.model,11);return {showing:numberResult(handler,6,'bool')};
}));
extensions.set('onboarding-exit',async(req,o)=>onUI(()=>{
 const handler=pointerResult(o.model,11);const showing=numberResult(handler,6,'bool');
 if(showing)check(call(handler,13,['int'],[0]),'Onboarding.Finish(Abort)');
 return {wasShowing:showing,showing:numberResult(handler,6,'bool')};
}));
async function awaitDelegateResult(read,timeout=60000){const end=Date.now()+timeout;while(read()===null&&Date.now()<end)await delay(25);if(read()===null)throw new Error('Native completion timeout; outcome unknown');return read();}
function progressDelegate(record){
 // MSVC x64 passes this 24-byte aggregate by an implicit pointer.
 return delegate('d2bc1688-da73-53ae-b94c-cc318602874c',['pointer'],p=>{
  const state={status:p.readS32(),phase:p.add(4).readS32(),total:p.add(8).readS32(),current:p.add(12).readS32(),errorCode:p.add(16).readS32(),hasDiscardedContent:!!p.add(20).readU8()};record(state);
 });
}
extensions.set('import-native',async(req,o)=>{
 await ensureModelMutation(o);
 let result=null;const states=[];const d=progressDelegate(s=>{states.push(s);if(s.status===2||s.status===3)result=s;});
 await onUI(()=>{const controller=pointerResult(o.app,31),options=alloc(32); // all nullable fields null; ShouldReplaceProject=false.
  check(call(controller,12,['pointer','pointer','pointer','pointer'],[hstr(req.path),hstr(req.name),options,d.pointer]),'ImportFileIntoCurrentProject');
 });
 await awaitDelegateResult(()=>result);
 if(result.status!==2||result.errorCode!==0)throw new Error('Import failed: '+JSON.stringify(result));
 return {completed:true,states};
});
extensions.set('export-stl',async(req,o)=>{
 let result=null;
 const d=delegate('f02e8944-5490-5cf3-b426-61cc5107adad',['pointer','pointer'],(path,error)=>{result={path:text(path),error:text(error)};});
 await onUI(()=>{
  const f=factory('Shapr.Kernel.MTExportOptions','70f4fc6a-3855-50b4-bffd-9466cd8e2300');
  const opts=pointerResult(f,6,['int'],[4]);
  check(call(opts,9,['pointer'],[hstr(req.name)]),'Export filename');
  const act=native('RoActivateInstance','int',['pointer','pointer']),out=alloc(8);
  check(act(hstr('Shapr.Kernel.MTStlExportOptions'),out),'Activate STL options');const stl=own(out.readPointer());
  const settings=query(stl,'6c8011fe-4d42-5008-a477-13cf28921bd3'),resolution=alloc(24);
  check(call(settings,6,['pointer'],[resolution]),'Read STL resolution');resolution.writeS32(0);
  check(call(settings,7,['pointer'],[resolution]),'Set Low resolution');
  check(call(settings,9,['int'],[1]),'Binary STL');check(call(settings,11,['int'],[0]),'Millimeter');
  const format=query(settings,'ac1261ce-e476-11eb-ba80-0242ac130004');check(call(opts,21,['pointer'],[format]),'Set STL format');
  const controller=pointerResult(o.app,30);
  check(call(controller,6,['pointer','pointer','pointer','pointer','pointer'],[hstr(req.directory),opts,nullp,nullp,d.pointer]),'Export STL');
 });
 await awaitDelegateResult(()=>result);
 if(result.error)throw new Error('Export failed: '+result.error);
 return {...result,format:'STL',resolution:'Low',unit:'mm'};
});
extensions.set('history-set',async(req,o)=>{
 await ensureModelMutation(o);
 let ui,id,before,result=null;
 await onUI(()=>{
  const manager=pointerResult(o.model,14),f=factory('Shapr.CommonApp.MTDesignHistoryStepsListUI',COM.historyFactory);ui=pointerResult(f,6,['pointer'],[manager]);
 });await delay(150);
 await onUI(()=>{
  const rows=historyRows(ui);
  for(const c of arrayResult(ui,22)){
   const step=pointerResult(c,8);if(step.isNull()||textResult(step,7)!==req.step)continue;
   for(const p of arrayResult(step,13)){
    const def=pointerResult(p,7);if(textResult(def,6)!==req.parameter)continue;
    if(id)throw new Error('Ambiguous history parameter');
    const info=pointerResult(def,10);if(numberResult(info,6)!==1)throw new Error('Parameter is not numeric');
    id=pointerResult(p,6);before=rows.find(s=>s.name===req.step).parameters.find(p=>p.label===req.parameter).numericValue;
   }
  }
  if(!id)throw new Error('History parameter not found');
 });
 const d=delegate('dab61c08-9b42-5617-858c-1822458a0b1b',['int'],code=>{result={errorCode:code};});
 await onUI(()=>{check(call(ui,31,['pointer','pointer','int','pointer'],[id,hstr(req.expression),0,d.pointer]),'SetStepValueParameter');});
 await awaitDelegateResult(()=>result);
 if(result.errorCode!==0)throw new Error('Native edit failed: '+JSON.stringify(result));
 return {step:req.step,parameter:req.parameter,before,expression:req.expression,...result,history:await onUI(()=>historyRows(ui))};
});
extensions.set('close-native',async(req,o)=>{
 if(projectToken.isNull())throw new Error('Close requires a project created by this pilot session');
 let done=null;const d=delegate('7f7be714-3548-54b1-94fc-c22f8a6afb29',[],()=>{done=true;});
 await onUI(()=>{check(call(pointerResult(o.app,31),8,['pointer'],[d.pointer]),'CloseProject');});
 await awaitDelegateResult(()=>done);return {completed:true};
});
extensions.set('reopen-native',async(req,o)=>{
 if(projectToken.isNull())throw new Error('No retained project token');
 let result=null;const states=[];const d=progressDelegate(s=>{states.push(s);if(s.status===2||s.status===3)result=s;});
 await onUI(()=>{check(call(pointerResult(o.app,31),10,['pointer','int','pointer','pointer'],[projectToken,0,nullp,d.pointer]),'OpenProject');});
 await awaitDelegateResult(()=>result);return {completed:result.status===2&&result.errorCode===0,states};
});

async function waitEditor(o,expected){const end=Date.now()+15000;let actual;do{actual=await onUI(()=>numberResult(o.editor,8));if(actual===expected)return actual;await delay(25);}while(Date.now()<end);throw new Error('Editor transition timeout: '+actual);}
extensions.set('editor-deactivate',async(req,o)=>{
 const before=await onUI(()=>{const before=numberResult(o.editor,8);check(call(o.editor,41),'Editor.Defocus');check(call(o.editor,9,['int'],[2]),'ActiveEditor.None');return before;});
 return {before,after:await waitEditor(o,2)};
});
extensions.set('editor-activate',async(req,o)=>{
 await onUI(()=>{check(call(o.editor,9,['int'],[1]),'ActiveEditor.Model');});
 await waitEditor(o,1);await onUI(()=>{check(call(o.editor,40),'Editor.Focus');});return {activeEditor:1};
});
extensions.set('project-close',async(req,o)=>{
 if(projectToken.isNull())throw new Error('Close requires a project created by this pilot session');
 await extensions.get('editor-deactivate')(req,o);
 return await extensions.get('close-native')(req,o);
});
extensions.set('project-reopen',async(req,o)=>{
 const result=await extensions.get('reopen-native')(req,o);
 if(!result.completed)throw new Error('Reopen failed: '+JSON.stringify(result));
 await extensions.get('editor-activate')(req,o);return result;
});
extensions.set('leave-native',async(req,o)=>{
 let done=null;const d=delegate('315d9005-7645-57d6-9121-a196622f1746',[],()=>{done=true;});
 await onUI(()=>{check(call(pointerResult(o.app,31),7,['pointer'],[d.pointer]),'LeaveProject');});
 await awaitDelegateResult(()=>done);return {completed:true};
});
