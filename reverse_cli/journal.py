"""Durable operation receipts. Unknown mutations are never automatically replayed."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

STATES = ('not-submitted', 'running', 'completed', 'partially-applied', 'unknown')

def now():
    return datetime.now(timezone.utc).isoformat()

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def operation_id(value=None):
    value = value or uuid.uuid4().hex
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', value):
        raise ValueError('operation-id must contain 1..96 ASCII letters, digits, dots or hyphens')
    if value.endswith('.') or value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'{a}{i}' for a in ('COM','LPT') for i in range(1,10)]}:
        raise ValueError('Invalid Windows operation-id')
    return value

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

class Journal:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, identity):
        return self.root/'operations'/(operation_id(identity)+'.json')

    def get(self, identity):
        record=json.loads(self.path(identity).read_text(encoding='utf-8'))
        # A dead controller cannot still report a trustworthy in-flight status.
        if record['state']=='running' and not alive(record['ownerPid']):
            record.update(state='unknown',ok=False,error='Controller exited before recording a terminal outcome',updatedAt=now())
            write(self.path(identity),record)
        return record

    def acquire(self, adapter, identity):
        path = self.root/'locks'/(adapter+'.lock')
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as stream:
                json.dump({'operationId': identity, 'ownerPid': os.getpid(), 'createdAt': now()}, stream)
        except FileExistsError:
            raise ValueError(f'Adapter busy or outcome unresolved; inspect {path}')
        return path

    def reserve(self, record):
        path = self.path(record['operationId']);path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive reservation protects IDs even across different adapter locks.
        with path.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, allow_nan=False)
        return path

def classify(response, exit_code, mutation):
    if response.get('ok') is True and exit_code == 0:
        return 'completed'
    error = response.get('error', {})
    outcome = error.get('outcome') if isinstance(error, dict) else None
    outcome = outcome or response.get('outcome')
    if outcome == 'partially-applied':
        return 'partially-applied'
    if outcome in ('not-applied', 'not-executed', 'not-submitted'):
        return 'not-submitted'
    # A business error after dispatch is not proof that no mutation happened.
    return 'unknown' if mutation else 'completed'

def alive(pid):
    if not pid:return False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
        k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=k.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            code=wintypes.DWORD();return bool(k.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:k.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except OSError:return False

def refresh(journal, identity):
    """Observe a late child response; never rerun a command or infer native rollback."""
    record=journal.get(identity)
    if record['state'] not in ('running','unknown') or alive(record.get('ownerPid')) or alive(record.get('childPid')):
        return record
    if record.get('logs'):
        log=Path(record['logs'])/'stdout.log'
        try:response=json.loads(log.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):return record
        if response.get('ok') is not True:
            # The bridge writes its exact request result before sending the pipe
            # response. A disconnected client may have missed that completion.
            for evidence in record.get('nativeEvidence',[]):
                if evidence['kind'] not in ('journal','requestId'):continue
                file=Path(evidence['path'])
                if file.stem!=response.get('requestId'):continue
                try:native=json.loads(file.read_text(encoding='utf-8-sig'))
                except (OSError,ValueError):continue
                if native.get('ok') is True:
                    response={**native,'requestId':file.stem}
                    record['lateNativeReceipt']=str(file)
                    break
        # We no longer have the child exit code. Trust only an explicit successful
        # adapter envelope, and record this narrower observation separately.
        if response.get('ok') is True or (record.get('tool')=='start' and response.get('ready') is True):
            record.update(response=response,ok=True,state='completed',updatedAt=now(),lateResponseObserved=True)
            record.pop('error',None);write(journal.path(identity),record)
            lock=Path(record['lock']) if record.get('lock') else None
            if lock and lock.exists() and json.loads(lock.read_text())['operationId']==identity:lock.unlink()
    return record

def resolve(journal, identity, evidence):
    """Explicit operator resolution with retained observations; never a force-unlock."""
    record=journal.get(identity)
    if record['state'] not in ('unknown','partially-applied'):raise ValueError('Only unresolved operations can be resolved')
    if alive(record.get('ownerPid')) or alive(record.get('childPid')):raise ValueError('Controller or child is still alive')
    proof=json.loads(Path(evidence).read_text(encoding='utf-8-sig'))
    if proof.get('operationId')!=identity or proof.get('nativeWorkFinished') is not True:raise ValueError('Resolution must identify this operation and verify native work finished')
    if proof.get('state') not in ('completed','not-submitted') or type(proof.get('ok')) is not bool:raise ValueError('Invalid resolution state/result')
    if not proof.get('checks') or not all(c.get('passed') is True and c.get('name') for c in proof['checks']):raise ValueError('Resolution requires passing, named observations')
    if not proof.get('evidenceFiles'):raise ValueError('Resolution requires hashed evidence files')
    for item in proof['evidenceFiles']:
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Resolution evidence hash mismatch')
    record.update(state=proof['state'],ok=proof['ok'],updatedAt=now(),resolution={'source':'explicit-caller-verification','path':str(Path(evidence).resolve()),'evidence':proof})
    write(journal.path(identity),record)
    lock=Path(record['lock']) if record.get('lock') else None
    if lock and lock.exists() and json.loads(lock.read_text())['operationId']==identity:lock.unlink()
    return record
