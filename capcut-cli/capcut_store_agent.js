// Version-pinned native CapCut project store bridge. Loading this agent is inert.
// The host verifies on-disk module hashes and source-media metadata before RPC.
// Import is restricted to a closed project: an active frontend model otherwise
// replaces the native material list on its next bulk save.
'use strict';
const HASHES = {
  'videoeditor.dll': '029986c9a26f3db4222402d00283cc610c81247b50ee9827e281daf626426b90',
  'lyra_cli_client.dll': '1760a1d8752c2cba1c3ea572f3c1ec0ce4e8ca0da90b0bb8032d297804bcde97',
  'VECreator.dll': '576bc1f51c0e81d50369e2ee69c157389a310151f1e75ea79813d9753be2db77',
  'Qt6Core.dll': '88f0da8219ab163c2949cb862fc00356e9c96df3bd4a0013bde14aa285bbc925',
};
const DIRECTORY = 'D:/Apps/CapCut2/CapCut/9.5.0.4050';
const ve = Process.getModuleByName('videoeditor.dll');
const lyra = Process.getModuleByName('lyra_cli_client.dll');
const frontend = Process.getModuleByName('VECreator.dll');
const qt = Process.getModuleByName('Qt6Core.dll');
const nf = (p, r, a) => new NativeFunction(p, r, a, {abi: 'win64', exceptions: 'propagate'});
const normalize = s => s.replace(/\\/g, '/').replace(/\/$/, '').toLowerCase();
let attempted = false, pending = null, createdPendingName = null;
let promotionDismissAttempted = false;

