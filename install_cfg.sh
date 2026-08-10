#!/usr/bin/env bash
set -e

CONFIG_HOME="$HOME/.config"
DOTFILES="$(dirname $(realpath "$0"))"

case "$(uname -s)" in
    Darwin) OS_DIR="$DOTFILES/home-macos" ;;
    Linux)  OS_DIR="$DOTFILES/home-linux" ;;
    *)      OS_DIR="" ;;
esac

mkdir -p $CONFIG_HOME

# Link everything under <layer>/.config into ~/.config
link_config() {
    local layer="$1"

    [[ -d "$layer/.config" ]] || return 0

    for dir in $layer/.config/*; do
        name="$(basename "$dir")"
        target="$CONFIG_HOME/$name"

        if [ -e "$target" ]; then
            echo "Skipping $target (already exists)"
            continue
        fi

        ln -sfn "$dir" "$target"
        echo "Linked ${layer#$DOTFILES/}/.config/$name to $target"
    done
}

# Link the dotfiles sitting directly in <layer>/ into $HOME
link_home() {
    local layer="$1"

    [[ -d "$layer" ]] || return 0

    for file in $layer/.*; do
        name="$(basename "$file")"

        if [[ $name == "." || $name == ".." || $name == ".config" ]]; then
            continue
        fi

        target="$HOME/$name"
        if [[ -e "$target" ]]; then
            echo "Skipping $target (already exists)"
            continue
        fi

        ln -sfn "$file" "$target"
        echo "Linked ${layer#$DOTFILES/}/$name to $target"
    done
}

# Shared layer first, then the platform-specific one on top
link_config "$DOTFILES/home"
link_home "$DOTFILES/home"

if [[ -n "$OS_DIR" ]]; then
    link_config "$OS_DIR"
    link_home "$OS_DIR"
else
    echo "Unknown platform $(uname -s), linked shared config only"
fi

if [[ ! -e "$HOME/.zsh" ]]; then
    mkdir "$HOME/.zsh"
    git clone https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/zsh-autosuggestions"
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$HOME/.zsh/zsh-syntax-highlighting"
    git clone https://github.com/jeffreytse/zsh-vi-mode.git "$HOME/.zsh/zsh-vi-mode"
fi
