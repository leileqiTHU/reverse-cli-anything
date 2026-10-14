// Version-pinned, narrow adapter for the running CapCut editor.
const lyra=Process.getModuleByName('lyra_cli_client.dll');
const ve=Process.getModuleByName('videoeditor.dll');
const nf=(p,r,a)=>new NativeFunction(p,r,a,{abi:'win64',exceptions:'propagate'});
const create=nf(lyra.getExportByName('?Create@Client@lyra_cli@@SA?AV?$shared_ptr@VClient@lyra_cli@@@std@@AEBUCreateOptions@12@@Z'),'pointer',['pointer','pointer']);
const release=nf(lyra.base.add(0x193a0),'void',['pointer']);
const destroy=nf(lyra.base.add(0x15b30),'void',['pointer']);
function str(p) {
  const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();
  if(n>4*1024*1024 || cap<n) throw Error('Invalid native string');
  return (cap<16?p:p.readPointer()).readUtf8String(n);
}
function inventory() {
  const server=ve.base.add(0x4243ca8),head=server.add(8).readPointer(),current=server.add(0x50).readS32();
  const sessions=[],seen=new Set();
  if(!head.isNull()) {
    let node=head.readPointer();
    for(let i=0;!node.equals(head);i++,node=node.readPointer()) {
      if(i>=128 || node.isNull() || seen.has(node.toString())) throw Error('Invalid session map');
      seen.add(node.toString());
      const sid=node.add(16).readS32(),s=node.add(24).readPointer();
      if(s.isNull()) continue;
      const name=str(s.add(0x140));
      sessions.push({sid,name,current:sid===current,ready:sid>0 && s.add(16).readS32()===sid && name==='edit' && !s.add(0x38).readPointer().isNull() && s.add(0xf8).readU8()===1});
    }
  }
  return {pid:Process.id,current,sessions,modules:[lyra.path,ve.path],executable:Process.mainModule.path};
}
function execute(bytes,sid,argvMode=false) {
  const active=inventory();
  const editors=active.sessions.filter(s=>s.ready);
  if(editors.length!==1 || editors[0].sid!==sid) throw Error('Editor session changed, is ambiguous or is uninitialized');
  const shared=Memory.alloc(16),result=Memory.alloc(104),input=Memory.alloc(32),keep=[];
  function borrowedString(p,b) {
    if(!Array.isArray(b)||b.length>262144||b.some(x=>!Number.isInteger(x)||x<1||x>255))throw Error('Invalid UTF-8 argument bytes');
    const data=Memory.alloc(b.length+1);keep.push(data);if(b.length)data.writeByteArray(b);data.add(b.length).writeU8(0);
    if(b.length<16){if(b.length)p.writeByteArray(b);}else p.writePointer(data);
    p.add(16).writeU64(b.length);p.add(24).writeU64(Math.max(15,b.length));
  }
  if(argvMode) {
    if(!Array.isArray(bytes)||bytes.length<2||bytes.length>128)throw Error('Invalid native argv');
    const vector=Memory.alloc(bytes.length*32);keep.push(vector);
    bytes.forEach((b,i)=>borrowedString(vector.add(i*32),b));
    input.writePointer(vector);input.add(8).writePointer(vector.add(bytes.length*32));input.add(16).writePointer(vector.add(bytes.length*32));
  } else borrowedString(input,bytes);
  const options=Memory.alloc(32),sentinel=Memory.alloc(0x60),factory=Memory.alloc(40);
  options.writeS32(-1); [0,8,16].forEach(o=>sentinel.add(o).writePointer(sentinel));
  sentinel.add(24).writeU16(0x101);options.add(8).writePointer(sentinel);options.add(24).writeU8(1);
  factory.writeS32(sid);factory.add(8).writeUtf8String('windows');factory.add(24).writeU64(7);factory.add(32).writeU64(15);
  create(shared,factory);
  const object=shared.readPointer(),control=shared.add(8).readPointer();let completed=false;
  try {
    const table=object.readPointer();if(!table.equals(lyra.base.add(0x6225a8))) throw Error('Native layout mismatch');
    if(argvMode&&!table.add(8).readPointer().equals(lyra.base.add(0x17bb0)))throw Error('Native argv ABI mismatch');
    nf(table.add(argvMode?8:16).readPointer(),'pointer',['pointer','pointer','pointer','pointer'])(object,result,input,options);completed=true;
    const report={exitCode:result.readS32(),stdout:str(result.add(8)),stderr:str(result.add(40))};
    if(report.exitCode!==0) throw Error(report.stderr || report.stdout);
    const envelope=JSON.parse(report.stdout);if(envelope.err_code!==0) throw Error(report.stdout);
    return envelope.result;
  } finally { if(completed) destroy(result);if(!control.isNull()) release(control); }
}
const ascii=s=>Array.from(s,c=>c.charCodeAt(0));
function snapshot(sid) { return JSON.parse(execute(ascii('draft extract --scope full'),sid).json_result); }
function createOwnedDraft() {
  const factory=ve.getExportByName('?CreateEmptyDraft@lvve@@YAPEAVDraft@1@XZ');
  const controlVtable=ve.base.add(0x2fa31e0);
  if(!factory.equals(ve.base.add(0x10cc460)) ||
      !controlVtable.readPointer().equals(ve.base.add(0xfcf40)) ||
      !controlVtable.add(8).readPointer().equals(ve.base.add(0xb1cb0))) throw Error('Native Draft ABI mismatch');
  const raw=nf(factory,'pointer',[])();
  if(raw.isNull()) throw Error('Native Draft allocation failed');
  let control=null;
  try {
    if(!raw.readPointer().equals(ve.base.add(0x2f59818))) throw Error('Native Draft vtable mismatch');
    const id=str(raw.add(8));
    if(!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)) throw Error('Invalid new Draft UUID');
    control=nf(ve.base.add(0x2d84a8c),'pointer',['uint64'])(0x18);
    if(control.isNull()) throw Error('Native Draft control allocation failed');
    // Native caller19f3d81..19f3dcf uses this exact raw-pointer control block.
    control.writePointer(controlVtable);control.add(8).writeU32(1);control.add(12).writeU32(1);control.add(16).writePointer(raw);
    return {raw,control,id};
  } catch(e) {
    if(control===null || control.isNull()) nf(raw.readPointer().readPointer(),'pointer',['pointer','uint'])(raw,1);
    else release(control);
    throw e;
  }
}
function addTimeline(req,sid,previousTimelineId,before) {
  const bytes=req.timeline_name_bytes;
  if(!Array.isArray(bytes)||bytes.length<1||bytes.length>255||bytes.some(b=>!Number.isInteger(b)||b<1||b>255)) throw Error('Timeline name must be 1..255 nonzero UTF-8 bytes');
  if(typeof req.render_index_track_mode_on!=='boolean') throw Error('Expected source draft render-index mode');
  const data=Memory.alloc(bytes.length+1);data.writeByteArray(bytes);data.add(bytes.length).writeU8(0);
  const name=data.readUtf8String(bytes.length); // Reject malformed UTF-8 before native allocations.
  const request=Memory.alloc(16),response=Memory.alloc(16);
  let requestControl=null,ownedDraft=null,entered=false,returned=false;
  let newUUID=null;
  try {
    nf(ve.base.add(0x222be40),'pointer',['pointer'])(request);
    requestControl=request.add(8).readPointer();
    const q=request.readPointer();
    if(q.isNull()||!q.readPointer().equals(ve.base.add(0x321dea8))) throw Error('Native AddTimeline request ABI mismatch');
    if(!q.add(0x78).readPointer().isNull()||!q.add(0x80).readPointer().isNull()) throw Error('Native AddTimeline draft slot not empty');
    // Same native string assign used by this factory; heap storage belongs to DLL.
    nf(ve.base.add(0xb55a0),'pointer',['pointer','pointer','uint64'])(q.add(0x58),data,bytes.length);
    if(str(q.add(0x58))!==name) throw Error('Native timeline name assignment failed');
    ownedDraft=createOwnedDraft();newUUID=ownedDraft.id;
    if(newUUID.toUpperCase()===previousTimelineId.toUpperCase()) throw Error('Native Draft UUID collision');
    // The native CreateEmptyDraftFromMainDraft path uses these same getter/setter
    // functions. Only configure this newly owned Draft, before publishing it.
    const mode=Memory.alloc(1);mode.writeU8(req.render_index_track_mode_on?1:0);
    nf(ve.base.add(0x66b820),'void',['pointer','pointer'])(ownedDraft.raw,mode);
    const actualMode=nf(ve.base.add(0x650fd0),'pointer',['pointer'])(ownedDraft.raw).readU8()!==0;
    if(actualMode!==req.render_index_track_mode_on) throw Error('New Draft native render-index mode readback failed');
    q.add(0x78).writePointer(ownedDraft.raw);q.add(0x80).writePointer(ownedDraft.control);
    ownedDraft=null; // Transfer the single native strong reference into request.
    q.add(0x88).writeU8(1);q.add(0x89).writeU8(0); // Open new tab, retain current focus.
    const checked=snapshot(sid).find(row=>row.type==='draft');
    if(!checked || checked.id.toUpperCase()!==previousTimelineId.toUpperCase()) throw Error('Active timeline changed while preparing the new timeline');
    send({event:'add-timeline',stage:'prepared',pid:Process.id,sid,previousTimelineId,newUUID,name});
    entered=true;
    nf(ve.base.add(0x1778050),'pointer',['pointer','pointer','int'])(response,request,sid);
    returned=true;requestControl=null; // Native API consumed request's reference.
    const r=response.readPointer(),control=response.add(8).readPointer();
    try {
      if(r.isNull()) throw Error('Native AddTimeline returned no response; outcome unknown for '+newUUID);
      const result={backend:'capcut-native-editor',pid:Process.id,sid,previousTimelineId,newUUID,
        timelineId:str(r.add(0x50)),nativeTimelineId:r.add(0x70).readS32(),nativeError:r.add(0x4c).readS32(),
        name,opened:true,focusRequested:false,persistenceVerified:false,
        renderIndexTrackModeOn:actualMode,before};
      send({event:'add-timeline',stage:'native-returned',...result});
      if(result.nativeError!==0) throw Error('Native AddTimeline failed: '+result.nativeError+'; candidate UUID '+newUUID);
      if(result.timelineId.toUpperCase()!==newUUID.toUpperCase() || result.nativeTimelineId<0) throw Error('Native AddTimeline identity/open result mismatch; outcome unknown for '+newUUID);
      // Python verifies saved project and draft content; the new tab need not be active.
      return result;
    } finally {if(!control.isNull()) release(control);}
  } finally {
    if(ownedDraft!==null) release(ownedDraft.control);
    if(!entered && requestControl!==null && !requestControl.isNull()) release(requestControl);
    if(entered&&!returned) send({event:'add-timeline',stage:'outcome-unknown',pid:Process.id,sid,newUUID});
  }
}
rpc.exports={
  identity() { return {modules:[lyra.path,ve.path],executable:Process.mainModule.path}; },
  inventory,
  active() {
    const editors=inventory().sessions.filter(s=>s.ready);
    if(editors.length!==1) throw Error('Exactly one initialized editable project is required');
    return {sid:editors[0].sid,summary:snapshot(editors[0].sid)};
  },
  run(req) {
    const state=inventory();
    const normalize=p=>p.replace(/\\/g,'/').toLowerCase();
    if(state.modules.some(p=>!normalize(p).startsWith(normalize(req.capcut_dir)+'/'))) throw Error('Module path mismatch');
    // The server-global current SID can still point at a background session
    // after a normal GUI project creation. Bind the unique initialized editor;
    // the next native read must also match the caller's exact timeline UUID.
    const editors=state.sessions.filter(s=>s.ready);
    if(editors.length!==1) throw Error('Exactly one initialized editable project is required');
    const sid=editors[0].sid;
    const before=snapshot(sid),draft=before.find(x=>x.type==='draft');
    if(!draft || draft.id.toUpperCase()!==req.timeline_id.toUpperCase()) throw Error('Active timeline does not match the requested project/timeline');
    if(req.action==='inspect') return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,summary:before};
    if(req.action==='extension-step') {
      const args=req.argv_bytes;
      if(!Array.isArray(args))throw Error('Expected structured native arguments');
      const decode=b=>{const p=Memory.alloc(b.length+1);p.writeByteArray(b);p.add(b.length).writeU8(0);return p.readUtf8String(b.length);};
      const head=args.slice(0,3).map(decode).join(' ');
      const allowed=['draft audio add','draft audio volume','draft audio fade','draft subtitle add',
        'draft text style','draft text translate','draft video crop','draft video scale',
        'draft video rotate','draft video translate','draft video alpha','draft video volume',
        'draft video speed','draft segment time-range','draft segment move'];
      if(!allowed.includes(head)||req.expected_sid!==sid)throw Error('Unsupported extension step or changed SID');
      if(JSON.stringify(before)!==JSON.stringify(JSON.parse(req.expected_summary)))throw Error('Native timeline changed between extension steps');
      try {
        const native=execute(args,sid,true);
        return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,native,summary:snapshot(sid)};
      } catch(error) {
        // A returned error plus a fresh snapshot lets Python distinguish a
        // confirmed unchanged rejection from a genuinely unknown native outcome.
        return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,nativeError:String(error),summary:snapshot(sid)};
      }
    }
    if(req.action==='frame') {
      if(!Number.isSafeInteger(req.at_us)||req.at_us<0||!Number.isSafeInteger(req.short_side)||req.short_side<1||req.short_side>4096)throw Error('Invalid native frame request');
      const bytes=req.frame_directory_bytes;
      if(!Array.isArray(bytes)||bytes.length<1||bytes.some(b=>!Number.isInteger(b)||b<1||b>255||[34,10,13].includes(b)))throw Error('Unsafe frame directory');
      const command=ascii('draft video extract-frames --output-path "').concat(bytes,ascii('" --timestamp '+req.at_us+'us --short-side '+req.short_side+'px'));
      const native=execute(command,sid),after=snapshot(sid);
      return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,native,summary:after};
    }
    if(req.action==='add-timeline') return addTimeline(req,sid,draft.id,before);
    if(req.action==='undo' || req.action==='redo') {
      if(!Number.isInteger(req.steps)||req.steps<1||req.steps>100) throw Error('Invalid history count');
      const native=execute(ascii('draft history '+req.action+' --steps '+req.steps),sid),after=snapshot(sid);
      return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,native,summary:after};
    }
    if(['trim','split','move','remove'].includes(req.action)) {
      const id=req.segment_id;
      if(!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)) throw Error('Invalid segment UUID');
      const matches=before.filter(x=>x.id.toUpperCase()===id.toUpperCase() && x.type==='video');
      if(matches.length!==1) throw Error('Requested video segment is not in the active timeline');
      const clip=matches[0],expected=req.expected_target_us;
      if(!expected || ['start','duration'].some(k=>Math.abs(clip.timeline[k+'.ms']*1000-expected[k])>=1000)) throw Error('Clip timing changed since validation');
      if(req.expected_source_us && ['start','duration'].some(k=>clip.attributes[k+'.ms']!==req.expected_source_us[k])) throw Error('Clip source changed since validation');
      const safe=n=>Number.isSafeInteger(n)&&n>=0;
      let command;
      if(req.action==='trim') {
        if(!safe(req.in_us)||!safe(req.out_us)||req.in_us>=req.out_us) throw Error('Invalid trim range');
        command='time-range --in '+req.in_us+'us --out '+req.out_us+'us';
      } else if(req.action==='split') {
        if(!Array.isArray(req.points_us)||!req.points_us.length||req.points_us.length>100||req.points_us.some((p,i)=>!safe(p)||p<=0||(i>0&&p<=req.points_us[i-1]))) throw Error('Invalid split points');
        command='split --points '+req.points_us.map(p=>p+'us').join(',');
      } else if(req.action==='move') {
        if(!safe(req.start_us)) throw Error('Invalid move start');
        command='move --start '+req.start_us+'us';
      } else command='remove';
      send({stage:'clip-command-enter',command:'draft segment '+command+' --seg-id '+id,sid});
      const native=execute(ascii('draft segment '+command+' --seg-id '+id),sid),after=snapshot(sid);
      return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,native,before,summary:after};
    }
    if(req.action!=='add-video') throw Error('Unsupported editor action');
    const track=req.track;
    if(!Number.isInteger(track)||track<0||track>1024) throw Error('Invalid native track/layer index');
    // Command bytes are built by the Python worker after local media validation.
    const prefix=ascii('draft video add --track '+track+' ');
    const native=execute(prefix.concat(req.video_arguments),sid),after=snapshot(sid);
    const ids=native.segment_ids??[];
    if(!ids.length || !ids.every(id=>after.some(x=>x.id===id))) throw Error('Native edit returned, but readback could not verify it; outcome unknown');
    return {backend:'capcut-native-editor',pid:Process.id,sid,timelineId:draft.id,requestedTrackIndex:track,native,summary:after,verified:'native-summary'};
  }
};
