"""Boundary and persisted-outcome checks, without attaching to a real editor."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capcut_agent import CliError, parse_args
from capcut_editor_worker import saved_matching, timeline_signature, validate_clip_edit, verify_clip_edit

SID = '40B3CE3F-F551-49DA-BBDA-40599BD74679'


def draft():
    return {'id': 'timeline', 'fps': 30, 'tracks': [{'type': 'video', 'segments': [{
        'id': SID, 'material_id': 'video', 'speed': 1, 'render_index': 0,
        'target_timerange': {'start': 0, 'duration': 3000000},
        'source_timerange': {'start': 0, 'duration': 3000000}}]}]}


class GuardTests(unittest.TestCase):
    def test_switch_signature_detects_loss_even_when_live_and_saved_agree(self):
        before = draft()
        before['tracks'][0]['id'] = 'track'
        after = copy.deepcopy(before)
        after['tracks'][0]['segments'] = []
        self.assertNotEqual(timeline_signature(before), timeline_signature(after))

    def test_switch_requires_explicit_target(self):
        with self.assertRaises(CliError):
            parse_args(['editor', 'switch-timeline', '--pid', '123', '--project', 'fixture'])

    def test_wrong_segment_and_retimed_trim_rejected(self):
        doc = draft()
        req = {'action': 'trim', 'segment_id': 'other', 'in_us': 0, 'out_us': 1000000}
        with self.assertRaisesRegex(ValueError, 'not in'):
            validate_clip_edit(req, doc)
        req['segment_id'] = SID
        doc['tracks'][0]['segments'][0]['speed'] = 2
        with self.assertRaisesRegex(ValueError, 'speed 1'):
            validate_clip_edit(req, doc)

    def test_trim_cannot_extend_beyond_source_or_keep_subframe(self):
        for start, end in ((0, 4000000), (0, 1), (-1, 1000000)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validate_clip_edit({'action': 'trim', 'segment_id': SID, 'in_us': start, 'out_us': end}, draft())

    def test_split_cannot_make_empty_or_subframe_part(self):
        for points in ([0], [3000000], [2999999], [500000, 500001]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                validate_clip_edit({'action': 'split', 'segment_id': SID, 'points_us': points}, draft())

    def test_saved_check_rejects_stale_timing_with_unchanged_ids(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            path = Path(tmp) / 'Timelines/timeline'
            path.mkdir(parents=True)
            (path / 'draft_content.json').write_text(json.dumps(draft()), encoding='utf8')
            summary = [{'type': 'track', 'attributes': {'segments': [SID]}},
                       {'id': SID, 'type': 'video', 'timeline': {'start.ms': 1000, 'duration.ms': 3000}}]
            with patch('capcut_editor_worker.time.monotonic', side_effect=[0, 9]):
                with self.assertRaisesRegex(ValueError, 'did not converge'):
                    saved_matching({'project': tmp, 'timeline_id': 'timeline'}, summary)

    def test_trim_checks_source_offset_not_just_target_duration(self):
        before = draft()
        previous = before['tracks'][0]['segments'][0]
        after = copy.deepcopy(before)
        clip = after['tracks'][0]['segments'][0]
        clip['target_timerange'] = {'start': 500000, 'duration': 2000000}
        clip['source_timerange'] = {'start': 0, 'duration': 2000000}
        req = {'action': 'trim', 'in_us': 500000, 'out_us': 2500000}
        with self.assertRaisesRegex(ValueError, 'not verified'):
            verify_clip_edit(req, previous, before, after)
        clip['source_timerange']['start'] = 500000
        verify_clip_edit(req, previous, before, after)

    def test_remove_requires_only_target_id_to_disappear(self):
        before = draft()
        extra = copy.deepcopy(before['tracks'][0]['segments'][0])
        extra['id'] = 'another'
        before['tracks'][0]['segments'].append(extra)
        after = copy.deepcopy(before)
        after['tracks'][0]['segments'] = []
        with self.assertRaises(ValueError):
            verify_clip_edit({'action': 'remove'}, before['tracks'][0]['segments'][0], before, after)

    def test_split_accepts_cloned_material_but_rejects_changed_source(self):
        before = draft()
        before['materials'] = {'videos': [{'id': 'video', 'path': 'D:/fixture.mp4',
                                           'width': 320, 'height': 180, 'duration': 3000000}]}
        previous = before['tracks'][0]['segments'][0]
        after = copy.deepcopy(before)
        left = after['tracks'][0]['segments'][0]
        right = copy.deepcopy(left)
        left['target_timerange']['duration'] = left['source_timerange']['duration'] = 1000000
        right.update(id='second', material_id='cloned-video',
                     target_timerange={'start': 1000000, 'duration': 2000000},
                     source_timerange={'start': 1000000, 'duration': 2000000})
        after['tracks'][0]['segments'].append(right)
        cloned = {**before['materials']['videos'][0], 'id': 'cloned-video'}
        after['materials']['videos'].append(cloned)
        request = {'action': 'split', 'points_us': [1000000]}
        verify_clip_edit(request, previous, before, after)
        cloned['path'] = 'D:/different-video.mp4'
        with self.assertRaisesRegex(ValueError, 'not verified'):
            verify_clip_edit(request, previous, before, after)


if __name__ == '__main__':
    unittest.main()
