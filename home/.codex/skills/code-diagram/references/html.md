# HTML/Mermaid workflow — default

Use this branch for ordinary code visualization and follow-up edits. Produce the
original interactive offline viewer, not a draw.io launcher. Keep `diagram.json`
as the reusable model; read [the input contract](input.md) when authoring it.

## Generate and open automatically

Use the standard-library helper (Python 3.10+), substituting actual paths:

```sh
python3 /path/to/code-diagram/scripts/render.py /path/to/diagram.json --output /path/to/diagram.html
```

After successfully writing HTML and `.mmd`, this command opens the HTML in the
default browser, including on rerendering. It uses the OS opener (`open` on macOS,
`xdg-open` on Linux). No separate opening command is needed. Because it launches
a GUI, use the required tool approval/escalation for this command when applicable.
If the opener fails, the files remain saved and the CLI reports the opening error.

Use `--no-open` when the user asks only to save files, for headless/batch generation,
or when preparing artifacts before a separately approved GUI launch. For multiple
views, generate background detail files with `--no-open` and automatically open
the main/requested view. The Python `render()` function itself only writes files;
callers importing it must open the final HTML separately when displaying it.

The output embeds the vendored Mermaid runtime and model. It requires no internet,
server or extension. Clicking a node opens the contextual panel with explanations,
source excerpts and verified `vscode://file` links. Named `paths` support highlighting
and step-through; SVG/PNG export stays available. The helper also writes a sibling
`diagram.mmd`. It does not create `.drawio` files.

The `+`/`−` buttons and trackpad pinch over the diagram share one scale and percentage
indicator. Pinch keeps the diagram point under the cursor in place where scrolling
allows. Only the canvas scrolls: the compact title/toolbar stays at the top and the
node details stay at the right edge with their own content scrollbar. On narrow
screens the details overlay the right side instead of moving above the diagram.
The header shows only the title and controls; the full scope remains in the saved
model. Mermaid source remains available through its download button. `Fit` fits
both canvas dimensions and resets panning. The same controller supports Safari's
gesture events as well as Ctrl+wheel pinch events in Chromium/Firefox.

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

## Verify and reopen

Check Mermaid rendering, normal-size readability, node-to-panel mapping, panel
scrolling, source `href` targets, route highlighting, alternating buttons/pinch,
cursor anchoring, fixed toolbar/sidebar during panning, Fit after manual zoom, and export when browser
inspection is available. Report only what was checked; do not launch code links
as part of automated inspection.

The CLI already opened the generated HTML. To view an existing file without
regenerating it, or after a `--no-open` run, open it directly. On macOS:

```sh
open '/absolute/path/diagram.html'
```

Use the equivalent local opener on other platforms. A browser may request
confirmation before opening a source link in VS Code. Retain JSON and `.mmd`
alongside HTML for edits and for an explicit later draw.io conversion.
