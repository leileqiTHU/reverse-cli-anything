"""Discover actual argument parsers without launching or attaching to applications."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from reverse_cli.config import ROOT

ENTRYPOINTS = {'capcut':'capcut-cli/capcut_agent.py', 'axure':'axure-cli/axure_cli.py', 'shapr3d':'shapr3d-cli/pilot.py'}

def module(app):
    path = ROOT/ENTRYPOINTS[app]
    if str(path.parent) not in sys.path:
        sys.path.insert(0,str(path.parent))
    spec = importlib.util.spec_from_file_location('reverse_adapter_'+app,path)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def preflight(app, argv):
    m = module(app)
    if app == 'capcut':
        args = vars(m.parse_args(argv))
        words = [args['operation']]+([args.get('editor_action') or args.get('project_action') or args.get('media_action')] if args['operation'] in ('editor','project','media') else [])
    elif app == 'axure':
        args = vars(m.parser().parse_args(argv));words=[args['command']]+([args['action']] if 'action' in args else [])
    else:
        parser=argparse.ArgumentParser(exit_on_error=False)
        parser.add_argument('mode',choices=['start','call'])
        parser.add_argument('--pid',type=int);parser.add_argument('--session');parser.add_argument('--json')
        args=vars(parser.parse_args(argv));words=[args['mode']]
        if args['mode']=='call':
            if not args['session'] or not args['json']:raise ValueError('call requires --session and --json')
            payload=m.validate_request(json.loads(args['json']));words=[payload['operation']]
        elif not args['pid'] or args['pid']<=0:raise ValueError('start requires a positive --pid')
    return '.'.join(words),args

READS = {'capcut':{'capabilities','help','version','probe','project.list','editor.sessions','editor.inspect'},
         'axure':{'capabilities','status','inspect','page.list','widget.list','interaction.get','project.sitemap'},
         'shapr3d':{'inspect','history','visible-status','model-annotations'}}

def mutates(app, tool):
    return tool not in READS[app]

def load(app):
    return json.loads((ROOT/'schemas/tools'/(app+'.json')).read_text(encoding='utf-8'))

def command(app, tool, arguments):
    entry = next((t for t in load(app)['tools'] if t['name']==tool),None)
    if entry is None:raise ValueError('Unknown tool: '+tool)
    from reverse_cli.schema import validate
    schema=entry['inputSchema'];validate(arguments,schema)
    if app=='shapr3d':
        if tool=='start':return ['start','--pid',str(arguments['pid'])]
        payload={k:v for k,v in arguments.items() if k!='session'}
        return ['call','--session',arguments['session'],'--json',json.dumps(dict(payload,operation=tool),ensure_ascii=False)]
    before=[];after=[]
    for key,v in arguments.items():
        prop=schema['properties'][key];target=before if prop.get('x-global') else after
        flag=prop['x-cli-flag']
        if prop['type']=='boolean':
            if v:target.append(flag)
        else:
            target.append(flag);target.extend(map(str,v if isinstance(v,list) else [v]))
    return before+entry['command']+after
