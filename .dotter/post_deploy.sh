#!/usr/bin/env bash
set -euo pipefail

case "${DOTFILES_PROFILE:-}" in
    mac)
        agent="$HOME/Library/LaunchAgents/com.lorut0.arc-autostart.plist"
        domain="gui/$(id -u)"
        if ! launchctl print "$domain" >/dev/null 2>&1; then
            echo "LaunchAgent will load at the next graphical login: $agent" >&2
            exit 0
        fi
        target="$domain/com.lorut0.arc-autostart"
        if ! launchctl print "$target" >/dev/null 2>&1; then
            launchctl bootstrap "$domain" "$agent"
        fi
        ;;
    linux-vm)
        systemctl --user daemon-reload
        for slot in first second third fourth; do
            systemctl --user enable --now "arc-autostart@$slot.service"
        done
        ;;
esac
