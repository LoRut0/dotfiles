# HTML/Mermaid workflow — default

Use this branch for ordinary code visualization and follow-up edits. Produce the
original interactive offline viewer, not a draw.io launcher. Keep `diagram.json`
as the reusable model; read [the input contract](input.md) when authoring it.

## Generate

Use the standard-library helper (Python 3.10+), substituting actual paths:

```sh
python3 /path/to/code-diagram/scripts/render.py /path/to/diagram.json --output /path/to/diagram.html
```

The output embeds the vendored Mermaid runtime and model. It requires no internet,
server or extension. Clicking a node opens the contextual panel with explanations,
source excerpts and verified `vscode://file` links. Named `paths` support highlighting
and step-through; SVG/PNG export stays available. The helper also writes a sibling
`diagram.mmd`. It does not create `.drawio` files.

Supply `mermaid` when custom flowchart layout/subgraphs are useful; otherwise the
helper derives it from `nodes` and `edges`. Preserve the original Mermaid styling
on follow-up edits and keep node IDs and ordered edges consistent with metadata.

Do not introduce draw.io page geometry or `views` merely to prepare for a future
conversion. Ordinary HTML models retain the full chosen flow and named paths.
If a large explanation needs multiple `views`, render a separate HTML per view
with `--view <id>` and link all of those files in the response. With `views`, the
helper renders only the first view unless selected explicitly, derives Mermaid
from that view, and omits root paths; there is no built-in HTML page switcher.
Do not silently deliver only an overview while claiming all details are included.

## Verify and open

Check Mermaid rendering, normal-size readability, node-to-panel mapping, panel
scrolling, source `href` targets, route highlighting and export when browser
inspection is available. Report only what was checked; do not launch code links
as part of automated inspection.

Open the resulting HTML in the default browser. On macOS:

```sh
open '/absolute/path/diagram.html'
```

Use the equivalent local opener on other platforms. A browser may request
confirmation before opening a source link in VS Code. Retain JSON and `.mmd`
alongside HTML for edits and for an explicit later draw.io conversion.
