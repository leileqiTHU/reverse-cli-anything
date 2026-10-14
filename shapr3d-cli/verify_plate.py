"""Independently measure a rectangular two-hole plate from an STL, without CAD APIs.

All dimensions and tolerances are in millimetres. STL itself has no unit metadata.
The accepted shape is a straight extrusion with a rectangular outer boundary and
two circular through holes; chamfers, fillets and countersinks are intentionally
outside this demo's acceptance contract. The mesh may be rotated and translated.
Only the Python standard library is required.
"""

import argparse
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import struct
import sys


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    length = norm(a)
    if not length:
        raise ValueError('Cannot normalize a zero vector')
    return tuple(x / length for x in a)


def read_stl(path):
    data = Path(path).read_bytes()
    count = struct.unpack_from('<I', data, 80)[0] if len(data) >= 84 else 0
    triangles = []
    if count and len(data) == 84 + 50 * count:
        encoding = 'binary'
        for i in range(count):
            values = struct.unpack_from('<12fH', data, 84 + 50 * i)
            triangles.append(tuple(tuple(values[j:j + 3]) for j in (3, 6, 9)))
    else:
        encoding = 'ascii'
        text = data.decode('ascii')
        if not re.match(r'\s*solid(?:\s|$)', text) or not re.search(r'endsolid(?:\s|$)', text):
            raise ValueError('STL is neither a valid binary size nor an ASCII solid')
        facets = re.findall(r'\bfacet\b(.*?)\bendfacet\b', text, re.S)
        if len(facets) != len(re.findall(r'\bfacet\b', text)):
            raise ValueError('Incomplete ASCII STL facet')
        for facet in facets:
            vertices = re.findall(r'\bvertex\s+(\S+)\s+(\S+)\s+(\S+)', facet)
            if len(vertices) != 3:
                raise ValueError('ASCII STL facet must contain exactly three vertices')
            triangles.append(tuple(tuple(map(float, p)) for p in vertices))
    if not triangles or not all(math.isfinite(x) for tri in triangles for p in tri for x in p):
        raise ValueError('STL has no triangles or contains nonfinite coordinates')
    return triangles, {'path': str(Path(path).resolve()), 'encoding': encoding,
                       'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def weld(triangles, tolerance):
    """Merge coincident vertices, including adjacent quantization buckets."""
    vertices, faces = [], []
    buckets = collections.defaultdict(list)
    offsets = list(itertools.product((-1, 0, 1), repeat=3))
    for tri in triangles:
        face = []
        for p in tri:
            key = tuple(math.floor(x / tolerance) for x in p)
            candidates = (i for off in offsets
                          for i in buckets.get(tuple(key[j] + off[j] for j in range(3)), ()))
            match = next((i for i in candidates if norm(sub(vertices[i], p)) <= tolerance), None)
            if match is None:
                match = len(vertices)
                vertices.append(p)
                buckets[key].append(match)
            face.append(match)
        faces.append(tuple(face))
    return vertices, faces


def component_count(adjacency):
    unseen = set(adjacency)
    count = 0
    while unseen:
        count += 1
        pending = [unseen.pop()]
        while pending:
            for neighbor in adjacency[pending.pop()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    pending.append(neighbor)
    return count


def topology(vertices, faces, weld_tolerance):
    edges = collections.defaultdict(list)
    links = collections.defaultdict(lambda: collections.defaultdict(list))
    degenerate = 0
    for i, face in enumerate(faces):
        a, b, c = (vertices[j] for j in face)
        if len(set(face)) != 3 or norm(cross(sub(b, a), sub(c, a))) <= weld_tolerance ** 2:
            degenerate += 1
        for a, b in zip(face, face[1:] + face[:1]):
            edges[tuple(sorted((a, b)))].append((i, a, b))
        for a, b, c in ((face[0], face[1], face[2]), (face[1], face[2], face[0]),
                        (face[2], face[0], face[1])):
            links[a][b].append(c)
            links[a][c].append(b)
    adjacent = {i: set() for i in range(len(faces))}
    for incidents in edges.values():
        for a, b in itertools.combinations(incidents, 2):
            adjacent[a[0]].add(b[0])
            adjacent[b[0]].add(a[0])
    invalid_links = sum(any(len(ns) != 2 for ns in link.values()) or component_count(link) != 1
                        for link in links.values())
    euler = len(vertices) - len(edges) + len(faces)
    return {
        'vertices': len(vertices), 'edges': len(edges), 'triangles': len(faces),
        'edgeUseHistogram': dict(sorted(collections.Counter(map(len, edges.values())).items())),
        'nonManifoldEdges': sum(len(v) != 2 for v in edges.values()),
        'nonManifoldVertices': invalid_links,
        'inconsistentlyOrientedEdges': sum(len(v) == 2 and v[0][1:] == v[1][1:] for v in edges.values()),
        'degenerateTriangles': degenerate,
        'duplicateTriangles': len(faces) - len({tuple(sorted(f)) for f in faces}),
        'connectedComponents': component_count(adjacent), 'eulerCharacteristic': euler,
        'genusIfClosedConnectedOrientable': (2 - euler) / 2,
    }


def boundary_loops(cap_faces):
    counts = collections.Counter(tuple(sorted((a, b))) for f in cap_faces
                                 for a, b in zip(f, f[1:] + f[:1]))
    adjacent = collections.defaultdict(list)
    for (a, b), count in counts.items():
        if count == 1:
            adjacent[a].append(b)
            adjacent[b].append(a)
        elif count != 2:
            raise ValueError('Cap triangulation has a nonmanifold edge')
    if not adjacent or any(len(ns) != 2 for ns in adjacent.values()):
        raise ValueError('Cap boundary is not a set of closed simple loops')
    unused = set(adjacent)
    loops = []
    while unused:
        start = min(unused)
        loop, previous, current = [], None, start
        while current in unused:
            unused.remove(current)
            loop.append(current)
            following = next(n for n in adjacent[current] if n != previous)
            previous, current = current, following
        if current != start or len(loop) < 3:
            raise ValueError('Broken cap boundary cycle')
        loops.append(loop)
    return loops


def area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(points, points[1:] + points[:1]))) / 2


