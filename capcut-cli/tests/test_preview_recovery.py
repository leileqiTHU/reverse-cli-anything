"""Inject unavailable runtime/autosave failures without damaging a live project."""
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capcut_preview import render_preview
from capcut_export import ExportCancellationUnconfirmed, cleanup_without_masking


class PreviewRecovery(unittest.TestCase):
    def fixture(self, directory, original):
        project = Path(directory)
        (project / 'Timelines/timeline').mkdir(parents=True)
        (project / '.runtime').mkdir()
        (project / 'Timelines/project.json').write_text('{"main_timeline_id":"main"}')
        for name in ('capcut_timeline_agent.js', 'capcut_preview_range_agent.js'):
            (project / name).write_text('')
        saved = {'config': {'export_range': original}}
        draft = project / 'Timelines/timeline/draft_content.json'
        draft.write_text(json.dumps(saved))
        req = dict(project=str(project), pid=1, project_id='project', timeline_id='timeline',
                   stage_output=str(project / '.capcut-export-test/video.mp4'), output=str(project / 'out.mp4'),
                   start_us=2300000, end_us=4700000, deadline_monotonic=time.monotonic() + 90)
        state = {'range': original, 'calls': 0}
        def get_range(context):
            return {'range': state['range']}
        def set_range(context):
            journal = json.loads(next((project / '.runtime').glob('preview-range-*.json')).read_text())
            self.assertEqual(journal['originalRange'], original)
            self.assertEqual(context['expectedRange'], state['range'])
            before = state['range']
            state['range'] = context['desiredRange']
            state['calls'] += 1
            draft.write_text(json.dumps({'config': {'export_range': state['range']}}))
            return {'before': before, 'after': state['range']}
        def unload():
            raise RuntimeError('script destroyed')
        script = SimpleNamespace(on=lambda *args: None, load=lambda: None, unload=unload,
                                 exports_sync=SimpleNamespace(previewrange=get_range, previewsetrange=set_range))
        return req, saved, SimpleNamespace(create_script=lambda source: script), state, draft

    def test_unknown_native_outcome_survives_cleanup_and_retains_original_range(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            original = {'start': 1000000, 'duration': 8000000}
            req, saved, session, state, draft = self.fixture(folder, original)
            failure = ExportCancellationUnconfirmed('bound task cancellation unconfirmed')
            with patch('capcut_preview.ROOT', Path(folder)), patch('capcut_export.render_frontend', side_effect=failure):
                with self.assertRaises(ExportCancellationUnconfirmed) as raised:
                    render_preview(req, session, saved, 47, {})
            self.assertIs(raised.exception, failure)
            self.assertTrue(raised.exception.preserve_pid_lock)
            self.assertEqual(state['calls'], 1)  # Never change range while native render outcome is unknown.
            record = json.loads(next((Path(folder) / '.runtime').glob('*.json')).read_text())
            self.assertEqual(record['originalRange'], original)
            self.assertEqual(record['status'], 'prepared-before-native-change')

    def test_transient_autosave_reads_retry_and_non_null_range_restores(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            original = {'start': 1000000, 'duration': 8000000}
            req, saved, session, state, draft = self.fixture(folder, original)
            real_read = Path.read_text
            failures = [OSError('file replacing'), json.JSONDecodeError('incomplete', '', 0)]
            def read(path, *args, **kwargs):
                if path == draft and failures:
                    raise failures.pop(0)
                return real_read(path, *args, **kwargs)
            with patch('capcut_preview.ROOT', Path(folder)), patch('capcut_export.render_frontend', return_value={}), patch.object(Path, 'read_text', read):
                result = render_preview(req, session, saved, 47, {})
            self.assertTrue(result['exportRangeRestored'])
            self.assertEqual(state['range'], original)
            self.assertEqual(json.loads(Path(result['rangeRecoveryRecord']).read_text())['status'], 'restored')

    def test_cleanup_cannot_replace_an_inflight_preserve_lock_error(self):
        def failing_cleanup():
            raise RuntimeError('disconnected')
        with self.assertRaises(ExportCancellationUnconfirmed):
            try:
                raise ExportCancellationUnconfirmed('keep original')
            finally:
                cleanup_without_masking('observer', failing_cleanup)


if __name__ == '__main__':
    unittest.main()
