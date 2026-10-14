"""Real decoder tests: non-keyframe cuts, VFR timestamps, audio and safe publication."""
from fractions import Fraction
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capcut_media as media


@unittest.skipUnless(media.DECODER.is_file(), 'Requires the existing local FFmpeg executable')
class MediaPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='media-tests-', dir=ROOT / 'tests')
        cls.folder = Path(cls.temp.name)
        cls.cfr = cls.folder / 'cfr.mp4'
        cls.vfr = cls.folder / 'vfr.mp4'
        env = dict(os.environ, TEMP=cls.temp.name, TMP=cls.temp.name, TMPDIR=cls.temp.name)
        base = [str(media.DECODER), '-hide_banner', '-loglevel', 'error', '-nostdin', '-f', 'lavfi',
                '-i', 'testsrc2=size=160x90:rate=10:duration=3', '-f', 'lavfi', '-i',
                'sine=frequency=440:sample_rate=48000:duration=3']
        encoding = ['-c:v', 'libx264', '-preset', 'veryfast', '-g', '250', '-keyint_min', '250',
                    '-sc_threshold', '0', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest']
        for output, filters in ((cls.cfr, []), (cls.vfr, ['-vf', 'select=not(eq(mod(n\\,3)\\,2))', '-fps_mode', 'passthrough'])):
            subprocess.run(base + filters + encoding + [str(output)], check=True, capture_output=True,
                           env=env, timeout=20, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def args(self, action, output, **changes):
        base = dict(action=action, input=str(self.cfr), output=str(self.folder / output), timeout=30)
        base.update(dict(at_us=0) if action == 'frame' else dict(start_us=0, end_us=1000000))
        return SimpleNamespace(**{**base, **changes})

    def execute(self, action, output, **changes):
        return media.execute_media(media.prepare_media(self.args(action, output, **changes)))

    def test_frame_reports_real_pts_after_nonframe_time(self):
        result = self.execute('frame', 'at-230ms.png', at_us=230000)
        self.assertEqual(result['actualAtUs'], 300000)
        self.assertEqual(Fraction(result['sourceFramePts']) * Fraction(result['sourceTimeBase']), Fraction(3, 10))
        self.assertEqual((result['width'], result['height']), (160, 90))
        self.assertTrue(result['fullDecodeVerified'])

    def test_nonkeyframe_preview_tracks_audio_and_actual_start(self):
        result = self.execute('preview', 'non-keyframe.mp4', start_us=230000, end_us=1470000)
        self.assertEqual(result['effectiveStartUs'], 300000)
        self.assertEqual(result['previewDurationUs'], 1170000)
        self.assertEqual(result['decodedFrames'], 12)
        self.assertEqual(result['firstOutputFramePtsUs'], 0)
        self.assertEqual(result['lastSourceFrameAtUs'], 1400000)
        self.assertEqual(result['decodedVideoEndUs'], 1170000)
        self.assertTrue(result['presentationTimestampsVerified'])
        self.assertTrue(result['hasAudio'])
        self.assertEqual(result['trimmedSourceAudioSamples'], 56160)
        self.assertGreaterEqual(result['aacPaddingSamples'], 0)
        self.assertLessEqual(result['aacPaddingSamples'], 1024)

    def test_vfr_frame_selection_and_preview_keep_actual_pts(self):
        frame = self.execute('frame', 'vfr-frame.png', input=str(self.vfr), at_us=210000)
        self.assertEqual(frame['actualAtUs'], 300000)
        preview = self.execute('preview', 'vfr-preview.mp4', input=str(self.vfr), start_us=210000, end_us=1450000)
        self.assertEqual(preview['effectiveStartUs'], 300000)
        self.assertEqual(preview['decodedFrames'], 8)
        self.assertEqual(preview['lastSourceFrameAtUs'], 1300000)
        self.assertEqual(preview['decodedVideoEndUs'], 1150000)
        self.assertTrue(preview['presentationTimestampsVerified'])
        expected = [0, 100000, 300000, 400000, 600000, 700000, 900000, 1000000]
        self.assertEqual(preview['presentationTimestampsSha256'], media._pts_digest(expected))

    def test_invalid_paths_and_intervals_do_not_create_outputs(self):
        invalid = [self.args('frame', 'invalid.png', at_us=-1),
                   self.args('frame', 'invalid.png', input='https://example.com/video.mp4'),
                   self.args('frame', 'invalid.png', input='concat:one.mp4|two.mp4'),
                   self.args('preview', 'invalid.mp4', start_us=10, end_us=10),
                   self.args('preview', 'invalid.mp4', start_us=11, end_us=10),
                   self.args('frame', 'invalid.png', timeout=float('nan')),
                   self.args('frame', str(self.cfr))]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                media.prepare_media(args)
        for action, name, changes in [('frame', 'past-end.png', {'at_us': 3000000}),
                                      ('preview', 'past-end.mp4', {'end_us': 3100000}),
                                      ('preview', 'no-frame.mp4', {'start_us': 210000, 'end_us': 290000})]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.execute(action, name, **changes)
            self.assertFalse((self.folder / name).exists())
        self.assertEqual(list(self.folder.glob('.capcut-media-*')), [])

    def test_no_overwrite_even_when_destination_appears_at_publication(self):
        output = self.folder / 'racing.png'
        req = media.prepare_media(self.args('frame', output.name))
        original_link = os.link
        def competing_writer(source, target):
            Path(target).write_bytes(b'concurrent-user-file')
            return original_link(source, target)
        with patch.object(media.os, 'link', side_effect=competing_writer), self.assertRaises(FileExistsError):
            media.execute_media(req)
        self.assertEqual(output.read_bytes(), b'concurrent-user-file')
        with self.assertRaises(FileExistsError):
            media.prepare_media(self.args('frame', output.name))
        self.assertEqual(list(self.folder.glob('.capcut-media-*')), [])

    def test_expired_deadline_cleans_partial_workspace(self):
        req = media.prepare_media(self.args('preview', 'timed-out.mp4'))
        req['deadline_monotonic'] = time.monotonic() - 1
        with self.assertRaises(TimeoutError):
            media.execute_media(req)
        self.assertFalse(Path(req['output']).exists())
        self.assertEqual(list(self.folder.glob('.capcut-media-*')), [])

    def test_interleaved_audio_log_cannot_supply_video_timestamp(self):
        # Actual FFmpeg stderr shape reproduced while decoding the 12 s export:
        # an audio log fragment and the complete next video row share one line.
        log = self.folder / 'interleaved.log'
        log.write_text(
            '[Parsed_showinfo_1] config in time_base: 1/30, frame_rate: 30/1\n'
            '[Parsed_showinfo_1] n: 67 pts: 67 pts_time:2.233333 duration: 1 duration_time:0.0333333 '
            'fmt:yuv420p cl:left sar:1/1 s:1920x1080 i:P iskey:0 type:P\n'
            '[Parsed_ashowinfo_0] n:130 pts:133120 pts_time:3.018594 fmt:fltp channels:2 chlayout:stereo '
            'rate:44100 nb_samples:1024 checksum:00000000 '
            'n: 68 pts: 68 pts_time:2.266667 duration: 1 duration_time:0.0333333 '
            'fmt:yuv420p cl:left sar:1/1 s:1920x1080 i:P iskey:0 type:P\n'
            '[Parsed_showinfo_1] n: 69 pts: 69 pts_time:2.3 duration: 1 duration_time:0.0333333 '
            'fmt:yuv420p cl:left sar:1/1 s:1920x1080 i:P iskey:0 type:B\n', encoding='utf8')
        self.assertEqual([frame['pts'] for frame in media._read_video(log)], [67, 68, 69])
        self.assertEqual(list(media._read_audio(log)), [{'pts': 133120, 'rate': 44100, 'samples': 1024}])


if __name__ == '__main__':
    unittest.main()
