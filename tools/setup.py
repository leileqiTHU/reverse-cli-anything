"""Configure and verify a complete framework installation without target applications."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli.doctor import inspect
from reverse_cli import installation

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure',action='store_true',help='Create missing local settings and retain the effective installation context')
    args=parser.parse_args()
    try:
        resources=installation.resources()
        configured=installation.configure() if args.configure and resources['passed'] else None
        result=inspect()
        result['checks'].append({'name':'generic-resources','passed':resources['passed'],'required':True,'detail':resources})
        result['ok']=all(c['passed'] for c in result['checks'] if c['required'])
        if configured:result['configuration']=configured
        if args.configure and result['ok']:result['installation']=installation.record()
    except (OSError,ValueError,KeyError,TypeError) as error:
        result={'ok':False,'scope':'core','error':str(error)}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['ok'] else 1

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
