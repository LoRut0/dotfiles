---
name: code-diagram
description: Explain selected source code or a program process as an interactive offline HTML/Mermaid flowchart at a user-controlled abstraction level, with verified function names and code navigation. Convert an existing diagram to editable draw.io on explicit request; update individual parts on follow-up requests. Use for requests to visualize how code works, not mechanical full call graphs or generic non-code diagrams.
---

# Code Diagram

Create an explanation grounded in inspected source code. Respond and label conceptual steps in the user's language; preserve actual symbol names.

## Choose the branch

- **HTML/Mermaid — default.** For a new code diagram or an ordinary follow-up edit, use [the HTML workflow](references/html.md): interactive offline HTML, a Mermaid source file and a retained JSON model. Keep the contextual source panel, source links and guided paths. Do not generate or open draw.io unless requested; there is no need to ask which format to use.
- **draw.io — explicit request.** For “convert this to drawio”, “сделай версию для draw.io” or a new diagram explicitly requested in `.drawio`, use [the draw.io workflow](references/drawio.md). Convert from the existing model, preserve the HTML/Mermaid originals and open the export with `drawio-open`. A request to open an existing `.drawio` only opens that file; it does not change the default for new diagrams.

Use only the selected branch's workflow. For a conversion, reuse the inspected explanation and recheck source positions rather than starting a new analysis or changing its abstraction level. If the user names an existing artifact for editing, retain that artifact's format.

## Choose the view

Use selected code, a named entry point, scenario, or files as the starting point. If none is available, ask for the code or entry point before inventing a process. Inspect the source and relevant definitions with available code navigation/search. Builds, service tests, and compilation database regeneration are not required or authorized by this skill.

Default to **working logic**: significant functions, conditions, data stores and external interactions, roughly 8–12 nodes. Adapt to the user's limits:

- **Overview:** meaningful process stages; several functions may implement one stage.
- **Working logic:** key functions and branches relevant to the scenario.
- **Detailed:** requested nested calls, failures, retries, transactions, or concurrency within explicit boundaries.

Abstraction and completeness are independent. A detailed business process need not expose helper calls. Support mixed granularity such as “expand pricing, keep persistence in one block.” Do not generate the full call graph merely because symbols are available. State the scenario and relevant omissions in one short scope sentence.

## Make it readable

For a large process, present a compact overview and focused details. Keep one question or stage per diagram, usually 6–10 blocks. Preserve the underlying nodes, evidence and edges when splitting the explanation. Do not squeeze a 50-node process onto a single canvas or enlarge boxes while leaving tiny text inside them. The selected branch describes how to handle multiple views.

Use short action captions, usually 2–6 words, readable at normal zoom. Keep service names, endpoints, full symbol lists and long explanations in the contextual panel/tooltips unless they are the specific subject of that view. Function-level views can use a significant exact symbol as the caption. Label branches and outcomes concisely; ordinary sequential arrows often need no caption. Put uncertainty in styling and explanations instead of repeating long annotations on every arrow.

## Ground the explanation

- Check each function's definition and source position. Never invent names or lines. When useful, add a second reference to the call site with a descriptive label.
- Separate conceptual stage labels from exact function names; a stage may reference multiple functions. A conceptual/external node may have no source references, with an explicit explanation.
- Give each meaningful node a short explanation of what it does in this scenario. Add a 1–5 line source excerpt when it provides a useful anchor; the renderer reads it from the checked file and line range.
- Distinguish process order, direct calls, data flow and async dispatch. Record each meaningful connection with its type and confidence (`confirmed`, `inferred`, `unresolved`); explain inferred or unresolved edges. An arrow between collapsed stages does not prove a direct call.
- Preserve significant conditions, failures and concurrency relevant to the requested explanation. If the scenario has a useful route through branches, define a named path so the viewer can highlight it and step through its nodes.
- Store repo-relative paths plus the exact checkout root. Link local working-tree files, not an unrelated revision. Recheck positions on updates; links are line-based snapshots, not symbol tracking.

## Retain the model and deliver

Read [the shared input contract](references/input.md). Write `diagram.json` in an existing user-designated artifact directory or a dedicated local artifact directory outside the service repository. Retain it for edits and later conversion. Record complete `nodes`, `edges`, sources and evidence even when authoring explicit Mermaid; keep the Mermaid topology consistent with that metadata. Rendering does not analyze code or prove edge semantics.

Follow the selected branch's generation, verification and opening steps. Open the result after generation or rerendering, unless the user says otherwise. Browser launch is a GUI action: use the required tool approval/escalation when applicable. Do not install an editor, extension or URL handler just to display a diagram. If opening or GUI verification is unavailable, state the limit; a successful launcher exit confirms dispatch, not rendering. Do not launch source links during automated checks.

Return the scope, a clickable absolute link to the selected artifact (HTML by default, `.drawio` after requested conversion), and concise navigation instructions. Preserve unchanged node IDs, abstraction and user edits on follow-ups. Keep a copy before replacing a manually edited artifact. Viewing an existing file does not require regeneration.

## Boundaries

Source positions are snapshots, not symbol tracking. Moving a `.drawio` separately from its checkout can break the extension's relative paths; rerender for the new location. For SSH/container paths, keep the diagram and code in the same VS Code remote context and verify the target before claiming navigation works; local `vscode://file` URLs cannot address remote-only files. The HTML viewer supports flowcharts only. Do not add Neovim support or build services to obtain a diagram.
