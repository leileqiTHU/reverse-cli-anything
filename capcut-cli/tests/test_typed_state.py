"""Typed saved-state evidence and unrelated-content regression tests."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capcut_state import assert_unrelated, items_from_doc

ROOT = Path(__file__).resolve().parents[1]


def sample(name):
    path = Path(__file__).parent / 'fixtures' / (name + '.json')
    return json.loads(path.read_text(encoding='utf-8-sig'))['saved']


class TypedStateTests(unittest.TestCase):
    def test_audio_fade_and_gain_read_back_from_linked_material(self):
        item = next(i for i in items_from_doc(sample('audio-fade')) if i['type'] == 'audio')
        self.assertEqual(item['targetUs'], {'start': 1000000, 'duration': 3000000})
        self.assertEqual(item['properties']['fadeInUs'], 500000)
        self.assertEqual(item['properties']['fadeOutUs'], 500000)
        self.assertAlmostEqual(item['properties']['volumeLinear'], 10 ** (-12 / 20))
        self.assertEqual(item['properties']['speed'], 1)
        self.assertTrue(item['sourcePath'].endswith('.wav'))

    def test_rich_style_overrides_stale_flat_text_fields(self):
        doc = sample('caption-position')
        item = next(i for i in items_from_doc(doc) if i['type'] == 'text')
        material = next(m for m in doc['materials']['texts'] if m['id'] == item['materialId'])
        self.assertEqual(material['text_color'], '')
        self.assertEqual(item['properties']['style']['color'], '0xFFFF00')
        self.assertEqual(item['properties']['style']['outlineColor'], '0x000000')
        self.assertAlmostEqual(item['properties']['style']['outlineWidth'], .08)
        self.assertEqual(item['properties']['style']['size'], 64)
        self.assertEqual(item['properties']['text'], json.loads(material['content'])['text'])
        self.assertEqual(item['properties']['transform']['xRatio'], .1)
        self.assertEqual(item['properties']['transform']['yRatio'], -.5)
        self.assertIsNone(item['sourceUs'])

    def test_video_transform_and_crop_are_independent(self):
        item = next(i for i in items_from_doc(sample('video-crop')) if i['type'] == 'video')
        props = item['properties']
        self.assertEqual(props['transform'], {'scaleX': .65, 'scaleY': .7, 'rotationDeg': 0,
                                            'xRatio': .2, 'yRatio': -.1})
        self.assertEqual(props['opacity'], .8)
        for key, expected in {'left': .1, 'top': .1, 'right': .9, 'bottom': .9}.items():
            self.assertAlmostEqual(props['crop'][key], expected)

    def test_mixed_styles_do_not_claim_uniform_color(self):
        doc = sample('caption-position')
        material = doc['materials']['texts'][0]
        rich = json.loads(material['content'])
        second = copy.deepcopy(rich['styles'][0])
        second['fill']['content']['solid']['color'] = [1, 0, 0]
        rich['styles'].append(second)
        material['content'] = json.dumps(rich)
        props = next(i['properties'] for i in items_from_doc(doc) if i['type'] == 'text')
        self.assertIsNone(props['style']['color'])
        self.assertEqual(props['style']['size'], 64)
        self.assertEqual(len(props['richTextStyles']), 2)

    def test_returned_state_is_detached_and_rotated_crop_not_a_fake_box(self):
        doc = sample('video-crop')
        original = copy.deepcopy(doc)
        items_from_doc(doc)[0]['targetUs']['start'] = 999
        self.assertEqual(doc, original)
        doc['materials']['videos'][0]['crop']['upper_left_y'] = .2
        props = items_from_doc(doc)[0]['properties']
        self.assertIsNone(props['crop'])
        self.assertEqual(props['cropCorners']['upper_left_y'], .2)

    def test_unrelated_allows_native_bookkeeping_and_explicit_target_change(self):
        before = sample('caption-position')
        after = copy.deepcopy(before)
        target = after['tracks'][0]['segments'][0]
        target['volume'] = .4
        for track in after['tracks']:
            for segment in track['segments']:
                segment['track_render_index'] += 1
        after['tracks'].insert(0, {'id': 'new-track', 'type': 'audio', 'segments': []})
        self.assertTrue(assert_unrelated(before, after, [target['id']]))

    def test_unrelated_rejects_segment_resource_and_track_changes(self):
        before = sample('caption-position')
        changes = [lambda d: d['tracks'][0]['segments'][0].update(render_index=99),
                   lambda d: d['tracks'][0]['segments'][0]['target_timerange'].update(start=1),
                   lambda d: d['materials']['videos'][0].update(path='D:/different.mp4'),
                   lambda d: d['tracks'][0].update(attribute=99),
                   lambda d: d['tracks'][0].update(segments=[])]
        for mutate in changes:
            after = copy.deepcopy(before)
            mutate(after)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, 'Unrelated|unrelated'):
                assert_unrelated(before, after, [])

    def test_shared_material_of_changed_and_unchanged_clip_remains_protected(self):
        before = sample('video-crop')
        clone = copy.deepcopy(before['tracks'][0]['segments'][0])
        clone['id'] = 'untouched-copy'
        before['tracks'][0]['segments'].append(clone)
        after = copy.deepcopy(before)
        after['materials']['videos'][0]['crop']['upper_left_x'] = .3
        with self.assertRaisesRegex(ValueError, 'Material'):
            assert_unrelated(before, after, [before['tracks'][0]['segments'][0]['id']])


if __name__ == '__main__':
    unittest.main()
