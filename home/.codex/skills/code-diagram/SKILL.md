---
name: code-diagram
description: Explain selected source code or a program process as an editable draw.io flowchart at a user-controlled abstraction level, with verified function names and VS Code navigation. Generate native .drawio files and optional offline HTML; update individual parts on follow-up requests. Use for requests to visualize how code works, not mechanical full call graphs or generic non-code diagrams.
---

# Code Diagram

Create an explanation grounded in inspected source code. Default to native draw.io diagrams and VS Code source navigation. Keep the offline HTML viewer available when requested or useful for its contextual panel and guided paths. Respond and label conceptual steps in the user's language; preserve actual symbol names.

## Choose the view

Use selected code, a named entry point, scenario, or files as the starting point. If none is available, ask for the code or entry point before inventing a process. Inspect the source and relevant definitions with available code navigation/search. Builds, service tests, and compilation database regeneration are not required or authorized by this skill.

Default to **working logic**: significant functions, conditions, data stores and external interactions, roughly 8–12 nodes. Adapt to the user's limits:

- **Overview:** meaningful process stages; several functions may implement one stage.
- **Working logic:** key functions and branches relevant to the scenario.
- **Detailed:** requested nested calls, failures, retries, transactions, or concurrency within explicit boundaries.

Abstraction and completeness are independent. A detailed business process need not expose helper calls. Support mixed granularity such as “expand pricing, keep persistence in one block.” Do not generate the full call graph merely because symbols are available. State the scenario and relevant omissions in one short scope sentence.

## Make it readable

For a large process, author a compact overview and separate detail `views`. Keep one question or stage per page, usually 6–10 blocks. Preserve the underlying nodes, evidence and edges across those views; a route page should contain its route, not repeat the entire graph with highlights. Do not squeeze a 50-node process onto a single canvas or enlarge boxes while leaving tiny text inside them.

Use short action captions, usually 2–6 words, at 18 px. Keep service names, endpoints, full symbol lists and long explanations in tooltips/source references unless they are the specific subject of that view. Function-level views can use a significant exact symbol as the caption. Label branches and outcomes concisely; ordinary sequential arrows often need no caption. Put uncertainty in the legend, styling and tooltip instead of repeating long annotations on every arrow.

The renderer wraps captions, routes connectors around blocks and places edge captions in free space. It rejects overlapping blocks, overly long captions, more than 12 nodes per page and canvases over 1500×1100. Resolve those failures by editing the view, not reducing fonts. `allow_large_page` is for an explicitly requested poster or large canvas only. Manual geometry belongs to a particular view; retain clear corridors between rows/columns and inspect the result at normal reading size.

## Ground the explanation

- Check each function's definition and source position. Never invent names or lines. When useful, add a second reference to the call site with a descriptive label.
- Separate conceptual stage labels from exact function names; a stage may reference multiple functions. A conceptual/external node may have no source references, with an explicit explanation.
- Give each meaningful node a short explanation of what it does in this scenario. Add a 1–5 line source excerpt when it provides a useful anchor; the renderer reads it from the checked file and line range.
- Distinguish process order, direct calls, data flow and async dispatch. Record each meaningful connection with its type and confidence (`confirmed`, `inferred`, `unresolved`); explain inferred or unresolved edges. An arrow between collapsed stages does not prove a direct call.
- Preserve significant conditions, failures and concurrency relevant to the requested explanation. If the scenario has a useful route through branches, define a named path so the viewer can highlight it and step through its nodes.
- Store repo-relative paths plus the exact checkout root. Link local working-tree files, not an unrelated revision. Recheck positions on updates; links are line-based snapshots, not symbol tracking.

## Produce and open

Read [the input contract](references/input.md). Write `diagram.json` in an existing user-designated artifact directory or a dedicated local artifact directory outside the service repository. Keep it for follow-up edits. `nodes` and `edges` define the draw.io graph; Mermaid text is optional and only used for HTML.

Generate with the standard-library-only helper (Python 3.10+); substitute the actual skill and artifact paths:

```sh
python3 /path/to/code-diagram/scripts/render.py /path/to/diagram.json --output /path/to/diagram.drawio
```

This creates editable native shapes/connectors in uncompressed `.drawio` XML. It validates source locations and adds links to the first source of each node and the first evidence reference of each edge. Hover tooltips contain explanations, excerpts and uncertainty. Paginated `Sources` cards retain every distinct source location. Explicit `views` define pages; without views, named paths become focused route pages. Overview nodes can link to a `detail_view`, and detail pages include a return link. XML escaping is handled by the helper. It does not analyze code or prove edge semantics.

Read [draw.io navigation and verification](references/drawio.md) before choosing how to open the result. Prefer an already installed Draw.io Integration extension in VS Code for offline editing and code navigation. Do not install an editor, extension or URL handler or change editor configuration merely to display a diagram. If no suitable local viewer is available, deliver the `.drawio` file and generate/open a companion HTML for immediate viewing. Do not upload source or diagram content to online services without the user's request.

For the companion or explicitly requested HTML:

```sh
python3 /path/to/code-diagram/scripts/render.py /path/to/diagram.json --output /path/to/diagram.html
```

HTML embeds the vendored Mermaid runtime, needs no server or extension, and keeps the contextual source panel, source excerpts, path highlighting/step-through and SVG/PNG export. Without explicit Mermaid text, the helper derives it from the nodes/edges. It also saves a sibling `.mmd`. These interactive HTML controls are not reproduced by the native draw.io file.

For a model with `views`, HTML renders only the first view by default; use `--view <id>` for a detail view. Its Mermaid graph is derived from that view. Do not export the full underlying graph as the HTML fallback for a deliberately split diagram.

Check the generated artifact before delivery. For draw.io inspect native shapes, edge endpoints, page layout, tooltips, source metadata and the extension's relative paths; use an available local editor for visual verification. For HTML check rendering, panel interaction/scrolling, source `href` targets, route highlighting and export when browser inspection is available. Do not launch source links during automated checks. If GUI verification is unavailable, state the limit instead of claiming the UI was checked.

When GUI access is unavailable, `scripts/preview.py diagram.drawio --output-dir preview` can render PNG previews of the generated XML geometry (optional Pillow dependency; `--font` selects a TrueType font). Inspect the overview and dense detail pages for text overflow, confusing shared connector segments and collisions. This is a layout preview, not a verification of draw.io's own rendering or editor navigation. The script's preview shapes are approximate; code links are not executed.

Open the result with the available local viewer after generation or rerendering, and when the user asks to view an existing artifact. Verify the absolute file path first. For HTML on macOS invoke `open '/absolute/path/diagram.html'`; on other platforms use the equivalent opener. For `.drawio`, use the installed editor described in the reference. If opening is blocked or no editor is installed, provide the file link and explain that limit.

Return the scope, a clickable absolute `.drawio` link (plus HTML when generated), and concise opening/navigation instructions. On follow-up edits preserve unchanged node IDs and abstraction and recheck source positions. If the user edited the `.drawio` manually, inspect it and preserve their changes: either patch XML directly or reconcile geometry/content into JSON before regenerating. Keep a copy before replacing a manually edited artifact. Viewing an existing file does not require regeneration.

## Boundaries

Source positions are snapshots, not symbol tracking. Moving a `.drawio` separately from its checkout can break the extension's relative paths; rerender for the new location. For SSH/container paths, keep the diagram and code in the same VS Code remote context and verify the target before claiming navigation works; local `vscode://file` URLs cannot address remote-only files. The HTML viewer supports flowcharts only. Do not add Neovim support or build services to obtain a diagram.
