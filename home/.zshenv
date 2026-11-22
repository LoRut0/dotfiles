if [[ -r "$HOME/.cargo/env" ]]; then
    . "$HOME/.cargo/env"
elif [[ -d "$HOME/.cargo/bin" && ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi
