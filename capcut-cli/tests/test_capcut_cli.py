"""Native integration checks using generated test media already in this workspace."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]


class NativeCliTests(unittest.TestCase):
    def invoke(self, *args, ok=True):
        child = subprocess.run([sys.executable, "-B", str(ROOT / "capcut_agent.py"), *args],
                               capture_output=True, text=True, encoding="utf8", timeout=90)
        result = json.loads(child.stdout)
        self.assertEqual(result["ok"], ok, result)
        self.assertEqual(child.returncode == 0, ok, result)
        return result

    def test_probe_generated_video(self):
        result = self.invoke("probe", "--input", str(ROOT / "capcut-test-media/live-edit-test.mp4"))["result"]
        self.assertEqual((result["width"], result["height"], result["duration_us"], result["fps"]),
                         (1280, 720, 9000000, 30.0))

    def test_convert_and_refuse_overwrite(self):
        output_dir = ROOT / "tests/output" / uuid.uuid4().hex
        output_dir.mkdir(parents=True)
        output = output_dir / "native converted.jpg"
        source = ROOT / "capcut-test-media/card-A.png"
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        result = self.invoke("convert-image", "--input", str(source), "--output", str(output))["result"]
        self.assertEqual((result["width"], result["height"], result["format"]), (1280, 720, "jpeg"))
        self.assertTrue(output.read_bytes().startswith(b"\xff\xd8"))
        before = hashlib.sha256(output.read_bytes()).hexdigest()
        error = self.invoke("convert-image", "--input", str(source), "--output", str(output), ok=False)
        self.assertEqual(error["error"]["code"], "output_exists")
        self.assertEqual(before, hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(source_hash, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_explicit_png_format_without_suffix(self):
        output_dir = ROOT / "tests/output" / uuid.uuid4().hex
        output_dir.mkdir(parents=True)
        output = output_dir / "converted image"
        result = self.invoke("convert-image", "--input", str(ROOT / "capcut-test-media/card-B.png"),
                             "--output", str(output), "--format", "png")["result"]
        self.assertEqual(result["format"], "png")
        self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_reject_missing_input_and_same_path(self):
        error = self.invoke("probe", "--input", str(ROOT / "tests/output/absent-input.mp4"), ok=False)
        self.assertEqual(error["error"]["code"], "input_not_found")
        source = str(ROOT / "capcut-test-media/card-A.png")
        error = self.invoke("convert-image", "--input", source, "--output", source, ok=False)
        self.assertEqual(error["error"]["code"], "same_path")

    def test_version_and_help(self):
        self.assertIn("lyra", self.invoke("version")["result"]["text"].lower())
        self.assertIn("--input", self.invoke("help", "--topic", "convert-image")["result"]["text"])

    def test_utf8_json_under_legacy_windows_encoding(self):
        output_dir = ROOT / "tests/output" / uuid.uuid4().hex
        output_dir.mkdir(parents=True)
        source = output_dir / "中文测试.png"
        source.write_bytes((ROOT / "capcut-test-media/card-C.png").read_bytes())
        with patch.dict(os.environ, {"PYTHONIOENCODING": "gbk"}):
            result = self.invoke("probe", "--input", str(source))["result"]
        self.assertIn("中文测试.png", result["input"])
        self.assertEqual((result["width"], result["height"]), (1280, 720))


if __name__ == "__main__":
    unittest.main()
