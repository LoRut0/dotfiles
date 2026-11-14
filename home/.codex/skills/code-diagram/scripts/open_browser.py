#!/usr/bin/env python3
"""Open a local draw.io snapshot in the default browser; no server or dependencies."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import webbrowser
import xml.etree.ElementTree as ET


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "browser-launcher.html"


def launcher_html(source):
    xml = source.read_bytes().decode("utf-8-sig")
    root = ET.fromstring(xml)
    if root.tag not in {"mxfile", "mxGraphModel"}:
        raise ValueError("Expected a draw.io mxfile or mxGraphModel XML document")
    if root.tag == "mxfile" and root.find("diagram") is None:
        raise ValueError("The draw.io file has no diagram pages")
    payload = json.dumps({"title": source.name, "xml": xml}, ensure_ascii=True)
    # XML labels can contain </script>; never interpolate them as HTML markup.
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DRAWIO_PAYLOAD__", payload)


def prepare_launcher(source, cache_dir=None):
    source = Path(source).expanduser().resolve(strict=True)
    html = launcher_html(source)
    if cache_dir is None:
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "drawio-open"
    cache_dir = Path(cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()[:24]
    target = cache_dir / f"{digest}.html"
    fd, temporary = tempfile.mkstemp(prefix=".launcher-", dir=cache_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(html)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def open_launcher(path):
    # Pass only a short local URL to the OS, even for diagrams with large images.
    url = path.as_uri()
    if sys.platform == "darwin":
        subprocess.run(["open", url], check=True)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", url], check=True)
    elif not webbrowser.open_new_tab(url):
        raise RuntimeError("No browser opener is available; open the launcher HTML manually")


def main():
    parser = argparse.ArgumentParser(
        description="Open a .drawio in the default browser without a file picker.",
        epilog="Requires internet for the draw.io editor. Save downloads an edited copy; "
        "the input file is not overwritten. Launchers are cached under $XDG_CACHE_HOME/drawio-open "
        "(default: ~/.cache/drawio-open).",
    )
    parser.add_argument("diagram", type=Path, help="local .drawio or draw.io XML file")
    parser.add_argument("--no-open", action="store_true", help="prepare the launcher and print its path only")
    args = parser.parse_args()
    try:
        path = prepare_launcher(args.diagram)
        if args.no_open:
            print(path)
        else:
            open_launcher(path)
            print(f"Opened browser copy: {args.diagram.name}")
            print("Save downloads an edited .drawio copy; the original file stays unchanged.")
    except (OSError, UnicodeError, ET.ParseError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"drawio-open: {error}\n")


if __name__ == "__main__":
    main()
