# Diagram input

UTF-8 JSON, version 1. Names and paths below are illustrative; replace them with inspected source locations.

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

- IDs: ASCII letter followed by letters, digits or underscores; keep stable across edits. Use `nodes` and `edges` as the authoritative draw.io graph. In explicit Mermaid, each flowchart node needs one metadata entry; subgraphs are not source nodes.
- `root`: existing absolute checkout directory. `file`: relative path resolving to an existing UTF-8 text file inside it. Outside-root symlinks are rejected; use a common real root when appropriate.
- `line` and `column`: positive 1-based integers; column defaults to 1. The renderer checks bounds; the agent checks correspondence to the named symbol. Prefer column 1 unless a precise editor-compatible column was checked.
- `sources`: definitions/call sites; optional `label` explains a reference's role. Empty lists are allowed for conceptual/external nodes with a mandatory explanatory `note`.
- `description`: concise scenario-specific purpose, recommended for meaningful nodes. `snippet` is optional and uses a source file already listed for that node. The renderer copies the exact 1–5 lines from `start` through `end`; do not duplicate code text in JSON. Omit snippets for conceptual nodes or when they add no insight.
- Diagram labels should include important real function names. Keep additional implementation functions in the source list when the overview would otherwise be crowded.
- `direction`: optional `LR` (default), `RL`, `TB`/`TD` or `BT`. Applies to draw.io layout and generated Mermaid.
- Node `shape`: optional `process` (default), `decision`, `store`, or `external`. Node `geometry`: optional object with all of `x`, `y`, `width`, `height`, finite nonnegative numbers, width ≥ 80 and height ≥ 40. Without it, draw.io lays out nodes by graph rank, with back edges retained for cycles. Geometry and store/external shapes apply to draw.io only. Check long labels and branch spacing visually.
- `mermaid`: optional, for HTML only; `flowchart`/`graph` only. No `click` directives, configuration directives, frontmatter, HTML tags or external images. Use ordinary quoted labels and plain text. The viewer wires node clicks to a contextual panel containing the verified source links.
- `edges`: defines the actual draw.io connectors (never parsed from Mermaid). Describe each meaningful connection with `from`, `to`, a short `label`, `relation` (`process`, `call`, `data`, `async`) and `confidence` (`confirmed`, `inferred`, `unresolved`). `evidence` uses the same source-reference shape as `sources` and points to code supporting the relationship. Inferred or unresolved edges need a `note` explaining the uncertainty. With explicit Mermaid, keep the same arrows in the same declaration order for HTML route highlighting. Metadata is displayed in tooltips/HTML; the renderer validates endpoints and positions but cannot prove the relationship or confidence.
- `paths`: optional named routes for separate highlighted draw.io pages or HTML highlighting and step-through. Each path has a stable ASCII `id`, a `label`, and at least two node IDs. Every consecutive pair must appear in `edges`. Use routes for meaningful alternatives, not every graph traversal.
- Explain edge semantics in `scope` where needed; label uncertainty and asynchronous boundaries. A process edge can connect collapsed stages without implying a direct function call.

The `.drawio` file is editable uncompressed XML with native shapes, source links, tooltips, route pages and a `Sources` page. Read [draw.io navigation](drawio.md) for viewer-specific behavior. HTML is an optional self-contained offline companion with SVG/PNG export; keep JSON and generated `.mmd` for updates. Existing version 1 Mermaid inputs still render as HTML. To export an older Mermaid-only graph to draw.io, first supply complete node/edge metadata; the helper refuses a multi-node Mermaid model with no edges to avoid silently dropping its connectors. Source paths refer to a particular checkout. Line links can become stale after code changes.

Mermaid Tiny 12.1.0 is vendored with its license. To update deliberately, retrieve the pinned `@mermaid-js/tiny` npm tarball, replace `assets/mermaid.tiny.js` and its license, update `assets/vendor.json`, and verify rendering and node mapping. Never auto-update at render time.
