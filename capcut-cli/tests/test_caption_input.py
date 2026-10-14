"""Input-contract tests only: these never attach to or write to CapCut."""
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capcut_captions import (MAX_CUE_CHARS, MAX_CUES, MAX_FILE_BYTES,
                            MAX_SAFE_INTEGER, load_captions, normalize_style)


class CaptionInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, content, suffix='.json'):
        path = self.root / ('captions' + suffix)
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        path.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
        return path

    def doc(self, **overrides):
        return {'timebase': 'timeline_us', 'cues': [
            {'id': 'c1', 'startUs': 0, 'endUs': 1000000, 'text': 'Hello', **overrides}]}

    def test_srt_bom_crlf_complex_literals_and_offset_are_preserved(self):
        literal = '  中文 "引号" \\path --action 😀\n第二行\t保留空格  '
        srt = '1\n00:00:00,000 --> 00:00:01,500\n' + literal + '\n\n2\n00:00:01,500 --> 00:00:02,000\n尾声\n'
        path = self.write(b'\xef\xbb\xbf' + srt.replace('\n', '\r\n').encode('utf-8'), '.srt')
        result = load_captions(path, offset_us=100000, timeline_duration_us=2100000)
        self.assertEqual(result[0], {'id': '1', 'startUs': 100000, 'endUs': 1600000, 'text': literal})
        self.assertEqual(result[1]['startUs'], 1600000)
        self.assertEqual(result[1]['endUs'], 2100000)

    def test_json_literal_text_avoids_shell_interpretation(self):
        literal = '中文 "double" \'single\' \\ ${name} $(whoami) `raw` --start 5s\n😀'
        result = load_captions(self.write(self.doc(text=literal)))
        self.assertEqual(result[0]['text'], literal)

    def test_srt_blank_separator_whitespace_does_not_strip_caption_spaces(self):
        srt = ' \n1\n00:00:00,000 --> 00:00:01,000\n A  \n \n\t\n2\n00:00:01,000 --> 00:00:02,000\n B \n\n \t'
        result = load_captions(self.write(srt, '.srt'))
        self.assertEqual([cue['text'] for cue in result], [' A  ', ' B '])

    def test_json_optional_ids_and_format_override(self):
        doc = self.doc()
        del doc['cues'][0]['id']
        self.assertEqual(load_captions(self.write(doc, '.data'), format='json')[0]['id'], 'cue-0001')

    def test_adjacent_intervals_and_negative_offset_are_valid(self):
        doc = self.doc(startUs=100000, endUs=1100000)
        doc['cues'].append({'id': 'second', 'startUs': 1100000, 'endUs': 2100000, 'text': 'Next'})
        cues = load_captions(self.write(doc), offset_us=-100000, timeline_duration_us=2000000)
        self.assertEqual([(c['startUs'], c['endUs']) for c in cues], [(0, 1000000), (1000000, 2000000)])

    def test_missing_or_ambiguous_json_fields_rejected(self):
        invalid = [[], {}, {'timebase': 'seconds', 'cues': []},
                   {'timebase': 'timeline_us', 'cues': [], 'extra': True},
                   self.doc(unrecognized=1)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_captions(self.write(json.dumps(value)))

    def test_duplicate_json_keys_and_nonfinite_constants_rejected(self):
        for raw in ('{"timebase":"timeline_us","timebase":"timeline_us","cues":[]}',
                    '{"timebase":"timeline_us","cues":[{"startUs":NaN,"endUs":1000000,"text":"A"}]}',
                    '{"timebase":"timeline_us","cues":[{"startUs":0,"startUs":1,"endUs":1000000,"text":"A"}]}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_captions(self.write(raw))

    def test_integer_time_safe_range_and_offset_overflow(self):
        for value in (True, 0.0, '0', -1, MAX_SAFE_INTEGER + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_captions(self.write(self.doc(startUs=value)))
        for offset in (True, 0.1, -1, MAX_SAFE_INTEGER):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                load_captions(self.write(self.doc()), offset_us=offset)

    def test_at_least_one_frame_duration_with_fractional_fps(self):
        path = self.write(self.doc(endUs=33333))
        with self.assertRaisesRegex(ValueError, 'one frame'):
            load_captions(path)
        self.assertEqual(load_captions(self.write(self.doc(endUs=33334)))[0]['endUs'], 33334)
        with self.assertRaisesRegex(ValueError, 'one frame'):
            load_captions(self.write(self.doc(endUs=33366)), fps=Fraction(30000, 1001))
        self.assertEqual(load_captions(self.write(self.doc(endUs=33367)), fps=Fraction(30000, 1001))[0]['endUs'], 33367)

    def test_invalid_fps_and_timeline_duration_rejected(self):
        path = self.write(self.doc())
        for fps in (True, '30', 0, -30, float('nan'), float('inf'), 1001, 10**999):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                load_captions(path, fps=fps)
        for duration in (0, True, 1.5, 999999):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                load_captions(path, timeline_duration_us=duration)

    def test_duplicate_ids_overlap_and_out_of_order_rejected(self):
        first = self.doc()['cues'][0]
        for second in ({**first, 'startUs': 1000000, 'endUs': 2000000},
                       {**first, 'id': 'c2', 'startUs': 999999, 'endUs': 2000000},
                       {**first, 'id': 'c2', 'startUs': 0, 'endUs': 500000}):
            with self.subTest(second=second), self.assertRaises(ValueError):
                load_captions(self.write({'timebase': 'timeline_us', 'cues': [first, second]}))

    def test_text_not_silently_truncated_and_controls_rejected(self):
        for text in ('', ' \t\n', 'a\0b', 'a\rb', 'a\x1bb', 'x' * (MAX_CUE_CHARS + 1)):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                load_captions(self.write(self.doc(text=text)))
        with self.assertRaises(ValueError):
            load_captions(self.write('{"timebase":"timeline_us","cues":[{"startUs":0,"endUs":1000000,"text":"\\ud800"}]}'))

    def test_file_cue_and_total_text_budgets(self):
        with self.assertRaisesRegex(ValueError, 'bytes'):
            load_captions(self.write(b' ' * (MAX_FILE_BYTES + 1)))
        cues = [{'startUs': n * 1000000, 'endUs': (n + 1) * 1000000, 'text': 'A'} for n in range(MAX_CUES + 1)]
        with self.assertRaisesRegex(ValueError, 'cues'):
            load_captions(self.write({'timebase': 'timeline_us', 'cues': cues}))
        cues = [{**c, 'text': 'x' * MAX_CUE_CHARS} for c in cues[:26]]
        with self.assertRaisesRegex(ValueError, 'total characters'):
            load_captions(self.write({'timebase': 'timeline_us', 'cues': cues}))

    def test_strict_encoding_empty_and_bad_srt(self):
        invalid = [b'\xff\xfe1\x00', b'', b'1\n00:00:00.000 --> 00:00:01,000\nA',
                   b'1\n00:61:00,000 --> 00:62:00,000\nA',
                   b'1\n00:00:00,000 --> 00:00:01,000\n',
                   b'1\n00:00:00,000 --> 00:00:01,000\nA\n2\n00:00:01,000 --> 00:00:02,000\nB']
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_captions(self.write(raw, '.srt'))

    def test_style_normalizes_colors_without_native_unit_claims(self):
        style = {'size': 64, 'color': '#ff00cC', 'font': 'SystemFont-01',
                 'outlineColor': '0x000000', 'outlineWidth': 0.08}
        self.assertEqual(normalize_style(style), {**style, 'color': '0xFF00CC'})
        self.assertEqual(style['color'], '#ff00cC')

    def test_style_rejects_unknown_fields_nonfinite_and_token_injection(self):
        for style in ({'positionX': 0}, {'size': True}, {'size': float('nan')},
                      {'size': 501}, {'size': 10**999}, {'outlineWidth': -1}, {'color': '#fff'},
                      {'font': 'Font --size 99'}, {'font': '--size'}, {'font': 'Font"'},
                      {'font': 'A\nB'}, {'font': 'A/B'}, []):
            with self.subTest(style=style), self.assertRaises(ValueError):
                normalize_style(style)


if __name__ == '__main__':
    unittest.main()
