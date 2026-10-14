"""Strict, side-effect-free input contracts for native subtitle import.

This module does not quote native command strings or infer native font/position
units. Cue times are integer timeline microseconds and use [start, end). Limits
are deliberately bounded because importing cues can require one native mutation
per cue. UTF-8 BOM and CRLF are accepted; caption text otherwise stays literal.
"""
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import unicodedata


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_CUES = 500
MAX_CUE_CHARS = 2000
MAX_TOTAL_CHARS = 50000
MAX_SAFE_INTEGER = 2**53 - 1
_ID = re.compile(r'[A-Za-z0-9._:-]{1,128}\Z')
_STAMP = r'([0-9]{2,6}):([0-5][0-9]):([0-5][0-9]),([0-9]{3})'
_TIMING = re.compile(r'^' + _STAMP + r'[ \t]+-->[ \t]+' + _STAMP + r'[ \t]*$')
_FONT = re.compile(r'[^\W-][\w.-]{0,127}\Z', re.UNICODE)


def _integer(value, name, *, signed=False):
    lower = -MAX_SAFE_INTEGER if signed else 0
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= MAX_SAFE_INTEGER:
        raise ValueError(f'{name} must be an integer in [{lower}, {MAX_SAFE_INTEGER}]')
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must contain non-whitespace caption text')
    value = value.replace('\r\n', '\n')
    if len(value) > MAX_CUE_CHARS:
        raise ValueError(f'{name} exceeds {MAX_CUE_CHARS} characters')
    for char in value:
        if unicodedata.category(char) in ('Cc', 'Cs') and char not in '\n\t':
            raise ValueError(f'{name} contains an unsupported control character or Unicode surrogate')
    return value


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'Duplicate JSON key: {key}')
        obj[key] = value
    return obj


def _bad_json_constant(value):
    raise ValueError(f'Non-finite JSON constant is not allowed: {value}')


def _parse_json(text):
    try:
        doc = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_bad_json_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f'Invalid caption JSON: {exc}') from exc
    if not isinstance(doc, dict) or set(doc) != {'timebase', 'cues'}:
        raise ValueError('Caption JSON must contain exactly timebase and cues')
    if doc['timebase'] != 'timeline_us':
        raise ValueError('Caption JSON timebase must be timeline_us')
    cues = doc['cues']
    if not isinstance(cues, list):
        raise ValueError('Caption JSON cues must be an array')
    result = []
    for index, cue in enumerate(cues, 1):
        if not isinstance(cue, dict) or set(cue) - {'id', 'startUs', 'endUs', 'text'}:
            raise ValueError(f'Cue {index} contains unknown fields or is not an object')
        if not {'startUs', 'endUs', 'text'} <= set(cue):
            raise ValueError(f'Cue {index} requires startUs, endUs and text')
        result.append({'id': cue.get('id', f'cue-{index:04d}'),
                       'startUs': cue['startUs'], 'endUs': cue['endUs'], 'text': cue['text']})
    return result


def _stamp_us(parts):
    hours, minutes, seconds, millis = map(int, parts)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000000 + millis * 1000


def _parse_srt(text):
    text = text.replace('\r\n', '\n')
    if '\r' in text:
        raise ValueError('SRT requires LF or CRLF line endings, not a lone CR')
    # Blank lines separate SRT records and do not form part of their text.
    text = re.sub(r'\A(?:[ \t]*\n)+', '', text)
    text = re.sub(r'(?:\n[ \t]*)+\Z', '', text)
    if not text:
        raise ValueError('Caption input contains no cues')
    blocks = re.split(r'\n(?:[ \t]*\n)+', text)
    result = []
    for block_number, block in enumerate(blocks, 1):
        lines = block.split('\n')
        if len(lines) < 3 or not re.fullmatch(r'[0-9]{1,9}', lines[0].strip()):
            raise ValueError(f'SRT cue {block_number} requires an integer index, a timing line and text')
        cue_number = int(lines[0].strip())
        if cue_number < 1:
            raise ValueError(f'SRT cue {block_number} index must be positive')
        timing = _TIMING.fullmatch(lines[1].strip())
        if not timing:
            raise ValueError(f'SRT cue {block_number} has invalid HH:MM:SS,mmm --> HH:MM:SS,mmm timing')
        # A second indexed record without a blank delimiter is ambiguous, not
        # a request to silently include that record's timing in caption text.
        for line_index in range(2, len(lines) - 1):
            if re.fullmatch(r'[0-9]{1,9}', lines[line_index].strip()) and _TIMING.fullmatch(lines[line_index + 1].strip()):
                raise ValueError(f'SRT cue {block_number} is missing a blank line before the next cue')
        result.append({'id': str(cue_number), 'startUs': _stamp_us(timing.groups()[:4]),
                       'endUs': _stamp_us(timing.groups()[4:]), 'text': '\n'.join(lines[2:])})
    return result


