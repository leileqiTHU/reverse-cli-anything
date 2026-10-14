"""Real CapCut workflow using only the JSON CLI. Run with CapCut on its homepage."""
import argparse
from datetime import datetime, timezone
import json
import os
import uuid
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--name', default='REA CLI 全流程 ' + datetime.now().strftime('%H%M%S'))
    parser.add_argument('--media', default=str(ROOT / 'capcut-test-media/live-edit-test.mp4'))
    parser.add_argument('--report', default=str(ROOT / 'capcut-analysis/workflow-verification.json'))
    args = parser.parse_args()
    report_path = Path(args.report).resolve()
    if report_path.exists():
        parser.error('Report already exists; choose a new --report path')
    report = {'startedAt': datetime.now(timezone.utc).isoformat(), 'pid': args.pid,
              'driver': 'CLI subprocesses only; no UI automation or project JSON writes',
              'steps': [], 'ok': False}

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')

    def call(group, action=None, *params, expect_ok=True):
        command = [group] + ([action, '--pid', str(args.pid)] if action else []) + list(map(str, params))
        gateway = os.environ.get('REVERSE_CLI_ACCEPTANCE_GATEWAY') == '1' and expect_ok
        argv = [sys.executable, '-B', str(ROOT / 'capcut_agent.py'), *command]
        if gateway: argv = [sys.executable, '-B', str(ROOT.parent/'reverse-cli.py'), 'run', 'capcut', '--operation-id', 'capcut-regression-'+uuid.uuid4().hex, '--', *command]
        child = subprocess.run(argv,
                               capture_output=True, encoding='utf8', timeout=75,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        envelope = json.loads(child.stdout)
        response = envelope.get('response', envelope) if gateway else envelope
        report['steps'].append({'argv': command, 'exitCode': child.returncode, 'response': response, 'commonReceipt': envelope.get('receipt')})
        save()
        print(json.dumps({'step': len(report['steps']), 'command': ' '.join(command[:2]),
                          'ok': response['ok'], 'expectedOk': expect_ok, 'logs': response.get('logs')}, ensure_ascii=False), flush=True)
        assert response['ok'] is expect_ok and (child.returncode == 0) is expect_ok, response
        return response.get('result', response)

    def edit(action, *params, timeline=None, expect_ok=True):
        return call('editor', action, '--project', project, '--timeline', timeline or timeline_id,
                    *params, expect_ok=expect_ok)

    try:
        state = call('project', 'list')
        assert state['currentProject'] is None, 'Close the current project with project close before this test'
        created = call('project', 'create', '--name', args.name)
        project = created['projectPath']
        project_id = created['projectId']
        main_id = created['mainTimelineId']
        closed = call('project', 'close', '--project', project)
        project = closed['projectPath']
        report.update(projectId=created['projectId'], projectPath=project, mainTimelineId=main_id)
        assert call('project', 'close', '--project-id', project_id)['alreadyClosed']
        imported = call('project', 'import-media', '--project-id', project_id, '--input', args.media)
        assert imported['persistenceVerified'] and not imported['timelineModified']
        duplicate = call('project', 'import-media', '--project-id', project_id, '--input', args.media)
        assert duplicate['alreadyImported'] and duplicate['materialId'] == imported['materialId']
        opened = call('project', 'open', '--project-id', project_id)
        project = opened['projectPath']
        assert call('project', 'open', '--project-id', project_id)['alreadyOpen']
        timeline_id = main_id
        assert edit('inspect')['clips'] == []
        new = edit('add-timeline', '--name', 'CLI 剪辑时间线')
        timeline_id = new['timelineId']
        report['editTimelineId'] = timeline_id
        edit('switch-timeline')
        assert edit('switch-timeline')['changed'] is False
        video = edit('add-video', '--input', args.media, '--duration-us', 3000000)
        segment = video['clips'][0]['id']
        trimmed = edit('trim', '--segment', segment, '--in-us', 500000, '--out-us', 2500000)
        assert trimmed['clips'][0]['sourceUs'] == {'start': 500000, 'duration': 2000000}
        split = edit('split', '--segment', segment, '--points-us', 1000000)
        assert len(split['clips']) == 2
        assert [c['sourceUs'] for c in split['clips']] == [
            {'start': 500000, 'duration': 1000000}, {'start': 1500000, 'duration': 1000000}]
        layer = edit('add-track', '--input', args.media, '--start-us', 1000000, '--duration-us', 1000000)
        overlay = layer['clips'][0]['id']
        moved = edit('move', '--segment', overlay, '--start-us', 3000000)
        assert next(c for c in moved['clips'] if c['id'] == overlay)['targetUs']['start'] == 3000000
        edit('remove', '--segment', overlay)
        edit('undo')
        assert len(edit('inspect')['clips']) == 3
        edit('redo')
        final = edit('inspect')['clips']
        assert len(final) == 2
        edit('split', '--segment', segment, '--points-us', 0, expect_ok=False)
        edit('trim', '--segment', segment, '--in-us', 0, '--out-us', 9000000, expect_ok=False)
        edit('inspect', timeline=main_id, expect_ok=False)
        assert edit('inspect')['clips'] == final
        edit('switch-timeline', timeline=main_id)
        assert edit('inspect', timeline=main_id)['clips'] == []
        edit('switch-timeline')
        closed = call('project', 'close', '--project', project)
        project = closed['projectPath']
        project = call('project', 'open', '--project-id', project_id)['projectPath']
        edit('switch-timeline')
        assert edit('inspect')['clips'] == final, 'Reopened clip IDs, source and target ranges must match'
        meta = json.loads((Path(project) / 'draft_meta_info.json').read_text(encoding='utf-8-sig'))
        bin_items = [i for g in meta['draft_materials'] if g['type'] == 0 for i in g['value']]
        assert any(i['id'] == imported['materialId'] for i in bin_items)
        report.update(ok=True, finishedAt=datetime.now(timezone.utc).isoformat(), finalClips=final,
                      projectPath=project, binMaterialId=imported['materialId'],
                      mainTimelineUnchanged=True, persistenceAfterReopenVerified=True)
        save()
        print(json.dumps({'ok': True, 'report': str(report_path), 'project': project}, ensure_ascii=False))
    except Exception as error:
        report['error'] = str(error)
        save()
        raise


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf8')
    main()
