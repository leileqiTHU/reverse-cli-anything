"""Strict, side-effect-free contracts for ``editor set-clip``.

Command plans describe the syntax recovered from CapCut's native help. They do
not establish that a handler works in the current editor session. The caller
must check native capabilities, target identity, keyframes, geometry calibration,
save convergence and rendered results before advertising a property as supported.

Values are absolute. Ratios become native percent tokens, not pixels; geometric
origin/direction must be calibrated by the native adapter. No shell is involved.
"""
import json
import math
from pathlib import Path
import re


MAX_PATCH_BYTES = 16384
MAX_FADE_US = 12 * 60 * 60 * 1_000_000
_UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
_TRANSFORM_FIELDS = {'scaleX', 'scaleY', 'rotationDeg', 'xRatio', 'yRatio'}
_CROP_FIELDS = {'left', 'top', 'right', 'bottom'}
_ALLOWED = {
    'video': {'transform', 'crop', 'opacity', 'volumeLinear', 'gainDb', 'speed'},
    'audio': {'volumeLinear', 'gainDb', 'fadeInUs', 'fadeOutUs'},
}


def _object(value, label, allowed, *, required=None):
    if not isinstance(value, dict) or not value:
        raise ValueError(f'{label} must be a nonempty JSON object')
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f'{label} keys must be strings')
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f'{label} has unsupported fields: {", ".join(sorted(unknown))}')
    if required is not None and set(value) != required:
        raise ValueError(f'{label} requires all of: {", ".join(sorted(required))}')


def _number(value, label, low, high, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be an absolute finite number')
    # Comparing bounded integers before converting also rejects huge Python ints
    # without raising OverflowError inside math.isfinite or float conversion.
    if not low <= value <= high or not math.isfinite(value):
        raise ValueError(f'{label} must be between {low} and {high}')
    if integer and not isinstance(value, int):
        raise ValueError(f'{label} must be an integer in microseconds')
    return value if integer else float(value)


def normalize_patch(patch, segment_type):
    """Validate the entire patch before native writes, returning a detached dict.

    Omitted fields remain absent, including individual transform axes. A crop is
    deliberately a complete box because its native setter requires four edges.
    ``speed`` is syntactically validated here; executing it is separately gated.
    Conservative first-version bounds are part of this wrapper's contract, not
    claims about the full native UI range.
    """
    if segment_type not in _ALLOWED:
        raise ValueError('set-clip supports video or audio segments only')
    _object(patch, 'patch', _ALLOWED[segment_type])
    if 'volumeLinear' in patch and 'gainDb' in patch:
        raise ValueError('volumeLinear and gainDb are mutually exclusive')
    result = {}
    for key, value in patch.items():
        if key == 'transform':
            _object(value, 'transform', _TRANSFORM_FIELDS)
            ranges = {'scaleX': (0.01, 10), 'scaleY': (0.01, 10),
                      'rotationDeg': (-360, 360), 'xRatio': (-2, 2), 'yRatio': (-2, 2)}
            result[key] = {name: _number(item, f'transform.{name}', *ranges[name])
                           for name, item in value.items()}
        elif key == 'crop':
            _object(value, 'crop', _CROP_FIELDS, required=_CROP_FIELDS)
            box = {name: _number(value[name], f'crop.{name}', 0, 1)
                   for name in ('left', 'top', 'right', 'bottom')}
            if box['left'] >= box['right'] or box['top'] >= box['bottom']:
                raise ValueError('crop requires left < right and top < bottom')
            result[key] = box
        elif key in ('fadeInUs', 'fadeOutUs'):
            result[key] = _number(value, key, 0, MAX_FADE_US, integer=True)
        else:
            ranges = {'opacity': (0, 1), 'volumeLinear': (0, 4),
                      'gainDb': (-96, 12), 'speed': (0.1, 10)}
            result[key] = _number(value, key, *ranges[key])
    return result


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'Duplicate JSON field: {key}')
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError(f'Nonfinite JSON number is not allowed: {value}')


