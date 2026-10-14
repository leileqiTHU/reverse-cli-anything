"""Run an explicitly selected adapter's own native acceptance procedure."""
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli import config,registry
p=argparse.ArgumentParser();p.add_argument('adapter');a,forwarded=p.parse_known_args()
entry=registry.find(a.adapter);command=entry.get('regression')
if not command:raise SystemExit('This adapter has no native regression procedure; implement and declare one first.')
script=(Path(entry['_root'])/command[0]).resolve()
if not script.is_relative_to(Path(entry['_root'])) or not script.is_file():raise SystemExit('Invalid regression script')
raise SystemExit(subprocess.run([config.python(),'-B',str(script),*command[1:],*forwarded],cwd=entry['_root'],env=config.child_env(a.adapter)).returncode)
