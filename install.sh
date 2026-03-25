#!/usr/bin/env bash
set -e

CONFIG_HOME="$HOME/.config"
DOTFILES="$(dirname $(realpath "$0"))"

mkdir -p $CONFIG_HOME

for dir in $DOTFILES/home/.config/*; do
    name="$(basename "$dir")"
    target="$CONFIG_HOME/$name"

    if [ -e "$target" ]; then
        echo "Skipping $target (already exists)"
        continue
    fi

    ln -sfn "$dir" "$target"
    echo "Linked dotfiles/home/.config/$name to $target"
done

for file in $DOTFILES/home/.*; do
    name="$(basename "$file")"

    if [[ $name == ".config" ]]; then
        continue
    fi

    target="$HOME/$name"
    if [[ -e "$target" ]]; then
        echo "Skipping $target (already exists)"
        continue
    fi

    ln -sfn "$file" "$target"
    echo "Linked dotfiles/home/$name to $target"
done

if [[ ! -e "$HOME/.zsh" ]]; then
    mkdir "$HOME/.zsh"
    git clone https://github.com/zsh-users/zsh-autosuggestions.git "$HOME/.zsh/zsh-autosuggestions"
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$HOME/.zsh/zsh-syntax-highlighting"
    git clone https://github.com/jeffreytse/zsh-vi-mode.git "$HOME/.zsh/zsh-vi-mode"
fi
