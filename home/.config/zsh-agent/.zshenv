. "$HOME/.cargo/env"

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
export EDITOR=nvim

# so `claude`/`forge` work when launched directly in this shell (e.g. via
# the SUPER+SHIFT+Q terminal), not just through the personal .zshrc wrappers
export HTTP_PROXY=http://127.0.0.1:10809
export HTTPS_PROXY=http://127.0.0.1:10809
