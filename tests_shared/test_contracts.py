"""Core tests use a temporary synthetic adapter; no showcased software or code is imported."""
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from reverse_cli import config,registry
from reverse_cli.catalog import command
from reverse_cli.cli import run
from reverse_cli.scaffold import create
from reverse_cli.journal import Journal,classify,operation_id,write,refresh,resolve
from reverse_cli.schema import validate
from reverse_cli.acceptance import inspect as acceptance

class Core(unittest.TestCase):
    def setUp(self):
        cache=config.directory('cache');cache.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=cache);self.base=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'REVERSE_CLI_CONFIG':str(self.base/'absent.json'),'REVERSE_CLI_REGISTRY':str(self.base/'registry.json'),'REVERSE_CLI_STATE_DIR':str(self.base/'state'),'REVERSE_CLI_CACHE_DIR':str(self.base/'cache'),'REVERSE_CLI_OUTPUT_DIR':str(self.base/'output'),'REVERSE_CLI_PYTHON':sys.executable})
        self.env.start();write(self.base/'registry.json',{'schemaVersion':1,'adapters':[]})
        create('fixture',self.base/'fixture')
        self.root=self.base/'fixture';self.manifest=self.root/'adapter.json'
        catalog=registry.read(self.root/'tools.json')
        catalog['tools']+=[{'name':name,'adapter':'fixture','mutates':name=='write','inputSchema':{'type':'object','properties':{'text':{'type':'string'},'number':{'type':'number'},'points':{'type':'array','items':{'type':'integer'},'minItems':3,'maxItems':3}},'additionalProperties':False},'outputSchema':{'type':'object'}} for name in ('read','write')]
        write(self.root/'tools.json',catalog)
        (self.root/'cli.py').write_text("import sys,json\nfrom pathlib import Path\np=Path(__file__).with_name('count.json')\nc=json.loads(p.read_text()) if p.exists() else 0\nif sys.argv[1]=='write':\n c+=1;p.write_text(json.dumps(c))\nprint(json.dumps({'ok':True,'result':{'count':c}}))\n",encoding='utf-8')
        registry.register(self.manifest)
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_register_and_discover_arbitrary_adapter(self):self.assertEqual([e['id'] for e in registry.entries()],['fixture'])
    def test_empty_registry_supported(self):
        with patch.dict(os.environ,{'REVERSE_CLI_STATE_DIR':str(self.base/'empty-state')}):self.assertEqual(registry.entries(),[])
    def test_registration_idempotent(self):
        registry.register(self.manifest);self.assertEqual(len(registry.entries()),1)
    def test_duplicate_id_rejected(self):
        create('fixture',self.base/'other')
        with self.assertRaises(ValueError):registry.register(self.base/'other/adapter.json')
    def test_manifest_cannot_escape_declared_root(self):
        data=registry.read(self.manifest);data['entrypoint']='../outside.py';write(self.base/'outside.py',{})
        write(self.manifest,data)
        with self.assertRaises(ValueError):registry.manifest(self.manifest)
    def test_scaffold_refuses_existing_directory(self):
        with self.assertRaises(FileExistsError):create('another',self.root)
    def test_id_traversal_rejected(self):
        for bad in ('../other','a/b','CON','aux.txt','bad.'):
            with self.assertRaises(ValueError):operation_id(bad)
        for bad in ('../target','CON','Foo','a.b'):
            with self.assertRaises(ValueError):registry.adapter_id(bad)
    def test_config_env_wins(self):
        path=self.base/'settings.json';write(path,{'cacheDir':str(self.base/'wrong')})
        with patch.dict(os.environ,{'REVERSE_CLI_CONFIG':str(path)}):self.assertEqual(config.directory('cache'),self.base/'cache')
    def test_core_doctor_never_inventories_applications(self):
        from reverse_cli.doctor import inspect
        with patch('reverse_cli.doctor.inventory',side_effect=AssertionError('target dependency')):
            self.assertTrue(inspect()['ok'])
    def test_replay_does_not_execute_write_twice(self):
        first=run('fixture',['write'],'once',30);self.assertTrue(first['ok'])
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('replayed')):again=run('fixture',['write'],'once',30)
        self.assertTrue(again['replayed']);self.assertFalse(again['freshStateVerified'])
        self.assertEqual(json.loads((self.root/'count.json').read_text()),1)
    def test_id_cannot_change_arguments(self):
        run('fixture',['read'],'fixed',30)
        with self.assertRaises(ValueError):run('fixture',['write'],'fixed',30)
    def test_invalid_command_not_submitted(self):
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('launched')):result=run('fixture',['absent'],'invalid',10)
        self.assertEqual(result['state'],'not-submitted')
    def test_write_lock_blocks_dispatch(self):
        Journal(config.directory('state')).acquire('fixture','other')
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('launched')):result=run('fixture',['write'],'blocked',10)
        self.assertEqual(result['state'],'not-submitted')
    def test_native_error_not_assumed_rollback(self):self.assertEqual(classify({'ok':False},2,True),'unknown')
    def test_partial_propagated(self):self.assertEqual(classify({'ok':False,'outcome':'partially-applied'},2,True),'partially-applied')
    def test_read_failure_completed_but_not_success(self):self.assertEqual(classify({'ok':False},2,False),'completed')
    def test_dead_owner_becomes_unknown(self):
        j=Journal(config.directory('state'));j.reserve({'operationId':'dead','state':'running','ownerPid':99999999})
        self.assertEqual(j.get('dead')['state'],'unknown')
    def test_timeout_retains_write_lock(self):
        class Child:
            pid=99999999
            def wait(self,timeout):raise subprocess.TimeoutExpired('fixture',timeout)
        with patch('reverse_cli.cli.subprocess.Popen',return_value=Child()):result=run('fixture',['write'],'timeout',1)
        self.assertEqual(result['state'],'unknown');self.assertTrue((config.directory('state')/'locks/fixture.lock').exists())
    def test_late_success_refresh_only_observes(self):
        j=Journal(config.directory('state'));log=self.base/'log';log.mkdir();write(log/'stdout.log',{'ok':True})
        lock=j.acquire('fixture','late');j.reserve({'operationId':'late','state':'unknown','ownerPid':99999999,'childPid':99999998,'logs':str(log),'lock':str(lock)})
        self.assertEqual(refresh(j,'late')['state'],'completed');self.assertFalse(lock.exists())
    def test_exact_late_request_evidence(self):
        j=Journal(config.directory('state'));log=self.base/'log';log.mkdir();write(log/'stdout.log',{'ok':False,'requestId':'native-id'})
        evidence=self.base/'native-id.json';write(evidence,{'ok':True});lock=j.acquire('fixture','late')
        j.reserve({'operationId':'late','adapter':'fixture','state':'unknown','ownerPid':99999999,'childPid':99999998,'logs':str(log),'lock':str(lock),'nativeEvidence':[{'kind':'requestId','path':str(evidence)}]})
        self.assertTrue(refresh(j,'late')['ok']);self.assertFalse(lock.exists())
    def test_reads_allowed_during_unknown_write(self):
        lock=Journal(config.directory('state')).acquire('fixture','unknown')
        self.assertTrue(run('fixture',['read'],'read',30)['ok']);self.assertTrue(lock.exists())
    def resolution(self):
        j=Journal(config.directory('state'));lock=j.acquire('fixture','resolve')
        j.reserve({'operationId':'resolve','state':'unknown','ownerPid':99999999,'childPid':99999998,'lock':str(lock),'response':{'ok':False,'error':'failed'}})
        data=self.base/'observation.json';write(data,{'finished':True})
        proof=self.base/'proof.json';write(proof,{'operationId':'resolve','nativeWorkFinished':True,'state':'completed','ok':False,'checks':[{'name':'finished','passed':True}],'evidenceFiles':[{'path':str(data),'sha256':hashlib.sha256(data.read_bytes()).hexdigest()}]})
        return j,lock,proof,data
    def test_resolution_preserves_failed_response(self):
        j,lock,proof,_=self.resolution();result=resolve(j,'resolve',proof)
        self.assertEqual(result['response']['error'],'failed');self.assertFalse(result['ok']);self.assertFalse(lock.exists())
    def test_resolution_rejects_changed_evidence(self):
        j,lock,proof,data=self.resolution();write(data,{'finished':False})
        with self.assertRaises(ValueError):resolve(j,'resolve',proof)
        self.assertTrue(lock.exists())
    def test_resolution_rejects_live_worker(self):
        j,lock,proof,_=self.resolution()
        with patch('reverse_cli.journal.alive',return_value=True):
            with self.assertRaises(ValueError):resolve(j,'resolve',proof)
    def test_command_unicode_roundtrip(self):
        argv=command('fixture','write',{'text':'中文 "quoted"'})
        self.assertEqual(json.loads(argv[2]),{'text':'中文 "quoted"'})
    def test_invalid_numeric_and_array_inputs(self):
        for args in ({'number':True},{'number':float('nan')},{'points':[1,2]},{'points':[1,2,'3']}):
            with self.assertRaises(ValueError):command('fixture','write',args)
    def test_receipt_accepts_arbitrary_target(self):
        result=run('fixture',['read'],'schema',30)
        validate(registry.read(result['receipt']),registry.read(ROOT/'schemas/operation.schema.json'))
    def test_unexecuted_acceptance_plan_fails(self):self.assertFalse(acceptance(self.root/'acceptance-plan.json')['ok'])
    def evidence_report(self):
        data=self.base/'assertions.json';write(data,{'observed':True,'kind':'synthetic-test'})
        proof={'path':data.name,'sha256':hashlib.sha256(data.read_bytes()).hexdigest()}
        report={'schemaVersion':1,'adapter':'fixture','target':{'name':'synthetic-test','build':'1'},'workflow':'test validator only','checks':[{'layer':layer,'name':layer,'status':'passed','evidence':[proof]} for layer in ('request','state','persistence','artifact','recovery')]}
        path=self.base/'report.json';write(path,report);return path,data,report
    def test_acceptance_rejects_tampered_evidence(self):
        path,data,_=self.evidence_report();self.assertTrue(acceptance(path)['ok']);write(data,{'changed':True})
        self.assertFalse(acceptance(path)['ok'])
    def test_acceptance_cannot_skip_native_state(self):
        path,_,report=self.evidence_report();report['checks'][1].update(status='not-applicable',reason='unsupported');write(path,report)
        self.assertFalse(acceptance(path)['ok'])
    def test_acceptance_missing_layer_fails(self):
        path,_,report=self.evidence_report();report['checks'].pop();write(path,report)
        self.assertFalse(acceptance(path)['ok'])

if __name__=='__main__':unittest.main()
