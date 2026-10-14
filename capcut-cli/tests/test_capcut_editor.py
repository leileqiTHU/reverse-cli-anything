"""Opt-in live integration test; use only a dedicated disposable CapCut draft."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PID = os.environ.get('CAPCUT_TEST_PID')
PROJECT = os.environ.get('CAPCUT_TEST_PROJECT')


@unittest.skipUnless(PID and PROJECT, 'Set CAPCUT_TEST_PID and CAPCUT_TEST_PROJECT to an open dedicated test draft')
class EditorTests(unittest.TestCase):
    def call(self, action, *args, ok=True, project=None):
        command = [sys.executable, '-B', str(ROOT / 'capcut_agent.py'), 'editor', action, '--pid', PID]
        if action != 'sessions':
            command += ['--project', project or PROJECT]
        child = subprocess.run(command + list(args), capture_output=True, encoding='utf8', timeout=90)
        value = json.loads(child.stdout)
        self.assertEqual(value['ok'], ok, value)
        self.assertEqual(child.returncode == 0, ok, value)
        return value

    def test_01_identity_and_mismatch_refusal(self):
        state = self.call('sessions')['result']
        self.assertTrue(any(s['current'] and s['ready'] for s in state['sessions']))
        before = self.call('inspect')['result']['summary']
        project_data = json.loads((Path(PROJECT) / 'Timelines/project.json').read_text(encoding='utf8'))
        self.assertEqual(before[0]['id'], project_data['main_timeline_id'])
        # A real different draft is a stronger guard check than a missing path.
        other = Path(PROJECT).parent / '1012'
        self.assertNotEqual(other.resolve(), Path(PROJECT).resolve())
        error = self.call('inspect', project=str(other), ok=False)
        self.assertIn('does not match', error['error']['message'])
        self.assertEqual(before, self.call('inspect')['result']['summary'])

    def test_02_invalid_range_does_not_edit(self):
        before = self.call('inspect')['result']['summary']
        error = self.call('add-video', '--input', str(ROOT / 'capcut-test-media/live-edit-test.mp4'),
                          '--duration-us', '999999999', ok=False)
        self.assertEqual(error['error']['code'], 'invalid_range')
        self.assertEqual(before, self.call('inspect')['result']['summary'])

    def check_saved(self, result):
        path = Path(PROJECT) / 'Timelines' / result['timelineId'] / 'draft_content.json'
        ids = result['native']['segment_ids']
        deadline = time.monotonic() + 8
        while True:
            doc = json.loads(path.read_text(encoding='utf8'))
            clips = [s for t in doc['tracks'] for s in t['segments']]
            if all(any(s['id'] == sid for s in clips) for sid in ids):
                break
            if time.monotonic() > deadline:
                self.fail('Native edit did not autosave within eight seconds')
            time.sleep(.25)
        material_ids = {s['material_id'] for s in clips if s['id'] in ids}
        for material in doc['materials']['videos']:
            if material['id'] in material_ids:
                self.assertEqual((material['width'], material['height']), (1280, 720))
                self.assertTrue(Path(material['path']).is_file())

    def test_03_add_video_existing_track(self):
        result = self.call('add-video', '--input', str(ROOT / 'capcut-test-media/live-edit-test.mp4'),
                           '--track', '0', '--start-us', '4000000', '--duration-us', '1000000')['result']
        self.assertFalse(result['addedRenderLayer'])
        self.assertEqual(result['requestedTrackIndex'], 0)
        self.assertEqual(result['clips'][0]['renderIndex'], 0)
        self.check_saved(result)

    def test_04_create_track_with_unicode_media(self):
        output = ROOT / 'tests/output/editor-fixture'
        output.mkdir(parents=True, exist_ok=True)
        media = output / '新轨道 视频.mp4'
        if not media.exists():
            media.write_bytes((ROOT / 'capcut-test-media/live-edit-test.mp4').read_bytes())
        before = self.call('inspect')['result']['summary']
        doc = json.loads((Path(PROJECT) / 'draft_content.json').read_text(encoding='utf8'))
        layers = {s['render_index'] for t in doc['tracks'] if t['type'] == 'video' for s in t['segments']}
        next_layer = max(layers, default=-1) + 1
        result = self.call('add-track', '--input', str(media), '--duration-us', '1000000')['result']
        self.assertTrue(result['addedRenderLayer'])
        self.assertEqual(result['requestedTrackIndex'], next_layer)
        self.assertEqual(result['clips'][0]['renderIndex'], next_layer)
        self.check_saved(result)


if __name__ == '__main__':
    unittest.main()
