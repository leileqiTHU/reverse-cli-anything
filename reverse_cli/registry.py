"""Manifest-based adapters. Listing the core never imports example application code."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from . import config
from .journal import write

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def adapter_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',value):
        raise ValueError('Adapter ID must be lowercase letters, digits or hyphens, starting with a letter')
    if value.upper() in {'CON','PRN','AUX','NUL',*[f'{a}{i}' for a in ('COM','LPT') for i in range(1,10)]}:
        raise ValueError('Reserved adapter ID')
    return value

def reference(entry,key):
    base=Path(entry['_root']);path=(base/entry[key]).resolve()
    if not path.is_relative_to(base):raise ValueError('Adapter reference leaves its declared root: '+key)
    return path

def normalize(entry,base,source):
    from .schema import validate
    result={'schemaVersion':1,**entry}
    validate(result,read(config.ROOT/'schemas/adapter.schema.json'))
    adapter_id(result['id'])
    result['_root']=str(Path(base).resolve());result['_source']=source
    for field in ('entrypoint','toolSchema'):
        if field not in result or not reference(result,field).is_file():raise ValueError('Missing adapter '+field)
    if result.get('runtime') and not reference(result,'runtime').is_file():raise ValueError('Missing adapter runtime')
    return result

def manifest(path):
    path=Path(path).resolve();value=read(path)
    return normalize(value,(path.parent/value.get('root','.')).resolve(),str(path))

def registry_path():return Path(config.value('registry','REVERSE_CLI_REGISTRY',config.ROOT/'registry.json')).resolve()

def from_registry(path,source):
    if not path.is_file():return []
    data=read(path);base=(path.parent/data.get('root','.')).resolve()
    return [manifest((base/e['manifest']).resolve()) if 'manifest' in e else normalize(e,base,source) for e in data.get('adapters',[])]

def entries(examples=False):
    path=registry_path();base=from_registry(path,'registry')
    local=config.directory('state')/'adapters.json'
    extra=from_registry(local,'registered') if local.is_file() else []
    selected={}
    for entry in [*base,*extra]:
        if entry['id'] in selected:raise ValueError('Duplicate registered adapter ID: '+entry['id'])
        selected[entry['id']]=entry
    if examples and path.is_file():
        index=read(path).get('examples')
        if index:
            for entry in from_registry((path.parent/index).resolve(),'example'):
                selected.setdefault(entry['id'],entry)
    return list(selected.values())

def find(name):
    adapter_id(name)
    for entry in entries():
        if entry['id']==name:return entry
    # Explicit selection retains compatibility with optional examples. They are
    # never required for installation, core diagnostics or the default catalog.
    for entry in entries(examples=True):
        if entry['id']==name:return entry
    raise ValueError('Unknown adapter: '+name+'; use register <adapter.json>')

def register(path):
    path=Path(path).resolve();entry=manifest(path)
    local=config.directory('state')/'adapters.json';data=read(local) if local.is_file() else {'schemaVersion':1,'adapters':[]}
    for existing in entries():
        if existing['id']==entry['id']:
            if existing['_source']==str(path):return entry
            raise ValueError('Adapter ID already registered; choose a distinct ID')
    data['adapters'].append({'manifest':str(path)});write(local,data);return entry

_modules={}
def hooks(entry):
    if not entry.get('runtime'):return None
    path=reference(entry,'runtime');signature=hashlib.sha256(path.read_bytes()).hexdigest();key=(str(path),signature)
    if key not in _modules:
        spec=importlib.util.spec_from_file_location('reverse_cli_adapter_'+entry['id']+'_'+signature[:8],path)
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);_modules[key]=result
    return _modules[key]

def invoke(entry,name,*args,default=None):
    module=hooks(entry);method=getattr(module,name,None) if module else None
    return method(*args) if method else default

def public(entry):return {key:value for key,value in entry.items() if not key.startswith('_')}
