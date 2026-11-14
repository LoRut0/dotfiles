# Diagram input

UTF-8 JSON, version 1. Names and paths below are illustrative; replace them with inspected source locations.
This model supports both branches: [HTML/Mermaid by default](html.md), and
[draw.io on explicit request](drawio.md). Keep it alongside the generated HTML
and `.mmd` so later conversion retains the graph and verified code references.

```json
{
  "version": 1,
  "title": "Оформление заказа",
  "scope": "Ключевые функции. Стрелки показывают этапы процесса, не обязательно прямые вызовы.",
  "root": "/absolute/path/to/checkout",
  "direction": "LR",
  "nodes": [
    {"id": "validate", "label": "Проверить заказ", "description": "Проверяет обязательные поля перед оплатой.", "sources": [
      {"symbol": "ValidateOrder", "file": "src/order.cpp", "line": 42, "column": 1}
    ], "snippet": {"file": "src/order.cpp", "start": 42, "end": 44}},
    {"id": "pay", "label": "Оплатить", "description": "Передаёт сумму платёжному клиенту.", "sources": [
      {"symbol": "ChargePayment", "file": "src/payment.cpp", "line": 80, "column": 1}
    ]}
  ],
  "edges": [
    {"from": "validate", "to": "pay", "label": "после успешной проверки", "relation": "process", "confidence": "confirmed", "evidence": [
      {"symbol": "PlaceOrder", "file": "src/order.cpp", "line": 64, "label": "порядок вызовов"}
    ]}
  ],
  "paths": [{"id": "success", "label": "Успешная оплата", "nodes": ["validate", "pay"]}]
}
```

- IDs: ASCII letter followed by letters, digits or underscores; keep stable across edits. Record the complete graph in `nodes` and `edges` for HTML navigation and later native export. In explicit Mermaid, each flowchart node needs one metadata entry; subgraphs are not source nodes. Keep Mermaid topology consistent with the metadata.
- `root`: existing absolute checkout directory. `file`: relative path resolving to an existing UTF-8 text file inside it. Outside-root symlinks are rejected; use a common real root when appropriate.
- `line` and `column`: positive 1-based integers; column defaults to 1. The renderer checks bounds; the agent checks correspondence to the named symbol. Prefer column 1 unless a precise editor-compatible column was checked.
- `sources`: definitions/call sites; optional `label` explains a reference's role. Empty lists are allowed for conceptual/external nodes with a mandatory explanatory `note`.
- `description`: concise scenario-specific purpose, recommended for meaningful nodes. `snippet` is optional and uses a source file already listed for that node. The renderer copies the exact 1–5 lines from `start` through `end`; do not duplicate code text in JSON. Omit snippets for conceptual nodes or when they add no insight.
- Node `caption`: optional short visible label; defaults to `label`. Applies to draw.io and generated Mermaid; explicit Mermaid controls its own labels. Keep the full service/endpoint description in `label` for the panel/tooltip. The renderer does not append source symbols to the visible text. For function-level views put the important symbol in the caption; overview captions should describe the action. draw.io accepts at most three wrapped lines.
- Node `detail_view`: optional ID of an existing view, used for draw.io navigation only. The shape's ordinary hyperlink opens that page; its Code Link metadata still targets its primary source when supplied. Use conceptual overview nodes with no sources when the main action should be opening a detail page.
- `direction`: optional `LR` (default), `RL`, `TB`/`TD` or `BT`. Applies to draw.io layout and generated Mermaid.
- Node `shape`: optional `process` (default), `decision`, `store`, or `external`. Node `geometry`: optional object with all of `x`, `y`, `width`, `height`, finite nonnegative numbers, width ≥ 80 and height ≥ 40. Without it, draw.io lays out nodes by graph rank, with back edges retained for cycles. Geometry and store/external shapes apply to draw.io only. Check long labels and branch spacing visually.
- `mermaid`: optional, for HTML only; `flowchart`/`graph` only. No `click` directives, configuration directives, frontmatter, HTML tags or external images. Use ordinary quoted labels and plain text. The viewer wires node clicks to a contextual panel containing the verified source links.
- `edges`: defines the actual draw.io connectors (never parsed from Mermaid). Describe each meaningful connection with `from`, `to`, a short `label`, `relation` (`process`, `call`, `data`, `async`) and `confidence` (`confirmed`, `inferred`, `unresolved`). `evidence` uses the same source-reference shape as `sources` and points to code supporting the relationship. Inferred or unresolved edges need a `note` explaining the uncertainty. With explicit Mermaid, keep the same arrows in the same declaration order for HTML route highlighting. Metadata is displayed in tooltips/HTML; the renderer validates endpoints and positions but cannot prove the relationship or confidence.
- `paths`: optional named routes for focused draw.io pages or HTML highlighting and step-through. Each path has a stable ASCII `id`, a `label`, and at least two node IDs. Every consecutive pair must appear in `edges`. Use routes for meaningful alternatives, not every graph traversal.
- Explain edge semantics in `scope` where needed; label uncertainty and asynchronous boundaries. A process edge can connect collapsed stages without implying a direct function call.