def solve3(matrix, values):
    rows = [list(row) + [value] for row, value in zip(matrix, values)]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda j: abs(rows[j][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        if abs(rows[i][i]) < 1e-12:
            raise ValueError('Degenerate circle fit')
        scale = rows[i][i]
        rows[i] = [x / scale for x in rows[i]]
        for j in range(3):
            if i != j:
                factor = rows[j][i]
                rows[j] = [a - factor * b for a, b in zip(rows[j], rows[i])]
    return tuple(row[-1] for row in rows)


def circle(points):
    # Center before least squares to avoid cancellation after large translations.
    origin = tuple(sum(p[j] for p in points) / len(points) for j in range(2))
    centered = [sub(p, origin) for p in points]
    rows = [(2 * x, 2 * y, 1) for x, y in centered]
    rhs = [x * x + y * y for x, y in centered]
    solution = solve3([[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)],
                      [sum(row[i] * value for row, value in zip(rows, rhs)) for i in range(3)])
    center = (solution[0] + origin[0], solution[1] + origin[1])
    radius = math.sqrt(solution[2] + solution[0] ** 2 + solution[1] ** 2)
    boundary_angles = [math.atan2(p[1] - center[1], p[0] - center[0]) for p in points]
    angles = sorted(boundary_angles)
    max_gap = max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + math.tau]))
    turns = [(b - a + math.pi) % math.tau - math.pi
             for a, b in zip(boundary_angles, boundary_angles[1:] + boundary_angles[:1])]
    single_turn = (all(turn > 1e-10 for turn in turns) or all(turn < -1e-10 for turn in turns)) \
        and abs(abs(sum(turns)) - math.tau) < 1e-7
    return {'centerMm': center, 'radiusMm': radius, 'diameterMm': 2 * radius,
            'radialResidualMm': max(abs(norm(sub(p, center)) - radius) for p in points),
            'vertices': len(points), 'maximumAngularGapDegrees': math.degrees(max_gap),
            'singleSimpleCircularBoundary': single_turn,
            'maximumChordSagittaMm': radius * (1 - math.cos(max_gap / 2)),
            'polygonAreaMm2': area(points)}


