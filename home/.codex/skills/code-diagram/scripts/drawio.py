"""Native, uncompressed mxGraph XML; no draw.io service or runtime required."""
from collections import defaultdict, deque
import json
import math
import os
from pathlib import Path
import copy
import textwrap
import xml.etree.ElementTree as ET

from routing import route, label_position, rectangle


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


def visible_label(node, geometry):
    caption = node.get("caption", node["label"])
    if not isinstance(caption, str) or not caption.strip():
        raise ValueError(f"caption must be nonempty: {node['id']}")
    columns = max(8, int((geometry["width"] - 32) / 10.5))
    lines = [line for part in caption.splitlines() for line in textwrap.wrap(part, columns)]
    if len(lines) > 3:
        raise ValueError(f"Node {node['id']} needs a short caption (at most 3 lines); keep details in its tooltip")
    return "\n".join(lines)


def page_models(model):
    """Explicit views preserve the graph while splitting its presentation."""
    views = model.get("views")
    if views is None:
        yield "flow", model
        # Named routes show only their nodes and route edges, not copies of the graph.
        for path in model.get("paths", []):
            ids = set(path["nodes"])
            pairs = set(zip(path["nodes"], path["nodes"][1:]))
            part = {**model, "title": path["label"], "nodes": [copy.deepcopy(n) for n in model["nodes"] if n["id"] in ids],
                    "edges": [e for e in model.get("edges", []) if (e["from"], e["to"]) in pairs]}
            for n in part["nodes"]:
                n.pop("geometry", None)
            yield "route-" + path["id"], part
        return
    if not isinstance(views, list) or not views:
        raise ValueError("views must be a nonempty list")
    nodes = {n["id"]: n for n in model["nodes"]}
    seen, covered_nodes, covered_edges = set(), set(), set()
    for view in views:
        view_id = view.get("id")
        if not isinstance(view_id, str) or not view_id.isascii() or not view_id.replace('_', '').isalnum() or view_id in seen or view_id.startswith('sources'):
            raise ValueError("Each view needs a unique ASCII id, excluding the sources prefix")
        seen.add(view_id)
        ids = view.get("nodes")
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)) or any(i not in nodes for i in ids):
            raise ValueError(f"View {view_id} needs unique existing node IDs")
        indices = view.get("edges", [i for i, e in enumerate(model.get("edges", [])) if e["from"] in ids and e["to"] in ids])
        if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(model.get("edges", [])) for i in indices):
            raise ValueError(f"Invalid edge indices in view {view_id}")
        edges = [model["edges"][i] for i in indices]
        if any(e["from"] not in ids or e["to"] not in ids for e in edges):
            raise ValueError(f"View {view_id} omits an edge endpoint")
        if not isinstance(view.get("title"), str) or not view["title"].strip():
            raise ValueError(f"View {view_id} needs a title")
        geometry = view.get("geometry", {})
        if not isinstance(geometry, dict) or any(i not in ids for i in geometry):
            raise ValueError(f"Invalid view geometry: {view_id}")
        chosen = []
        for node_id in ids:
            node = copy.deepcopy(nodes[node_id])
            node.pop("geometry", None)
            if node_id in geometry:
                node["geometry"] = geometry[node_id]
            chosen.append(node)
        part = {**model, "title": view["title"], "scope": view.get("scope", model["scope"]),
                "direction": view.get("direction", model.get("direction", "LR")), "nodes": chosen, "edges": edges}
        validate_layout(part)
        covered_nodes.update(ids)
        covered_edges.update(indices)
        yield view_id, part
    if covered_nodes != set(nodes) or covered_edges != set(range(len(model.get("edges", [])))):
        missing_nodes = sorted(set(nodes) - covered_nodes)
        missing_edges = sorted(set(range(len(model.get("edges", [])))) - covered_edges)
        raise ValueError(f"Views must preserve all nodes and edges; missing nodes={missing_nodes}, edges={missing_edges}")


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
        # Fold long chains into a readable serpentine instead of an endless strip.
        band, column = divmod(rank, 3)
        max_lanes = max(list(ranks.values()).count(r) for r in set(ranks.values()))
        if band % 2:
            column = 2 - column
        x = column * 390 if horizontal else (band * max_lanes + lane) * 390
        y = (band * max_lanes + lane) * 200 if horizontal else column * 200
        result[node["id"]] = node.get("geometry", {"x": 70 + x, "y": 200 + y, "width": 250, "height": 100})
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
    parts = [item[key] for key in ("label", "description", "note") if item.get(key)]
    if item.get("relation"):
        parts.append(f"{item['relation']} · {item['confidence']}")
    parts.extend(reference_label(ref) for ref in item.get("sources", item.get("evidence", [])))
    if item.get("snippet"):
        parts.append(item["snippet"]["text"])
    return "\n\n".join(parts)


