"""Verify installation, cold-session use and development helpers in a complete isolated bundle."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reverse_cli import config
from reverse_cli.delivery import install_skill
from reverse_cli.journal import write


def main():
    base = config.directory('cache')
    base.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='portable-install-', dir=base))
    installed = install_skill(destination / 'skill')
    framework = Path(installed['framework'])
    temporary = destination / 'temp'
    temporary.mkdir()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('REVERSE_CLI_') and key not in ('PYTHONPATH', 'PYTHONHOME')}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
               TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary))
    bootstrap = dict(env, REVERSE_CLI_CACHE_DIR=str(destination / 'cache'),
                     REVERSE_CLI_STATE_DIR=str(destination / 'state'), REVERSE_CLI_OUTPUT_DIR=str(destination / 'output'))
    checks = []

    def execute(script, argv, predicate, environment=env, cwd=framework):
        command = [sys.executable, '-B', str(framework / script), *argv]
        process = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                                 text=True, encoding='utf-8', timeout=60)
        try:
            response = json.loads(process.stdout)
            passed = process.returncode == 0 and bool(predicate(response))
        except (ValueError, KeyError, TypeError):
            response = {'stdout': process.stdout}
            passed = False
        checks.append({'script': script, 'arguments': argv, 'passed': passed,
                       'response': response, 'stderr': process.stderr})
        return response

    setup = execute('tools/setup.py', ['--configure'], lambda r: r['ok'] and r['configuration']['created'], bootstrap)
    if setup.get('ok'):
        expected = setup['installation']
        execute('tools/setup.py', [], lambda r: r['ok'], cwd=destination)
        execute('reverse-cli-anything.py', ['doctor'], lambda r: r['ok'] and r['scope'] == 'core', cwd=destination)
        execute('reverse-cli-anything.py', ['list'], lambda r: r['adapters'] == [], cwd=destination)
        settings = json.loads((framework / 'reverse-cli.local.json').read_text(encoding='utf-8'))
        checks.append({'name': 'persistent-installation-context', 'passed':
                       settings['python'] == sys.executable and settings['stateDir'] == expected['directories']['state']
                       and settings['outputDir'] == str(destination / 'output')})

        research = destination / 'research'
        execute('tools/research.py', ['init', 'fresh-target', '--application', 'Selected target', '--goal', 'Inspect requested data',
                '--operation', 'inspect-data', '--output', str(research)], lambda r: r['nativeImplemented'] is False)
        execute('tools/research.py', ['status', str(research)], lambda r: r['ok'] and r['declaredCounts']['planned'] == 1)
        adapter = destination / 'adapter'
        execute('reverse-cli-anything.py', ['init', 'fresh-target', '--output', str(adapter)], lambda r: r['nativeImplemented'] is False)
        execute('reverse-cli-anything.py', ['register', str(adapter / 'adapter.json')], lambda r: r['adapter']['id'] == 'fresh-target')
        execute('reverse-cli-anything.py', ['tools', 'fresh-target'], lambda r: len(r['result']['tools']) == 1)
        execute('reverse-cli-anything.py', ['call', 'fresh-target', 'status', '--args', '{}', '--operation-id', 'first'],
                lambda r: r['ok'] and r['response']['result']['nativeImplemented'] is False)
        execute('reverse-cli-anything.py', ['call', 'fresh-target', 'status', '--args', '{}', '--operation-id', 'first'],
                lambda r: r['replayed'] is True and r['freshStateVerified'] is False, cwd=destination)
        execute('reverse-cli-anything.py', ['operation', 'get', 'first'], lambda r: r['result']['state'] == 'completed', cwd=destination)
        execute('tools/generate-docs.py', [str(adapter / 'adapter.json'), '--output', str(adapter / 'agent-docs')],
                lambda r: r['ok'] and r['nativeValidationRun'] is False)
        execute('reverse-cli-anything.py', ['list'], lambda r: len(r['adapters']) == 1, cwd=destination)
        if os.name == 'nt' and shutil.which('pwsh'):
            process = subprocess.run(['pwsh', '-NoProfile', '-File', str(framework / 'reverse-cli-anything.ps1'), 'list'],
                                     cwd=destination, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            try:
                passed = process.returncode == 0 and len(json.loads(process.stdout)['adapters']) == 1
            except (ValueError, KeyError, TypeError):
                passed = False
            checks.append({'name': 'powershell-cold-session', 'passed': passed, 'stderr': process.stderr})

    report = {'passed': all(check['passed'] for check in checks), 'directory': str(destination), 'checks': checks,
              'scope': 'Complete generic Skill installation, fresh process without inherited framework variables, research records and synthetic adapter transport.',
              'nativeValidationRun': False, 'hostDiscoveryVerified': False}
    write(config.directory('output') / 'portable-smoke.json', report)
    print(json.dumps({'passed': report['passed'], 'checks': len(checks), 'directory': str(destination),
                      'failures': [check for check in checks if not check['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
