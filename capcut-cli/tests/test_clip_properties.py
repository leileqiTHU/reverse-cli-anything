"""No CapCut attachment: reject unsafe or ambiguous set-clip requests."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capcut_clip_properties import (MAX_PATCH_BYTES, build_property_commands,
                                    changed_fields, load_patch_file,
                                    normalize_patch, validate_fade_window)

SID = '40B3CE3F-F551-49DA-BBDA-40599BD74679'


class ClipPatchTests(unittest.TestCase):
    def test_valid_patch_is_detached_and_keeps_omitted_properties_absent(self):
        raw = {'transform': {'scaleX': 0.65}, 'opacity': 0.8}
        previous = copy.deepcopy(raw)
        normalized = normalize_patch(raw, 'video')
        self.assertEqual(normalized, raw)
        normalized['transform']['scaleX'] = 1
        self.assertEqual(raw, previous)
        self.assertNotIn('scaleY', normalized['transform'])

    def test_unknown_fields_reject_whole_patch(self):
        for raw in ({'opacity': 0.8, 'delete': True},
                    {'transform': {'scaleX': 1, 'raw': '--seg-id all'}},
                    {'crop': {'left': 0, 'top': 0, 'right': 1, 'bottom': 1, 'rotation': 5}}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                build_property_commands(raw, 'video', SID)

    def test_malformed_and_empty_objects_rejected(self):
        for raw in (None, [], 'opacity=1', {}, {'transform': {}}, {1: 0}, {'crop': []}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                normalize_patch(raw, 'video')

    def test_numbers_are_absolute_finite_and_not_booleans(self):
        for value in (True, False, None, '0.5', '+=0.5', '1.2x', '50%',
                      '0.5 --seg-id all', float('nan'), float('inf'), -float('inf'), 10**1000):
            with self.subTest(value=repr(value)[:50]), self.assertRaises(ValueError):
                normalize_patch({'opacity': value}, 'video')

    def test_conservative_boundaries(self):
        for raw in ({'opacity': -0.01}, {'opacity': 1.01}, {'volumeLinear': 4.01},
                    {'gainDb': 12.01}, {'gainDb': -97}, {'speed': 0},
                    {'transform': {'scaleX': 0}}, {'transform': {'scaleY': 11}},
                    {'transform': {'rotationDeg': 361}}, {'transform': {'xRatio': 2.01}}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                normalize_patch(raw, 'video')
        self.assertEqual(normalize_patch({'opacity': 0, 'volumeLinear': 0}, 'video'),
                         {'opacity': 0.0, 'volumeLinear': 0.0})

    def test_segment_types_have_distinct_whitelists(self):
        for segment_type, patch in (('text', {'opacity': 1}), ('audio', {'speed': 2}),
                                    ('audio', {'transform': {'scaleX': 1}}),
                                    ('video', {'fadeInUs': 500000})):
            with self.subTest(segment_type=segment_type, patch=patch), self.assertRaises(ValueError):
                normalize_patch(patch, segment_type)

    def test_volume_units_cannot_conflict(self):
        for segment_type in ('video', 'audio'):
            with self.assertRaisesRegex(ValueError, 'mutually exclusive'):
                normalize_patch({'gainDb': -6, 'volumeLinear': 0.5}, segment_type)

    def test_crop_requires_complete_nonempty_normalized_box(self):
        for box in ({'left': 0}, {'left': 0.5, 'top': 0, 'right': 0.5, 'bottom': 1},
                    {'left': 0, 'top': 1, 'right': 1, 'bottom': 0},
                    {'left': -0.1, 'top': 0, 'right': 1, 'bottom': 1}):
            with self.subTest(box=box), self.assertRaises(ValueError):
                normalize_patch({'crop': box}, 'video')

    def test_untrusted_ids_never_become_command_tokens(self):
        for sid in ('all', SID + ' --speed 3', SID + '\n', '"' + SID + '"', None):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                build_property_commands({'opacity': 1}, 'video', sid)

    def test_native_mapping_is_explicit_without_claiming_calibration(self):
        plans = build_property_commands({
            'transform': {'scaleX': 0.65, 'rotationDeg': -90, 'xRatio': 0.1, 'yRatio': -0.2},
            'opacity': 0.8,
            'crop': {'left': 0.1, 'top': 0.2, 'right': 0.9, 'bottom': 0.8},
        }, 'video', SID)
        by_name = {plan['operation']: plan for plan in plans}
        self.assertEqual(by_name['translate']['argv'][-4:], ['--x', '10%', '--y', '-20%'])
        self.assertEqual(by_name['alpha']['argv'][-2:], ['--alpha', '80%'])
        self.assertEqual(by_name['crop']['argv'][-2:], ['--box', '<10%,20%,90%,80%>'])
        self.assertEqual(by_name['scale']['argv'][-2:], ['--x', '0.65'])
        self.assertNotIn('--y', by_name['scale']['argv'])
        self.assertIn('omitted-axis-preservation', by_name['scale']['requires'])
        self.assertIn('geometry-calibration', by_name['translate']['requires'])

    def test_constant_speed_needs_explicit_runtime_gate(self):
        self.assertEqual(normalize_patch({'speed': 2}, 'video'), {'speed': 2.0})
        with self.assertRaisesRegex(ValueError, 'runtime isolation'):
            build_property_commands({'opacity': 0.8, 'speed': 2}, 'video', SID)
        plans = build_property_commands({'speed': 2}, 'video', SID, allow_speed=True)
        self.assertEqual(plans[0]['argv'][-2:], ['--speed', '2'])
        self.assertIn('neighbor-preservation', plans[0]['requires'])

    def test_gain_preserves_requested_unit(self):
        plans = build_property_commands({'gainDb': -12}, 'audio', SID)
        self.assertEqual(plans[0]['argv'], ['draft', 'audio', 'volume', '--seg-id', SID, '--db', '-12'])

    def test_fades_have_integer_microseconds_and_retained_side_validation(self):
        for value in (1.0, True, -1, '500000us', math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_patch({'fadeInUs': value}, 'audio')
        plans = build_property_commands({'fadeInUs': 500000, 'fadeOutUs': 1000000}, 'audio', SID)
        self.assertEqual(plans[0]['argv'][-4:], ['--in', '500000us', '--out', '1000000us'])
        self.assertEqual(validate_fade_window({'fadeInUs': 500000}, 1500000,
                                             current_fade_out_us=1000000),
                         {'fadeInUs': 500000, 'fadeOutUs': 1000000})
        with self.assertRaisesRegex(ValueError, 'Combined'):
            validate_fade_window({'fadeInUs': 500000}, 1400000, current_fade_out_us=1000000)

    def test_changed_fields_are_leaves(self):
        self.assertEqual(changed_fields({'opacity': 0.8, 'transform': {'scaleX': 0.7, 'yRatio': 0}},
                                        'video'), ['opacity', 'transform.scaleX', 'transform.yRatio'])

    def test_bounded_file_read_rejects_duplicates_nonfinite_and_bad_encodings(self):
        bad = (b'{"opacity":1,"opacity":0}', b'{"transform":{"scaleX":1,"scaleX":2}}',
               b'{"opacity":NaN}', b'{"opacity":1e999}', b'\xff', b'{',
               b' ' * (MAX_PATCH_BYTES + 1))
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / 'patch.json'
            for data in bad:
                path.write_bytes(data)
                with self.subTest(data=data[:40]), self.assertRaises(ValueError):
                    load_patch_file(path, 'video')
            path.write_bytes(b'\xef\xbb\xbf{"opacity":0.8}\r\n')
            self.assertEqual(load_patch_file(path, 'video'), {'opacity': 0.8})


if __name__ == '__main__':
    unittest.main()
