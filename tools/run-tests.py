"""Run core tests by default, or an explicitly selected test directory."""
import argparse,io,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli import config,registry
from reverse_cli.journal import now,write
p=argparse.ArgumentParser();p.add_argument('suite',nargs='?',default='core');p.add_argument('--directory',type=Path);a=p.parse_args()
if a.directory:folder=a.directory.resolve()
elif a.suite in ('core','shared'):folder=config.ROOT/'tests_shared'
else:folder=registry.reference(registry.find(a.suite),'entrypoint').parent/'tests'
if not folder.is_dir():raise ValueError('Missing test directory')
suite=unittest.TestLoader().discover(str(folder));stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out=config.directory('output');out.mkdir(parents=True,exist_ok=True);name=registry.adapter_id(a.suite);log=out/(name+'-tests.log');log.write_text(stream.getvalue(),encoding='utf-8')
data={'passed':result.wasSuccessful(),'suite':name,'utc':now(),'run':result.testsRun,'passedTests':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'skipped':[{'test':str(t),'reason':reason} for t,reason in result.skipped],'failures':[{'test':str(t),'trace':trace} for t,trace in result.failures+result.errors],'log':str(log)}
write(out/(name+'-tests.json'),data);print(json.dumps(data));raise SystemExit(0 if data['passed'] else 1)
