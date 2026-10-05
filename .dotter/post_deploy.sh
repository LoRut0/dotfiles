#!/usr/bin/env bash
set -euo pipefail

case "${DOTFILES_PROFILE:-}" in
    mac)
        yazi_ya=/opt/homebrew/bin/ya
        if [[ -L "$yazi_ya" && "$(readlink "$yazi_ya")" == ../Cellar/yazi/*/bin/ya ]]; then
            rm "$yazi_ya"
            echo "Removed Homebrew Yazi's ya command: $yazi_ya"
        fi
        agent="$HOME/Library/LaunchAgents/com.lorut0.arc-autostart.plist"
        domain="gui/$(id -u)"
        if ! launchctl print "$domain" >/dev/null 2>&1; then
            echo "LaunchAgent will load at the next graphical login: $agent" >&2
            exit 0
        fi
        if [[ -d "$HOME/Applications/Alacritty.app" || -d /Applications/Alacritty.app ]]; then
            bash "$HOME/.local/share/ssh-alacritty-url-handler/install.sh"
        else
            echo 'Install Alacritty and redeploy the mac profile to register ssh:// links.' >&2
        fi
        target="$domain/com.lorut0.arc-autostart"
        if ! launchctl print "$target" >/dev/null 2>&1; then
            launchctl bootstrap "$domain" "$agent"
        fi
        ;;
    linux-vm)
        zsh_path="$(command -v zsh)"
        current_shell="$(getent passwd "$(id -un)" | cut -d: -f7)"
        bash_fallback='$HOME/.config/bash/zsh-default.bash'
        bashrc_line='[[ -r "$HOME/.config/bash/zsh-default.bash" ]] && source "$HOME/.config/bash/zsh-default.bash" bashrc'
        bash_profile_line='[[ -r "$HOME/.config/bash/zsh-default.bash" ]] && source "$HOME/.config/bash/zsh-default.bash" login'
        if [[ "$(readlink -f -- "$current_shell")" != "$(readlink -f -- "$zsh_path")" ]]; then
            passwd_mount_options="$(findmnt -no OPTIONS -T /etc/passwd 2>/dev/null || true)"
            if grep -Fqx "$bashrc_line" "$HOME/.bashrc" 2>/dev/null &&
                grep -Fqx "$bash_profile_line" "$HOME/.bash_profile" 2>/dev/null; then
                echo "Using the existing Zsh startup fallback from $bash_fallback."
            elif [[ ",$passwd_mount_options," != *,ro,* && ",$passwd_mount_options," != *,nosuid,* ]] &&
                chsh -s "$zsh_path"; then
                echo "Default shell changed to $zsh_path; it will be used from the next login."
            else
                touch "$HOME/.bashrc" "$HOME/.bash_profile"
                grep -Fqx "$bashrc_line" "$HOME/.bashrc" || printf '\n%s\n' "$bashrc_line" >> "$HOME/.bashrc"
                grep -Fqx "$bash_profile_line" "$HOME/.bash_profile" || printf '\n%s\n' "$bash_profile_line" >> "$HOME/.bash_profile"
                echo "Could not update the login shell; installed the Zsh startup fallback from $bash_fallback."
            fi
        fi

        systemctl --user daemon-reload
        for slot in first second third fourth; do
            systemctl --user enable --now "arc-autostart@$slot.service"
        done
        ;;
esac
