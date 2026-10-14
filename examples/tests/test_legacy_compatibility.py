"""Offline failure/replay/config/schema tests. No target application is called."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from reverse_cli import config
from reverse_cli.catalog import command
from reverse_cli.cli import run
from reverse_cli.journal import Journal, classify, operation_id, write, refresh, resolve
from reverse_cli.schema import validate

class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path('D:/Caches/reverse-cli') if Path('D:/Caches/reverse-cli').exists() else None)
        self.base=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'REVERSE_CLI_STATE_DIR':str(self.base/'state'),'REVERSE_CLI_CACHE_DIR':str(self.base/'cache'),'REVERSE_CLI_OUTPUT_DIR':str(self.base/'output')})
        self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_id_traversal_rejected(self):
        for bad in ('../other','a/b','CON','aux.txt','bad.'):
            with self.assertRaises(ValueError):operation_id(bad)
    def test_defaults_and_override(self):self.assertEqual(config.directory('cache'),self.base/'cache')
    def test_config_explicit_env_wins(self):
        path=self.base/'config.json';write(path,{'cacheDir':str(self.base/'wrong')})
        with patch.dict(os.environ,{'REVERSE_CLI_CONFIG':str(path)}):self.assertEqual(config.directory('cache'),self.base/'cache')
    def test_doctor_rejects_explicit_missing_app_instead_of_falling_back(self):
        from reverse_cli.doctor import inspect
        with patch.dict(os.environ,{'AXURE_APP':str(self.base/'missing/AxureRP11.exe')}), patch('reverse_cli.doctor.inventory',return_value=[{'ProcessId':1,'Name':'AxureRP11.exe','ExecutablePath':str(config.ROOT/'not-a-real-app.exe')}]):
            result=inspect('axure',1)
        module=next(c for c in result['checks'] if c['name']=='module:AxureRP11.dll')
        self.assertFalse(module['passed']);self.assertIn('missing',module['detail']['path'])
    def test_doctor_explicit_pid_is_a_required_check(self):
        from reverse_cli.doctor import inspect
        with patch.dict(os.environ,{'AXURE_APP':str(self.base/'missing/AxureRP11.exe')}), patch('reverse_cli.doctor.inventory',return_value=[]):result=inspect('axure',12345)
        process=next(c for c in result['checks'] if c['name']=='process')
        self.assertTrue(process['required']);self.assertFalse(process['passed'])
    def test_replay_does_not_launch_child(self):
        with patch('reverse_cli.cli.preflight',return_value=('capabilities',{})):
            first=run('capcut',['capabilities'],'once',30)
        self.assertTrue(first['ok'])
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('replayed')):
            again=run('capcut',['capabilities'],'once',30)
        self.assertTrue(again['replayed']);self.assertFalse(again['freshStateVerified'])
    def test_id_cannot_change_arguments(self):
        run('capcut',['capabilities'],'fixed',30)
        with self.assertRaises(ValueError):run('capcut',['help'],'fixed',30)
    def test_invalid_command_not_submitted(self):
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('launched')):
            result=run('axure',['not-a-command'],'invalid',10)
        self.assertEqual(result['state'],'not-submitted')
    def test_adapter_lock_blocks_parallel_dispatch(self):
        j=Journal(config.directory('state'));j.acquire('capcut','other')
        with patch('reverse_cli.cli.subprocess.Popen',side_effect=AssertionError('launched')):
            result=run('capcut',['project','create','--pid','1','--name','test'],'blocked',10)
        self.assertEqual(result['state'],'not-submitted')
    def test_native_error_not_assumed_rollback(self):
        self.assertEqual(classify({'ok':False,'error':'failed'},2,True),'unknown')
    def test_partial_propagated(self):
        self.assertEqual(classify({'ok':False,'error':{'outcome':'partially-applied'}},2,True),'partially-applied')
    def test_read_failure_completed_but_not_success(self):
        self.assertEqual(classify({'ok':False},2,False),'completed')
    def test_dead_owner_becomes_unknown(self):
        j=Journal(config.directory('state'));j.reserve({'operationId':'dead','state':'running','ownerPid':99999999})
        self.assertEqual(j.get('dead')['state'],'unknown')
    def test_timeout_keeps_child_and_lock(self):
        class Child:
            pid=99999999
            def wait(self,timeout):raise subprocess.TimeoutExpired('test',timeout)
        with patch('reverse_cli.cli.subprocess.Popen',return_value=Child()):result=run('capcut',['project','create','--pid','1','--name','test'],'timeout',1)
        self.assertEqual(result['state'],'unknown')
        self.assertTrue((config.directory('state')/'locks/capcut.lock').exists())
    def test_late_success_refresh_only_observes(self):
        j=Journal(config.directory('state'));log=self.base/'log';log.mkdir();write(log/'stdout.log',{'ok':True,'result':{}})
        lock=j.acquire('axure','late')
        j.reserve({'operationId':'late','state':'unknown','ownerPid':99999999,'childPid':99999998,'logs':str(log),'lock':str(lock)})
        result=refresh(j,'late');self.assertEqual(result['state'],'completed');self.assertFalse(lock.exists())
    def test_read_allowed_while_mutation_unresolved(self):
        j=Journal(config.directory('state'));lock=j.acquire('capcut','unresolved')
        result=run('capcut',['capabilities'],'read',30)
        self.assertTrue(result['ok']);self.assertTrue(lock.exists())
    def test_axure_exact_late_native_receipt(self):
        j=Journal(config.directory('state'));log=self.base/'log';log.mkdir()
        write(log/'stdout.log',{'ok':False,'requestId':'native-id'})
        evidence=self.base/'native-id.json';write(evidence,{'ok':True,'result':{'ready':True}})
        lock=j.acquire('axure','late')
        j.reserve({'operationId':'late','adapter':'axure','state':'unknown','ownerPid':99999999,'childPid':99999998,'logs':str(log),'lock':str(lock),'nativeEvidence':[{'kind':'requestId','path':str(evidence)}]})
        result=refresh(j,'late');self.assertTrue(result['ok']);self.assertFalse(lock.exists())
        self.assertEqual(result['lateNativeReceipt'],str(evidence))
    def resolution_fixture(self):
        import hashlib
        j=Journal(config.directory('state'));lock=j.acquire('capcut','resolve')
        j.reserve({'operationId':'resolve','state':'unknown','ownerPid':99999999,'childPid':99999998,'lock':str(lock),'response':{'ok':False,'error':'guard rejected'}})
        observation=self.base/'observation.json';write(observation,{'finished':True})
        proof=self.base/'proof.json'
        write(proof,{'operationId':'resolve','nativeWorkFinished':True,'state':'completed','ok':False,'checks':[{'name':'renderer terminal','passed':True}],'evidenceFiles':[{'path':str(observation),'sha256':hashlib.sha256(observation.read_bytes()).hexdigest()}]})
        return j,lock,proof,observation
    def test_explicit_failed_resolution_retains_response(self):
        j,lock,proof,_=self.resolution_fixture();result=resolve(j,'resolve',proof)
        self.assertEqual(result['state'],'completed');self.assertFalse(result['ok']);self.assertFalse(lock.exists())
        self.assertEqual(result['response']['error'],'guard rejected')
    def test_resolution_rejects_changed_evidence(self):
        j,lock,proof,observation=self.resolution_fixture();write(observation,{'finished':False})
        with self.assertRaisesRegex(ValueError,'hash mismatch'):resolve(j,'resolve',proof)
        self.assertTrue(lock.exists())
    def test_resolution_rejects_live_child(self):
        j,lock,proof,_=self.resolution_fixture()
        with patch('reverse_cli.journal.alive',return_value=True):
            with self.assertRaisesRegex(ValueError,'still alive'):resolve(j,'resolve',proof)
        self.assertTrue(lock.exists())
    def test_schema_to_argv_preserves_unicode(self):
        args=command('axure','widget.text',{'id':'id','text':'Hello 中文 "quoted"'})
        self.assertEqual(args,['widget','text','--id','id','--text','Hello 中文 "quoted"'])
    def test_exclusive_project_identity(self):
        with self.assertRaises(ValueError):command('capcut','project.open',{'pid':1,'project':'x','project_id':'y'})
    def test_missing_identity(self):
        with self.assertRaises(ValueError):command('capcut','project.open',{'pid':1})
    def test_bool_not_integer(self):
        with self.assertRaises(ValueError):command('capcut','editor.sessions',{'pid':True})
    def test_array_items(self):
        with self.assertRaises(ValueError):command('capcut','editor.split',{'pid':1,'project':'x','segment':'x','points_us':['wrong']})
    def test_shapr_ray_length(self):
        with self.assertRaises(ValueError):command('shapr3d','model-pick',{'session':'x','nearMm':[1,2]})
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):command('axure','widget.bounds',{'id':'x','width':float('nan')})
    def test_receipt_schema(self):
        result=run('capcut',['capabilities'],'schema',30)
        report=json.loads(Path(result['receipt']).read_text())
        import jsonschema
        jsonschema.validate(report,json.loads((ROOT/'schemas/operation.schema.json').read_text()))

if __name__=='__main__':unittest.main()
