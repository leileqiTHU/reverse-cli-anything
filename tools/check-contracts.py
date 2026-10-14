"""Generic schema, manifest and evidence-coverage validation. No fixed target list."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli import config,registry
from reverse_cli.catalog import generated
from jsonschema import Draft202012Validator

def main():
    p=argparse.ArgumentParser();p.add_argument('--examples',action='store_true');p.add_argument('--adapter');a=p.parse_args()
    for path in (config.ROOT/'schemas').glob('*.schema.json'):Draft202012Validator.check_schema(registry.read(path))
    report={'ok':False,'adapters':0,'tools':0,'coverage':{'current-native':0,'historical-workflow':0,'not-run':0},'failures':[]}
    entries=[registry.find(a.adapter)] if a.adapter else registry.entries(examples=a.examples)
    for entry in entries:
        try:
            app=entry['id'];catalog=registry.read(registry.reference(entry,'toolSchema'))
            Draft202012Validator(registry.read(config.ROOT/'schemas/adapter.schema.json')).validate({'schemaVersion':1,**registry.public(entry)})
            assert catalog==generated(app),'Generated catalog is stale'
            names=[t['name'] for t in catalog['tools']]
            assert catalog['adapter']==app and len(names)==len(set(names)),'Duplicate or mismatched tool identity'
            for tool in catalog['tools']:
                Draft202012Validator.check_schema(tool['inputSchema'])
                output=tool['outputSchema']
                if '$ref' in output:output=registry.read(registry.reference(entry,'toolSchema').parent/output['$ref'])
                Draft202012Validator.check_schema(output)
                assert tool.get('adapter',app)==app and type(tool['mutates']) is bool
            for field in ('skill','readme'):
                if entry.get(field):assert registry.reference(entry,field).is_file(),'Missing '+field
            if entry.get('acceptance'):
                acceptance=registry.read(registry.reference(entry,'acceptance'))
                Draft202012Validator(registry.read(config.ROOT/'schemas/acceptance.schema.json')).validate(acceptance)
                coverage=[t['name'] for t in acceptance['tools']]
                assert acceptance['adapter']==app and len(coverage)==len(set(coverage)) and set(names)==set(coverage),'Missing or duplicate coverage'
                for tool in acceptance['tools']:
                    report['coverage'][tool['coverage']]+=1
                    if tool['coverage']!='not-run':assert acceptance['build'] in entry.get('testedBuilds',[]),'Unverified build'
                    for ref in tool['evidence']:
                        evidence=(Path(entry['_root'])/ref).resolve();doc=registry.read(evidence)
                        assert doc.get('passed') is True,'Evidence does not pass'
                        if tool['coverage']=='current-native':
                            observation=doc.get('adapters',{}).get(app,doc if doc.get('adapter')==app else {})
                            assert tool['name'] in observation.get('executedTools',[]),'Evidence did not execute this tool'
            report['adapters']+=1;report['tools']+=len(names)
        except Exception as error:report['failures'].append(entry['id']+': '+str(error))
    report['ok']=not report['failures'];print(json.dumps(report));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