Edge `caption` overrides the visible label in draw.io and generated Mermaid; `""` hides ordinary call/process labels while retaining full `label`, evidence and uncertainty in metadata. Explicit Mermaid controls its own edge labels. For draw.io, use brief words for actual conditions/outcomes, at most 32 characters. Edge captions must fit the free corridor, so even a valid length may require shortening or repositioning blocks. The draw.io renderer emits explicit orthogonal waypoints and label offsets instead of relying on automatic straight-line connections.

## Multiple views

Large models keep the full graph in `nodes`/`edges` and present it through `views`:

```json
"views": [
  {"id": "overview", "title": "Обзор", "scope": "Основные этапы процесса.",
   "nodes": ["validate", "pay"], "edges": [0], "direction": "LR",
   "geometry": {"validate": {"x": 70, "y": 170, "width": 250, "height": 100}}}
]
```

- IDs must be unique ASCII letters/digits/underscores; `sources` is reserved as a prefix.
- `nodes` lists visible IDs in layout order; `edges` optionally selects zero-based indices from the root edge list. By default all edges between the selected nodes are included. Every selected edge needs both endpoints on the page. The union of views must cover every node and edge; duplication for context is allowed.
- `scope` is a short page-specific subtitle (up to 200 characters). `geometry` overrides coordinates by node ID for this view only; root geometry is ignored when views are supplied. Geometry does not carry between views. `direction` is optional.
- Author collapsed overview nodes and process edges explicitly, with grounded descriptions and uncertainty. Give overview nodes `detail_view` links. Do not invent a direct call by collapsing a multi-service stage.
- draw.io pages must stay within 12 nodes and 1500×1100. `allow_large_page: true` at the root relaxes those two bounds only for a user-requested poster. It does not relax source validation or allow overlapping blocks. These numeric limits are not imposed by the HTML renderer.
- With views, draw.io does not additionally duplicate root `paths` as pages. Without views, route pages contain only their selected nodes and route edges. HTML renders the first view by default or the one selected with `--view <id>`; it does not reuse the root Mermaid text or routes.

HTML is the default interactive offline artifact; keep JSON and generated `.mmd` for updates and optional conversion. Existing version 1 Mermaid inputs still render as HTML. An explicitly requested `.drawio` export is editable XML with native shapes, source links, tooltips, focused pages and paginated `Sources` cards. Read [the conversion workflow](drawio.md) for legacy Mermaid inputs and viewer-specific behavior. Source paths refer to a particular checkout and line links can become stale after code changes.

Mermaid Tiny 12.1.0 is vendored with its license. To update deliberately, retrieve the pinned `@mermaid-js/tiny` npm tarball, replace `assets/mermaid.tiny.js` and its license, update `assets/vendor.json`, and verify rendering and node mapping. Never auto-update at render time.
