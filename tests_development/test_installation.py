"""Install from generic resources and check failures without loading target code."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reverse_cli import config, delivery


class Installation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = config.directory('cache') / 'installation-checks'
        cache.mkdir(parents=True, exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(prefix='installation-', dir=cache))

    def setUp(self):
        self.directory = self.root / self._testMethodName
        self.bundle = self.directory / 'skill'
        self.framework = Path(delivery.install_skill(self.bundle)['framework'])
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith('REVERSE_CLI_') and k not in ('PYTHONPATH', 'PYTHONHOME')}
        temporary = self.directory / 'temp'
        temporary.mkdir()
        self.env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                        TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary))
        self.bootstrap = dict(self.env, REVERSE_CLI_CACHE_DIR=str(self.directory / 'cache'),
                              REVERSE_CLI_STATE_DIR=str(self.directory / 'state'),
                              REVERSE_CLI_OUTPUT_DIR=str(self.directory / 'output'))

    def run_setup(self, configure=False, env=None):
        process = subprocess.run([sys.executable, '-B', str(self.framework / 'tools/setup.py'),
                                  *(['--configure'] if configure else [])],
                                 cwd=self.directory, env=env or self.bootstrap,
                                 capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertFalse(process.stderr, process.stderr)
        value = json.loads(process.stdout)
        self.assertEqual(process.returncode, 0 if value['ok'] else 1)
        return value

    def test_persisted_context_survives_fresh_process(self):
        first = self.run_setup(configure=True)
        self.assertTrue(first['ok'], first)
        second = self.run_setup(configure=True, env=self.env)
        self.assertTrue(second['ok'], second)
        self.assertFalse(second['configuration']['created'])
        for key in ('frameworkRoot', 'python', 'configPath', 'registry', 'directories'):
            self.assertEqual(first['installation'][key], second['installation'][key])
        self.assertEqual(second['installation']['environmentOverrides'], [])
        self.assertEqual(second['installation']['python'], sys.executable)
        self.assertEqual(second['installation']['hostDiscovery'], 'not-verified')

    def test_existing_configuration_is_preserved(self):
        path = self.framework / 'reverse-cli.local.json'
        contents = json.dumps({'python': sys.executable, 'customSetting': 'retain me',
                               'cacheDir': str(self.directory / 'existing-cache'),
                               'stateDir': str(self.directory / 'existing-state'),
                               'outputDir': str(self.directory / 'existing-output')}, indent=4) + '\n'
        path.write_text(contents, encoding='utf-8')
        baseline = path.read_bytes()
        result = self.run_setup(configure=True, env=self.env)
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['configuration']['created'])
        self.assertEqual(path.read_bytes(), baseline)
        self.assertEqual(result['installation']['directories']['state'], str(self.directory / 'existing-state'))

    def test_missing_linked_resource_rejected(self):
        path = self.framework / 'docs/guides/reconnaissance.md'
        path.rename(path.with_suffix('.missing'))
        result = self.run_setup(configure=True)
        self.assertFalse(result['ok'], result)
        self.assertIn('reconnaissance.md', json.dumps(result))
        self.assertFalse((self.framework / 'reverse-cli.local.json').exists())

    def test_broken_outer_skill_reference_rejected(self):
        with (self.bundle / 'SKILL.md').open('a', encoding='utf-8') as stream:
            stream.write('\n[Required resource](framework/missing.md)\n')
        result = self.run_setup()
        self.assertFalse(result['ok'], result)
        self.assertIn('missing.md', json.dumps(result))

    def test_missing_host_entry_rejected(self):
        path = self.bundle / 'SKILL.md'
        path.rename(self.bundle / 'SKILL.missing')
        result = self.run_setup()
        self.assertFalse(result['ok'], result)
        self.assertIn('SKILL.md', json.dumps(result))

    def test_missing_required_script_rejected(self):
        path = self.framework / 'tools/research.py'
        path.rename(path.with_suffix('.missing'))
        result = self.run_setup()
        self.assertFalse(result['ok'], result)
        self.assertIn('research.py', result['error'])

    def test_invalid_configuration_rejected_without_overwrite(self):
        path = self.framework / 'reverse-cli.local.json'
        path.write_text('[]', encoding='utf-8')
        result = self.run_setup(configure=True)
        self.assertFalse(result['ok'], result)
        self.assertIn('JSON object', result['error'])
        self.assertEqual(path.read_text(encoding='utf-8'), '[]')

    def test_registry_override_is_persisted(self):
        path = self.directory / 'separate-registry.json'
        path.write_text('{"schemaVersion":1,"adapters":[]}', encoding='utf-8')
        first = self.run_setup(configure=True, env=dict(self.bootstrap, REVERSE_CLI_REGISTRY=str(path)))
        self.assertTrue(first['ok'], first)
        second = self.run_setup(configure=True, env=self.env)
        self.assertTrue(second['ok'], second)
        self.assertEqual(second['installation']['registry'], str(path))


if __name__ == '__main__':
    unittest.main()
