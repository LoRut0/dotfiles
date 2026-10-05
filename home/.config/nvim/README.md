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
Each query returns at most 1,000 results. `ya` must be available on PATH.

File search (`\ff` for cwd, `\fF` or `\<Space>` for the root) waits for a
query instead of scanning the checkout. Type a path fragment; space-separated
fragments match in order.
Outside Arc checkouts, the usual Snacks search backends remain in use.

The explorer opens at cwd with `\e` and at the project root with `\E`.
