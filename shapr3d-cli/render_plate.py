"""Render an independently verified native STL; this is not a Shapr3D screenshot.

Requires Pillow and NumPy. The report must come from verify_plate.py and its SHA256
must match the input STL. Geometry is rasterized directly from the STL triangles;
dimensions are measured values from that independent report, not requested values.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from verify_plate import cross, dot, norm, read_stl, sub, unit

SCALE = 2
INK = '#183047'
MUTED = '#56697b'
ACCENT = '#227a9d'
WHITE = '#ffffff'


def font(size, bold=False):
    candidates = ([r'C:\Windows\Fonts\arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else
                  [r'C:\Windows\Fonts\arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size * SCALE)
    return ImageFont.load_default(size=size * SCALE)


def rasterize(triangles, panel_size, view, px_per_mm):
    """Orthographic triangle rasterizer with a depth buffer and real mesh edges."""
    width, height = [round(x * SCALE) for x in panel_size]
    pixels = np.full((height, width, 3), 255, dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    view = np.array(unit(view))
    up_reference = (0, 1, 0) if abs(view[2]) > .99 else (0, 0, 1)
    right = np.array(unit(cross(up_reference, view)))
    up = np.array(cross(view, right))
    matrix = np.array([right, -up, view])
    source = np.array(triangles, dtype=np.float64)
    transformed = source @ matrix.T
    projected_bounds = (transformed[:, :, :2].min(axis=(0, 1)), transformed[:, :, :2].max(axis=(0, 1)))
    center = (projected_bounds[0] + projected_bounds[1]) / 2
    factor = px_per_mm * SCALE
    projected = transformed.copy()
    projected[:, :, :2] = (projected[:, :, :2] - center) * factor + np.array([width / 2, height / 2])
    light = np.array(unit((-0.3, -0.6, 1)))
    normals = []
    for tri, projected_tri in zip(source, projected):
        normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        normal /= np.linalg.norm(normal)
        normals.append(normal)
        if float(normal @ view) <= 1e-7:
            continue
        lo = np.maximum(np.floor(projected_tri[:, :2].min(axis=0)).astype(int), (0, 0))
        hi = np.minimum(np.ceil(projected_tri[:, :2].max(axis=0)).astype(int), (width - 1, height - 1))
        if any(hi < lo):
            continue
        x, y = np.meshgrid(np.arange(lo[0], hi[0] + 1) + .5, np.arange(lo[1], hi[1] + 1) + .5)
        a, b, c = projected_tri
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-10:
            continue
        first = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
        second = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
        third = 1 - first - second
        z = first * a[2] + second * b[2] + third * c[2]
        region = depth[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        mask = (first >= -1e-8) & (second >= -1e-8) & (third >= -1e-8) & (z > region)
        region[mask] = z[mask]
        shade = .64 + .36 * max(0, float(normal @ light))
        color = np.array((139, 188, 207)) * shade
        pixels[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1][mask] = color.astype(np.uint8)
    # Draw only geometric feature edges; invisible rear edges fail the same depth test.
    edges = {}
    for index, tri in enumerate(source):
        for i, j in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted((tuple(tri[i]), tuple(tri[j]))))
            edges.setdefault(key, []).append((index, i, j))
    for incidents in edges.values():
        if len(incidents) == 2 and float(normals[incidents[0][0]] @ normals[incidents[1][0]]) > .9995:
            continue
        index, i, j = incidents[0]
        a, b = projected[index][i], projected[index][j]
        steps = max(2, math.ceil(float(np.linalg.norm(b[:2] - a[:2])) * 1.5))
        line = a + np.linspace(0, 1, steps)[:, None] * (b - a)
        for point in line:
            x, y = round(point[0]), round(point[1])
            if 0 <= x < width and 0 <= y < height and point[2] >= depth[y, x] - .025:
                pixels[y, x] = (49, 103, 126)
    return Image.fromarray(pixels)


def render(stl_path, report_path, output_path, title):
    triangles, source = read_stl(stl_path)
    report = json.loads(Path(report_path).read_text(encoding='utf-8-sig'))
    if source['sha256'] != report.get('source', {}).get('sha256'):
        raise ValueError('Verification report SHA256 does not match the input STL')
    if not report.get('passed') or not all(row['passed'] for row in report.get('checks', [])):
        raise ValueError('Only independently passing plate reports can be rendered with this tool')
    measured = report['measurements']
    axes = measured['frameAxes']
    # Reorient the actual mesh into the independently recovered plate frame.
    axes = [axes[name] for name in ('length', 'width', 'thickness')]
    points = [tuple(dot(p, axis) for axis in axes) for tri in triangles for p in tri]
    middle = tuple((min(p[j] for p in points) + max(p[j] for p in points)) / 2 for j in range(3))
    triangles = [tuple(tuple(dot(p, axis) - middle[j] for j, axis in enumerate(axes)) for p in tri) for tri in triangles]
    canvas = Image.new('RGB', (1800 * SCALE, 1230 * SCALE), '#eef3f7')
    draw = ImageDraw.Draw(canvas)

    def text(position, value, size=22, color=INK, bold=False, anchor=None):
        draw.text(tuple(x * SCALE for x in position), str(value), font=font(size, bold), fill=color, anchor=anchor)

    def line(points, color=ACCENT, width=1):
        draw.line([tuple(x * SCALE for x in p) for p in points], fill=color, width=width * SCALE)

    def arrow(point, direction, size=7):
        direction = unit(direction)
        side = (-direction[1], direction[0])
        polygon = [point, tuple(point[j] + size * direction[j] + size * .45 * side[j] for j in range(2)),
                   tuple(point[j] + size * direction[j] - size * .45 * side[j] for j in range(2))]
        draw.polygon([tuple(x * SCALE for x in p) for p in polygon], fill=ACCENT)

    def dimension(a, b, label, label_offset=(0, -15), size=20):
        line([a, b])
        direction = sub(b, a)
        arrow(a, direction)
        arrow(b, tuple(-x for x in direction))
        midpoint = tuple((a[j] + b[j]) / 2 + label_offset[j] for j in range(2))
        label_font = font(size, True)
        bbox = draw.textbbox(tuple(x * SCALE for x in midpoint), label, font=label_font, anchor='mm')
        draw.rectangle((bbox[0] - 7 * SCALE, bbox[1] - 3 * SCALE,
                        bbox[2] + 7 * SCALE, bbox[3] + 3 * SCALE), fill=WHITE)
        draw.text(tuple(x * SCALE for x in midpoint), label, font=label_font, fill=ACCENT, anchor='mm')

    def panel(box):
        draw.rounded_rectangle(tuple(x * SCALE for x in box), radius=18 * SCALE, fill=WHITE,
                               outline='#d6e2ea', width=SCALE)

    def number(value):
        return f'{value:.3f}'.rstrip('0').rstrip('.')

    length = measured['lengthMm']
    width = measured['widthMm']
    thickness = measured['thicknessMm']
    cap = measured['caps'][1]
    pitch = cap['holePitchMm']
    diameters = [hole['diameterMm'] for hole in cap['holes']]
    text((44, 32), title, size=38, bold=True)
    text((46, 89), 'Independent STL inspection  |  Native export geometry  |  Not an application screenshot',
         size=22, color=MUTED)
    panel((40, 150, 1080, 850))
    panel((1100, 150, 1760, 850))
    text((68, 175), 'TOP VIEW', size=22, bold=True)
    text((1128, 175), 'ORTHOGRAPHIC 3D VIEW', size=22, bold=True)
    scale = min(9.0, 790 / length, 420 / width)
    top_box = (155, 270, 990, 730)
    top_image = rasterize(triangles, (top_box[2] - top_box[0], top_box[3] - top_box[1]), (0, 0, 1), scale)
    canvas.paste(top_image, (top_box[0] * SCALE, top_box[1] * SCALE))
    center = ((top_box[0] + top_box[2]) / 2, (top_box[1] + top_box[3]) / 2)
    left, right = center[0] - length * scale / 2, center[0] + length * scale / 2
    top, bottom = center[1] - width * scale / 2, center[1] + width * scale / 2
    dimension_y = top - 50
    for x in (left, right):
        line([(x, top - 8), (x, dimension_y - 10)], color='#93a9b6')
    dimension((left, dimension_y), (right, dimension_y), number(length) + ' mm')
    dimension_x = left - 57
    for y in (top, bottom):
        line([(left - 8, y), (dimension_x - 10, y)], color='#93a9b6')
    dimension((dimension_x, top), (dimension_x, bottom), number(width) + ' mm', label_offset=(-1, 0), size=18)
    hole_positions = [(center[0] + hole['centerMm'][0] * scale,
                       center[1] - hole['centerMm'][1] * scale) for hole in cap['holes']]
    hole_radius = max(diameters) * scale / 2
    pitch_y = bottom + 53
    for x, y in hole_positions:
        # Center marks and measurement extensions are overlays, not new geometry.
        line([(x - hole_radius - 10, y), (x + hole_radius + 10, y)], color='#6c8d9e')
        line([(x, y - hole_radius - 10), (x, y + hole_radius + 10)], color='#6c8d9e')
        line([(x, y + hole_radius + 18), (x, pitch_y + 8)], color='#93a9b6')
    dimension((hole_positions[0][0], pitch_y), (hole_positions[1][0], pitch_y), number(pitch) + ' mm pitch')
    leader_start = (hole_positions[1][0] + hole_radius * .75, hole_positions[1][1] - hole_radius * .75)
    leader_end = (min(right - 10, leader_start[0] + 100), leader_start[1] - 91)
    line([leader_start, leader_end])
    arrow(leader_start, sub(leader_end, leader_start), size=6)
    text((leader_end[0], leader_end[1] - 17), '2 × Ø' + number(sum(diameters) / 2) + ' mm', size=19,
         bold=True, color=ACCENT, anchor='mm')
    text((70, 805), 'Actual triangulated holes; dimensions measured from mesh vertices.', size=19, color=MUTED)
    iso_size = (600, 360)
    iso_scale = min(6.6, 520 / length)
    iso_image = rasterize(triangles, iso_size, (1, -1.7, 1.35), iso_scale)
    canvas.paste(iso_image, (1130 * SCALE, 235 * SCALE))
    text((1128, 645), 'SIDE VIEW / THICKNESS', size=21, bold=True)
    side_size = (580, 110)
    side_scale = min(5.5, 480 / length)
    side_image = rasterize(triangles, side_size, (0, -1, 0), side_scale)
    canvas.paste(side_image, (1122 * SCALE, 688 * SCALE))
    side_center = (1122 + side_size[0] / 2, 688 + side_size[1] / 2)
    side_right = side_center[0] + length * side_scale / 2
    side_top = side_center[1] - thickness * side_scale / 2
    side_bottom = side_center[1] + thickness * side_scale / 2
    x = side_right + 29
    for y in (side_top, side_bottom):
        line([(side_right + 5, y), (x + 7, y)], color='#93a9b6')
    dimension((x, side_top), (x, side_bottom), number(thickness) + ' mm', label_offset=(-25, -39), size=20)
    panel((40, 880, 1760, 1190))
    text((68, 906), 'INDEPENDENT ACCEPTANCE: PASS', size=25, bold=True, color='#236549')
    topology = report['topology']
    text((68, 951), f"{topology['triangles']} triangles  ·  1 connected solid  ·  Closed manifold  ·  Euler characteristic −2",
         size=23)
    max_sagitta = max(h['maximumChordSagittaMm'] for c in measured['caps'] for h in c['holes'])
    text((68, 996), f"Mesh volume {measured['signedVolumeMm3']:,.3f} mm³  ·  Maximum hole chord sagitta {max_sagitta:.4f} mm",
         size=22, color=MUTED)
    text((68, 1037), f"All {len(report['checks'])} checks passed. Dimensions assume STL units are millimetres.", size=21, color=MUTED)
    text((68, 1080), 'SOURCE: ' + Path(stl_path).name, size=20, bold=True)
    text((68, 1120), 'SHA256: ' + source['sha256'], size=17, color=MUTED)
    text((68, 1152), 'This image is rendered from exported triangles. It does not independently prove CAD history or save/reopen behavior.',
         size=18, color=MUTED)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.resize((1800, 1230), Image.Resampling.LANCZOS).save(output_path)
    evidence = {'kind': 'independent-stl-render', 'notApplicationScreenshot': True,
                'stlPath': str(Path(stl_path).resolve()), 'stlSha256': source['sha256'],
                'verificationPath': str(Path(report_path).resolve()), 'passed': True,
                'outputPath': str(output_path.resolve()),
                'imageSha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
                'renderMethod': 'Orthographic depth-buffer rasterization of input STL triangles; no CAD reconstruction',
                'pixelSize': [1800, 1230]}
    evidence_path = output_path.with_suffix('.render.json')
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stl', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--title', default='Mounting plate · native Shapr3D export')
    args = parser.parse_args()
    try:
        result = render(args.stl, args.report, args.out, args.title)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
