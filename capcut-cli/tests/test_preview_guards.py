"""Guard the native-frame boundary without touching a running project."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capcut_agent import CliError, parse_args
from capcut_preview import prepare_frame, prepare_preview, verify_frame_and_publish


class PreviewGuards(unittest.TestCase):
    def test_editor_requests_require_timeline_and_time(self):
        for action in ('frame', 'preview'):
            with self.assertRaises(CliError):
                parse_args(['editor', action, '--pid', '1', '--project', 'fixture', '--output', 'new.png'])
        with self.assertRaises(CliError):
            parse_args(['media', 'preview', '--input', 'a.mp4', '--output', 'b.mp4', '--start-us', '0'])

    def test_frame_bounds_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as directory:
            output = Path(directory) / 'frame.png'
            content = {'duration': 12000000, 'canvas_config': {'width': 1920, 'height': 1080}}
            for changes in ({'at_us': -1}, {'at_us': 12000000}, {'short_side': 4097}, {'short_side': 0}):
                args = SimpleNamespace(**{'output': str(output), 'at_us': 3500000, 'short_side': None, **changes})
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    prepare_frame(args, content)
            self.assertEqual(list(Path(directory).iterdir()), [])
            output.write_bytes(b'user-file')
            with self.assertRaises(FileExistsError):
                prepare_frame(SimpleNamespace(output=str(output), at_us=3500000, short_side=None), content)
            self.assertEqual(output.read_bytes(), b'user-file')

    def test_preview_bounds_precede_any_native_state_change(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as directory:
            content = {'duration': 12000000, 'fps': 30, 'canvas_config': {'width': 1920, 'height': 1080}}
            for start, end in [(-1, 1000000), (0, 12000001), (100, 100), (1000, 999), (0, 1)]:
                with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                    prepare_preview(SimpleNamespace(output=str(Path(directory) / 'new.mp4'), start_us=start, end_us=end), content)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_manifest_cannot_substitute_other_draft_or_frame(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as directory:
            parent = Path(directory)
            stage = parent / '.capcut-frame-owned'
            stage.mkdir()
            image = stage / 'frame.png'
            Image.new('RGB', (32, 18), 'red').save(image)
            req = {'output': str(parent / 'published.png'), 'frame_directory': str(stage),
                   'at_us': 500000, 'short_side': 18, 'canvas_width': 32, 'canvas_height': 18, 'timeline_id': 'draft-A'}
            info = {'name': 'extract_frames', 'draft_id': 'draft-A', 'mode': 'draft', 'task_id': 'task',
                    'operate_result': {'status': 'succeed'}, 'manifest_path': str(stage / 'manifest.json'),
                    'sampling': {'timestamp_us': 500000}, 'materials': [{'segment_id': '', 'frames': [
                        {'path': 'frame.png', 'width': 32, 'height': 18, 'draft_time_us': 500000, 'pts_us': 500000}]}]}
            manifest = stage / 'manifest.json'
            manifest.write_text(json.dumps(info), encoding='utf8')
            for key, value in [('draft_id', 'draft-B'), ('mode', 'segment')]:
                changed = {**info, key: value}
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_frame_and_publish(req, {'extras': [changed], 'affected_segments': []})
            changed = copy.deepcopy(info)
            changed['materials'][0]['frames'][0]['path'] = '../other.png'
            manifest.write_text(json.dumps(changed), encoding='utf8')
            with self.assertRaises(ValueError):
                verify_frame_and_publish(req, {'extras': [changed], 'affected_segments': []})
            self.assertFalse(Path(req['output']).exists())
            manifest.write_text(json.dumps(info), encoding='utf8')
            result = verify_frame_and_publish(req, {'extras': [info], 'affected_segments': []})
            self.assertTrue(result['fullImageDecodeVerified'])
            self.assertTrue(Path(req['output']).is_file())


if __name__ == '__main__':
    unittest.main()
