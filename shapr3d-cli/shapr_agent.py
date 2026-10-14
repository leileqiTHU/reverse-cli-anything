"""Experimental, version-pinned Shapr3D native WinRT bridge."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
BUILD = '26.180.11926.0'
HASHES = {
    'Shapr3D.exe': '6cbf9f5c398085157d51fb0927a2850c1f3d217fd9538cc5225ad7fa0288d98e',
    'Shapr3D.dll': 'a8a348183a7c50ed97af4b8776349628a60d8694eb832593c4baecf05f79481e',
    'Shapr.Native.dll': '9a47cdba304b905653d4cbce4a6bef2cd0270fe588764f4f443abd2ef25bbc53',
}

def image_path(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        buffer=ctypes.create_unicode_buffer(32768)
        count=wintypes.DWORD(len(buffer))
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return Path(buffer.value)
    finally:
        kernel.CloseHandle(handle)

def validate_target(pid):
    image=image_path(pid)
    if image.name.lower() != 'shapr3d.exe':
        raise ValueError('PID is not Shapr3D.exe')
    hashes={}
    for name,expected in HASHES.items():
        with (image.parent/name).open('rb') as f:
            actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual != expected:
            raise ValueError(f'Unsupported build: {name} hash mismatch')
        hashes[name]=actual
    return {'pid':pid,'build':BUILD,'image':str(image),'sha256':hashes}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['inspect','history','command','command-check'])
    parser.add_argument('--pid',required=True,type=int)
    parser.add_argument('--name',choices=['NewProject','CloseProject','Undo','Redo'])
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    request={'operation':args.operation,'name':args.name}
    opid=str(uuid.uuid4())
    runtime=ROOT/'.runtime'
    runtime.mkdir(exist_ok=True)
    receipt=runtime/(opid+'.json')
    result={'operationId':opid,'request':request,'status':'not-executed'}
    dest=None
    try:
        if args.operation in ('command','command-check') and args.name is None:
            raise ValueError('--name is required for command')
        if args.out:
            candidate=args.out.resolve()
            if candidate.drive.upper() != 'D:':
                raise ValueError('Evidence output must be on D:')
            if candidate.exists():
                raise ValueError('Evidence output already exists; choose a new path')
            candidate.parent.mkdir(parents=True,exist_ok=True)
            # Check the destination before submitting any native operation.
            with candidate.open('x',encoding='utf-8') as output:
                output.write(json.dumps(result,indent=2))
            dest=candidate
        target=validate_target(args.pid)
        candidates=[os.environ.get('REVERSE_CLI_NATIVE_TOOLS'),str(ROOT/'.native-tools'),str(ROOT.parent/'capcut-cli'/'.native-tools')]
        for path in reversed(candidates):
            if path and Path(path).is_dir():
                sys.path.insert(0,path)
        import frida
        result['target']=target
        result['status']='running'
        receipt.write_text(json.dumps(result,indent=2),encoding='utf-8')
        session=frida.attach(args.pid)
        messages=[]
        script=None
        try:
            script=session.create_script((ROOT/'native_bridge.js').read_text(encoding='utf-8'))
            script.on('message',lambda m,d: messages.append(m))
            script.load()
            result['result']=script.exports_sync.run(request)
            result['status']='completed'
            result['messages']=messages
        finally:
            if script is not None:
                cleanup=script.exports_sync.close()
                if not cleanup['safeToDetach']:
                    # Unloading a JS callback still owned by native COM would
                    # leave a dangling function pointer inside the application.
                    result['bridgeCleanup']=cleanup
                    receipt.write_text(json.dumps(result,indent=2),encoding='utf-8')
                    print(json.dumps({'bridgeRetained':True,'receipt':str(receipt),'cleanup':cleanup}),file=sys.stderr,flush=True)
                    while not cleanup['safeToDetach']:
                        time.sleep(2)
                        cleanup=script.exports_sync.close()
                script.unload()
            session.detach()
        code=0
    except Exception as exc:
        result['status']='unknown' if result['status']=='running' else 'not-executed'
        result['error']={'type':type(exc).__name__,'message':str(exc)}
        code=2
    result['receipt']=str(receipt)
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if dest:
        dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    return code

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