def segment_distance(point, a, b):
    direction = sub(b, a)
    ratio = max(0, min(1, dot(sub(point, a), direction) / dot(direction, direction)))
    return norm(sub(point, tuple(x + ratio * d for x, d in zip(a, direction))))


def verify(path, *, length, width, thickness, pitch, diameter, dimension_tolerance=0.1,
           planar_tolerance=0.002, surface_tolerance=0.25, weld_tolerance=0.00001,
           volume_relative_tolerance=0.005):
    expected = {'lengthMm': length, 'widthMm': width, 'thicknessMm': thickness,
                'holePitchMm': pitch, 'holeDiameterMm': diameter}
    if not all(math.isfinite(v) and v > 0 for v in list(expected.values()) + [
            dimension_tolerance, planar_tolerance, surface_tolerance, weld_tolerance, volume_relative_tolerance]):
        raise ValueError('Dimensions and tolerances must be finite and positive')
    if length < width or pitch + diameter >= length or diameter >= width:
        raise ValueError('Expected plate must have length >= width and two separated holes inside it')
    if pitch <= diameter:
        raise ValueError('Expected circular holes must not overlap')
    triangles, source = read_stl(path)
    source['geometrySha256'] = hashlib.sha256(
        repr(sorted(tuple(sorted(tri)) for tri in triangles)).encode('ascii')).hexdigest()
    source['geometryHashMethod'] = 'Sorted triangles with sorted exact vertex tuples; ignores face/vertex order only'
    vertices, faces = weld(triangles, weld_tolerance)
    checks = []

    def check(name, passed, actual=None, target=None, tolerance=None):
        row = {'name': name, 'passed': bool(passed)}
        for key, value in [('measured', actual), ('expected', target), ('tolerance', tolerance)]:
            if value is not None:
                row[key] = value
        checks.append(row)

    def near(name, actual, target, tolerance=dimension_tolerance):
        check(name, abs(actual - target) <= tolerance, actual, target, tolerance)

    mesh = topology(vertices, faces, weld_tolerance)
    for key, value in [('nonManifoldEdges', 0), ('nonManifoldVertices', 0),
                       ('inconsistentlyOrientedEdges', 0), ('degenerateTriangles', 0),
                       ('duplicateTriangles', 0), ('connectedComponents', 1), ('eulerCharacteristic', -2)]:
        check(key, mesh[key] == value, mesh[key], value)
    report = {'schemaVersion': 1, 'passed': False, 'source': source, 'expected': expected,
              'units': 'mm (supplied externally; STL contains no units)',
              'tolerances': {'dimensionMm': dimension_tolerance, 'planarityMm': planar_tolerance,
                             'circleChordSagittaMm': surface_tolerance, 'weldMm': weld_tolerance,
                             'idealVolumeRelative': volume_relative_tolerance},
              'topology': mesh, 'checks': checks}
    if not all(row['passed'] for row in checks):
        report['error'] = 'Invalid closed two-hole solid topology; geometric fitting skipped'
        return report

    # Translate coordinates near zero for stable normals, planar fits and volume.
    origin = tuple(sum(p[j] for p in vertices) / len(vertices) for j in range(3))
    points = [sub(p, origin) for p in vertices]
    face_normals, clusters = [], []
    signed_volume = 0.0
    for face in faces:
        a, b, c = [points[j] for j in face]
        n = cross(sub(b, a), sub(c, a))
        face_normals.append(unit(n))
        size = norm(n) / 2
        signed_volume += dot(a, cross(b, c)) / 6
        n = unit(n)
        if n[max(range(3), key=lambda k: abs(n[k]))] < 0:
            n = tuple(-x for x in n)
        cluster = next((group for group in clusters if dot(group[0], n) > 1 - 1e-8), None)
        if cluster is None:
            clusters.append([n, size])
        else:
            cluster[1] += size
    axis = max(clusters, key=lambda group: group[1])[0]
    heights = [dot(p, axis) for p in points]
    low, high = min(heights), max(heights)
    cap_indices = [[i for i, face in enumerate(faces)
                    if all(abs(heights[j] - level) <= planar_tolerance for j in face)] for level in (low, high)]
    if not all(cap_indices):
        raise ValueError('Could not find two planar extrusion caps')
    cap_loops = [boundary_loops([faces[i] for i in indices]) for indices in cap_indices]
    for i, loops in enumerate(cap_loops):
        check(f'cap{i}BoundaryLoops', len(loops) == 3, len(loops), 3)
    if any(len(loops) != 3 for loops in cap_loops):
        report['error'] = 'Each extrusion cap must contain one exterior loop and two holes'
        return report
    initial_u = unit(cross(axis, (1, 0, 0) if abs(axis[0]) < 0.8 else (0, 1, 0)))
    initial_v = cross(axis, initial_u)
    initial_xy = [(dot(p, initial_u), dot(p, initial_v)) for p in points]
    exterior = max(cap_loops[0], key=lambda loop: area([initial_xy[j] for j in loop]))
    # The longest exterior edge defines one rectangle axis even with extra collinear vertices.
    edge = max((sub(points[b], points[a]) for a, b in zip(exterior, exterior[1:] + exterior[:1])), key=norm)
    u = unit(sub(edge, tuple(dot(edge, axis) * n for n in axis)))
    v = cross(axis, u)
    xy = [(dot(p, u), dot(p, v)) for p in points]
    spans = [max(x[j] for x in xy) - min(x[j] for x in xy) for j in range(2)]
    if spans[0] < spans[1]:
        u, v = v, tuple(-x for x in u)
        xy = [(dot(p, u), dot(p, v)) for p in points]
    bounds = [[min(p[j] for p in xy) for j in range(2)], [max(p[j] for p in xy) for j in range(2)]]
    midpoint = tuple((bounds[0][j] + bounds[1][j]) / 2 for j in range(2))
    xy = [sub(p, midpoint) for p in xy]
    measured_length, measured_width = (bounds[1][j] - bounds[0][j] for j in range(2))
    measured_thickness = high - low
    near('lengthMm', measured_length, length)
    near('widthMm', measured_width, width)
    near('thicknessMm', measured_thickness, thickness)
    caps = []
    for i, loops in enumerate(cap_loops):
        loops = sorted(loops, key=lambda loop: area([xy[j] for j in loop]), reverse=True)
        outline = [xy[j] for j in loops[0]]
        rectangle_error = max(min(abs(abs(p[0]) - measured_length / 2),
                                  abs(abs(p[1]) - measured_width / 2)) for p in outline)
        near(f'cap{i}RectangleBoundaryErrorMm', rectangle_error, 0, planar_tolerance)
        near(f'cap{i}RectangleAreaMm2', area(outline), measured_length * measured_width,
             planar_tolerance * 2 * (measured_length + measured_width))
        holes = sorted((circle([xy[j] for j in loop]) for loop in loops[1:]), key=lambda h: h['centerMm'][0])
        for j, hole in enumerate(holes):
            near(f'cap{i}Hole{j}DiameterMm', hole['diameterMm'], diameter)
            near(f'cap{i}Hole{j}CircularResidualMm', hole['radialResidualMm'], 0, planar_tolerance)
            near(f'cap{i}Hole{j}CenterLongMm', hole['centerMm'][0], (-1 if j == 0 else 1) * pitch / 2)
            near(f'cap{i}Hole{j}CenterCrossMm', hole['centerMm'][1], 0)
            check(f'cap{i}Hole{j}CircularSampling', hole['vertices'] >= 6 and hole['maximumAngularGapDegrees'] <= 60.0001,
                  {'vertices': hole['vertices'], 'maxGapDegrees': hole['maximumAngularGapDegrees']})
            check(f'cap{i}Hole{j}SimpleCircularBoundary', hole['singleSimpleCircularBoundary'])
            check(f'cap{i}Hole{j}ChordSagittaMm', hole['maximumChordSagittaMm'] <= surface_tolerance,
                  hole['maximumChordSagittaMm'], tolerance=surface_tolerance)
        measured_pitch = norm(sub(holes[1]['centerMm'], holes[0]['centerMm']))
        near(f'cap{i}HolePitchMm', measured_pitch, pitch)
        caps.append({'heightMm': (low if i == 0 else high), 'holes': holes, 'holePitchMm': measured_pitch,
                     'netPolygonAreaMm2': area(outline) - sum(h['polygonAreaMm2'] for h in holes)})
    for j in range(2):
        near(f'hole{j}ThroughAlignmentMm', norm(sub(caps[0]['holes'][j]['centerMm'], caps[1]['holes'][j]['centerMm'])),
             0, planar_tolerance)
        near(f'hole{j}ThroughDiameterChangeMm', caps[0]['holes'][j]['diameterMm'], caps[1]['holes'][j]['diameterMm'],
             planar_tolerance)
    cap_set = set(cap_indices[0] + cap_indices[1])
    side_indices = [i for i in range(len(faces)) if i not in cap_set]
    max_side_tilt = max(abs(dot(face_normals[i], axis)) for i in side_indices)
    check('straightExtrusionSideNormals', max_side_tilt < 0.001, max_side_tilt, tolerance=0.001)
    segments = [(xy[a], xy[b]) for loop in cap_loops[0] for a, b in zip(loop, loop[1:] + loop[:1])]
    side_vertices = {j for i in side_indices for j in faces[i]}
    max_profile_error = max(min(segment_distance(xy[j], a, b) for a, b in segments) for j in side_vertices)
    near('straightExtrusionProfileErrorMm', max_profile_error, 0, planar_tolerance)
    analytic_volume = (length * width - 2 * math.pi * (diameter / 2) ** 2) * thickness
    polygon_volume = sum(cap['netPolygonAreaMm2'] for cap in caps) / 2 * measured_thickness
    near('meshVolumeVsExtrudedPolygonMm3', abs(signed_volume), polygon_volume,
         max(0.001, polygon_volume * 0.00001))
    near('meshVolumeVsExpectedAnalyticMm3', abs(signed_volume), analytic_volume,
         analytic_volume * volume_relative_tolerance)
    check('outwardWinding', signed_volume > 0, signed_volume, 'positive signed volume')
    report['measurements'] = {'lengthMm': measured_length, 'widthMm': measured_width,
                              'thicknessMm': measured_thickness, 'caps': caps,
                              'signedVolumeMm3': signed_volume, 'idealExpectedVolumeMm3': analytic_volume,
                              'measuredPolygonExtrusionVolumeMm3': polygon_volume,
                              'worldOriginMm': origin, 'frameAxes': {'length': u, 'width': v, 'thickness': axis},
                              'axisAlignedWorldBoundsMm': [[min(p[j] for p in vertices) for j in range(3)],
                                                          [max(p[j] for p in vertices) for j in range(3)]]}
    report['passed'] = all(row['passed'] for row in checks)
    report['limitations'] = [
        'STL units are assumed to be mm; no STL unit metadata exists.',
        'Acceptance is restricted to a straight rectangular extrusion with two centered circular through holes.',
        'Circle diameters are fits to tessellation vertices; maximum chord sagitta is reported and bounded separately.',
        'This verifies exported geometry, not CAD history, project persistence or print-material suitability.',
    ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stl', type=Path)
    for option in ('length', 'width', 'thickness', 'pitch', 'diameter'):
        parser.add_argument('--' + option, type=float, required=True)
    parser.add_argument('--dimension-tolerance', type=float, default=0.1)
    parser.add_argument('--planar-tolerance', type=float, default=0.002)
    parser.add_argument('--surface-tolerance', type=float, default=0.25)
    parser.add_argument('--weld-tolerance', type=float, default=0.00001)
    parser.add_argument('--volume-relative-tolerance', type=float, default=0.005)
    parser.add_argument('--out', type=Path, help='Optional JSON report (D: preferred)')
    args = parser.parse_args()
    output = args.out
    options = vars(args).copy()
    del options['out']
    source = options.pop('stl')
    try:
        report = verify(source, **options)
    except (ValueError, OSError, UnicodeError, struct.error, ZeroDivisionError) as exc:
        report = {'schemaVersion': 1, 'passed': False, 'source': {'path': str(source.resolve())}, 'error': str(exc)}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
