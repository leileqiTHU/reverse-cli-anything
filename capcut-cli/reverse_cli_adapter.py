"""Optional showcase integration. Native behavior stays in the original adapter."""
from examples import legacy_catalog, legacy_paths, build_catalog, doctor
from reverse_cli.config import ROOT
APP='capcut'
def preflight(argv):return legacy_catalog.preflight(APP,argv)
def command(tool,arguments):return legacy_catalog.command(APP,tool,arguments)
def tools():return build_catalog.tools_for(APP)
def app_path():return legacy_paths.app_path(APP)
def native_tools():return legacy_paths.native_tools(APP)
def ffmpeg():return legacy_paths.ffmpeg()
def doctor_checks(pid,inventory):return doctor.inspect(APP,pid,inventory)['checks']
def child_env():
    return {'CAPCUT_DIR':str(app_path())} if APP=='capcut' else {'AXURE_APP':str(app_path())} if APP=='axure' else {}
def prepare(argv,identity):
    tool,_=preflight(argv)
    if APP=='capcut' and tool in ('editor.add-audio','editor.captions-import','editor.set-clip') and '--request-id' not in argv:return [*argv,'--request-id',identity]
    return argv
def successful(tool,response,code):return code==0 and (response.get('ok') is True or APP=='shapr3d' and tool=='start' and response.get('ready') is True)
def evidence(response):
    if APP=='axure' and response.get('requestId'):
        return [{'kind':'requestId','path':str(ROOT/'axure-cli/.runtime/requests'/(response['requestId']+'.json'))}]
    return []
