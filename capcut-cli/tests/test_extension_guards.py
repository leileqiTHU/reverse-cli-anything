"""Extension preflight, native-boundary, and durable-receipt regression tests.

All native calls are fakes; temporary files and journals live under this D:
workspace. These tests never attach to or write to CapCut.
"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import capcut_extensions as ext

SID = '11111111-1111-4111-8111-111111111111'
SECOND = '22222222-2222-4222-8222-222222222222'
TID = 'AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA'


def document():
    return {'id': TID, 'duration': 1000000, 'fps': 30, 'render_index_track_mode_on': True,
            'tracks': [{'id': 'video-track', 'type': 'video', 'segments': [{
                'id': SID, 'material_id': 'video-material', 'render_index': 0, 'track_render_index': 0,
                'target_timerange': {'start': 0, 'duration': 1000000},
                'source_timerange': {'start': 0, 'duration': 1000000},
                'volume': 1., 'speed': 1., 'visible': True, 'reverse': False,
                'common_keyframes': [], 'keyframe_refs': [], 'extra_material_refs': [],
                'clip': {'scale': {'x': 1., 'y': 1.}, 'transform': {'x': 0., 'y': 0.},
                         'rotation': 0., 'alpha': 1.}}]}],
            'materials': {'videos': [{'id': 'video-material', 'path': 'D:/fixture.mp4', 'type': 'video'}]}}


class FakeNative:
    def __init__(self, doc, behaviors=None):
        self.doc = copy.deepcopy(doc)
        self.behaviors = behaviors or {}
        self.calls = []
        self.exports_sync = self

    def result(self, **kwargs):
        return {'sid': 81, 'summary': [{'generation': len(self.calls)}], **kwargs}

    def run(self, request):
        if request['action'] == 'inspect':
            return self.result()
        assert request['action'] == 'extension-step'
        argv = [bytes(value).decode('utf8') for value in request['argv_bytes']]
        self.calls.append(argv)
        behavior = self.behaviors.get(len(self.calls))
        if isinstance(behavior, Exception):
            raise behavior
        if callable(behavior):
            return behavior(self, argv)
        clip = self.doc['tracks'][0]['segments'][0]
        if argv[2] == 'volume':
            clip['volume'] = float(argv[-1])
        elif argv[2] == 'alpha':
            clip['clip']['alpha'] = float(argv[-1].rstrip('%')) / 100
        else:
            raise AssertionError('Unexpected fake command: ' + repr(argv))
        return self.result(native={'segment_ids': [], 'affected_segments': [SID]})

    def saved(self, request, summary):
        return copy.deepcopy(self.doc)


class ExtensionGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.runtime').mkdir()
        self.root_patch = patch.object(ext, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def request(self, **changes):
        return {'action': 'set-clip', 'pid': 1234, 'project': str(self.root / 'project'),
                'timeline_id': TID, 'request_id': 'test-request', 'segment_id': SID,
                'patch': {'volumeLinear': .5}, 'deadline_monotonic': time.monotonic() + 60, **changes}

    def receipt(self, request_id='test-request'):
        return json.loads((self.root / '.runtime/mutations' / (request_id + '.json')).read_text(encoding='utf8'))

    def json_file(self, value, name='input.json'):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')
        return str(path)

    def caption_args(self, **changes):
        return SimpleNamespace(editor_action='captions-import', request_id='captions', format='json',
                               offset_us=0, input=self.json_file({'timebase': 'timeline_us', 'cues': [
                                   {'id': 'a', 'startUs': 0, 'endUs': 500000, 'text': '中文 😀'}]}),
                               **{'style': None, **changes})

    def test_secondary_literal_keeps_newlines_and_escapes_quotes_backslashes(self):
        text = '中文 "quote" \\path --action remove\n😀\tend'
        literal = ext.content_literal(text)
        self.assertEqual(literal, '"中文 \\"quote\\" \\\\path --action remove\n😀\tend"')
        self.assertIn('\n', literal)
        self.assertNotIn('\\n', literal)
        self.assertEqual(ext.content_literal('--seg-id'), '"--seg-id"')

    def test_property_expected_preserves_omitted_axes_and_normalizes_gain(self):
        old = {'transform': {'scaleX': 1, 'scaleY': 2, 'xRatio': .1, 'yRatio': -.2},
               'volumeLinear': 1, 'opacity': .8, 'cropCorners': {'raw': True}}
        result = ext.property_expected({'transform': {'scaleX': .5}, 'gainDb': -6}, old)
        self.assertEqual(result['transform'], {**old['transform'], 'scaleX': .5})
        self.assertAlmostEqual(result['volumeLinear'], 10 ** (-6 / 20))
        self.assertEqual(old['transform']['scaleX'], 1)
        self.assertNotIn('gainDb', result)
        self.assertNotIn('cropCorners', ext.property_expected({'crop': {'left': .1}}, old))

    def test_prepare_captions_defaults_and_explicit_native_positions(self):
        style = self.json_file({'size': 9, 'color': '#00ff00', 'yRatio': -.5}, 'style.json')
        request = ext.prepare(self.caption_args(style=style), document())
        self.assertEqual(request['cues'][0]['text'], '中文 😀')
        self.assertEqual(request['style']['color'], '0x00FF00')
        self.assertEqual(request['position'], {'xRatio': 0, 'yRatio': -.5})

    def test_prepare_style_rejects_nonobject_and_large_coordinate_cleanly(self):
        for style in ([], None, 42, {'xRatio': 10**999}):
            with self.subTest(style=style), self.assertRaises(ValueError):
                ext.prepare(self.caption_args(style=self.json_file(style, 'style.json')), document())

    def test_prepare_rejects_unknown_style_font_and_bad_request_id(self):
        for style in ({'unknown': 3}, {'font': 'Arial'}, {'xRatio': 2}):
            with self.subTest(style=style), self.assertRaises(ValueError):
                ext.prepare(self.caption_args(style=self.json_file(style, 'style.json')), document())
        args = self.caption_args()
        args.request_id = '../escape'
        with self.assertRaisesRegex(ValueError, 'request-id'):
            ext.prepare(args, document())

    def test_preflight_keyframes_rejected_without_a_native_write(self):
        doc = document()
        doc['tracks'][0]['segments'][0]['common_keyframes'] = [{'id': 'animation'}]
        native = FakeNative(doc)
        with self.assertRaises(ext.MutationError) as caught:
            ext.execute_extension(self.request(), native, native.saved)
        self.assertEqual(native.calls, [])
        self.assertEqual(caught.exception.details['outcome'], 'not-applied')
        self.assertEqual(self.receipt()['completedSteps'], [])

    def test_success_request_replay_performs_no_second_native_mutation(self):
        native = FakeNative(document())
        request = self.request()
        first = ext.execute_extension(request, native, native.saved)
        replay = ext.execute_extension(request, native, native.saved)
        self.assertFalse(first['replayed'])
        self.assertTrue(replay['replayed'])
        self.assertEqual(len(native.calls), 1)
        self.assertEqual(self.receipt()['outcome'], 'success')

    def test_request_id_collision_and_modified_poststate_reject_replay(self):
        native = FakeNative(document())
        ext.execute_extension(self.request(), native, native.saved)
        with self.assertRaisesRegex(ValueError, 'different parameters'):
            ext.execute_extension(self.request(patch={'volumeLinear': .25}), native, native.saved)
        native.doc['tracks'][0]['segments'][0]['visible'] = False
        with self.assertRaises(ext.MutationError):
            ext.execute_extension(self.request(), native, native.saved)
        self.assertEqual(len(native.calls), 1)

    def test_transport_exception_keeps_unknown_receipt_and_pid_lock(self):
        native = FakeNative(document(), {1: RuntimeError('native transport lost')})
        with self.assertRaises(ext.MutationError) as caught:
            ext.execute_extension(self.request(), native, native.saved)
        self.assertTrue(caught.exception.preserve_pid_lock)
        self.assertEqual(caught.exception.details['outcome'], 'unknown')
        self.assertFalse(caught.exception.details['retryAllowed'])
        self.assertEqual(self.receipt()['pendingStep'][:3], ['draft', 'video', 'volume'])

    def test_replay_tolerates_native_identity_cache_and_project_folder_rename(self):
        native=FakeNative(document())
        req=self.request(project_id='stable-project')
        ext.execute_extension(req,native,native.saved)
        native.doc['materials']['videos'][0]['unique_id']='native-cache-id'
        replay=ext.execute_extension({**req,'project':'D:/renamed-project'},native,native.saved)
        self.assertTrue(replay['replayed'])
        self.assertEqual(len(native.calls),1)

    def test_second_command_rejection_reports_partial_without_blind_retry(self):
        native = FakeNative(document(), {2: lambda engine, argv: engine.result(nativeError='rejected')})
        with self.assertRaises(ext.MutationError) as caught:
            ext.execute_extension(self.request(patch={'opacity': .8, 'volumeLinear': .5}), native, native.saved)
        self.assertFalse(caught.exception.preserve_pid_lock)
        self.assertEqual(caught.exception.details['outcome'], 'partially-applied')
        self.assertEqual(caught.exception.details['completedSteps'], 1)
        self.assertEqual(native.doc['tracks'][0]['segments'][0]['clip']['alpha'], .8)
        self.assertFalse(caught.exception.details['retryAllowed'])

    def test_native_error_with_observed_mutation_stays_unknown(self):
        def change_then_error(engine, argv):
            engine.doc['tracks'][0]['segments'][0]['volume'] = .7
            return engine.result(nativeError='handler raised after modifying state')
        native = FakeNative(document(), {1: change_then_error})
        with self.assertRaises(ext.MutationError) as caught:
            ext.execute_extension(self.request(), native, native.saved)
        self.assertEqual(caught.exception.details['outcome'], 'unknown')
        self.assertTrue(caught.exception.preserve_pid_lock)

    def test_unrelated_clip_mutation_cannot_be_reported_as_success(self):
        doc = document()
        second = copy.deepcopy(doc['tracks'][0]['segments'][0])
        second['id'] = SECOND
        doc['tracks'][0]['segments'].append(second)
        def change_both(engine, argv):
            engine.doc['tracks'][0]['segments'][0]['volume'] = .5
            engine.doc['tracks'][0]['segments'][1]['visible'] = False
            return engine.result(native={'segment_ids': [], 'affected_segments': [SID]})
        native = FakeNative(doc, {1: change_both})
        with self.assertRaises(ext.MutationError) as caught:
            ext.execute_extension(self.request(), native, native.saved)
        self.assertEqual(caught.exception.details['outcome'], 'partially-applied')
        self.assertIn('Unrelated', str(caught.exception))

    def test_unrequested_target_property_mutation_cannot_be_reported_as_success(self):
        def unexpected_target_change(engine, argv):
            engine.doc['tracks'][0]['segments'][0].update(volume=.5, visible=False)
            return engine.result(native={'segment_ids': [], 'affected_segments': [SID]})
        native = FakeNative(document(), {1: unexpected_target_change})
        with self.assertRaises(ext.MutationError):
            ext.execute_extension(self.request(), native, native.saved)

    def test_target_invariant_allows_volume_bookkeeping_but_preserves_other_axes(self):
        before = document()
        after = copy.deepcopy(before)
        after['tracks'][0]['segments'][0].update(volume=.5, last_nonzero_volume=.5)
        ext.verify_target_preserved(before, after, SID, {'volumeLinear': .5})
        after = copy.deepcopy(before)
        after['tracks'][0]['segments'][0]['clip']['scale']['x'] = .5
        after['tracks'][0]['segments'][0]['uniform_scale'] = {'on': False, 'value': .5}
        ext.verify_target_preserved(before, after, SID, {'transform': {'scaleX': .5}})
        after['tracks'][0]['segments'][0]['clip']['scale']['y'] = .25
        with self.assertRaises(ValueError):
            ext.verify_target_preserved(before, after, SID, {'transform': {'scaleX': .5}})

    def test_target_invariant_crop_does_not_permit_media_replacement(self):
        before = document()
        after = copy.deepcopy(before)
        after['materials']['videos'][0]['crop'] = {'upper_left_x': .1}
        after['materials']['videos'][0]['crop_ratio'] = 'free'
        patch_value = {'crop': {'left': .1, 'top': .1, 'right': .9, 'bottom': .9}}
        ext.verify_target_preserved(before, after, SID, patch_value)
        after['materials']['videos'][0]['path'] = 'D:/unexpected-replacement.mp4'
        with self.assertRaises(ValueError):
            ext.verify_target_preserved(before, after, SID, patch_value)

    def test_target_invariant_rejects_track_reassignment_or_metadata_changes(self):
        before = document()
        for change in ({'id': 'different-track'}, {'attribute': 99}, {'name': 'unexpected'}):
            after = copy.deepcopy(before)
            after['tracks'][0]['segments'][0]['volume'] = .5
            after['tracks'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                ext.verify_target_preserved(before, after, SID, {'volumeLinear': .5})

    def test_target_invariant_accepts_only_audio_fade_ref_changes(self):
        before = document()
        before['tracks'][0]['type'] = 'audio'
        after = copy.deepcopy(before)
        after['materials']['audio_fades'] = [{'id': 'fade', 'type': 'audio_fade',
                                            'fade_in_duration': 100000, 'fade_out_duration': 0}]
        after['tracks'][0]['segments'][0]['extra_material_refs'].append('fade')
        ext.verify_target_preserved(before, after, SID, {'fadeInUs': 100000})
        after['materials']['effects'] = [{'id': 'effect', 'type': 'audio_effect'}]
        after['tracks'][0]['segments'][0]['extra_material_refs'].append('effect')
        with self.assertRaises(ValueError):
            ext.verify_target_preserved(before, after, SID, {'fadeInUs': 100000})

    def test_retry_allowed_is_consistent_with_same_id_retry_behavior(self):
        native = FakeNative(document(), {1: lambda engine, argv: engine.result(nativeError='rejected')})
        with self.assertRaises(ext.MutationError) as first:
            ext.execute_extension(self.request(), native, native.saved)
        first_retry_allowed = first.exception.details['retryAllowed']
        native.behaviors = {}
        if first_retry_allowed:
            result = ext.execute_extension(self.request(), native, native.saved)
            self.assertTrue(result['persistenceVerified'])
        else:
            with self.assertRaises(ext.MutationError):
                ext.execute_extension(self.request(), native, native.saved)
            self.assertEqual(len(native.calls), 1)


if __name__ == '__main__':
    unittest.main()
