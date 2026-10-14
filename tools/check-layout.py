"""Check generic documentation and registered manifests; showcase validation is opt-in."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli import config,registry
p=argparse.ArgumentParser();p.add_argument('--examples',action='store_true');a=p.parse_args()
failures=[];entries=registry.entries(examples=a.examples)
for entry in entries:
    for field in ('entrypoint','toolSchema','readme','skill','acceptance','evidence'):
        if entry.get(field) and not registry.reference(entry,field).is_file():failures.append(entry['id']+': missing '+field)
    if entry.get('evidence') and entry.get('status') in ('validated','pilot-validated'):
        if not registry.read(registry.reference(entry,'evidence')).get('passed'):failures.append(entry['id']+': evidence failed')
    if entry.get('demo'):
        for field in ('video','poster','manifest'):
            path=Path(entry['_root'])/entry['demo'][field]
            if not path.is_file() or not path.stat().st_size:failures.append(entry['id']+': missing demo '+field)
docs=list(config.ROOT.glob('*.md'))
for folder in ('docs','skills','acceptance','tools/rea','templates/research'):
    docs+=list((config.ROOT/folder).rglob('*.md'))
for entry in entries:
    parent=registry.reference(entry,'entrypoint').parent
    docs+=list(parent.glob('*.md'))
    for folder in ('docs','examples','tests'):docs+=list((parent/folder).rglob('*.md'))
links=0
for path in set(docs):
    for raw in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        target=raw.strip('<>').split('#',1)[0]
        if not target or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target):continue
        links+=1
        if not (path.parent/target).exists():failures.append(str(path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path)+': missing '+target)
print(json.dumps({'ok':not failures,'adapters':len(entries),'markdownFiles':len(set(docs)),'localLinksChecked':links,'failures':failures}));raise SystemExit(0 if not failures else 1)
