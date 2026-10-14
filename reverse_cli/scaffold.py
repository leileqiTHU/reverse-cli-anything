"""Create a target-neutral adapter shell; never claim to have recovered native calls."""
import json
from pathlib import Path
from .registry import adapter_id
from .journal import write

def create(name,output):
    adapter_id(name);root=Path(output).resolve()
    root.mkdir(parents=True,exist_ok=False)
    write(root/'adapter.json',{'schemaVersion':1,'id':name,'name':name,'status':'scaffold','entrypoint':'cli.py','toolSchema':'tools.json','skill':'SKILL.md','acceptance':'acceptance.json','readme':'README.md','testedBuilds':[]})
    write(root/'tools.json',{'schemaVersion':1,'adapter':name,'tools':[{'name':'status','adapter':name,'mutates':False,'provenance':'adapter-infrastructure','inputSchema':{'type':'object','properties':{},'additionalProperties':False},'outputSchema':{'$ref':'response.schema.json'}}]})
    write(root/'response.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','required':['ok'],'properties':{'ok':{'type':'boolean'}}})
    write(root/'acceptance.json',{'schemaVersion':1,'adapter':name,'build':'uninvestigated','checklist':[{'id':'native-state','assertion':'Define and independently verify a useful native operation.'}],'tools':[{'name':'status','coverage':'not-run','evidence':[],'scope':'Scaffold infrastructure only; no native capability has been recovered.'}]})
    write(root/'acceptance-plan.json',{'schemaVersion':1,'adapter':name,'target':{'name':name,'build':'uninvestigated'},'workflow':'Define the user task before investigating','checks':[{'layer':layer,'name':layer,'status':'not-run','evidence':[]} for layer in ('request','state','persistence','artifact','recovery')]})
    (root/'cli.py').write_text('''"""Infrastructure-only scaffold. Replace with recovered, verified native operations."""
import argparse,json
p=argparse.ArgumentParser();p.add_argument('tool');p.add_argument('--input',default='{}');a=p.parse_args()
arguments=json.loads(a.input)
if a.tool=='status' and arguments=={}:
    print(json.dumps({'ok':True,'result':{'stage':'scaffold','nativeImplemented':False}}))
else:
    print(json.dumps({'ok':False,'outcome':'not-submitted','error':'Native operation not implemented'}));raise SystemExit(2)
''',encoding='utf-8')
    (root/'README.md').write_text('# '+name+' adapter\n\nThis scaffold has no native editing capability. Define the target build, user task, evidence, commands and limitations before implementing operations.\n',encoding='utf-8')
    (root/'SKILL.md').write_text('---\nname: '+name+'\ndescription: Inspect the development status of the '+name+' adapter; native capabilities are not implemented yet.\n---\n\nRead README.md, tools.json and acceptance.json in this adapter directory. The status command reports infrastructure readiness only. Add native operations and update this Skill after task-specific investigation and acceptance.\n',encoding='utf-8')
    return {'ok':True,'directory':str(root),'manifest':str(root/'adapter.json'),'stage':'scaffold','nativeImplemented':False,'registered':False}
