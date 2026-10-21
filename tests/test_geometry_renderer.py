"""幾何不變量與公開規格的回歸測試，不依賴 PNG 後端。"""
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/math-geometry/scripts'
sys.path.insert(0, str(SCRIPTS))
from geometry_renderer import render_figure

NS = {'s': 'http://www.w3.org/2000/svg'}


def svg(kind, config, **extra):
    return ET.fromstring(render_figure({'type': kind, 'config': config, **extra}))


def triangle_edges(root):
    return [((float(e.get('x1')), float(e.get('y1'))),
             (float(e.get('x2')), float(e.get('y2'))))
            for e in root.findall('s:line', NS)[:3]]


def text_positions(root):
    return {''.join(e.itertext()): (float(e.get('x')), float(e.get('y')))
            for e in root.findall('s:text', NS)}


class GeometryTests(unittest.TestCase):
    def test_right_trapezoid_has_parallel_bases_and_two_left_right_angles(self):
        root = svg('quadrilateral', {'subtype': 'right_trapezoid'})
        pts = [tuple(map(float, p.split(','))) for p in root.find('s:polygon', NS).get('points').split()]
        a, b, c, d = pts
        self.assertAlmostEqual(a[1], b[1])
        self.assertAlmostEqual(c[1], d[1])
        self.assertAlmostEqual(a[0], d[0])
        self.assertLess(d[0], c[0])
        self.assertEqual(len(root.findall('s:polyline', NS)), 2)

    def test_rhombus_has_four_equal_sides_and_documented_vertex_order(self):
        root = svg('quadrilateral', {'subtype': 'rhombus'})
        pts = [tuple(map(float, p.split(','))) for p in root.find('s:polygon', NS).get('points').split()]
        lengths = [math.dist(pts[i], pts[(i+1)%4]) for i in range(4)]
        for length in lengths:
            self.assertAlmostEqual(length, lengths[0], delta=0.002)
        self.assertLess(pts[0][0], pts[1][0])
        self.assertGreater(pts[0][1], pts[3][1])

    def test_custom_centroid_is_mean_of_the_rendered_vertices(self):
        root = svg('triangle_center', {'center_type': 'centroid', 'triangle': {
            'vertices': {'A': [0, 3], 'B': [6, 3], 'C': [1.2, 0]}}})
        vertices = [edge[0] for edge in triangle_edges(root)]
        center = next(e for e in root.findall('s:circle', NS) if e.get('r') == '5')
        self.assertAlmostEqual(float(center.get('cx')), sum(p[0] for p in vertices)/3, delta=0.002)
        self.assertAlmostEqual(float(center.get('cy')), sum(p[1] for p in vertices)/3, delta=0.002)

    def test_custom_circumcircle_passes_through_vertices_and_fits_canvas(self):
        root = svg('triangle_center', {'center_type': 'circumcenter', 'triangle': {
            'vertices': {'A': [0, 3], 'B': [6, 3], 'C': [1.2, 0]}}})
        circle = next(e for e in root.findall('s:circle', NS) if e.get('fill') == 'none')
        x, y, radius = (float(circle.get(k)) for k in ('cx', 'cy', 'r'))
        for p, _ in triangle_edges(root):
            self.assertAlmostEqual(math.dist(p, (x, y)), radius, delta=0.003)
        self.assertGreaterEqual(min(x-radius, y-radius), 0)
        self.assertLessEqual(x+radius, float(root.get('width')))
        self.assertLessEqual(y+radius, float(root.get('height')))

    def test_custom_incenter_is_equidistant_from_all_three_sides(self):
        root = svg('triangle_center', {'center_type': 'incenter', 'triangle': {
            'vertices': {'A': [0, 3], 'B': [6, 3], 'C': [1.2, 0]}}})
        circle = next(e for e in root.findall('s:circle', NS) if e.get('fill') == 'none')
        x, y, radius = (float(circle.get(k)) for k in ('cx', 'cy', 'r'))
        for (ax, ay), (bx, by) in triangle_edges(root):
            distance = abs((bx-ax)*(ay-y)-(ax-x)*(by-ay))/math.hypot(bx-ax, by-ay)
            self.assertAlmostEqual(distance, radius, delta=0.003)

    def test_conflicting_geometry_is_rejected(self):
        cases = [
            ('triangle', {'subtype': 'general', 'right_angle_at': 'A'}),
            ('triangle', {'subtype': 'isosceles', 'equal_marks': {'AB': 1, 'AC': 1}}),
            ('triangle', {'subtype': 'isosceles', 'angle_arcs': {'B': 1, 'C': 1}}),
            ('triangle', {'vertices': {'A': [0, 0], 'B': [1, 1], 'C': [2, 2]}}),
            ('triangle', {'side_labels': {'AD': '5'}}),
            ('triangle', {'vertices': {'A': [0, 0], 'B': [1, 1]}}),
            ('quadrilateral', {'subtype': 'parallelogram', 'right_angles': ['A']}),
            ('circle', {'points': {'A': 0, 'B': 120}, 'diameter': ['A', 'B']}),
            ('circle', {'points': {'A': 0}, 'chords': [['A', 'B']]}),
        ]
        for kind, cfg in cases:
            with self.subTest(kind=kind, config=cfg), self.assertRaises(ValueError):
                svg(kind, cfg)

    def test_side_label_is_outside_and_independent_of_edge_spelling(self):
        positions = []
        for edge in ('AB', 'BA'):
            root = svg('quadrilateral', {'subtype': 'rectangle', 'side_labels': {edge: '長'}})
            a = tuple(map(float, root.find('s:polygon', NS).get('points').split()[0].split(',')))
            position = text_positions(root)['長']
            self.assertGreater(position[1], a[1])
            positions.append(position)
        self.assertEqual(*positions)

    def test_manual_label_offset_and_xml_text_are_preserved(self):
        cfg = {'subtype': 'rectangle', 'side_labels': {'AB': 'a & b'}}
        base = text_positions(svg('quadrilateral', cfg))['a & b']
        cfg['label_offsets'] = {'AB': [0, 6]}
        shifted = text_positions(svg('quadrilateral', cfg))['a & b']
        self.assertEqual(shifted, (base[0], base[1]+6))

    def test_algebraic_side_label_fits_right_margin_at_exam_canvas_size(self):
        root = svg('quadrilateral', {'subtype':'rectangle','side_labels':{'AB':'2x+7','BC':'x+4'}})
        labels = text_positions(root)
        self.assertIn('x+4', labels)
        self.assertGreater(labels['x+4'][0], 242)
        self.assertLess(labels['x+4'][0], 265)

    def test_all_documented_figure_examples_render(self):
        files = [SCRIPTS.parent/'SKILL.md', SCRIPTS.parent/'references/figure-catalog.md']
        total = 0
        for path in files:
            for block in re.findall(r'```json\s*(.*?)```', path.read_text(encoding='utf-8'), re.S):
                try:
                    spec = json.loads(block)
                except json.JSONDecodeError:  # 文件中的 schema 佔位符
                    continue
                for figure in spec.get('figures', [spec]):
                    if 'type' not in figure:
                        continue
                    with self.subTest(file=path.name, figure=figure.get('id', figure['type'])):
                        ET.fromstring(render_figure(figure))
                    total += 1
        self.assertGreaterEqual(total, 25)

    def test_visual_review_cases_render_at_normal_and_small_canvas_sizes(self):
        fixture = Path(__file__).parent/'fixtures/geometry_review.json'
        for figure in json.loads(fixture.read_text(encoding='utf-8'))['figures']:
            with self.subTest(figure=figure['id']):
                root = ET.fromstring(render_figure(figure))
                self.assertGreater(len(root.findall('s:text', NS)), 2)

    def test_cli_returns_nonzero_and_records_failed_figure(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = Path(folder)/'bad.json'
            spec.write_text(json.dumps({'id': 'bad', 'type': 'circle', 'config': {
                'points': {'A': 0, 'B': 90}, 'diameter': ['A', 'B']}}), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPTS/'geometry_renderer.py'),
                                     str(spec), folder], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            manifest = json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))
            self.assertIn('error', manifest[0])
            self.assertFalse((Path(folder)/'bad.svg').exists())


if __name__ == '__main__':
    unittest.main()
