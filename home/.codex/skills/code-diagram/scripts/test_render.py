"""Artifact and navigation checks; no application/service build or tests."""
import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from render import render
from drawio import layout
from routing import intersects, rectangle, route


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="code-diagram-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "repo with spaces"
        self.root.mkdir()
        self.source = self.root / "код & example.py"
        self.source.write_text('def check():\n    return "<yes> & no"\n\ndef save():\n    return 1\n')
        self.ref = {"symbol": "check", "file": self.source.name, "line": 1, "column": 1}
        self.model = {
            "version": 1, "title": "Проверка <заказа> & оплаты", "scope": "Ветки и обратная связь",
            "root": str(self.root), "direction": "LR",
            "nodes": [
                {"id": "check", "label": "Есть данные?", "shape": "decision", "description": "Проверить вход",
                 "sources": [self.ref, {**self.ref, "symbol": "save", "line": 4}],
                 "snippet": {"file": self.source.name, "start": 1, "end": 2}},
                {"id": "save", "label": "Сохранить", "shape": "store", "sources": [{**self.ref, "symbol": "save", "line": 4}]},
                {"id": "stop", "label": "Завершить", "sources": [], "note": "Концептуальное завершение"},
            ],
            "edges": [
                {"from": "check", "to": "save", "label": "да & готово", "relation": "call", "confidence": "confirmed", "evidence": [self.ref]},
                {"from": "check", "to": "stop", "label": "нет", "relation": "process", "confidence": "confirmed"},
                {"from": "save", "to": "check", "label": "повтор", "relation": "async", "confidence": "inferred", "note": "Предположение"},
            ],
            "paths": [{"id": "success", "label": "Успех", "nodes": ["check", "save"]}],
        }
        self.output = Path(self.temp.name).resolve() / "artifacts & diagrams" / "flow.drawio"

    def generate(self, model=None):
        render(copy.deepcopy(self.model if model is None else model), self.output)
        return ET.parse(self.output).getroot()

    def test_editable_graph_routes_sources_and_exact_navigation(self):
        xml = self.generate()
        pages = xml.findall("diagram")
        self.assertEqual(len(pages), 3)
        for page in pages:
            root = page.find("mxGraphModel/root")
            ids = [child.attrib["id"] for child in root]
            self.assertEqual(len(ids), len(set(ids)))
            for edge in root.findall("object/mxCell[@edge='1']"):
                self.assertIn(edge.attrib["source"], ids)
                self.assertIn(edge.attrib["target"], ids)
            for obj in root.findall("object[@hedietLinkedDataV1_path]"):
                destination = (self.output / obj.attrib["hedietLinkedDataV1_path"]).resolve()
                self.assertEqual(destination, self.source)
                line = int(obj.attrib["hedietLinkedDataV1_start_line_x-num"]) + 1
                col = int(obj.attrib["hedietLinkedDataV1_start_col_x-num"]) + 1
                url = urlsplit(obj.attrib["link"])
                self.assertEqual((url.scheme, url.netloc), ("vscode", "file"))
                self.assertEqual(unquote(url.path), f"{self.source}:{line}:{col}")
        root = pages[0].find("mxGraphModel/root")
        self.assertEqual(len(root.findall("object/mxCell[@edge='1']")), 3)
        node = root.find("object[@id='node-check']")
        self.assertIn('return "<yes> & no"', node.attrib["tooltip"])
        self.assertEqual(len(json.loads(node.attrib["codeDiagramSources"])), 2)
        self.assertNotIn("link", root.find("object[@id='node-stop']").attrib)
        self.assertEqual(len(pages[2].findall(".//object[@link]")), 2)
        self.assertEqual(pages[1].attrib["name"], "Успех")
        self.assertEqual(len(pages[1].findall(".//object[@codeDiagramSources]")), 2)
        self.assertEqual(len(pages[1].findall(".//mxCell[@edge='1']")), 1)

    def test_layout_keeps_branch_boxes_apart_and_manual_geometry(self):
        xml = self.generate()
        boxes = [obj.find("mxCell/mxGeometry").attrib for obj in xml.findall("diagram")[0].findall(".//object[@codeDiagramSources]")]
        for i, box in enumerate(boxes):
            x, y, w, h = (float(box[k]) for k in ("x", "y", "width", "height"))
            for other in boxes[i + 1:]:
                ox, oy, ow, oh = (float(other[k]) for k in ("x", "y", "width", "height"))
                self.assertTrue(x + w <= ox or ox + ow <= x or y + h <= oy or oy + oh <= y)
        geometry = {"x": 20, "y": 800, "width": 350, "height": 180}
        self.model["nodes"][0]["geometry"] = geometry
        xml = self.generate()
        actual = xml.find(".//object[@id='node-check']/mxCell/mxGeometry").attrib
        self.assertEqual({key: float(actual[key]) for key in geometry}, geometry)

    def test_bad_source_positions_paths_and_metadata_are_rejected(self):
        cases = []
        for change in ({"line": 999}, {"column": 999}, {"file": "../outside.py"}):
            model = copy.deepcopy(self.model)
            model["nodes"][0]["sources"][0].update(change)
            cases.append(model)
        model = copy.deepcopy(self.model)
        model["edges"][2].pop("note")
        cases.append(model)
        model = copy.deepcopy(self.model)
        model["paths"][0]["nodes"] = ["save", "stop"]
        cases.append(model)
        model = copy.deepcopy(self.model)
        model["nodes"][0]["geometry"] = {"x": float("nan"), "y": 0, "width": 100, "height": 100}
        cases.append(model)
        for model in cases:
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.generate(model)
        self.assertFalse(self.output.exists())

    def test_symlink_outside_checkout_is_rejected(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("secret = 1\n")
        (self.root / "linked.py").symlink_to(outside)
        self.model["nodes"][0]["sources"][0]["file"] = "linked.py"
        with self.assertRaises(ValueError):
            self.generate()

    def test_html_compatibility_and_generated_mermaid(self):
        html = self.output.with_suffix(".html")
        original = copy.deepcopy(self.model)
        render(self.model, html)
        self.assertEqual(self.model, original)
        self.assertIn("flowchart LR", html.read_text())
        self.assertIn("check", html.with_suffix(".mmd").read_text())
        self.assertNotIn("__MODEL_JSON__", html.read_text())
        legacy = copy.deepcopy(self.model)
        legacy["mermaid"] = 'flowchart TB\n check["Check"] --> save["Save"]'
        render(legacy, html)
        self.assertEqual(html.with_suffix(".mmd").read_text().strip(), legacy["mermaid"])

    def test_legacy_mermaid_cannot_silently_lose_edges(self):
        self.model["mermaid"] = 'flowchart LR\n check --> save'
        self.model["edges"] = []
        self.model["paths"] = []
        with self.assertRaisesRegex(ValueError, "add edge metadata"):
            self.generate()

    def test_generated_mermaid_keeps_reserved_ids_navigable(self):
        self.model["nodes"].append({"id": "end", "label": 'Конец "A&B"', "sources": [], "note": "Concept"})
        html = self.output.with_suffix(".html")
        render(copy.deepcopy(self.model), html)
        payload = re.search(r'<script id="model" type="application/json">(.*?)</script>', html.read_text(), re.S)
        model = json.loads(payload.group(1))
        self.assertIn("end", {node["id"] for node in model["nodes"]})
        self.assertEqual(model["mermaid_ids"]["end"], "code_end")
        self.assertIn('code_end["', model["mermaid"])
        self.assertIn("#34;A#38;B#34;", model["mermaid"])

    def test_routes_avoid_nodes_and_support_self_loops(self):
        positions = layout(self.model)
        for edge in self.model["edges"] + [{"from": "check", "to": "check"}]:
            points, _, _ = route(edge["from"], edge["to"], positions)
            self.assertGreater(len(points), 1)
            for a, b in zip(points, points[1:]):
                self.assertTrue(a[0] == b[0] or a[1] == b[1])
                for node_id, g in positions.items():
                    self.assertFalse(intersects(a, b, rectangle(g)), (edge, node_id, a, b))

    def test_connector_detours_around_an_existing_caption(self):
        positions = {"a": {"x": 70, "y": 170, "width": 250, "height": 100},
                     "b": {"x": 460, "y": 170, "width": 250, "height": 100}}
        caption_box = (340, 205, 440, 235)
        points, _, _ = route("a", "b", positions, avoid=[caption_box])
        for a, b in zip(points, points[1:]):
            self.assertFalse(intersects(a, b, caption_box))

    def test_dense_pages_and_long_labels_require_editorial_changes(self):
        model = copy.deepcopy(self.model)
        model["nodes"] += [{"id": f"extra{i}", "label": "Concept", "sources": [], "note": "No code"} for i in range(10)]
        with self.assertRaisesRegex(ValueError, "12 nodes"):
            self.generate(model)
        self.model["nodes"][0]["label"] = "A long explanation " * 30
        with self.assertRaisesRegex(ValueError, "short caption"):
            self.generate()
        self.model["nodes"][0]["caption"] = "Check input"
        self.generate()

    def test_views_preserve_all_edges_and_html_selects_one_view(self):
        self.model["views"] = [
            {"id": "main", "title": "Main", "nodes": ["check", "save"], "edges": [0, 2]},
            {"id": "exit", "title": "Exit", "nodes": ["check", "stop"], "edges": [1]},
        ]
        xml = self.generate()
        self.assertEqual([p.get("id") for p in xml.findall("diagram")], ["main", "exit", "sources-1"])
        html = self.output.with_suffix(".html")
        render(self.model, html, view="exit")
        payload = re.search(r'<script id="model" type="application/json">(.*?)</script>', html.read_text(), re.S)
        self.assertEqual({n["id"] for n in json.loads(payload.group(1))["nodes"]}, {"check", "stop"})
        self.model["views"][0]["edges"] = [0]
        with self.assertRaisesRegex(ValueError, "missing.*edges"):
            self.generate()


if __name__ == "__main__":
    unittest.main()
