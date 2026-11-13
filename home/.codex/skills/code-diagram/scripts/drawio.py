"""Native, uncompressed mxGraph XML; no draw.io service or runtime required."""
from collections import defaultdict, deque
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def validate_layout(model):
    if model.get("direction", "LR") not in ("LR", "RL", "TB", "TD", "BT"):
        raise ValueError("direction must be LR, RL, TB, TD or BT")
    for node in model["nodes"]:
        if node.get("shape", "process") not in ("process", "decision", "store", "external"):
            raise ValueError(f"Unknown shape: {node['id']}")
        if "geometry" not in node:
            continue
        geometry = node["geometry"]
        if not isinstance(geometry, dict) or set(geometry) != {"x", "y", "width", "height"}:
            raise ValueError("geometry needs x, y, width and height")
        for key, value in geometry.items():
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid geometry {key}: {node['id']}")
        if geometry["width"] < 80 or geometry["height"] < 40:
            raise ValueError("geometry must be at least 80 × 40")


def layout(model):
    """Rank a DAG after excluding DFS back edges, keeping cycles as connectors."""
    adjacency = defaultdict(list)
    for edge in model.get("edges", []):
        adjacency[edge["from"]].append(edge["to"])
    state, forward = {}, defaultdict(list)

    def visit(node_id):
        state[node_id] = 1
        for target in adjacency[node_id]:
            if state.get(target) == 1:
                continue
            forward[node_id].append(target)
            if target not in state:
                visit(target)
        state[node_id] = 2

    for node in model["nodes"]:
        if node["id"] not in state:
            visit(node["id"])
    degree = dict.fromkeys(state, 0)
    for targets in forward.values():
        for target in targets:
            degree[target] += 1
    queue = deque(key for key, value in degree.items() if value == 0)
    ranks = dict.fromkeys(state, 0)
    while queue:
        current = queue.popleft()
        for target in forward[current]:
            ranks[target] = max(ranks[target], ranks[current] + 1)
            degree[target] -= 1
            if degree[target] == 0:
                queue.append(target)
    direction = model.get("direction", "LR")
    horizontal = direction in ("LR", "RL")
    lanes, result = defaultdict(int), {}
    max_rank = max(ranks.values())
    for node in model["nodes"]:
        rank = ranks[node["id"]]
        lane = lanes[rank]
        lanes[rank] += 1
        if direction in ("RL", "BT"):
            rank = max_rank - rank
        result[node["id"]] = node.get("geometry", {
            "x": 40 + (rank * 420 if horizontal else lane * 360),
            "y": 170 + (lane * 230 if horizontal else rank * 250),
            "width": 280,
            "height": 160 if node.get("shape") == "decision" else 110,
        })
    return result


def code_attributes(ref, model, output):
    # The extension resolves relative to the diagram FILE, not its directory.
    # See hediet/vscode-drawio CodePosition.serialize/deserialize.
    path = (Path(model["root"]) / ref["file"]).resolve()
    position = {"line": ref["line"] - 1, "col": ref["column"] - 1}
    attributes = {
        "link": ref["url"],
        "hedietLinkedDataV1_path": Path(os.path.relpath(path, output)).as_posix(),
    }
    for end in ("start", "end"):
        for key, value in position.items():
            attributes[f"hedietLinkedDataV1_{end}_{key}_x-num"] = str(value)
    return attributes


def reference_label(ref):
    role = f" ({ref['label']})" if ref.get("label") else ""
    return f"{ref['symbol']}{role}\n{ref['file']}:{ref['line']}:{ref['column']}"


def tooltip(item):
    parts = [item[key] for key in ("description", "note") if item.get(key)]
    if item.get("relation"):
        parts.append(f"{item['relation']} · {item['confidence']}")
    parts.extend(reference_label(ref) for ref in item.get("sources", item.get("evidence", [])))
    if item.get("snippet"):
        parts.append(item["snippet"]["text"])
    return "\n\n".join(parts)


def page(document, page_id, name):
    diagram = ET.SubElement(document, "diagram", id=page_id, name=name)
    graph = ET.SubElement(diagram, "mxGraphModel", grid="1", gridSize="10", guides="1",
                          tooltips="1", connect="1", arrows="1", fold="1", page="0",
                          pageScale="1", pageWidth="1169", pageHeight="827", math="0", shadow="0")
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    return root


