"""Generic configuration. Adapter-specific defaults belong to optional adapters."""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
def settings():
    path=Path(os.environ.get('REVERSE_CLI_CONFIG',ROOT/'reverse-cli.local.json'))
    result=json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
    if not isinstance(result,dict):raise ValueError('Configuration must be a JSON object: '+str(path))
    return result
def value(key,env,default=None):return os.environ.get(env) or settings().get(key) or default
def directory(kind):
    defaults={'cache':Path('D:/Caches/reverse-cli-anything') if Path('D:/').exists() else ROOT/'.runtime/cache','state':ROOT/'.reverse-cli','output':ROOT/'outputs/reverse-cli-anything'}
    return Path(value(kind+'Dir','REVERSE_CLI_'+kind.upper()+'_DIR',defaults[kind])).expanduser().resolve()
def python():return str(value('python','REVERSE_CLI_PYTHON',sys.executable))
def app_setting(app,key,default=None):return settings().get('adapters',{}).get(app,{}).get(key,default)
def app_path(app):
    from . import registry
    entry=registry.find(app)
    explicit=app_setting(app,'appPath')
    return Path(explicit).expanduser().resolve() if explicit else registry.invoke(entry,'app_path')
def native_tools(app):
    from . import registry
    entry=registry.find(app)
    candidates=[value('nativeTools','REVERSE_CLI_NATIVE_TOOLS'),app_setting(app,'nativeTools'),registry.reference(entry,'entrypoint').parent/'.native-tools']
    candidates+=registry.invoke(entry,'native_tools',default=[])
    return list(dict.fromkeys(str(Path(p).resolve()) for p in candidates if p and Path(p).is_dir()))
def ffmpeg(app=None):
    explicit=value('ffmpeg','REVERSE_CLI_FFMPEG')
    if explicit:return Path(explicit).expanduser().resolve()
    found=shutil.which('ffmpeg')
    if found:return Path(found)
    if app:
        from . import registry
        return registry.invoke(registry.find(app),'ffmpeg')
    return None
def child_env(app):
    from . import registry
    entry=registry.find(app);env=os.environ.copy()
    temp=directory('cache')/app/'temp';temp.mkdir(parents=True,exist_ok=True)
    env.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    paths=native_tools(app)
    env['PYTHONPATH']=os.pathsep.join(paths+([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    env.update(registry.invoke(entry,'child_env',default={}))
    media=ffmpeg(app)
    if media:env['REVERSE_CLI_FFMPEG']=str(media)
    return env
