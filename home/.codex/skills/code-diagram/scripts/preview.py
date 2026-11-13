#!/usr/bin/env python3
"""Preview generated XML geometry as PNG (Pillow required, not a draw.io UI render)."""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def style(cell):
    return dict(item.split("=", 1) for item in cell.get("style", "").split(";") if "=" in item)


def preview(source, output_dir, font_path, pages=None):
    from PIL import Image, ImageDraw, ImageFont

    document = ET.parse(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    for page in document.findall("diagram"):
        if pages and page.get("id") not in pages:
            continue
        objects = page.findall("mxGraphModel/root/object")
        vertices = {obj.get("id"): obj for obj in objects if obj.find("mxCell").get("vertex") == "1"}
        geometries = {key: {k: float(v) for k, v in obj.find("mxCell/mxGeometry").attrib.items() if k != "as"}
                      for key, obj in vertices.items()}
        width = math.ceil(max(g["x"] + g["width"] for g in geometries.values()) + 50)
        height = math.ceil(max(g["y"] + g["height"] for g in geometries.values()) + 50)
        scale = 2
        image = Image.new("RGB", (width * scale, height * scale), "white")
        draw = ImageDraw.Draw(image)

        def coords(points):
            return [(round(x * scale), round(y * scale)) for x, y in points]

        def text(value, box, size, color="#172b4d", left=False, bold=False):
            font = ImageFont.truetype(str(font_path), round(size * scale))
            x, y, w, h = box
            bbox = draw.multiline_textbbox((0, 0), value, font=font, spacing=5 * scale, align="left" if left else "center")
            tx = (x + 12) * scale if left else (x + w / 2) * scale - (bbox[2] - bbox[0]) / 2
            ty = (y + h / 2) * scale - (bbox[3] - bbox[1]) / 2 - bbox[1]
            draw.multiline_text((tx, ty), value, font=font, fill=color, spacing=5 * scale,
                                align="left" if left else "center", stroke_width=1 if bold else 0)

        for obj in objects:
            cell = obj.find("mxCell")
            if cell.get("edge") != "1":
                continue
            s = style(cell)
            a, b = geometries[cell.get("source")], geometries[cell.get("target")]
            geometry = cell.find("mxGeometry")
            points = [(a["x"] + a["width"] * float(s["exitX"]), a["y"] + a["height"] * float(s["exitY"]))]
            points.extend((float(p.get("x")), float(p.get("y"))) for p in geometry.findall("Array/mxPoint"))
            points.append((b["x"] + b["width"] * float(s["entryX"]), b["y"] + b["height"] * float(s["entryY"])))
            color = s.get("strokeColor", "#64748b")
            for start, end in zip(points, points[1:]):
                if s.get("dashed") == "1":
                    length = math.dist(start, end)
                    for offset in range(0, int(length), 12):
                        part = [(start[0] + (end[0] - start[0]) * d / length, start[1] + (end[1] - start[1]) * d / length)
                                for d in (offset, min(offset + 7, length))]
                        draw.line(coords(part), fill=color, width=3)
                else:
                    draw.line(coords([start, end]), fill=color, width=3)
            end, prev = points[-1], points[-2]
            angle = math.atan2(end[1] - prev[1], end[0] - prev[0])
            arrow = [end, (end[0] - 10 * math.cos(angle) + 4 * math.sin(angle), end[1] - 10 * math.sin(angle) - 4 * math.cos(angle)),
                     (end[0] - 10 * math.cos(angle) - 4 * math.sin(angle), end[1] - 10 * math.sin(angle) + 4 * math.cos(angle))]
            draw.polygon(coords(arrow), fill=color)
        for key, obj in vertices.items():
            g, s = geometries[key], style(obj.find("mxCell"))
            x, y, w, h = (g[k] for k in ("x", "y", "width", "height"))
            fill, stroke = s.get("fillColor", "none"), s.get("strokeColor", "none")
            if fill != "none" or stroke != "none":
                box = (round(x * scale), round(y * scale), round((x + w) * scale), round((y + h) * scale))
                draw.rounded_rectangle(box, radius=12 * scale, fill=fill if fill != "none" else None,
                                       outline=stroke if stroke != "none" else None, width=2)
            text(obj.get("label", ""), (x, y, w, h), float(s.get("fontSize", 18)),
                 s.get("fontColor", "#172b4d"), s.get("align") == "left", s.get("fontStyle") == "1")
        for obj in objects:
            if "codeDiagramLabelBox" in obj.attrib:
                l, t, r, b = json.loads(obj.get("codeDiagramLabelBox"))
                draw.rectangle((l * scale, t * scale, r * scale, b * scale), fill="white")
                text(obj.get("label", ""), (l, t, r - l, b - t), 13, "#475569")
        path = output_dir / (page.get("id") + ".png")
        image.save(path)
        print(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagram", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--page", action="append")
    args = parser.parse_args()
    candidates = [args.font] if args.font else [Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
                                               Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                                               Path("C:/Windows/Fonts/arial.ttf")]
    font = next((p for p in candidates if p and p.is_file()), None)
    if font is None:
        parser.error("Pass --font with a TrueType font supporting the diagram's language")
    preview(args.diagram, args.output_dir, font, args.page)


if __name__ == "__main__":
    main()
