# draw.io workflow — explicit request

Use this branch only when the user asks for draw.io generation or conversion,
or names an existing `.drawio` for editing/viewing. Ordinary new diagrams use
[the HTML/Mermaid workflow](html.md).

## Convert or generate

For a conversion, locate the existing `diagram.json` beside the HTML/Mermaid
artifacts. Reuse its nodes, edges, descriptions, evidence, source references,
paths and abstraction; recheck source positions. Preserve the HTML, `.mmd` and
original JSON. If draw.io needs shorter captions, geometry or page `views`, save
those presentation changes in a sibling `diagram.drawio.json` and render from
that copy. Preserve every original node/edge and its evidence across pages.

For an older model with explicit Mermaid but incomplete edge metadata, reconcile
the graph into complete `nodes`/`edges` using the existing diagram and inspected
code before export. The renderer does not parse Mermaid into draw.io connectors.
If only HTML remains, recover its embedded model (`script#model`); if only `.mmd`
remains, reconstruct and verify the missing source metadata. Do not invent links
or silently omit branches to complete the conversion. If the user explicitly
requests a new draw.io diagram, author the model directly; no preliminary HTML is
required. See [the shared input contract](input.md).

```sh
python3 /path/to/code-diagram/scripts/render.py /path/to/diagram.json --output /path/to/diagram.drawio
```

Substitute `diagram.drawio.json` when using an adapted copy. This exports native
shapes and connectors; it does not embed a screenshot of the HTML diagram.
The HTML contextual panel, guided path controls and export UI do not transfer.
Their source references/explanations become links, tooltips and `Sources` cards;
routes can become focused pages. Manual draw.io edits do not sync back into HTML
or JSON: inspect and preserve them before rerendering, either by patching XML or
reconciling the edited content/geometry into the export model.

## Readable pages

For a large process, use a compact overview and separate detail `views`, usually
6–10 blocks each. Without views, named paths become focused route pages, not
copies of the full graph. Use short captions at 18 px; full labels and explanations
remain in tooltips. The renderer wraps captions, routes around blocks and places
edge captions in free space. It rejects overlaps, overly long captions, more
than 12 nodes per page and canvases over 1500×1100. Resolve failures by changing
the view, not reducing fonts. `allow_large_page` is only for an explicitly requested
poster. Manual geometry belongs to each view; keep clear corridors and inspect
the result at normal reading size.

## Navigation

The helper writes native uncompressed `.drawio` XML, not a Mermaid image embedded in a shape. Every source-bearing node carries both a `vscode://file/...:line:column` hyperlink and Draw.io Integration code-link metadata. Conceptual nodes without sources or a `detail_view` remain unlinked. Edge evidence is linked too. All references are also accessible as separate cards on `Sources`.

Conceptual overview nodes with `detail_view` link to a detail page using draw.io's [page-link format](https://www.drawio.com/docs/reference/animation-actions-json/), `data:page/id,<id>`. Select the shape and follow its normal link popup; this is separate from the extension's Code Link double-click. Detail pages have a return link. `Sources` is paginated so individual references remain readable.

## Browser — opening a requested draw.io result

Run `drawio-open '/absolute/path/diagram.drawio'` after generation or rerendering.
Dotter's `ai` profile installs this command. The standalone fallback is
`python3 /path/to/code-diagram/scripts/open_browser.py '/absolute/path/diagram.drawio'`.
No Finder, file picker, drag-and-drop, local server or browser extension is needed.