function textAt(p) {
  const n = p.add(16).readU64().toNumber(), c = p.add(24).readU64().toNumber();
  if (!Number.isSafeInteger(n) || n > 32768 || c < n || c > 0x7fffffff) throw Error('Native string bounds');
  return n ? (c < 16 ? p : p.readPointer()).readUtf8String(n) : '';
}
function input(bytes, allowEmpty = false) {
  if (!Array.isArray(bytes) || (!allowEmpty && bytes.length === 0) || bytes.length > 32767 ||
      bytes.some(b => !Number.isInteger(b) || b < 1 || b > 255)) throw Error('Valid UTF-8 byte array required');
  const value = Memory.alloc(32), data = Memory.alloc(bytes.length + 1);
  data.writeByteArray(bytes); data.add(bytes.length).writeU8(0);
  if (bytes.length < 16) value.writeByteArray(bytes); else value.writePointer(data);
  value.add(16).writeU64(bytes.length); value.add(24).writeU64(Math.max(15, bytes.length));
  return {value, data, text: data.readUtf8String(bytes.length)};
}
function note(stage, data = {}) {
  send({event: 'native-project-store', stage, pid: Process.id, threadId: Process.getCurrentThreadId(), ...data});
}
function guard(req) {
  if (!req || req.pid !== Process.id || Process.arch !== 'x64' || Process.pointerSize !== 8) throw Error('Fresh x64 process identity required');
  for (const m of [ve, lyra, frontend, qt]) {
    if (normalize(m.path) !== normalize(DIRECTORY + '/' + m.name)) throw Error('Module path mismatch: ' + m.name);
    if (!req.verifiedHashes || req.verifiedHashes[m.name] !== HASHES[m.name]) throw Error('Host hash verification required: ' + m.name);
  }
  const singleton = frontend.base.add(0xe39e780), g = frontend.base.add(0xe39e940).readS32();
  if (g === 0 || g === -1) throw Error('Native frontend manager is not initialized');
  const shared = singleton.add(0x28), manager = shared.readPointer(), control = shared.add(8).readPointer();
  if (manager.isNull() || control.isNull()) throw Error('Native manager unavailable');
  const vt = manager.readPointer(), col = frontend.base.add(0xcd36da8);
  if (!vt.equals(frontend.base.add(0x969b3e0)) || !vt.readPointer().equals(frontend.base.add(0x10d5110)) ||
      !vt.sub(8).readPointer().equals(col) || col.readU32() !== 1 || col.add(4).readU32() !== 0 ||
      col.add(12).readU32() !== 0xe0351b8 || col.add(20).readU32() !== 0xcd36da8) throw Error('Native manager RTTI mismatch');
  if (!manager.add(8).readPointer().equals(manager) || !manager.add(16).readPointer().equals(control)) throw Error('Manager weak-self identity changed');
  const strong = control.add(8).readS32(), weak = control.add(12).readS32();
  if (strong < 1 || strong > 1000000 || weak < 1 || weak > 1000000) throw Error('Native manager reference counts invalid');
  const rootPath = textAt(manager.add(0x20)), draftRoot = textAt(manager.add(0x80));
  if (!/^d:\//i.test(normalize(draftRoot))) throw Error('Draft root must be on drive D:');
  if (req.expectedDraftRoot !== undefined && normalize(draftRoot) !== normalize(req.expectedDraftRoot)) throw Error('Draft root changed');
  const app = qt.base.add(0x4d7580).readPointer();
  if (app.isNull()) throw Error('Qt application unavailable');
  return {singleton, manager, control, rootPath, draftRoot, app, currentSid: ve.base.add(0x4243cf8).readS32()};
}
function qtExport(name, rva) {
  const p = qt.getExportByName(name);
  if (!p.equals(qt.base.add(rva))) throw Error('Qt export ABI mismatch: ' + name);
  return p;
}
function onApplicationThread(req, fn) {
  if (pending !== null) throw Error('A native operation is already queued');
  const initial = guard(req), expectedSid = initial.currentSid;
  const notify = qtExport('?notifyInternal2@QCoreApplication@@CA_NPEAVQObject@@PEAVQEvent@@@Z', 0x9ccd0);
  const eventCtor = nf(qtExport('??0QEvent@@QEAA@W4Type@0@@Z', 0xa2320), 'pointer', ['pointer', 'int']);
  const eventDtor = nf(qtExport('??1QEvent@@UEAA@XZ', 0xa2400), 'void', ['pointer']);
  const cloneEvent = nf(qtExport('?clone@QEvent@@UEBAPEAV1@XZ', 0xa2430), 'pointer', ['pointer']);
  const postEvent = nf(qtExport('?postEvent@QCoreApplication@@SAXPEAVQObject@@PEAVQEvent@@H@Z', 0x9cf10), 'void', ['pointer', 'pointer', 'int']);
  const objectThread = nf(qtExport('?thread@QObject@@QEBAPEAVQThread@@XZ', 0xe23e0), 'pointer', ['pointer']);
  const currentThread = nf(qtExport('?currentThread@QThread@@SAPEAV1@XZ', 0x1772c0), 'pointer', []);
  return new Promise((resolve, reject) => {
    let claimed = false, hook = null, timer = null, event = null, posted = false;
    const unhook = () => {if (hook !== null) {hook.detach(); hook = null;} if (timer !== null) {clearTimeout(timer); timer = null;}};
    const cleanup = () => {
      unhook(); pending = null;
      if (event !== null && !event.isNull() && !posted) {
        // QEvent::clone allocates on Qt's native heap. Its scalar-deleting
        // destructor frees an unposted clone; Qt owns every posted event.
        nf(qt.base.add(0x58f0), 'pointer', ['pointer', 'uint'])(event, 1); event = null;
      }
    };
    pending = {cancel() {if (!claimed) {claimed = true; cleanup(); reject(Error('Cancelled before native operation'));}}};
    try {
      // Use a native-owned, no-op QEvent::None addressed only to qApp. The
      // exact event pointer prevents unrelated UI callbacks from selecting
      // the scheduling point. An entry-only hook never leaves return hooks
      // outstanding in worker dispatchers or nested/modal event loops.
      const temporary = Memory.alloc(16);
      eventCtor(temporary, 0);
      try {event = cloneEvent(temporary);} finally {eventDtor(temporary);}
      if (event.isNull() || !event.readPointer().equals(qt.base.add(0x31e0e8)) ||
          !event.readPointer().readPointer().equals(qt.base.add(0x58f0)) || event.add(8).readU16() !== 0) throw Error('Native scheduling-event ABI mismatch');
      hook = Interceptor.attach(notify, {onEnter(args) {
        if (claimed || !args[0].equals(initial.app) || !args[1].equals(event)) return;
        claimed = true;
        unhook();
        try {
          if (!qt.base.add(0x4d7580).readPointer().equals(initial.app)) throw Error('Qt application changed');
          if (!currentThread().equals(objectThread(initial.app))) throw Error('Scheduling event reached the wrong Qt thread');
          const state = guard(req);
          // Native export creates its own background session. Its dedicated
          // adapter revalidates project/timeline identity inside each callback.
          const exportSession = req.operation === 'editor' && ['export','preview'].includes(req.action) && req.allowExportSessionChanges === true;
          if ((!exportSession && state.currentSid !== expectedSid) || !state.manager.equals(initial.manager) || !state.control.equals(initial.control)) throw Error('Project/session changed while operation was queued');
          const result = fn(state); cleanup(); setImmediate(() => resolve(result));
        } catch (e) {cleanup(); setImmediate(() => reject(e));}
      }});
      timer = setTimeout(() => {if (!claimed) {claimed = true; cleanup(); reject(Error('No Qt application scheduling event within 15 seconds; no operation attempted'));}}, 15000);
      Interceptor.flush();
      posted = true;
      postEvent(initial.app, event, 0);
    } catch (e) {cleanup(); reject(e);}
  });
}
const acquire = nf(ve.base.add(0xbf440), 'pointer', ['pointer', 'pointer']);
const release = nf(lyra.base.add(0x193a0), 'void', ['pointer']);
const destroyStrings = nf(lyra.base.add(0x15b30), 'void', ['pointer']);
function releaseShared(owned) {const c = owned.add(8).readPointer(); if (!c.isNull()) release(c);}
function describeStore(store) {
  const pack = Memory.alloc(104); for (const o of [8, 40, 72]) pack.add(o + 24).writeU64(15);
  try {
    for (const [rva, o] of [[0x1303e70, 8], [0x13040b0, 40], [0x1303e10, 72]]) nf(ve.base.add(rva), 'pointer', ['pointer', 'pointer'])(store, pack.add(o));
    return {id: textAt(pack.add(8)), name: textAt(pack.add(40)), path: textAt(pack.add(72))};
  } finally {destroyStrings(pack);}
}
function withManager(state, fn) {
  const owned = Memory.alloc(16); acquire(state.manager.add(8), owned);
  try {
    if (!owned.readPointer().equals(state.manager) || !owned.add(8).readPointer().equals(state.control)) throw Error('Manager strong reference mismatch');
    return fn();
  } finally {releaseShared(owned);}
}
function withStores(state, fn) {
  const ownedStores = [], lock = nf(ve.base.add(0x2d8407b), 'int', ['pointer']), unlock = nf(ve.base.add(0x2d84081), 'int', ['pointer']);
  try {
    if (lock(state.manager.add(0xa0)) !== 0) throw Error('Manager mutex lock failed');
    try {
      const begin = state.manager.add(0xf0).readPointer(), end = state.manager.add(0xf8).readPointer();
      const bytes = Number.parseInt(end.sub(begin).toString(), 16);
      if (end.compare(begin) < 0 || !Number.isSafeInteger(bytes) || bytes % 16 !== 0 || bytes > 16 * 256) throw Error('Manager project vector bounds');
      for (let i = 0; i < bytes / 16; i++) {
        const entry = begin.add(i * 16), store = entry.readPointer(), control = entry.add(8).readPointer();
        if (store.isNull() || control.isNull()) continue;
        if (!store.readPointer().equals(store) || !store.add(8).readPointer().equals(control)) throw Error('Store weak-self identity mismatch');
        const owned = Memory.alloc(16); acquire(store, owned); ownedStores.push(owned);
        if (!owned.readPointer().equals(store) || !owned.add(8).readPointer().equals(control)) throw Error('Store strong reference mismatch');
      }
    } finally {unlock(state.manager.add(0xa0));}
    return fn(ownedStores.map(owned => ({store: owned.readPointer(), ...describeStore(owned.readPointer())})));
  } finally {for (const owned of ownedStores) releaseShared(owned);}
}
function currentProject(state) {
  // Normal frontend material save: singleton.getCurrentProject(4906390),
  // project.getStoreWrapper(25d71e0), then StoreWrapper.getVirtualStore.
  // The runtime-resolved IAT for that third call is videoeditor+1304ae0;
  // therefore the second getter already returns the StoreWrapper we need.
  // Use the native shared_ptr-copy getters, including the singleton's mutex.
  const project = Memory.alloc(16), store = Memory.alloc(16);
  try {
    nf(frontend.base.add(0x4906390), 'pointer', ['pointer', 'pointer'])(state.singleton, project);
    if (project.readPointer().isNull()) return null;
    if (project.add(8).readPointer().isNull()) throw Error('Current project ownership unavailable');
    nf(frontend.base.add(0x25d71e0), 'pointer', ['pointer', 'pointer'])(project.readPointer(), store);
    const p = store.readPointer(), c = store.add(8).readPointer();
    if (p.isNull() || c.isNull()) throw Error('Current project is changing or has no native store');
    if (!p.readPointer().equals(p) || !p.add(8).readPointer().equals(c)) throw Error('Current StoreWrapper identity mismatch');
    const slot = frontend.base.add(0x73caa18).readPointer();
    if (!slot.equals(ve.base.add(0x1304ae0))) throw Error('Current-project getter ABI changed');
    return describeStore(p);
  } finally {releaseShared(store); releaseShared(project);}
}
function inspectOnUi(state) {
  const controller = windowController();
  const window = controller.add(0x28).readPointer().isNull() ? null : editorWindow(controller);
  // Native loadWindow marks +31 before constructing the QML window at +50.
  // +30 blocks mouse input until draft-loaded handling; +71 is realClose's
  // one-way closing flag. These complement, but do not establish by
  // themselves, readiness of a particular timeline's frontend dependencies.
  const windowLoaded = window !== null && window.add(0x31).readU8() === 1 && !window.add(0x50).readPointer().isNull();
  const inputBlocked = window !== null && window.add(0x30).readU8() !== 0;
  const windowClosing = window !== null && window.add(0x71).readU8() !== 0;
  const blockingModalPresent = window !== null && !!nf(frontend.base.add(0x4f3b980), 'bool', ['pointer'])(window);
  return withManager(state, () => withStores(state, stores => ({
    backend: 'capcut-native-project-store', pid: Process.id, threadId: Process.getCurrentThreadId(),
    draftRoot: state.draftRoot, rootPath: state.rootPath, currentSid: state.currentSid,
    editorWindowPresent: window !== null, windowLoaded, inputBlocked, windowClosing, blockingModalPresent,
    projectLoading: controller.add(0x140).readU8() !== 0,
    currentProject: currentProject(state), projects: stores.map(({store, ...item}) => item),
  })));
}
function importOnUi(req, state) {
  return withManager(state, () => withStores(state, stores => {
    const matches = stores.filter(s => s.id.toLowerCase() === req.projectId.toLowerCase());
    if (matches.length !== 1) throw Error('Project UUID must identify exactly one native store');
    const selected = matches[0];
    if (normalize(selected.path) !== normalize(req.projectPath)) throw Error('Project UUID/path mismatch');
    const active = currentProject(state);
    if (active !== null && (active.id.toLowerCase() === selected.id.toLowerCase() || normalize(active.path) === normalize(selected.path))) throw Error('Target project is currently open. Close it in CapCut before importing media.');
    const material = Memory.alloc(0x150), path = input(req.mediaPathBytes), filename = input(req.fileNameBytes);
    const type = Memory.alloc(4), range = Memory.alloc(16), importMicros = Memory.alloc(8);
    type.writeS32(0); range.writeS64(0); range.add(8).writeS64(req.durationUs); importMicros.writeS64(Date.now() * 1000);
    let constructed = false, entered = false, returned = false;
    try {
      nf(ve.base.add(0x123ce60), 'pointer', ['pointer', 'pointer', 'int'])(material, selected.store, 0); constructed = true;
      nf(ve.base.add(0x123f9e0), 'void', ['pointer', 'pointer'])(material, path.value);
      nf(ve.base.add(0x116ab60), 'void', ['pointer', 'pointer'])(material, filename.value);
      nf(ve.base.add(0x123f9c0), 'void', ['pointer', 'int64'])(material, req.durationUs);
      nf(ve.base.add(0x102e660), 'void', ['pointer', 'int'])(material, req.width);
      nf(ve.base.add(0x12402a0), 'void', ['pointer', 'int'])(material, req.height);
      nf(ve.base.add(0x1240330), 'void', ['pointer', 'int'])(material, 1);
      nf(ve.base.add(0x1240360), 'void', ['pointer', 'pointer'])(material, range);
      nf(ve.base.add(0x12402f0), 'void', ['pointer', 'pointer'])(material, importMicros);
      nf(ve.base.add(0x123f9a0), 'void', ['pointer', 'pointer'])(material, material.add(0x80));
      const materialId = textAt(material.add(0x60)), savedPath = textAt(material);
      if (normalize(savedPath) !== normalize(path.text)) throw Error('Native path normalization changed target');
      entered = true;
      const accepted = !!nf(ve.base.add(0x1304ba0), 'bool', ['pointer', 'pointer', 'pointer'])(selected.store, type, material); returned = true;
      const syncSaved = accepted && !!nf(ve.base.add(0x13071d0), 'bool', ['pointer'])(selected.store);
      return {backend: 'capcut-native-material-store', pid: Process.id, threadId: Process.getCurrentThreadId(),
        projectId: selected.id, projectPath: selected.path, materialId, mediaPath: savedPath,
        accepted, syncSaveReturned: syncSaved, persistenceVerified: false, uiRefreshVerified: false,
        targetWasClosed: true, visibleWhenProjectOpens: true, timelineModified: false};
    } finally {
      if (constructed) nf(ve.base.add(0x123cf90), 'void', ['pointer'])(material);
      if (entered && !returned) note('outcome-unknown', {reason: 'Native import did not return; inspect project state before retrying'});
    }
  }));
}
function windowController() {
  const controller = frontend.base.add(0xe3aa7f0).readPointer();
  if (controller.isNull() || !controller.readPointer().equals(frontend.base.add(0xc92dcc8))) throw Error('Native window-controller identity mismatch');
  const col = controller.readPointer().sub(8).readPointer();
  if (!col.equals(frontend.base.add(0xcf8f758)) || col.add(12).readU32() !== 0xe1e7088) throw Error('Window-controller RTTI mismatch');
  return controller;
}
function homeController() {
  const controller = windowController();
  if (!controller.add(0x28).readPointer().isNull()) throw Error('Close the CapCut editor and return to the homepage before creating or opening a project');
  if (controller.add(0x140).readU8() !== 0) throw Error('A native project is still loading');
  return controller;
}
function editorWindow(controller) {
  const window = controller.add(0x28).readPointer();
  if (window.isNull() || !window.readPointer().equals(frontend.base.add(0xc9312d0))) throw Error('Native editor-window identity mismatch');
  const col = window.readPointer().sub(8).readPointer();
  if (!col.equals(frontend.base.add(0xcf91000)) || col.readU32() !== 1 || col.add(4).readU32() !== 0 ||
      col.add(12).readU32() !== 0xe1e8850 || col.add(20).readU32() !== 0xcf91000) throw Error('Native editor-window RTTI mismatch');
  return window;
}
function validateProjectTarget(req) {
  if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(req.projectId || '') ||
      typeof req.projectPath !== 'string' || !req.projectPath) throw Error('Project UUID and path required');
}
function selectedProject(req, stores) {
  const matches = stores.filter(s => s.id.toLowerCase() === req.projectId.toLowerCase());
  if (matches.length !== 1 || normalize(matches[0].path) !== normalize(req.projectPath)) throw Error('Project UUID/path must identify exactly one registered native store');
  return matches[0];
}
function retainSelectedProject(req, state) {
  // withStores releases the manager mutex before invoking its callback.
  // Keep only the selected store alive across frontend lifecycle operations;
  // release the enumeration's references to all other stores before entering.
  const owned = Memory.alloc(16);
  try {
    const selected = withStores(state, stores => {
      const item = selectedProject(req, stores);
      acquire(item.store, owned);
      if (!owned.readPointer().equals(item.store) || !owned.add(8).readPointer().equals(item.store.add(8).readPointer())) throw Error('Selected project ownership mismatch');
      return item;
    });
    return {owned, ...selected};
  } catch (e) {releaseShared(owned); throw e;}
}
function qtString(text) {
  const bytes = Memory.allocUtf8String(text), value = Memory.alloc(24);
  nf(qtExport('??0QString@@QEAA@PEBD@Z', 0x3b20), 'pointer', ['pointer', 'pointer'])(value, bytes);
  return {value, bytes, dispose() {nf(qtExport('??1QString@@QEAA@XZ', 0x4000), 'void', ['pointer'])(value);}};
}
function openOnUi(req, state) {
  return withManager(state, () => {
    const selected = retainSelectedProject(req, state);
    try {
    const active = currentProject(state), description = {id: selected.id, name: selected.name, path: selected.path};
    if (active !== null) {
      if (active.id.toLowerCase() !== selected.id.toLowerCase() || normalize(active.path) !== normalize(selected.path)) throw Error('Another project is open; close it before opening the selected project');
      const controller = windowController(); editorWindow(controller);
      if (controller.add(0x140).readU8() !== 0) throw Error('The selected project is still loading');
      return {backend: 'capcut-native-project-store', pid: Process.id, ...description,
        alreadyOpen: true, openRequested: false, editorInitializationVerified: false};
    }
    const controller = homeController();
    let path = null, kind = null, entered = false, returned = false;
    try {
      path = qtString(selected.path); kind = qtString('local');
      const range = Memory.alloc(16), origin = input([], true);
      range.writeS64(-1); range.add(8).writeS64(-1);
      note('native-project-open-enter', {projectId: selected.id, projectPath: selected.path});
      entered = true;
      // The native overload builds the 0x68-byte request and owns its copies.
      // Normal homepage open was observed with path, "local", {-1,-1},
      // empty origin, type 0; the remaining flags are its native defaults.
      nf(frontend.base.add(0x4f1c310), 'void', ['pointer', 'pointer', 'pointer', 'pointer', 'pointer', 'int'])(
        controller, path.value, kind.value, range, origin.value, 0);
      returned = true;
      note('native-project-open-return', {projectId: selected.id, projectPath: selected.path});
      return {backend: 'capcut-native-project-store', pid: Process.id, threadId: Process.getCurrentThreadId(),
        ...description, alreadyOpen: false, openRequested: true,
        stage: 'native-project-opening', initializationAsynchronous: true, editorInitializationVerified: false};
    } finally {
      if (kind !== null) kind.dispose();
      if (path !== null) path.dispose();
      if (entered && !returned) note('outcome-unknown', {reason: 'Native open did not return; inspect the project before retrying'});
    }
    } finally {releaseShared(selected.owned);}
  });
}
function closeOnUi(req, state) {
  return withManager(state, () => {
    const selected = retainSelectedProject(req, state);
    try {
    const controller = windowController(), active = currentProject(state);
    const description = {id: selected.id, name: selected.name, path: selected.path};
    if (active === null && controller.add(0x28).readPointer().isNull() && controller.add(0x140).readU8() === 0) {
      return {backend: 'capcut-native-project-store', pid: Process.id, ...description,
        alreadyClosed: true, closeRequested: false, homepageVerified: true, persistenceVerified: false};
    }
    if (active === null || active.id.toLowerCase() !== selected.id.toLowerCase() || normalize(active.path) !== normalize(selected.path)) throw Error('Close is restricted to the explicitly selected open project');
    if (controller.add(0x140).readU8() !== 0) throw Error('The native project is still loading');
    const window = editorWindow(controller);
    let entered = false, returned = false;
    try {
      note('native-project-close-enter', {projectId: selected.id, projectPath: selected.path});
      entered = true;
      // MainWindowViewModel::attemptClose keeps dealClose's normal refusal
      // checks, then realClose's native save and window lifecycle sequence.
      nf(frontend.base.add(0x4f33970), 'void', ['pointer'])(window);
      returned = true;
      note('native-project-close-return', {projectId: selected.id, previousPath: selected.path});
      return {backend: 'capcut-native-project-store', pid: Process.id, threadId: Process.getCurrentThreadId(),
        ...description, previousPath: selected.path, closeRequested: true, alreadyClosed: false,
        stage: 'native-project-close-requested', closureMayBeAsynchronous: true,
        homepageVerified: false, persistenceVerified: false};
    } finally {
      if (entered && !returned) note('outcome-unknown', {reason: 'Native close did not return; inspect the project before retrying'});
    }
    } finally {releaseShared(selected.owned);}
  });
}
function createOnUi(req, state, creation) {
  return withManager(state, () => {
    const controller = homeController();
    if (!controller.equals(creation.controller) || !state.manager.equals(creation.manager)) throw Error('Homepage identity changed while creation was queued');
    if (currentProject(state) !== null) throw Error('A frontend project is still open; return to the homepage before creating');
    const previousIds = withStores(state, stores => {
      if (stores.some(s => s.name.toLowerCase() === creation.name.text.toLowerCase())) throw Error('A project with that name already exists');
      return stores.map(s => s.id);
    });
    const origin = Memory.alloc(24); origin.writeByteArray(new Uint8Array(24));
    let entered = false, returned = false;
    try {
      entered = true;
      nf(frontend.base.add(0x4f20b60), 'void', ['pointer', 'pointer'])(controller, origin);
      returned = true;
      const created = currentProject(state);
      if (created === null || previousIds.includes(created.id)) throw Error('Native creation returned no new frontend project; inspect before retrying');
      if (!normalize(created.path).startsWith(normalize(state.draftRoot) + '/')) throw Error('Native creation returned a path outside the configured draft root');
      createdPendingName = {...created, requestedName: creation.name, renameAttempted: false};
      return {backend: 'capcut-native-project-store', pid: Process.id, threadId: Process.getCurrentThreadId(), ...created,
        stage: 'native-project-initializing', requestedName: creation.name.text, namingPending: true,
        initializationAsynchronous: true, persistenceVerified: false, editorInitializationVerified: false, opened: true};
    } finally {
      if (entered && !returned) note('outcome-unknown', {reason: 'Native homepage creation did not return; inspect state before retrying'});
    }
  });
}
function finishCreateOnUi(req, state) {
  const created = createdPendingName;
  if (created === null || created.renameAttempted || req.projectId !== created.id || normalize(req.projectPath || '') !== normalize(created.path)) throw Error('Naming is restricted to this agent\'s newly created project');
  return withManager(state, () => withStores(state, stores => {
    const matches = stores.filter(s => s.id === created.id && normalize(s.path) === normalize(created.path));
    if (matches.length !== 1) throw Error('Created project identity changed');
    const selected = matches[0], active = currentProject(state);
    if (active === null || active.id !== created.id || normalize(active.path) !== normalize(created.path)) throw Error('Created project is no longer the open frontend project');
    if (stores.some(s => s.id !== created.id && s.name.toLowerCase() === created.requestedName.text.toLowerCase())) throw Error('Requested project name now exists');
    created.renameAttempted = true;
    note('native-project-rename-enter', {id: created.id, path: created.path, oldName: selected.name, requestedName: created.requestedName.text});
    const accepted = !!nf(ve.base.add(0x1305b20), 'bool', ['pointer', 'pointer'])(selected.store, created.requestedName.value);
    if (!accepted) throw Error('Native project rename was rejected; the automatically named project still exists');
    const saved = !!nf(ve.base.add(0x13071d0), 'bool', ['pointer'])(selected.store);
    const actual = describeStore(selected.store);
    if (!saved || actual.name !== created.requestedName.text || actual.id !== created.id) throw Error('Native project naming/save was not verified; inspect before retrying');
    const result = {backend: 'capcut-native-project-store', pid: Process.id, threadId: Process.getCurrentThreadId(), ...actual,
      stage: 'native-project-named', namingPending: false, nameMatched: true,
      originalGeneratedName: created.name, originalGeneratedPath: created.path, nativeRenameAccepted: accepted,
      syncMetadataSaveReturned: saved, persistenceVerified: false, editorInitializationVerified: false, opened: true};
    note('native-project-rename-return', result); return result;
  }));
}
function dismissStartupPromotionOnUi() {
  // This is the observed homepage advertisement, identified by its shipped
  // QML URL and class. Unknown dialogs retain their normal close blockers.
  const gui = Process.getModuleByName('Qt6Gui.dll'), qml = Process.getModuleByName('Qt6Qml.dll');
  for (const mod of [gui, qml]) if (normalize(mod.path) !== normalize(DIRECTORY+'/'+mod.name)) throw Error('Qt module path mismatch');
  function exported(mod, name, rva, ret, args) {
    const p=mod.getExportByName(name); if (!p.equals(mod.base.add(rva))) throw Error('Qt dialog ABI mismatch: '+name);
    return nf(p,ret,args);
  }
  const top=exported(gui,'?topLevelWindows@QGuiApplication@@SA?AV?$QList@PEAVQWindow@@@@XZ',0xb3e10,'pointer',['pointer']);
  const visible=exported(gui,'?isVisible@QWindow@@QEBA_NXZ',0xe54e0,'bool',['pointer']);
  const modal=exported(gui,'?isModal@QWindow@@QEBA_NXZ',0xe54c0,'bool',['pointer']);
  const transient=exported(gui,'?transientParent@QWindow@@QEBAPEAV1@XZ',0xe8ed0,'pointer',['pointer']);
  const closeWindow=exported(gui,'?close@QWindow@@QEAA_NXZ',0xe2f20,'bool',['pointer']);
  const name=exported(qt,'?objectName@QObject@@QEBA?AVQString@@XZ',0xdf680,'pointer',['pointer','pointer']);
  const className=exported(qt,'?className@QMetaObject@@QEBAPEBDXZ',0xa5360,'pointer',['pointer']);
  const stringDtor=exported(qt,'??1QString@@QEAA@XZ',0x4000,'void',['pointer']);
  const property=exported(qt,'?property@QObject@@QEBA?AVQVariant@@PEBD@Z',0xdf960,'pointer',['pointer','pointer','pointer']);
  const toBool=exported(qt,'?toBool@QVariant@@QEBA_NXZ',0xf3440,'bool',['pointer']);
  const variantDtor=exported(qt,'??1QVariant@@QEAA@XZ',0xf0af0,'void',['pointer']);
  const contextFor=exported(qml,'?contextForObject@QQmlEngine@@SAPEAVQQmlContext@@PEBVQObject@@@Z',0x1afa80,'pointer',['pointer']);
  const baseUrl=exported(qml,'?baseUrl@QQmlContext@@QEBA?AVQUrl@@XZ',0x1a2eb0,'pointer',['pointer','pointer']);
  const urlString=exported(qt,'?toString@QUrl@@QEBA?AVQString@@V?$QUrlTwoFlags@W4UrlFormattingOption@QUrl@@W4ComponentFormattingOption@2@@@@Z',0x62950,'pointer',['pointer','pointer','int']);
  const urlDtor=exported(qt,'??1QUrl@@QEAA@XZ',0x59ea0,'void',['pointer']);
  const deallocate=exported(qt,'?deallocate@QArrayData@@SAXPEAU1@_J1@Z',0x188680,'void',['pointer','int64','int64']);
  function stringResult(getter,obj) {
    const out=Memory.alloc(24);try {getter(obj,out);const n=out.add(16).readS64().toNumber();
      if(n<0||n>2048)throw Error('Dialog QString bounds');return n?out.add(8).readPointer().readUtf16String(n):'';
    } finally {stringDtor(out);}
  }
  function boolProperty(obj,key) {
    const out=Memory.alloc(32);try {property(obj,out,Memory.allocUtf8String(key));return !!toBool(out);}finally {variantDtor(out);}
  }
  function windows(fn) {
    const list=Memory.alloc(24);try {top(list);const count=list.add(16).readS64().toNumber(),data=list.add(8).readPointer();
      if(count<0||count>128)throw Error('Dialog window-list bounds');
      const items=[];for(let i=0;i<count;i++){const p=data.add(i*8).readPointer();if(p.isNull())throw Error('Invalid top-level window');items.push(p);}
      return fn(items);
    } finally {const owner=list.readPointer();if(!owner.isNull()){
      // Qt topLevelWindows creates a fresh QList of borrowed pointers.
      if(owner.readS32()!==1)throw Error('Unexpected shared diagnostic window list');deallocate(owner,8,8);
    }}
  }
  const candidate=windows(items=>{
    const blockers=items.filter(w=>visible(w)&&modal(w));
    if(blockers.length===0)return null;
    if(blockers.length!==1)throw Error('Multiple modal windows; startup promotion dismissal refused');
    const w=blockers[0],parent=transient(w);
    if(parent.isNull()||!items.some(p=>p.equals(parent))||stringResult(name,parent)!=='HomeWindow'||modal(parent))throw Error('Unknown modal parent; dismissal refused');
    const meta=nf(w.readPointer().readPointer(),'pointer',['pointer'])(w),cls=className(meta).readUtf8String();
    if(!/^SplashDialogV2_QMLTYPE_\d+(?:_QML_\d+)?$/.test(cls))throw Error('Unknown modal class; dismissal refused');
    const context=contextFor(w);if(context.isNull())throw Error('Promotion QML context unavailable');
    const url=Memory.alloc(8);let path;
    try {baseUrl(context,url);path=stringResult((a,b)=>urlString(a,b,0),url);}finally {urlDtor(url);}
    if(path!=='qrc:/VipBiz/vip_ad_view/qml/SplashDialogV2.qml')throw Error('Unknown modal QML URL; dismissal refused');
    if(boolProperty(w,'isLoading')||!boolProperty(w,'showCloseBtn')||!boolProperty(w,'deleteOnClose'))throw Error('Startup promotion is busy or not dismissible');
    return {window:w,identity:{className:cls,qmlBaseUrl:path,transientParentObjectName:'HomeWindow',pointer:w.toString()}};
  });
  if(candidate===null)return {dismissed:false,reason:'no-visible-modal',pid:Process.id};
  if(promotionDismissAttempted)throw Error('One startup promotion dismissal attempt per agent');
  promotionDismissAttempted=true;
  note('native-startup-promotion-close-enter',{window:candidate.identity});
  const accepted=!!closeWindow(candidate.window);
  // close may destroy the QML window. Re-enumerate before any further access
  // to that address, and preserve native close-event refusal if it stayed.
  const stillVisible=windows(items=>{const found=items.find(w=>w.equals(candidate.window));return found?!!visible(found):false;});
  const result={pid:Process.id,threadId:Process.getCurrentThreadId(),dismissed:accepted&&!stillVisible,nativeCloseAccepted:accepted,stillVisible,window:candidate.identity};
  note('native-startup-promotion-close-return',result);return result;
}
rpc.exports = {
  metadata() {return {hashes: HASHES, directory: DIRECTORY, experimental: true, automaticManagerDiscovery: true, automaticUiThread: true, importRequiresClosedProject: true, createRequiresHomepage: true, createUsesNativeInitialization: true, openRequiresHomepage: true, closeUsesNativeSave: true};},
  inspect(req) {return onApplicationThread(req, inspectOnUi);},
  dismissstartuppromotion(req) {return onApplicationThread(req, dismissStartupPromotionOnUi);},
  importvideo(req) {
    if (attempted) throw Error('One mutation attempt per loaded agent');
    if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(req.projectId || '') || typeof req.projectPath !== 'string') throw Error('Project UUID and path required');
    if (!Number.isSafeInteger(req.durationUs) || req.durationUs <= 0 || !Number.isInteger(req.width) || req.width < 1 || req.width > 32768 || !Number.isInteger(req.height) || req.height < 1 || req.height > 32768) throw Error('Validated video duration and size required');
    input(req.mediaPathBytes); input(req.fileNameBytes); guard(req); attempted = true;
    return onApplicationThread(req, state => importOnUi(req, state));
  },
  create(req) {
    if (attempted) throw Error('One mutation attempt per loaded agent');
    const nativeName = input(req.projectNameBytes), name = nativeName.text;
    if (!name.trim() || /[<>:"/\\|?*\x00-\x1f]/.test(name) || /[. ]$/.test(name) || name.length > 100 || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) throw Error('Invalid Windows project name');
    const initial = guard(req), controller = homeController(); attempted = true;
    const creation = {name: nativeName, manager: initial.manager, controller};
    return onApplicationThread(req, state => createOnUi(req, state, creation));
  },
  finishcreate(req) {return onApplicationThread(req, state => finishCreateOnUi(req, state));},
  open(req) {
    if (attempted) throw Error('One mutation attempt per loaded agent');
    validateProjectTarget(req); guard(req); attempted = true;
    return onApplicationThread(req, state => openOnUi(req, state));
  },
  close(req) {
    if (attempted) throw Error('One mutation attempt per loaded agent');
    validateProjectTarget(req); guard(req); attempted = true;
    return onApplicationThread(req, state => closeOnUi(req, state));
  },
  cancel() {if (pending !== null) pending.cancel(); return {attempted, pending: pending !== null};},
};