def load_captions(path, format=None, offset_us=0, timeline_duration_us=None, fps=30):
    """Read SRT or JSON and return [{id, startUs, endUs, text}, ...].

    JSON is {"timebase":"timeline_us","cues":[...]}; cue IDs are optional
    ASCII identifiers and default to cue-0001, etc. SRT's positive numeric
    indexes become IDs. Inputs retain their order; overlaps and unsorted cues
    are rejected, while adjacent cues are allowed. No frame quantization is
    performed here: the native adapter must verify any effective quantization.
    """
    offset_us = _integer(offset_us, 'offset_us', signed=True)
    if timeline_duration_us is not None:
        timeline_duration_us = _integer(timeline_duration_us, 'timeline_duration_us')
        if not timeline_duration_us:
            raise ValueError('timeline_duration_us must be positive')
    if isinstance(fps, bool) or not isinstance(fps, (int, float, Fraction)) or not 0 < fps <= 1000 or not math.isfinite(fps):
        raise ValueError('fps must be a finite number greater than zero and at most 1000')
    fps_fraction = fps if isinstance(fps, Fraction) else Fraction(str(fps))
    frame_us = math.ceil(Fraction(1000000, 1) / fps_fraction)
    source = Path(path)
    input_format = format if format is not None else source.suffix.lstrip('.').lower()
    if input_format not in ('srt', 'json'):
        raise ValueError('Caption format must be srt or json (or inferred from the file suffix)')
    with source.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f'Caption file exceeds {MAX_FILE_BYTES} bytes')
    try:
        text = raw.decode('utf-8-sig', errors='strict')
    except UnicodeDecodeError as exc:
        raise ValueError('Caption input must be valid UTF-8, optionally with a BOM') from exc
    cues = _parse_srt(text) if input_format == 'srt' else _parse_json(text)
    if not 1 <= len(cues) <= MAX_CUES:
        raise ValueError(f'Caption input must contain between 1 and {MAX_CUES} cues')
    result, seen_ids, previous_end, total_chars = [], set(), 0, 0
    for index, cue in enumerate(cues, 1):
        cue_id = cue['id']
        if not isinstance(cue_id, str) or not _ID.fullmatch(cue_id):
            raise ValueError(f'Cue {index} id must be 1..128 ASCII letters, digits or . _ : -')
        if cue_id in seen_ids:
            raise ValueError(f'Duplicate cue id: {cue_id}')
        seen_ids.add(cue_id)
        start = _integer(cue['startUs'], f'Cue {cue_id} startUs') + offset_us
        end = _integer(cue['endUs'], f'Cue {cue_id} endUs') + offset_us
        _integer(start, f'Offset cue {cue_id} startUs')
        _integer(end, f'Offset cue {cue_id} endUs')
        if end - start < frame_us:
            raise ValueError(f'Cue {cue_id} must have positive duration of at least one frame ({frame_us} us)')
        if start < previous_end:
            raise ValueError(f'Cue {cue_id} overlaps the previous cue or is out of timeline order')
        if timeline_duration_us is not None and end > timeline_duration_us:
            raise ValueError(f'Cue {cue_id} exceeds timeline duration')
        caption_text = _text(cue['text'], f'Cue {cue_id} text')
        total_chars += len(caption_text)
        if total_chars > MAX_TOTAL_CHARS:
            raise ValueError(f'Caption text exceeds {MAX_TOTAL_CHARS} total characters')
        result.append({'id': cue_id, 'startUs': start, 'endUs': end, 'text': caption_text})
        previous_end = end
    return result


def normalize_style(style):
    """Validate a style patch; native units still require runtime verification.

    Supported keys are size, color, font, outlineColor and outlineWidth. Values
    remain structured data, never an assembled command. Position is omitted
    until the native adapter establishes its coordinate semantics. Font values
    are bounded whitespace-free resource identifiers/names; this does not prove
    that the installed editor can resolve the named font.
    """
    if not isinstance(style, dict):
        raise ValueError('Caption style must be a JSON object')
    allowed = {'size', 'color', 'font', 'outlineColor', 'outlineWidth'}
    if set(style) - allowed:
        raise ValueError(f'Unsupported caption style fields: {sorted(set(style) - allowed)}')
    result = {}
    for key, value in style.items():
        if key in ('size', 'outlineWidth'):
            lower, upper = (1, 500) if key == 'size' else (0, 1)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper or not math.isfinite(value):
                raise ValueError(f'Caption style {key} must be a finite number in [{lower}, {upper}]')
            result[key] = value
        elif key in ('color', 'outlineColor'):
            if not isinstance(value, str) or not re.fullmatch(r'(?:#|0x)[0-9A-Fa-f]{6}', value):
                raise ValueError(f'Caption style {key} must be #RRGGBB or 0xRRGGBB')
            result[key] = '0x' + value[-6:].upper()
        elif key == 'font':
            if not isinstance(value, str) or not _FONT.fullmatch(value):
                raise ValueError('Caption font must be a 1..128 character whitespace-free resource identifier/name')
            result[key] = value
    return result
