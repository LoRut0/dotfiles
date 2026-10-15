#!/bin/sh
set -eu

# Run interactively once. Only the installed root-owned copies receive a Codex rule.
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
source_script="$script_dir/arc_pr_mount.py"
source_arc="$HOME/.arc/channels/stable/arc"
target_dir=/usr/local/libexec
target_script="$target_dir/codex-arc-pr-mount"
target_arc="$target_dir/codex-arc-pr-bin"
rules_file="$HOME/.codex/rules/default.rules"
rule='prefix_rule(pattern=["/usr/local/libexec/codex-arc-pr-mount"], decision="allow")'

if [ ! -f "$source_script" ] || [ ! -x "$source_arc" ]; then
    echo 'Source script or stable Arc binary is missing.' >&2
    exit 1
fi

sudo install -d -o root -g wheel -m 755 "$target_dir"
sudo install -o root -g wheel -m 755 "$source_script" "$target_script"
sudo install -o root -g wheel -m 755 "$source_arc" "$target_arc"

cmp "$source_script" "$target_script"
cmp "$source_arc" "$target_arc"
"$target_script" --help >/dev/null

mkdir -p "$(dirname "$rules_file")"
if ! grep -Fqx "$rule" "$rules_file" 2>/dev/null; then
    printf '\n%s\n' "$rule" >> "$rules_file"
fi
codex execpolicy check --pretty --rules "$rules_file" -- "$target_script" mount 16455286
echo 'Installed the protected PR mount helper and Codex rule. Restart Codex to load it.'