The helper creates a private local HTML snapshot in `~/.cache/drawio-open`
(or `$XDG_CACHE_HOME/drawio-open`) and opens it in the default browser. It loads
the full native XML, including all pages, into `https://embed.diagrams.net` using
the documented [embed JSON protocol](https://www.drawio.com/docs/reference/embed-mode/).
The editor needs internet; XML is sent via `postMessage` only after checking
the iframe's origin and window. It is not put in a URL or uploaded by the helper.
The editor uses `stealth=1` to disable features that require external web services.

**Save** downloads an edited `.drawio` copy; the browser has no write access to
the original input file. A fresh CLI invocation reads the latest input. Refreshing
the launcher reloads its original snapshot, so save browser edits before refreshing.
`--no-open` prints the launcher path without starting a browser, useful for browser
tools or headless hosts. Cache files can be removed after use. The command uses
Python's standard library and the existing OS browser opener.

## VS Code — for offline editing and code navigation

With the already installed `hediet.vscode-drawio` extension, open the `.drawio` in the second editor column, enable **Code Link** in the status bar, and double-click a node, edge or source card. The extension opens the exact source position in the first column and keeps the diagram visible. Use F2 or disable Code Link to edit a label. No workspace symbol search is needed for the generated position links.

Open with `code --reuse-window '/absolute/path/diagram.drawio'` when `code` is available and the extension is installed. On macOS the app-bundled CLI may be used if it is absent from PATH. Do not claim VS Code's ordinary XML editor is a diagram viewer when the extension is missing.

The extension's serialized metadata uses these object attributes:

```xml
<object id="node-check" label="Check"
  hedietLinkedDataV1_path="../../src/check.cpp"
  hedietLinkedDataV1_start_line_x-num="41"
  hedietLinkedDataV1_start_col_x-num="0"
  hedietLinkedDataV1_end_line_x-num="41"
  hedietLinkedDataV1_end_col_x-num="0">
  <!-- mxCell with geometry goes here -->
</object>
```

Positions are zero-based. Unusually, the path is relative to the **diagram file path**, treated as a directory, not to its parent. For `/project/docs/flow.drawio` → `/project/src/check.cpp`, the path is `../../src/check.cpp`. The helper computes this after resolving the output path. Recompute after relocating the artifact; preserve diagram/code relative placement when sharing. Remote navigation requires the diagram and source to belong to the same VS Code filesystem context. Do not encode a guessed SSH authority.

This contract is based on the upstream [CodeLinkFeature implementation](https://github.com/hediet/vscode-drawio/blob/main/src/features/CodeLinkFeature.ts) and [example diagram](https://github.com/hediet/vscode-drawio/blob/main/examples/linking/main.dio). See also [Code Link usage](https://github.com/hediet/vscode-drawio/blob/main/docs/code-link.md). Recheck upstream if a newer extension changes the contract.

## Desktop and browser editors

- **draw.io Desktop** opens and edits the diagram offline. On macOS, if installed, use `open -a 'draw.io' '/absolute/path/diagram.drawio'`. Do not promise direct VS Code jumps: the documented Desktop external-link allowlist excludes `vscode:`. Use the VS Code extension or companion HTML for navigation.
- **Browser draw.io** can display shape hyperlinks, but custom-protocol launches depend on browser/host restrictions and OS URL handlers. In editing mode, select a shape and follow its link popup; a normal click selects it. Do not promise one-click navigation in every viewer.
- **Offline HTML companion** retains the original contextual panel with multiple references and exact `vscode://file` links. The browser may ask before launching VS Code. It also retains guided path stepping and local SVG/PNG export. It is generated from the same JSON, but later manual edits to `.drawio` are not automatically synchronized back into it.

Sources: [draw.io links and tooltips](https://www.drawio.com/docs/manual/links-tooltips-tags/), [Desktop navigation restrictions](https://github.com/jgraph/drawio/wiki/Desktop-App#security-model), [VS Code URL syntax](https://code.visualstudio.com/docs/configure/command-line#_opening-vs-code-with-urls).

## Verification

Parse the XML and check unique cell IDs within each page, valid source/target endpoints and positive geometry. Check encoded URL targets and resolve the extension path starting from the output **file**, with line/column converted back to one-based. Inspect main and route pages, labels, branch spacing, tooltips and `Sources` cards in an available editor. Do not launch source links as part of automated inspection. Distinguish structural verification, visual verification and an actual editor jump; report only what was checked.

If the editor is unavailable, use `scripts/preview.py` with Pillow to inspect PNG previews of the generated XML's geometry, captions, waypoints and label boxes. These previews approximate shapes and fonts and do not execute draw.io. Check text fits, connector crossings are understandable, and the footer clears all edges; don't claim this verifies the editor UI. The renderer keeps source/evidence descriptions in tooltips even when their visible `caption` is short or empty.

The helper's regression checks run independently of any service:

```sh
python3 -B -m unittest discover -s /path/to/code-diagram/scripts -p 'test_*.py'
```