def page(document, page_id, name):
    diagram = ET.SubElement(document, "diagram", id=page_id, name=name)
    graph = ET.SubElement(diagram, "mxGraphModel", grid="0", gridSize="10", guides="1",
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


BASE_STYLE = "whiteSpace=wrap;html=0;fontFamily=Helvetica;fontSize=18;spacing=12;"
SHAPES = {
    "process": "rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "decision": "rhombus;fillColor=#fff2cc;strokeColor=#d6b656;",
    "store": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#d5e8d4;strokeColor=#82b366;",
    "external": "rounded=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;",
}


def graph_page(document, model, output, positions, page_id="flow", page_ids=()):
    name = model["title"]
    if len(model["nodes"]) > 12 and not model.get("allow_large_page"):
        raise ValueError("More than 12 nodes on one page: author a compact overview and detail views")
    if len(model["scope"]) > 200:
        raise ValueError(f"Page {page_id} needs a short scope (up to 200 characters); put detail in tooltips")
    root = page(document, page_id, name)
    width = max(1000, max(g["x"] + g["width"] for g in positions.values()) + 70)
    height = max(g["y"] + g["height"] for g in positions.values()) + 90
    if (width > 1500 or height > 1100) and not model.get("allow_large_page"):
        raise ValueError(f"Page {page_id} is {width}×{height}; compact its geometry or split the view")
    boxes = list(positions.items())
    for i, (node_id, g) in enumerate(boxes):
        a = rectangle(g, 12)
        for other_id, h in boxes[i + 1:]:
            b = rectangle(h, 12)
            if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                raise ValueError(f"Nodes {node_id}/{other_id} overlap or leave no routing gap")
    vertex(root, "heading", name, {"x": 50, "y": 20, "width": width - 100, "height": 42},
           BASE_STYLE + "text;align=left;strokeColor=none;fillColor=none;fontSize=26;fontStyle=1;")
    vertex(root, "scope", "\n".join(textwrap.wrap(model["scope"], 110)),
           {"x": 50, "y": 68, "width": width - 100, "height": 66},
           BASE_STYLE + "text;align=left;strokeColor=none;fillColor=none;fontSize=14;fontColor=#475569;")
    for node in model["nodes"]:
        attrs = {"tooltip": tooltip(node), "codeDiagramSources": json.dumps(node["sources"], ensure_ascii=False)}
        if node["sources"]:
            attrs.update(code_attributes(node["sources"][0], model, output))
        label = visible_label(node, positions[node["id"]])
        style = BASE_STYLE + SHAPES[node.get("shape", "process")]
        if node.get("detail_view"):
            if node["detail_view"] not in page_ids:
                raise ValueError(f"Missing detail view: {node['detail_view']}")
            attrs["link"] = "data:page/id," + node["detail_view"]
        vertex(root, "node-" + node["id"], label, positions[node["id"]], style, attrs)
    segments, labels = [], []
    for index, edge in enumerate(model.get("edges", [])):
        caption = edge.get("caption", edge["label"])
        if not isinstance(caption, str) or len(caption) > 32 or "\n" in caption:
            raise ValueError(f"Edge {edge['from']} → {edge['to']} needs a short caption (up to 32 characters)")
        attrs = {"id": f"edge-{index}", "label": caption, "tooltip": tooltip(edge),
                 "relation": edge["relation"], "confidence": edge["confidence"],
                 "codeDiagramEvidence": json.dumps(edge.get("evidence", []), ensure_ascii=False)}
        if edge.get("evidence"):
            attrs.update(code_attributes(edge["evidence"][0], model, output))
        points, exit_port, entry_port = route(edge["from"], edge["to"], positions, segments, labels)
        segments.extend(zip(points, points[1:]))
        try:
            label = label_position(points, caption, positions, labels, segments)
        except ValueError as exc:
            raise ValueError(f"{page_id}: {edge['from']} → {edge['to']}: {exc}") from exc
        style = ("noEdgeStyle=1;rounded=1;html=0;endArrow=block;endFill=1;strokeWidth=1.5;fontSize=13;"
                 "labelBackgroundColor=#ffffff;" + f"exitX={exit_port[0]};exitY={exit_port[1]};entryX={entry_port[0]};entryY={entry_port[1]};exitPerimeter=0;entryPerimeter=0;")
        style += {"process": "strokeColor=#64748b;", "call": "strokeColor=#2563eb;",
                  "data": "strokeColor=#15803d;endArrow=open;", "async": "strokeColor=#9333ea;dashed=1;"}[edge["relation"]]
        if edge["confidence"] != "confirmed":
            style += "dashed=1;strokeColor=#b45309;"
        obj = ET.SubElement(root, "object", attrs)
        cell = ET.SubElement(obj, "mxCell", edge="1", parent="1", source="node-" + edge["from"],
                             target="node-" + edge["to"], style=style)
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        waypoints = ET.SubElement(geometry, "Array", {"as": "points"})
        for x, y in points[1:-1]:
            ET.SubElement(waypoints, "mxPoint", x=str(x), y=str(y))
        if label:
            relative, dx, dy, box = label
            geometry.set("x", str(relative))
            ET.SubElement(geometry, "mxPoint", {"x": str(dx), "y": str(dy), "as": "offset"})
            obj.set("codeDiagramLabelBox", json.dumps(box))
    content_bottom = max([g["y"] + g["height"] for g in positions.values()] +
                         [p[1] for segment in segments for p in segment] + [box[3] for box in labels])
    footer_y = content_bottom + 36
    if page_ids and page_id != page_ids[0]:
        vertex(root, "back", "← Обзор", {"x": 50, "y": footer_y, "width": 140, "height": 32},
               BASE_STYLE + "text;fillColor=none;strokeColor=none;fontSize=14;fontColor=#2563eb;",
               {"link": "data:page/id," + page_ids[0]})
    vertex(root, "legend", "Синий: вызов · зелёный: данные · серый: этап · фиолетовый: async · оранжевый: предположение",
           {"x": 210, "y": footer_y, "width": width - 250, "height": 32},
           BASE_STYLE + "text;fillColor=none;strokeColor=none;fontSize=11;fontColor=#64748b;")


def sources_page(document, model, output):
    entries = [(node["label"], ref) for node in model["nodes"] for ref in node["sources"]]
    entries.extend((edge["label"], ref) for edge in model.get("edges", []) for ref in edge.get("evidence", []))
    if not entries:
        return
    # Deduplicate source coordinates and keep every source card at a readable scale.
    unique = {}
    for label, ref in entries:
        unique.setdefault((ref["file"], ref["line"], ref["column"], ref["symbol"]), (label, ref))
    entries = list(unique.values())
    for index, (label, ref) in enumerate(entries):
        slot = index % 8
        if slot == 0:
            root = page(document, f"sources-{index // 8 + 1}", f"Sources {index // 8 + 1}")
        attrs = {**code_attributes(ref, model, output), "tooltip": label + "\n" + reference_label(ref)}
        caption = "\n".join(textwrap.wrap(ref["symbol"], 42)) + "\n" + Path(ref["file"]).name + ":" + str(ref["line"])
        vertex(root, f"source-{index}", caption,
               {"x": 40 + (slot % 2) * 520, "y": 40 + (slot // 2) * 140, "width": 470, "height": 110},
               BASE_STYLE + SHAPES["process"], attrs)


def render_drawio(model, output):
    document = ET.Element("mxfile", host="code-diagram", agent="code-diagram", version="1.0",
                          compressed="false")
    pages = list(page_models(model))
    page_ids = [page_id for page_id, _ in pages]
    for page_id, part in pages:
        graph_page(document, part, output, layout(part), page_id, page_ids)
    sources_page(document, model, output)
    ET.indent(document, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(document).write(output, encoding="utf-8", xml_declaration=True)
    return output
