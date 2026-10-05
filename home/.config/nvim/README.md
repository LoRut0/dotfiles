# 💤 LazyVim

A starter template for [LazyVim](https://github.com/LazyVim/LazyVim).
Refer to the [documentation](https://lazyvim.github.io/installation) to get started.

## Search

The leader key is `\`. `\sg` searches the current working directory;
`\sG` and `\/` search the project root. Use `:pwd` and `:LazyRoot` to
inspect those directories.

Inside an Arc checkout or worktree (detected by its `.arc` marker), text,
word, and file searches use `ya grep --remote` with the selected directory
as their scope. Results come from **trunk**, so local edits and branch-only
files are not indexed; opening a result uses the corresponding local file.
Each query returns at most 1,000 results. The search runs the `ya` executable
from the current Arc checkout, even when Yazi's `ya` is first on `PATH`.

File search (`\ff` for cwd, `\fF` or `\<Space>` for the root) waits for a
query instead of scanning the checkout. Type a path fragment; space-separated
fragments match in order.
Outside Arc checkouts, the usual Snacks search backends remain in use.

The explorer opens at cwd with `\e` and at the project root with `\E`.
Press `/` to filter it, then `Enter` to browse the results with `j`/`k`.
The query remains active while you expand or collapse directories with `l`/`h`
or `Enter`, and while you open files. Press `/` again to edit the query.
In the filter, `Esc` clears the query; a second `Esc` or `Enter` with an empty
query returns to the unfiltered explorer.

## Codex

Install the Codex CLI on the machine running Neovim. `\ax` opens Codex in a
Snacks terminal on the right; `\ab` adds the current file, and visual `\as`
adds the selected line range. The same actions are available as `:Codex` and
`:CodexHere`. Codex starts in Neovim's current working directory (`:pwd`).

## OpenAPI

OpenAPI YAML and JSON files support `gd` on a `$ref` value. The OpenAPI
navigator follows both local `#/components/...` pointers and relative links to
other files, alongside the existing YAML language server. Use `Ctrl+O` to jump
back after following a definition.

## Surround shortcuts

In both terminal Neovim and VS Code, type `\W` followed by a surrounding
character to wrap the word under the cursor, or the selection in visual mode.
For example, `\W"` produces `"word"`. Opening brackets add padding (`\W(` →
`( word )`); closing brackets do not (`\W)` → `(word)`). The same distinction
applies to square, curly and angle brackets. Escape cancels the operation.
Existing mini.surround shortcuts (`gsa`, `gsd`, `gsr`, etc.) are preserved.

## VS Code

The same configuration supports `asvetliakov.vscode-neovim`. The installed
LazyVim automatically imports its VS Code extra when `vim.g.vscode` is set.
That extra filters out LSP, completion, formatter, debugger and UI plugins;
editing plugins such as mini.ai and mini.surround remain available.

Local overrides keep Treesitter parsing/textobjects but disable its highlighting,
indent and folds in VS Code. `config.keymaps` loads `config.vscode-keymaps` in
that mode, using the extension's clipboard instead of the terminal's OSC52.
VS Code editor settings are managed separately and are not changed here.

The leader is `\` in both modes. VS Code mappings:

| Keys | Action |
| --- | --- |
| `\y{motion}`, visual `\y` | Copy to clipboard |
| `\yy` | Copy line to clipboard |
| `\ff` | Find files |
| `\sg` | Search in files |
| `\e` | Focus Explorer |
| `\ca` | Code action |
| `\cr` | Rename |
| `\cf` | Format document, or selection in visual mode |

After changing the configuration, run **Neovim: Restart Extension** in VS Code.
Regular terminal Neovim retains its existing plugins, OSC52 mappings and
Treesitter behavior.
