#!/bin/zsh
tmp=$(mktemp)

command yazi --cwd-file="$tmp"

cwd=$(cat "$tmp" 2>/dev/null)

rm -f "$tmp"

if [ -z "$cwd" ]; then
    exit 0
fi

cd "$cwd"

exec zsh
