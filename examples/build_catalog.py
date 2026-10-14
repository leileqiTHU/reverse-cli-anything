"""Generate tool argument schemas from maintained parsers and explicit native requests."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from examples.legacy_catalog import module, mutates
from reverse_cli.config import ROOT

EVIDENCE={'capcut':'capcut-cli/evidence/real-media-20261013.json','axure':'axure-cli/evidence/native-login-acceptance.json','shapr3d':'shapr3d-cli/evidence/native-model-proof-20261013.json'}

def leaves(parser,command=(),inherited=()):
    local=[a for a in parser._actions if a.option_strings and a.dest!='help']
    children=[a for a in parser._actions if isinstance(a,argparse._SubParsersAction)]
    if children:
        for name,child in children[0].choices.items():yield from leaves(child,command+(name,),inherited+tuple((a,not command) for a in local))
    else:yield command,inherited+tuple((a,False) for a in local),parser

def prop(a,global_flag):
    typ='integer' if a.type is int else 'number' if a.type is float else 'boolean' if isinstance(a,(argparse._StoreTrueAction,argparse._StoreFalseAction)) else 'string'
    result={'type':typ,'x-cli-flag':a.option_strings[0],'x-global':global_flag}
    if a.choices is not None:result['enum']=list(a.choices)
    if a.nargs in ('+','*'):
        result={'type':'array','items':{'type':typ},'minItems':1 if a.nargs=='+' else 0,'x-cli-flag':a.option_strings[0],'x-global':global_flag}
    if a.dest.endswith('_us'):result['description']='Integer microseconds. Command-specific absolute/relative semantics remain in the adapter guide.'
    return result

def tools_for(app):
    m=module(app);tools=[]
    if app in ('capcut','axure'):
        parser=m.build_parser() if app=='capcut' else m.parser()
        for words,actions,leaf in leaves(parser):
            props={a.dest:prop(a,g) for a,g in actions};required=[a.dest for a,g in actions if a.required]
            schema={'type':'object','properties':props,'required':required,'additionalProperties':False}
            groups=[]
            for group in leaf._mutually_exclusive_groups:
                names=[a.dest for a in group._group_actions]
                clause={'oneOf':[{'required':[n],'not':{'anyOf':[{'required':[other]} for other in names if other!=n]}} for n in names]}
                if not group.required:clause['oneOf'].append({'not':{'anyOf':[{'required':[n]} for n in names]}})
                groups.append(clause)
            if groups:schema['allOf']=groups
            tools.append({'name':'.'.join(words),'command':list(words),'inputSchema':schema})
    else:
        s=lambda desc='':dict(type='string',**({'description':desc} if desc else {}))
        n={'type':'number'};b={'type':'boolean'}
        specs={
          'start':({'pid':{'type':'integer','minimum':1}},['pid']),
          'inspect':({},[]),'history':({},[]),'create-project':({},[]),'visible-status':({},[]),
          'import-native':({'path':s('Existing .shapr or .dxf file')},['path']),
          'history-set':({'step':s(),'parameter':s(),'expression':s('Native expression with explicit units')},['step','parameter','expression']),
          'export-stl':({'directory':s(),'name':s('Basename without extension')},['directory','name']),
          'export-shapr':({'directory':s(),'name':s('Basename without extension')},['directory','name']),
          'project-close':({},[]),'project-reopen':({},[]),'session-close':({},[]),
          'model-select-sketch':({},[]),
          'model-annotations':({},[]),
          'model-tool-start':({'tool':{'type':'string','enum':['extrude','move-rotate']}},['tool']),
          'model-tool-finish':({},[]),
          'model-pick':({'xMm':n,'yMm':n,'nearMm':{'type':'array','items':n,'minItems':3,'maxItems':3},'farMm':{'type':'array','items':n,'minItems':3,'maxItems':3},'select':b,'additive':b,'expectedRawID':s('Exact decimal uint64 native ID from a recent pick')},[]),
          'model-set-distance':({'expression':s('Explicit mm expression within +/-100 mm')},['expression']),
          'model-screenshot':({'path':s('Empty PNG reserved in app-accessible LocalState')},['path']),
          'model-command':({'name':{'type':'string','enum':['exit-sketch','deselect','default-view','zoom-fit','undo']},'check':b},['name']),
          'model-clear-demo':({'backup':s(),'confirm':{'type':'string','enum':['replace-backed-up-demo-plate']},'expectedHistory':{'type':'array','items':{'type':'object'}}},['backup','confirm','expectedHistory'])}
        assert set(specs)==m.OPERATIONS|{'start'}
        for name,(props,required) in specs.items():
            if name!='start':props={'session':s('Current public pilot session directory'),**props};required=['session',*required]
            tools.append({'name':name,'command':['start'] if name=='start' else ['call'],'inputSchema':{'type':'object','properties':props,'required':required,'additionalProperties':False}})
    for tool in tools:
        tool.update(adapter=app,mutates=mutates(app,tool['name']),
                    outputSchema={'$ref':'../legacy-response.schema.json'},
                    execution='version-pinned desktop adapter; native validation also applies',
                    evidenceIndex='../../acceptance/'+app+'.json',
                    provenance='recovered-internal')
        if app=='capcut' and tool['name'].startswith('media.'):tool['provenance']='external-helper'
        if app=='axure' and tool['name'] in ('project.sitemap','page.list'):tool['provenance']='built-in-document-service'
        if tool['name'] in ('help','capabilities','start','session-close'):tool['provenance']='adapter-infrastructure'
    return {'schemaVersion':1,'adapter':app,'tools':tools,'scope':'Argument schemas plus adapter runtime validation; descriptions do not expand native support.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    for app in EVIDENCE:
        target=ROOT/'schemas/tools'/(app+'.json');data=tools_for(app)
        if args.check:
            assert json.loads(target.read_text(encoding='utf-8'))==data,'Stale catalog: '+app
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'adapter':app,'tools':len(data['tools']),'checked':args.check}))
if __name__=='__main__':main()
