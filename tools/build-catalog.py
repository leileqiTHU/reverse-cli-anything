"""Check or regenerate catalogs for registered adapters; examples are opt-in."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli import registry
from reverse_cli.catalog import generated
from reverse_cli.journal import write

def tools_for(app):return generated(app)
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--examples',action='store_true');p.add_argument('--adapter');a=p.parse_args()
    entries=[registry.find(a.adapter)] if a.adapter else registry.entries(examples=a.examples)
    for entry in entries:
        data=tools_for(entry['id']);target=registry.reference(entry,'toolSchema')
        if a.check:
            if registry.read(target)!=data:raise ValueError('Stale catalog: '+entry['id'])
        else:write(target,data)
        print(json.dumps({'adapter':entry['id'],'tools':len(data['tools']),'checked':a.check}))
    if not entries:print(json.dumps({'ok':True,'adapters':0,'message':'No adapters registered; core setup supports an empty registry.'}))
if __name__=='__main__':main()
