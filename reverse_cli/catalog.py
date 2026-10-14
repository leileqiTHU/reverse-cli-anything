"""Application-independent catalog, with optional adapter-owned argument translation."""
import argparse
import json
from . import registry
from .schema import validate

def load(app):
    entry=registry.find(app)
    return registry.read(registry.reference(entry,'toolSchema'))

def tool(app,name):
    result=next((t for t in load(app)['tools'] if t['name']==name),None)
    if result is None:raise ValueError('Unknown tool: '+name)
    return result

def mutates(app,name):return tool(app,name).get('mutates',True)

def preflight(app,argv):
    entry=registry.find(app);custom=registry.invoke(entry,'preflight',argv)
    if custom is not None:return custom
    parser=argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument('tool');parser.add_argument('--input',default='{}')
    args=parser.parse_args(argv);payload=json.loads(args.input)
    validate(payload,tool(app,args.tool)['inputSchema'])
    return args.tool,payload

def command(app,name,arguments):
    entry=registry.find(app);validate(arguments,tool(app,name)['inputSchema'])
    custom=registry.invoke(entry,'command',name,arguments)
    return custom if custom is not None else [name,'--input',json.dumps(arguments,ensure_ascii=False)]

def generated(app):
    entry=registry.find(app)
    return registry.invoke(entry,'tools',default=load(app))
