"""Independently verify a new central through hole in a native-exported plate STL.

The before mesh must be the rectangular plate with two centered mounting holes.
The after mesh must retain those holes and add one central circular through hole.
All geometry comes from STL triangles, never from an application or CLI receipt.
Only the standard library and sibling verify_plate.py are used. STL units are mm
by caller convention. Rotation and translation of the whole mesh are supported.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import verify_plate as plate
from verify_plate import (area, boundary_loops, circle, cross, dot, norm, read_stl,
                          segment_distance, sub, topology, unit, weld)


def inspect_extrusion(vertices, faces, planar_tolerance):
    """Recover the extrusion direction, rectangular frame and cap boundary loops."""
    origin = tuple(sum(p[j] for p in vertices) / len(vertices) for j in range(3))
    points = [sub(p, origin) for p in vertices]
    normals, clusters = [], []
    volume = 0.0
    for face in faces:
        a, b, c = (points[j] for j in face)
        normal = cross(sub(b, a), sub(c, a))
        weight = norm(normal) / 2
        normal = unit(normal)
        normals.append(normal)
        volume += dot(a, cross(b, c)) / 6
        if normal[max(range(3), key=lambda j: abs(normal[j]))] < 0:
            normal = tuple(-x for x in normal)
        group = next((g for g in clusters if dot(g[0], normal) > 1 - 1e-8), None)
        if group is None:
            clusters.append([normal, weight])
        else:
            group[1] += weight
    axis = max(clusters, key=lambda group: group[1])[0]
    heights = [dot(p, axis) for p in points]
    low, high = min(heights), max(heights)
    cap_indices = [[i for i, face in enumerate(faces)
                    if all(abs(heights[j] - level) <= planar_tolerance for j in face)] for level in (low, high)]
    if not all(cap_indices):
        raise ValueError('Could not identify two planar extrusion caps')
    cap_loops = [boundary_loops([faces[i] for i in indices]) for indices in cap_indices]
    u = unit(cross(axis, (1, 0, 0) if abs(axis[0]) < .8 else (0, 1, 0)))
    v = cross(axis, u)
    xy = [(dot(p, u), dot(p, v)) for p in points]
    outer = max(cap_loops[0], key=lambda loop: area([xy[j] for j in loop]))
    edge = max((sub(points[b], points[a]) for a, b in zip(outer, outer[1:] + outer[:1])), key=norm)
    u = unit(sub(edge, tuple(dot(edge, axis) * n for n in axis)))
    v = cross(axis, u)
    xy = [(dot(p, u), dot(p, v)) for p in points]
    spans = [max(p[j] for p in xy) - min(p[j] for p in xy) for j in range(2)]
    if spans[0] < spans[1]:
        u, v = v, tuple(-x for x in u)
        xy = [(dot(p, u), dot(p, v)) for p in points]
    lows = [min(p[j] for p in xy) for j in range(2)]
    highs = [max(p[j] for p in xy) for j in range(2)]
    midpoint = tuple((lows[j] + highs[j]) / 2 for j in range(2))
    xy = [sub(p, midpoint) for p in xy]
    cap_faces = set(cap_indices[0] + cap_indices[1])
    sides = [i for i in range(len(faces)) if i not in cap_faces]
    if not sides:
        raise ValueError('Extrusion has no side walls')
    boundary_segments = [(xy[a], xy[b]) for loop in cap_loops[0]
                         for a, b in zip(loop, loop[1:] + loop[:1])]
    side_vertices = {j for i in sides for j in faces[i]}
    return {
        'origin': origin, 'axes': {'length': u, 'width': v, 'thickness': axis},
        'length': highs[0] - lows[0], 'width': highs[1] - lows[1], 'thickness': high - low,
        'volume': volume, 'xy': xy, 'capLoops': cap_loops, 'heights': [low, high],
        'sideNormalTilt': max(abs(dot(normals[i], axis)) for i in sides),
        'sideProfileError': max(min(segment_distance(xy[j], a, b) for a, b in boundary_segments)
                                for j in side_vertices),
    }


def verify(path, *, before, length=80, width=40, thickness=6, pitch=60,
           existing_diameter=6, new_diameter=8, dimension_tolerance=.1,
           planar_tolerance=.002, surface_tolerance=.25, weld_tolerance=.00001,
           volume_relative_tolerance=.005):
    expected = {'lengthMm': length, 'widthMm': width, 'thicknessMm': thickness,
                'originalHolePitchMm': pitch, 'originalHoleDiameterMm': existing_diameter,
                'newCentralHoleDiameterMm': new_diameter, 'newHoleCenterMm': [0, 0]}
    scalars = [length, width, thickness, pitch, existing_diameter, new_diameter,
               dimension_tolerance, planar_tolerance, surface_tolerance, weld_tolerance,
               volume_relative_tolerance]
    if not all(math.isfinite(v) and v > 0 for v in scalars):
        raise ValueError('Dimensions and tolerances must be finite and positive')
    if (length < width or pitch + existing_diameter >= length
            or max(existing_diameter, new_diameter) >= width
            or pitch <= existing_diameter + new_diameter):
        raise ValueError('The three expected holes must be separated and wholly inside the rectangle')
    tolerances = dict(dimension_tolerance=dimension_tolerance, planar_tolerance=planar_tolerance,
                      surface_tolerance=surface_tolerance, weld_tolerance=weld_tolerance,
                      volume_relative_tolerance=volume_relative_tolerance)
    before_report = plate.verify(before, length=length, width=width, thickness=thickness,
                                 pitch=pitch, diameter=existing_diameter, **tolerances)
    triangles, source = read_stl(path)
    source['geometrySha256'] = hashlib.sha256(
        repr(sorted(tuple(sorted(tri)) for tri in triangles)).encode('ascii')).hexdigest()
    source['geometryHashMethod'] = 'Sorted triangles with sorted exact vertex tuples; ignores face/vertex order only'
    vertices, faces = weld(triangles, weld_tolerance)
    mesh = topology(vertices, faces, weld_tolerance)
    checks = []

    def check(name, passed, measured=None, target=None, tolerance=None):
        row = {'name': name, 'passed': bool(passed)}
        for key, value in [('measured', measured), ('expected', target), ('tolerance', tolerance)]:
            if value is not None:
                row[key] = value
        checks.append(row)

    def near(name, measured, target, tolerance=dimension_tolerance):
        check(name, abs(measured - target) <= tolerance, measured, target, tolerance)

    check('beforeIsVerifiedTwoHolePlate', before_report['passed'])
    check('geometryChanged', source['geometrySha256'] != before_report['source']['geometrySha256'])
    for key, value in [('nonManifoldEdges', 0), ('nonManifoldVertices', 0),
                       ('inconsistentlyOrientedEdges', 0), ('degenerateTriangles', 0),
                       ('duplicateTriangles', 0), ('connectedComponents', 1), ('eulerCharacteristic', -4)]:
        check(key, mesh[key] == value, mesh[key], value)
    report = {
        'schemaVersion': 1, 'passed': False, 'kind': 'independent-three-hole-plate-acceptance',
        'source': source, 'expected': expected, 'topology': mesh, 'checks': checks,
        'units': 'mm assumed by caller; STL has no unit metadata', 'tolerances': tolerances,
        'before': {'source': before_report['source'], 'passed': before_report['passed'],
                   'topology': before_report['topology'],
                   'failedChecks': [r for r in before_report['checks'] if not r['passed']]},
        'limitations': [
            'Verifies only a straight rectangular plate with the three specified circular through holes.',
            'Diameter is fitted to tessellation vertices; maximum chord sagitta is checked separately.',
            'Does not establish how the app produced the geometry, foreground display or persistence.',
            'No general-purpose triangle-intersection sweep is performed; accepted shape is constrained by cap loops and straight walls.',
        ],
    }
    if not all(row['passed'] for row in checks):
        report['error'] = 'Before comparison or three-hole closed-solid topology failed; geometric fitting skipped'
        return report

    result = inspect_extrusion(vertices, faces, planar_tolerance)
    for i, loops in enumerate(result['capLoops']):
        check(f'cap{i}HasOuterAndThreeHoleLoops', len(loops) == 4, len(loops), 4)
    if any(len(loops) != 4 for loops in result['capLoops']):
        report['error'] = 'Each end cap must contain exactly one outer rectangle and three hole boundaries'
        return report
    near('lengthMm', result['length'], length)
    near('widthMm', result['width'], width)
    near('thicknessMm', result['thickness'], thickness)
    check('straightSideNormals', result['sideNormalTilt'] < .001, result['sideNormalTilt'], tolerance=.001)
    near('straightSideProfileErrorMm', result['sideProfileError'], 0, planar_tolerance)
    caps = []
    expected_holes = [(-pitch / 2, 0, existing_diameter), (0, 0, new_diameter),
                      (pitch / 2, 0, existing_diameter)]
    for i, loops in enumerate(result['capLoops']):
        loops = sorted(loops, key=lambda loop: area([result['xy'][j] for j in loop]), reverse=True)
        outer = [result['xy'][j] for j in loops[0]]
        rectangle_error = max(min(abs(abs(p[0]) - result['length'] / 2),
                                  abs(abs(p[1]) - result['width'] / 2)) for p in outer)
        near(f'cap{i}RectangleBoundaryErrorMm', rectangle_error, 0, planar_tolerance)
        near(f'cap{i}RectangleAreaMm2', area(outer), result['length'] * result['width'],
             planar_tolerance * 2 * (result['length'] + result['width']))
        holes = sorted((circle([result['xy'][j] for j in loop]) for loop in loops[1:]),
                       key=lambda hole: hole['centerMm'][0])
        for j, (hole, expected_hole) in enumerate(zip(holes, expected_holes)):
            near(f'cap{i}Hole{j}CenterXmm', hole['centerMm'][0], expected_hole[0])
            near(f'cap{i}Hole{j}CenterYmm', hole['centerMm'][1], expected_hole[1])
            near(f'cap{i}Hole{j}DiameterMm', hole['diameterMm'], expected_hole[2])
            near(f'cap{i}Hole{j}CircleResidualMm', hole['radialResidualMm'], 0, planar_tolerance)
            check(f'cap{i}Hole{j}SimpleCircularLoop', hole['singleSimpleCircularBoundary'])
            check(f'cap{i}Hole{j}Sampling', hole['vertices'] >= 6 and hole['maximumAngularGapDegrees'] <= 60.0001,
                  {'vertices': hole['vertices'], 'maximumAngularGapDegrees': hole['maximumAngularGapDegrees']})
            check(f'cap{i}Hole{j}ChordSagittaMm', hole['maximumChordSagittaMm'] <= surface_tolerance,
                  hole['maximumChordSagittaMm'], tolerance=surface_tolerance)
        near(f'cap{i}OriginalHolePitchMm', norm(sub(holes[2]['centerMm'], holes[0]['centerMm'])), pitch)
        caps.append({'heightMm': result['heights'][i], 'holes': holes,
                     'netPolygonAreaMm2': area(outer) - sum(h['polygonAreaMm2'] for h in holes)})
    for j in range(3):
        near(f'hole{j}ThroughCenterAlignmentMm', norm(sub(caps[0]['holes'][j]['centerMm'], caps[1]['holes'][j]['centerMm'])),
             0, planar_tolerance)
        near(f'hole{j}ThroughDiameterChangeMm', caps[0]['holes'][j]['diameterMm'], caps[1]['holes'][j]['diameterMm'],
             planar_tolerance)
    before_measure = before_report['measurements']
    ideal_volume = (length * width - 2 * math.pi * (existing_diameter / 2) ** 2
                    - math.pi * (new_diameter / 2) ** 2) * thickness
    polygon_volume = sum(cap['netPolygonAreaMm2'] for cap in caps) / 2 * result['thickness']
    near('volumeVsIndependentExtrusionMm3', abs(result['volume']), polygon_volume,
         max(.001, polygon_volume * .00001))
    near('volumeVsExpectedAnalyticMm3', abs(result['volume']), ideal_volume,
         ideal_volume * volume_relative_tolerance)
    check('outwardWinding', result['volume'] > 0, result['volume'])
    for key in ('length', 'width', 'thickness'):
        near(key + 'RetainedFromBeforeMm', result[key], before_measure[key + 'Mm'])
    old_before_area = sum(h['polygonAreaMm2'] for cap in before_measure['caps'] for h in cap['holes']) / 2
    old_after_area = sum(cap['holes'][j]['polygonAreaMm2'] for cap in caps for j in (0, 2)) / 2
    new_hole_area = sum(cap['holes'][1]['polygonAreaMm2'] for cap in caps) / 2
    removed_volume = abs(before_measure['signedVolumeMm3']) - abs(result['volume'])
    ideal_new_hole_volume = math.pi * (new_diameter / 2) ** 2 * thickness
    measured_new_hole_volume = new_hole_area * result['thickness']
    # Old circles may be re-tessellated without changing the native cylinder. Account
    # for their independently measured polygon areas rather than accepting any loss.
    old_mesh_change = (old_after_area - old_before_area) * result['thickness']
    observed_outer_change = ((before_measure['lengthMm'] * before_measure['widthMm'])
                             - result['length'] * result['width']) * result['thickness']
    thickness_change = ((before_measure['thicknessMm'] - result['thickness'])
                        * before_measure['caps'][0]['netPolygonAreaMm2'])
    expected_removal_from_mesh = measured_new_hole_volume + old_mesh_change + observed_outer_change + thickness_change
    check('materialWasRemoved', removed_volume > .85 * ideal_new_hole_volume,
          removed_volume, 'greater than 85% of the expected ideal center-hole volume')
    near('removedMaterialMatchesNewThroughHoleMm3', removed_volume, expected_removal_from_mesh,
         max(.002, polygon_volume * .00002))
    report['measurements'] = {
        'lengthMm': result['length'], 'widthMm': result['width'], 'thicknessMm': result['thickness'],
        'caps': caps, 'signedVolumeMm3': result['volume'], 'idealExpectedVolumeMm3': ideal_volume,
        'measuredPolygonExtrusionVolumeMm3': polygon_volume,
        'worldOriginMm': result['origin'], 'frameAxes': result['axes'],
    }
    report['comparison'] = {
        'beforeVolumeMm3': before_measure['signedVolumeMm3'], 'afterVolumeMm3': result['volume'],
        'removedVolumeMm3': removed_volume, 'idealNewHoleVolumeMm3': ideal_new_hole_volume,
        'newHolePolygonPrismVolumeMm3': measured_new_hole_volume,
        'oldHoleRetessellationVolumeAdjustmentMm3': old_mesh_change,
        'outerFootprintVolumeAdjustmentMm3': observed_outer_change,
        'thicknessVolumeAdjustmentMm3': thickness_change,
        'expectedRemovalFromMeasuredProfilesMm3': expected_removal_from_mesh,
        'beforeEulerCharacteristic': before_report['topology']['eulerCharacteristic'],
        'afterEulerCharacteristic': mesh['eulerCharacteristic'],
    }
    report['passed'] = all(row['passed'] for row in checks)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stl', type=Path, help='Native exported mesh after the cut')
    parser.add_argument('--before', type=Path, required=True, help='Native two-hole mesh before the cut')
    for key, default in [('length', 80), ('width', 40), ('thickness', 6), ('pitch', 60),
                         ('existing-diameter', 6), ('new-diameter', 8), ('dimension-tolerance', .1),
                         ('planar-tolerance', .002), ('surface-tolerance', .25), ('weld-tolerance', .00001),
                         ('volume-relative-tolerance', .005)]:
        parser.add_argument('--' + key, type=float, default=default)
    parser.add_argument('--out', type=Path)
    args = vars(parser.parse_args())
    output = args.pop('out')
    source = args.pop('stl')
    try:
        report = verify(source, **args)
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
