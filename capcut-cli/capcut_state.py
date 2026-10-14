"""Typed readback of saved CapCut documents, not an independent live-state probe.

Times retain the saved integer-microsecond {start, duration} representation.
Transform x/y retain native saved coordinates (positive y points up); public
coordinate conversion belongs to the caller. No guessed native summary units
or user-interface font-size units are introduced here.
"""
import copy
import json
import math


def _materials(doc):
    result = {}
    for collection, values in doc.get('materials', {}).items():
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict) and value.get('id'):
                key = value['id'].upper()
                if key in result and result[key][1] != value:
                    raise ValueError(f'Ambiguous duplicate material ID: {value["id"]}')
                result[key] = (collection, value)
    return result


def _material(index, material_id):
    return index.get(str(material_id).upper(), (None, {}))[1]


def _rgb(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in value)):
        return None
    return '0x' + ''.join(f'{round(v * 255):02X}' for v in value)


def _solid_color(value):
    if not isinstance(value, dict):
        return None
    content = value.get('content', {})
    if content.get('render_type') != 'solid':
        return None
    return _rgb(content.get('solid', {}).get('color'))


def _font(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return next((value.get(k) for k in ('resource_id', 'id', 'name', 'path') if value.get(k)), None)
    return None


def _text_properties(material):
    content = material.get('content')
    if isinstance(content, str):
        try:
            rich = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Malformed saved rich text content in material {material.get("id")}') from exc
    elif isinstance(content, dict):
        rich = content
    elif content is None:
        rich = {}
    else:
        raise ValueError(f'Unsupported saved text content in material {material.get("id")}')
    if not isinstance(rich, dict):
        raise ValueError(f'Saved rich text content is not an object in material {material.get("id")}')
    runs = rich.get('styles', [])
    if not isinstance(runs, list) or any(not isinstance(run, dict) for run in runs):
        raise ValueError(f'Malformed saved rich text styles in material {material.get("id")}')
    base = {'size': material.get('font_size'), 'color': material.get('text_color') or None,
            'outlineColor': material.get('border_color') or None,
            'outlineWidth': material.get('border_width'),
            'font': next((material.get(k) for k in ('font_resource_id', 'font_id', 'font_name') if material.get(k)), None)}
    effective_runs = []
    for run in runs:
        effective = dict(base)
        if 'size' in run:
            effective['size'] = run['size']
        if 'fill' in run:
            effective['color'] = _solid_color(run['fill'])
        if 'font' in run:
            effective['font'] = _font(run['font'])
        if 'strokes' in run:
            strokes = run['strokes']
            if isinstance(strokes, list) and len(strokes) == 1 and isinstance(strokes[0], dict):
                effective['outlineColor'] = _solid_color(strokes[0])
                effective['outlineWidth'] = strokes[0].get('width')
            elif strokes == []:
                effective['outlineColor'], effective['outlineWidth'] = None, 0
            else:
                effective['outlineColor'], effective['outlineWidth'] = None, None
        effective_runs.append(effective)
    # A mixed rich-text run is not a uniform style. Keep the complete raw runs
    # and report None for conflicting scalar values instead of choosing run 0.
    style = dict(base)
    if effective_runs:
        style = {key: values[0] if all(v == values[0] for v in values) else None
                 for key in base for values in [[run[key] for run in effective_runs]]}
    return {'text': rich.get('text'), 'style': style,
            'richTextStyles': copy.deepcopy(runs), 'textType': material.get('type')}


def _transform(clip):
    if not isinstance(clip, dict):
        return None
    scale, position = clip.get('scale') or {}, clip.get('transform') or {}
    return {'scaleX': scale.get('x'), 'scaleY': scale.get('y'),
            'rotationDeg': clip.get('rotation'), 'xRatio': position.get('x'), 'yRatio': position.get('y')}


def _crop(corners):
    if not isinstance(corners, dict):
        return None
    keys = ('upper_left_x', 'upper_left_y', 'upper_right_x', 'upper_right_y',
            'lower_left_x', 'lower_left_y', 'lower_right_x', 'lower_right_y')
    if any(not isinstance(corners.get(k), (int, float)) or isinstance(corners[k], bool)
           or not math.isfinite(corners[k]) for k in keys):
        return None
    if not (math.isclose(corners['upper_left_x'], corners['lower_left_x'], abs_tol=1e-9)
            and math.isclose(corners['upper_right_x'], corners['lower_right_x'], abs_tol=1e-9)
            and math.isclose(corners['upper_left_y'], corners['upper_right_y'], abs_tol=1e-9)
            and math.isclose(corners['lower_left_y'], corners['lower_right_y'], abs_tol=1e-9)):
        return None
    return {'left': corners['upper_left_x'], 'top': corners['upper_left_y'],
            'right': corners['lower_right_x'], 'bottom': corners['lower_right_y']}


def items_from_doc(doc):
    """Return typed saved items with linked material properties, without mutation."""
    index = _materials(doc)
    result = []
    for track_index, track in enumerate(doc.get('tracks', [])):
        kind = track.get('type')
        for segment in track.get('segments', []):
            material = _material(index, segment.get('material_id'))
            props = {}
            if kind in ('video', 'audio'):
                props.update(volumeLinear=segment.get('volume'), speed=segment.get('speed'))
            if kind == 'audio':
                fades = [_material(index, ref) for ref in segment.get('extra_material_refs', [])
                         if index.get(str(ref).upper(), (None,))[0] == 'audio_fades']
                if len(fades) > 1:
                    raise ValueError(f'Ambiguous multiple audio fades for segment {segment.get("id")}')
                fade = fades[0] if fades else {}
                props.update(fadeInUs=fade.get('fade_in_duration', 0), fadeOutUs=fade.get('fade_out_duration', 0))
            if kind in ('video', 'text'):
                props['transform'] = _transform(segment.get('clip'))
                props['opacity'] = (segment.get('clip') or {}).get('alpha')
            if kind == 'video':
                props['crop'] = _crop(material.get('crop'))
                props['cropCorners'] = copy.deepcopy(material.get('crop'))
            if kind == 'text':
                props.update(_text_properties(material))
            result.append({'id': segment.get('id'), 'type': kind, 'trackId': track.get('id'),
                           'storedTrackIndex': track_index, 'renderIndex': segment.get('render_index'),
                           'materialId': segment.get('material_id'),
                           'targetUs': copy.deepcopy(segment.get('target_timerange')),
                           'sourceUs': copy.deepcopy(segment.get('source_timerange')),
                           'sourcePath': material.get('path') or None, 'properties': props})
    return result


def _segment_index(doc):
    result = {}
    for track in doc.get('tracks', []):
        for segment in track.get('segments', []):
            sid = str(segment.get('id')).upper()
            if sid in result:
                raise ValueError(f'Duplicate saved segment ID: {segment.get("id")}')
            result[sid] = (track, segment)
    return result


def _without_render_index(value):
    # Only this top-level bookkeeping field is excluded. render_index, timing,
    # keyframes and every other actual segment/track value remain significant.
    return {key: val for key, val in value.items() if key != 'track_render_index'}


def assert_unrelated(before, after, changed_ids):
    """Raise if any pre-existing unrelated segment or its resources changed.

    New segments/tracks/materials are allowed. Existing track metadata remains
    unchanged where an unaffected segment lives; list positions may shift when
    native code inserts a track. A shared material is protected if even one
    untouched segment references it. The helper does not verify target changes
    or overall timeline duration; those are the operation's postconditions.
    """
    changed = {str(sid).upper() for sid in changed_ids}
    old_segments, new_segments = _segment_index(before), _segment_index(after)
    old_materials, new_materials = _materials(before), _materials(after)
    for sid, (track, segment) in old_segments.items():
        if sid in changed:
            continue
        if sid not in new_segments:
            raise ValueError(f'Unrelated segment disappeared: {segment.get("id")}')
        new_track, new_segment = new_segments[sid]
        if str(track.get('id')).upper() != str(new_track.get('id')).upper():
            raise ValueError(f'Unrelated segment changed track: {segment.get("id")}')
        if _without_render_index(segment) != _without_render_index(new_segment):
            raise ValueError(f'Unrelated segment content changed: {segment.get("id")}')
        old_track_meta = {k: v for k, v in track.items() if k != 'segments'}
        new_track_meta = {k: v for k, v in new_track.items() if k != 'segments'}
        if _without_render_index(old_track_meta) != _without_render_index(new_track_meta):
            raise ValueError(f'Unrelated track metadata changed: {track.get("id")}')
        refs = [segment.get('material_id'), *segment.get('extra_material_refs', [])]
        for ref in refs:
            if ref is None:
                continue
            key = str(ref).upper()
            if old_materials.get(key) != new_materials.get(key):
                raise ValueError(f'Material referenced by unrelated segment changed: {ref}')
    return True
