#!/usr/bin/env python3
"""Render an inspected code diagram as editable draw.io XML or offline HTML."""
import argparse
import base64
import copy
import json
from pathlib import Path
import re
from urllib.parse import quote

from drawio import render_drawio, validate_layout, page_models

SKILL_DIR = Path(__file__).resolve().parent.parent


def positive_int(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def checked_file(root, files, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Source file must be relative to root")
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Source outside root or missing: {relative}")
    if path not in files:
        files[path] = path.read_text(encoding="utf-8").splitlines()
    return path, files[path]


def checked_reference(root, files, ref):
    if not isinstance(ref, dict) or not isinstance(ref.get("symbol"), str) or not ref["symbol"].strip():
        raise ValueError("Missing source symbol")
    path, lines = checked_file(root, files, ref.get("file"))
    line = positive_int(ref.get("line"), "line")
    column = positive_int(ref.get("column", 1), "column")
    if line > len(lines) or column > len(lines[line - 1]) + 1:
        raise ValueError(f"Source position out of range: {ref['file']}:{line}:{column}")
    ref["column"] = column
    ref["url"] = f"vscode://file{quote(path.as_posix(), safe='/')}:{line}:{column}"
    return path


def prepare_model(model):
    if not isinstance(model, dict) or model.get("version") != 1:
        raise ValueError("Expected a version 1 diagram object")
    for key in ("title", "scope", "root"):
        if not isinstance(model.get(key), str) or not model[key].strip():
            raise ValueError(f"Missing nonempty string: {key}")
    root = Path(model["root"]).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("root must be an existing absolute directory")
    root = root.resolve()
    source = model.get("mermaid")
    if source is not None and (not isinstance(source, str) or not re.match(r"^\s*(flowchart|graph)\s+(TB|TD|BT|LR|RL)\b", source)):
        raise ValueError("Expected a Mermaid flowchart with an explicit direction")
    if source is not None and re.search(r"\bclick\s|%%\{|<\s*/?\s*[A-Za-z]|@\{", source):
        raise ValueError("Use plain labels; links are generated from source metadata")
    nodes = model.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("nodes must be a nonempty list")
    seen, files = set(), {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("Each node must be an object")
        node_id = node.get("id", "")
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", node_id) or node_id in seen:
            raise ValueError(f"Invalid or duplicate node id: {node_id}")
        seen.add(node_id)
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            raise ValueError(f"Missing label: {node_id}")
        if "description" in node and (not isinstance(node["description"], str) or not node["description"].strip()):
            raise ValueError(f"description must be nonempty text: {node_id}")
        sources = node.get("sources")
        if not isinstance(sources, list):
            raise ValueError(f"sources must be a list: {node_id}")
        if not sources and not (isinstance(node.get("note"), str) and node["note"].strip()):
            raise ValueError(f"Explain missing sources with a note: {node_id}")
        source_paths = {checked_reference(root, files, ref) for ref in sources}
        if "snippet" in node:
            snippet = node["snippet"]
            if not isinstance(snippet, dict):
                raise ValueError(f"snippet must be an object: {node_id}")
            path, lines = checked_file(root, files, snippet.get("file"))
            if path not in source_paths:
                raise ValueError(f"snippet file must be one of the node sources: {node_id}")
            start = positive_int(snippet.get("start"), "snippet start")
            end = positive_int(snippet.get("end"), "snippet end")
            if end < start or end > len(lines) or end - start > 4:
                raise ValueError(f"snippet must contain 1–5 existing lines: {node_id}")
            snippet["text"] = "\n".join(lines[start - 1:end])
            snippet["url"] = f"vscode://file{quote(path.as_posix(), safe='/')}:{start}:1"
    edges = model.get("edges", [])
    if not isinstance(edges, list):
        raise ValueError("edges must be a list")
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("Each edge must be an object")
        if edge.get("from") not in seen or edge.get("to") not in seen:
            raise ValueError("Edge endpoints must be declared nodes")
        if edge.get("relation") not in ("process", "call", "data", "async"):
            raise ValueError("Edge relation must be process, call, data, or async")
        if edge.get("confidence") not in ("confirmed", "inferred", "unresolved"):
            raise ValueError("Edge confidence must be confirmed, inferred, or unresolved")
        if not isinstance(edge.get("label"), str) or not edge["label"].strip():
            raise ValueError("Each edge needs a label")
        if edge["confidence"] != "confirmed" and (not isinstance(edge.get("note"), str) or not edge["note"].strip()):
            raise ValueError("Inferred and unresolved edges need an explanation")
        evidence = edge.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("edge evidence must be a list")
        for ref in evidence:
            checked_reference(root, files, ref)
    paths = model.get("paths", [])
    if not isinstance(paths, list):
        raise ValueError("paths must be a list")
    path_ids = set()
    pairs = {(edge["from"], edge["to"]) for edge in edges}
    for path in paths:
        if not isinstance(path, dict) or not isinstance(path.get("id"), str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", path["id"]) or path["id"] in path_ids:
            raise ValueError("Invalid or duplicate path id")
        path_ids.add(path["id"])
        if not isinstance(path.get("label"), str) or not path["label"].strip():
            raise ValueError("Each path needs a label")
        chain = path.get("nodes")
        if not isinstance(chain, list) or len(chain) < 2 or any(node_id not in seen for node_id in chain):
            raise ValueError("Each path needs at least two declared nodes")
        if any(pair not in pairs for pair in zip(chain, chain[1:])):
            raise ValueError(f"Path contains a connection missing from edges: {path['id']}")
    model["root"] = str(root)
    validate_layout(model)
    return model


def mermaid_from_model(model):
    # JSON-quoted labels need Mermaid entities for punctuation with syntax meaning.
    def label(value):
        return "".join(f"#{ord(char)};" if char in '&"<>#\n' else char for char in value)

    # Avoid Mermaid keywords such as 'end' without changing the model's stable IDs.
    ids = {node["id"]: "code_" + node["id"] for node in model["nodes"]}
    model["mermaid_ids"] = ids
    lines = [f"flowchart {model.get('direction', 'LR')}"]
    for node in model["nodes"]:
        title = node.get("caption", node["label"])
        left, right = ('{', '}') if node.get("shape") == "decision" else ('[', ']')
        lines.append(f'  {ids[node["id"]]}{left}"{label(title)}"{right}')
    for edge in model.get("edges", []):
        arrow = "-->" if edge["confidence"] == "confirmed" else "-.->"
        caption = edge.get("caption", edge["label"])
        annotation = f'|"{label(caption)}"|' if caption else ""
        lines.append(f'  {ids[edge["from"]]} {arrow}{annotation} {ids[edge["to"]]}')
    return "\n".join(lines)


def render(model, output, view=None):
    model = prepare_model(copy.deepcopy(model))
    output = output.expanduser().resolve()
    if output.suffix.lower() == ".drawio":
        if view is not None:
            raise ValueError("--view selects an HTML view; draw.io contains all views")
        if model.get("mermaid") and len(model["nodes"]) > 1 and not model.get("edges"):
            raise ValueError("draw.io uses nodes/edges; add edge metadata to this older Mermaid model first")
        return render_drawio(model, output)
    if model.get("views"):
        pages = dict(page_models(model))
        chosen = view or next(iter(pages))
        if chosen not in pages:
            raise ValueError(f"Unknown view: {chosen}")
        model = copy.deepcopy(pages[chosen])
        model.pop("mermaid", None)
        model["paths"] = []
    elif view is not None:
        raise ValueError("This model does not define views")
    model.pop("mermaid_ids", None)
    if not model.get("mermaid"):
        model["mermaid"] = mermaid_from_model(model)
    template = (SKILL_DIR / "assets/viewer.html").read_text(encoding="utf-8")
    runtime = base64.b64encode((SKILL_DIR / "assets/mermaid.tiny.js").read_bytes()).decode("ascii")
    payload = json.dumps(model, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = template.replace("__MERMAID_RUNTIME__", runtime).replace("__MODEL_JSON__", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    output.with_suffix(".mmd").write_text(model["mermaid"] + "\n", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--view", help="HTML view ID; defaults to the first view")
    args = parser.parse_args()
    if args.output.suffix.lower() not in (".drawio", ".html") or args.output.resolve() == args.model.resolve():
        parser.error("Output must be a separate .drawio or .html file")
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
        print(render(model, args.output, args.view))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(1, f"code-diagram: {exc}\n")


if __name__ == "__main__":
    main()
