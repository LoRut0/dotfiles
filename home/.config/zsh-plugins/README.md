# Vendored Zsh plugins

Runtime files and upstream licenses are copied from these clean revisions:

| Plugin | Upstream | Commit |
| --- | --- | --- |
| arc-zsh-plugin | https://github.com/dkryaklin/arc-zsh-plugin | `65d2d7deaee9f67d9f8a8a5d62c7e92e402b1f85` |
| zsh-autosuggestions | https://github.com/zsh-users/zsh-autosuggestions | `85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5` |
| zsh-syntax-highlighting | https://github.com/zsh-users/zsh-syntax-highlighting | `1d85c692615a25fe2293bdd44b34c217d5d2bf04` |
| zsh-vi-mode | https://github.com/jeffreytse/zsh-vi-mode | `91cafe4a09b6670cb8e761aa413e5f7b9e00816f` |

Update these files and commit IDs together when upgrading. For
zsh-syntax-highlighting, keep its `highlighters/*/*-highlighter.zsh`, `.version`,
and `.revision-hash` files beside the main script. Keep its `source` line last
in `.zshrc`.
