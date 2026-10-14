"""Check evidence structure and integrity; semantic native verification belongs to the target."""
import hashlib
from pathlib import Path
from .registry import read
from .schema import validate
from .config import ROOT

def inspect(path):
    path=Path(path).resolve();report=read(path)
    validate(report,read(ROOT/'schemas/acceptance-report.schema.json'))
    failures=[];layers={c['layer'] for c in report['checks']}
    required={'request','state','persistence','artifact','recovery'}
    for layer in sorted(required-layers):failures.append('Missing acceptance layer: '+layer)
    for check in report['checks']:
        status=check['status']
        if status in ('failed','not-run'):failures.append(check['name']+': '+status)
        if status=='not-applicable' and not check.get('reason'):failures.append(check['name']+': explain non-applicability')
        if check['layer'] in ('request','state') and status=='not-applicable':failures.append(check['layer']+' cannot be omitted')
        if status=='passed' and not check.get('evidence'):failures.append(check['name']+': passing claims require hashed evidence')
        for item in check.get('evidence',[]):
            file=(path.parent/item['path']).resolve()
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:
                failures.append(check['name']+': missing or changed evidence '+item['path'])
    return {'ok':not failures,'adapter':report['adapter'],'checks':len(report['checks']),'failures':failures,'scope':'Evidence completeness and hash integrity only; this does not independently execute or prove native behavior.'}