def vertex(root, cell_id, label, geometry, style, attributes=None):
    obj = ET.SubElement(root, "object", {"id": cell_id, "label": label, **(attributes or {})})
    cell = ET.SubElement(obj, "mxCell", vertex="1", parent="1", style=style)
    ET.SubElement(cell, "mxGeometry", {**{key: str(value) for key, value in geometry.items()}, "as": "geometry"})
    return obj


BASE_STYLE = "whiteSpace=wrap;html=0;fontSize=14;spacing=12;"
SHAPES = {
    "process": "rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "decision": "rhombus;fillColor=#fff2cc;strokeColor=#d6b656;",
    "store": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#d5e8d4;strokeColor=#82b366;",
    "external": "rounded=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;",
}


def graph_page(document, model, output, positions, route=None):
    page_id, name = (f"route-{route['id']}", route["label"]) if route else ("flow", model["title"])
    root = page(document, page_id, name)
    selected = set(route["nodes"]) if route else set()
    pairs = set(zip(route["nodes"], route["nodes"][1:])) if route else set()
    width = max(900, max(g["x"] + g["width"] for g in positions.values()) - 40)
    vertex(root, "heading", name + "\n" + model["scope"],
           {"x": 40, "y": 30, "width": width, "height": 100},
           BASE_STYLE + "text;align=left;verticalAlign=top;strokeColor=none;fillColor=none;fontSize=18;")
    for node in model["nodes"]:
        attrs = {"tooltip": tooltip(node), "codeDiagramSources": json.dumps(node["sources"], ensure_ascii=False)}
        if node["sources"]:
            attrs.update(code_attributes(node["sources"][0], model, output))
        symbols = ", ".join(dict.fromkeys(ref["symbol"] for ref in node["sources"] if ref["symbol"] not in node["label"]))
        label = node["label"] + ("\n" + symbols if symbols else "")
        style = BASE_STYLE + SHAPES[node.get("shape", "process")]
        if node["id"] in selected:
            style += "strokeColor=#d97706;strokeWidth=3;"
        vertex(root, "node-" + node["id"], label, positions[node["id"]], style, attrs)
    for index, edge in enumerate(model.get("edges", [])):
        attrs = {"id": f"edge-{index}", "label": edge["label"], "tooltip": tooltip(edge),
                 "relation": edge["relation"], "confidence": edge["confidence"],
                 "codeDiagramEvidence": json.dumps(edge.get("evidence", []), ensure_ascii=False)}
        if edge.get("evidence"):
            attrs.update(code_attributes(edge["evidence"][0], model, output))
        style = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;endFill=1;fontSize=12;labelBackgroundColor=#ffffff;"
        style += {"process": "strokeColor=#64748b;", "call": "strokeColor=#2563eb;",
                  "data": "strokeColor=#15803d;endArrow=open;", "async": "strokeColor=#9333ea;dashed=1;"}[edge["relation"]]
        if edge["confidence"] != "confirmed":
            style += "dashed=1;strokeColor=#b45309;"
            attrs["label"] += " [" + edge["confidence"] + "]"
        if (edge["from"], edge["to"]) in pairs:
            style += "strokeColor=#d97706;strokeWidth=3;"
        obj = ET.SubElement(root, "object", attrs)
        cell = ET.SubElement(obj, "mxCell", edge="1", parent="1", source="node-" + edge["from"],
                             target="node-" + edge["to"], style=style)
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def sources_page(document, model, output):
    entries = [(node["label"], ref) for node in model["nodes"] for ref in node["sources"]]
    entries.extend((edge["label"], ref) for edge in model.get("edges", []) for ref in edge.get("evidence", []))
    if not entries:
        return
    root = page(document, "sources", "Sources")
    for index, (label, ref) in enumerate(entries):
        vertex(root, f"source-{index}", label + "\n" + reference_label(ref),
               {"x": 40 + (index % 2) * 540, "y": 40 + (index // 2) * 180, "width": 500, "height": 140},
               BASE_STYLE + SHAPES["process"], code_attributes(ref, model, output))


def render_drawio(model, output):
    document = ET.Element("mxfile", host="code-diagram", agent="code-diagram", version="1.0",
                          compressed="false")
    positions = layout(model)
    graph_page(document, model, output, positions)
    for route in model.get("paths", []):
        graph_page(document, model, output, positions, route)
    sources_page(document, model, output)
    ET.indent(document, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(document).write(output, encoding="utf-8", xml_declaration=True)
    return output
