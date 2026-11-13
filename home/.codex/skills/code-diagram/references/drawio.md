# draw.io navigation

The helper writes native uncompressed `.drawio` XML, not a Mermaid image embedded in a shape. Every source-bearing node carries both a `vscode://file/...:line:column` hyperlink and Draw.io Integration code-link metadata. Conceptual nodes without sources remain unlinked. Edge evidence is linked too. All references are also accessible as separate cards on `Sources`.

## VS Code — preferred for code navigation

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

The helper's regression checks run independently of any service:

```sh
python3 -B -m unittest discover -s /path/to/code-diagram/scripts -p 'test_*.py'
```
