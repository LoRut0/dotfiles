#!/bin/sh
# Copy to this host's desktop when available. Remote clients also receive OSC 52
# from tmux itself; no desktop clipboard program is needed on a headless VM.
set -eu

if command -v pbcopy >/dev/null 2>&1; then
    exec pbcopy
elif [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wl-copy >/dev/null 2>&1; then
    exec wl-copy
elif [ -n "${DISPLAY:-}" ] && command -v xclip >/dev/null 2>&1; then
    exec xclip -selection clipboard -in >/dev/null
elif [ -n "${DISPLAY:-}" ] && command -v xsel >/dev/null 2>&1; then
    exec xsel --clipboard --input
else
    cat >/dev/null
fi