def load_patch_file(path, segment_type):
    """Read bounded UTF-8/BOM JSON with duplicate-key and NaN rejection."""
    with Path(path).open('rb') as source:
        data = source.read(MAX_PATCH_BYTES + 1)
    if len(data) > MAX_PATCH_BYTES:
        raise ValueError(f'Patch file exceeds {MAX_PATCH_BYTES} bytes')
    try:
        patch = json.loads(data.decode('utf-8-sig'), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Patch must be valid UTF-8 JSON: {exc}') from exc
    return normalize_patch(patch, segment_type)


def changed_fields(patch, segment_type):
    """List requested leaf fields in a deterministic order."""
    normalized = normalize_patch(patch, segment_type)
    return sorted(f'{name}.{child}' if isinstance(value, dict) else name
                  for name, value in normalized.items()
                  for child in (value if isinstance(value, dict) else (None,)))


def _numeric_token(value):
    # Fixed-point output avoids native parsers treating scientific notation as
    # another syntax. 15 decimal places is ample for these bounded UI values.
    return format(value, '.15f').rstrip('0').rstrip('.') or '0'


def _percent(value):
    return _numeric_token(value * 100) + '%'


def build_property_commands(patch, segment_type, segment_id, *, allow_speed=False):
    """Return native argv plans; never execute or join them as a shell string.

    Each plan contains ``operation``, ``fields``, ``argv`` and ``requires``.
    ``requires`` documents runtime gates for the adapter, not completed checks.
    Callers must explicitly enable speed after checking neighbor/magnetic/curve
    semantics. An invalid later property cannot produce a partial plan.
    """
    normalized = normalize_patch(patch, segment_type)
    if not isinstance(segment_id, str) or not _UUID.fullmatch(segment_id):
        raise ValueError('segment_id must be one UUID, without command syntax')
    if 'speed' in normalized and not allow_speed:
        raise ValueError('Constant speed requires verified runtime isolation and explicit enablement')
    plans = []

    def add(operation, fields, flags, requires=()):
        plans.append({'operation': operation, 'fields': fields,
                      'argv': ['draft', segment_type, operation, '--seg-id', segment_id] + flags,
                      'requires': list(requires)})

    if 'crop' in normalized:
        box = normalized['crop']
        add('crop', [f'crop.{name}' for name in ('left', 'top', 'right', 'bottom')],
            ['--box', '<' + ','.join(_percent(box[name]) for name in
                                    ('left', 'top', 'right', 'bottom')) + '>'],
            ('geometry-calibration',))
    transform = normalized.get('transform', {})
    flags, fields = [], []
    for name, flag in (('scaleX', '--x'), ('scaleY', '--y')):
        if name in transform:
            fields.append(f'transform.{name}')
            flags.extend([flag, _numeric_token(transform[name])])
    if flags:
        add('scale', fields, flags, ('geometry-calibration', 'omitted-axis-preservation'))
    if 'rotationDeg' in transform:
        add('rotate', ['transform.rotationDeg'],
            ['--rotation', _numeric_token(transform['rotationDeg'])], ('geometry-calibration',))
    flags, fields = [], []
    for name, flag in (('xRatio', '--x'), ('yRatio', '--y')):
        if name in transform:
            fields.append(f'transform.{name}')
            flags.extend([flag, _percent(transform[name])])
    if flags:
        add('translate', fields, flags, ('geometry-calibration', 'omitted-axis-preservation'))
    if 'opacity' in normalized:
        add('alpha', ['opacity'], ['--alpha', _percent(normalized['opacity'])])
    for name, flag in (('volumeLinear', '--linear'), ('gainDb', '--db')):
        if name in normalized:
            add('volume', [name], [flag, _numeric_token(normalized[name])])
    flags, fields = [], []
    for name, flag in (('fadeInUs', '--in'), ('fadeOutUs', '--out')):
        if name in normalized:
            fields.append(name)
            flags.extend([flag, f'{normalized[name]}us'])
    if flags:
        add('fade', fields, flags, ('fade-duration-bounds', 'omitted-fade-preservation'))
    if 'speed' in normalized:
        add('speed', ['speed'], ['--speed', _numeric_token(normalized['speed'])],
            ('speed-isolation', 'source-window-preservation', 'neighbor-preservation'))
    return plans


def validate_fade_window(patch, duration_us, *, current_fade_in_us=0, current_fade_out_us=0):
    """Check requested and retained audio fades together before any write.

    The caller must provide current values from native/persisted readback when
    either fade is omitted. This check does not assert native omission behavior.
    """
    normalized = normalize_patch(patch, 'audio')
    duration = _number(duration_us, 'duration_us', 1, 2**53 - 1, integer=True)
    incoming = _number(current_fade_in_us, 'current_fade_in_us', 0, MAX_FADE_US, integer=True)
    outgoing = _number(current_fade_out_us, 'current_fade_out_us', 0, MAX_FADE_US, integer=True)
    incoming = normalized.get('fadeInUs', incoming)
    outgoing = normalized.get('fadeOutUs', outgoing)
    if incoming + outgoing > duration:
        raise ValueError('Combined fade durations exceed the segment duration')
    return {'fadeInUs': incoming, 'fadeOutUs': outgoing}
