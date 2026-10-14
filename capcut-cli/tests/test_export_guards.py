"""Export safety and media identity checks; no live CapCut edits."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capcut_agent import CliError, parse_args
from capcut_export import prepare_export, validate_probe, export_content_signature
import copy


class ExportGuards(unittest.TestCase):
    def test_requires_explicit_timeline_and_output(self):
        base = ['editor', 'export', '--pid', '123', '--project', 'fixture']
        for args in (base, base + ['--output', 'D:/out.mp4']):
            with self.assertRaises(CliError):
                parse_args(args)

    def test_existing_output_is_rejected_before_renderer(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            output = Path(folder) / 'existing.mp4'
            output.write_bytes(b'existing-user-file')
            args = SimpleNamespace(output=str(output))
            with self.assertRaises(FileExistsError):
                prepare_export(args, {})
            self.assertEqual(output.read_bytes(), b'existing-user-file')

    def test_rejects_invalid_dimensions_fps_and_duration(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            base = dict(output=str(Path(folder) / 'new.mp4'), width=None, height=None, fps=None, timeout=60)
            content = {'canvas_config': {'width': 1920, 'height': 1080}, 'fps': 30, 'duration': 12000000}
            for changes in ({'width': 1920}, {'width': 1919, 'height': 1080}, {'fps': float('nan')},
                            {'fps': 0}, {'timeout': 10}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    prepare_export(SimpleNamespace(**{**base, **changes}), content)
            with self.assertRaises(ValueError):
                prepare_export(SimpleNamespace(**base), {**content, 'duration': 0})
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_output_probe_must_match_expected_export(self):
        req = {'width': 1920, 'height': 1080, 'fps': 30, 'duration_us': 12000000}
        probe = {'container_format': 'mp4', 'video_codec': 'h264', 'width': 1920, 'height': 1080,
                 'fps': 30, 'duration_us': 12000000}
        validate_probe(probe, req)
        for change in ({'duration_us': 3000000}, {'video_codec': 'mpeg4'}, {'width': 1280}, {'fps': 25}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_probe({**probe, **change}, req)

    def test_export_rejects_render_content_changes_even_when_clip_times_match(self):
        doc = {'id': 'draft', 'duration': 12000000, 'fps': 30,
               'canvas_config': {'width': 1920, 'height': 1080},
               'tracks': [{'segments': [{'id': 'clip', 'volume': 1, 'clip': {'scale': 1}}]}],
               'materials': {'effects': [{'id': 'effect', 'intensity': .5}]}}
        original = export_content_signature(doc)
        for key, value in [('duration', 3000000), ('fps', 25), ('canvas_config', {'width': 720, 'height': 1280})]:
            self.assertNotEqual(original, export_content_signature({**doc, key: value}))
        changed = copy.deepcopy(doc)
        changed['tracks'][0]['segments'][0]['volume'] = 0
        self.assertNotEqual(original, export_content_signature(changed))
        changed = copy.deepcopy(doc)
        changed['materials']['effects'][0]['intensity'] = 1
        self.assertNotEqual(original, export_content_signature(changed))
        changed = copy.deepcopy(doc)
        changed['tracks'][0]['attribute'] = 2
        self.assertNotEqual(original, export_content_signature(changed))
        self.assertEqual(original, export_content_signature({**doc, 'update_time': 1234}))


if __name__ == '__main__':
    unittest.main()
