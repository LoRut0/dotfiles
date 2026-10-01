# ssh-agent eval for correct ssh work
# (macOS wires its own agent to Keychain, so the eval lives in linux.zsh)
clear

# Register before tmux starts: pane shells belong to the tmux server, not Terminal.
if [[ $OSTYPE == darwin* && -o interactive && -z $TMUX ]]; then
    source "$HOME/.config/zsh/terminal-exit.zsh"
fi

# Каждый терминал — отдельный клиент tmux: список окон общий, но текущее окно
# у каждого своё. Держится на session groups: базовая сессия хранит окна, а
# терминал получает собственную сессию-«вид» в той же группе.
# Отключить: NO_TMUX=1. На VM это делает маркер профиля Dotter
# или systemd-detect-virt, если профиль ещё не успел развернуться.
# Сменить базу: TMUX_BASE_SESSION=имя.
typeset _dotfiles_vm_without_tmux=
if [[ -e "$HOME/.dotter-linux-vm" ]] ||
    { [[ $OSTYPE == linux* ]] && (( $+commands[systemd-detect-virt] )) && systemd-detect-virt --quiet; }; then
    _dotfiles_vm_without_tmux=1
fi
if [[ -o interactive && -z $TMUX && -t 1 && -z $NO_TMUX && -z $_dotfiles_vm_without_tmux && "$TERM_PROGRAM" != "vscode" ]] && (( $+commands[tmux] )); then
    () {
        local base=${TMUX_BASE_SESSION:-main} stale
        tmux has-session -t "=$base" 2>/dev/null || tmux new-session -d -s "$base" 2>/dev/null
        tmux has-session -t "=$base" 2>/dev/null || return

        # убрать «виды», осиротевшие от закрытых терминалов
        for stale in ${(f)"$(tmux list-sessions -F '#{session_name}' \
            -f "#{&&:#{m:$base-view-*,#{session_name}},#{==:#{session_attached},0}}" 2>/dev/null)"}; do
            [[ -n $stale ]] && tmux kill-session -t "=$stale" 2>/dev/null
        done

        if (( ${+_dotfiles_terminal_pid} )); then
            # Keep the outer shell so its exit hook runs after the client detaches.
            tmux new-session -s "$base-view-$$" -t "$base"
            exit $?
        else
            exec tmux new-session -s "$base-view-$$" -t "$base"
        fi
    }
fi
unset _dotfiles_vm_without_tmux

ZSH_PARTS="$HOME/.config/zsh"
ZSH_PLUGINS_DIR="$HOME/.config/zsh-plugins"
[[ -d $ZSH_PLUGINS_DIR ]] || ZSH_PLUGINS_DIR="$HOME/.zsh"

fpath+=~/.zfunc

# Init completion system (must be after fpath)
autoload -Uz compinit && compinit

# PATH changing
export EDITOR=nvim
[[ -d $HOME/.cargo/bin ]] && export PATH="$HOME/.cargo/bin:$PATH"

# Created by newuser for 5.9

# Lines configured by zsh-newuser-install
HISTFILE=~/.histfile
HISTSIZE=1000
SAVEHIST=1000
unsetopt autocd extendedglob
bindkey -v
# End of lines configured by zsh-newuser-install

# Enable colors
autoload -U colors && colors

# Prompt tweaking
# Loading version control system
autoload -Uz vcs_info

ARC_ZSH_PLUGIN="$ZSH_PLUGINS_DIR/arc-zsh-plugin/arc.plugin.zsh"
[[ -r $ARC_ZSH_PLUGIN ]] && source "$ARC_ZSH_PLUGIN"

precmd() {
    vcs_info
    _dotfiles_arc_branch=
    if [[ -z $vcs_info_msg_0_ ]] &&
        (( $+commands[arc] && $+functions[arc_is_repo] && $+functions[arc_current_branch] )) &&
        arc_is_repo; then
        _dotfiles_arc_branch="$(arc_current_branch)"
    fi
}
zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:git:*' formats '%b'

# Show cwd + current branch + prompt symbol
setopt PROMPT_SUBST
PROMPT='%F{green}%n%f %F{blue}%~%f%F{red}${vcs_info_msg_0_:+ (${vcs_info_msg_0_})}${_dotfiles_arc_branch:+ (${_dotfiles_arc_branch})}%f> '

# autoload vigo command from ~/.zfunc
autoload -Uz vigo

# Completion sys
[[ -r $ZSH_PLUGINS_DIR/zsh-autosuggestions/zsh-autosuggestions.zsh ]] &&
    source "$ZSH_PLUGINS_DIR/zsh-autosuggestions/zsh-autosuggestions.zsh"
[[ -r $ZSH_PLUGINS_DIR/zsh-vi-mode/zsh-vi-mode.plugin.zsh ]] &&
    source "$ZSH_PLUGINS_DIR/zsh-vi-mode/zsh-vi-mode.plugin.zsh"

export PATH="$HOME/.local/bin:$PATH"

alias ll="ls -lh"

function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	command yazi "$@" --cwd-file="$tmp"
	IFS= read -r -d '' cwd < "$tmp"
	[ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
	command rm -f -- "$tmp"
}

(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"

# Platform-specific bits
case "$OSTYPE" in
    darwin*) [[ -r $ZSH_PARTS/macos.zsh ]] && source "$ZSH_PARTS/macos.zsh" ;;
    linux*)  [[ -r $ZSH_PARTS/linux.zsh ]] && source "$ZSH_PARTS/linux.zsh" ;;
esac

# Per-machine overrides (not tracked in git)
[[ -r $HOME/.zshrc.local ]] && source "$HOME/.zshrc.local"

# Must run after all other code that may register ZLE widgets.
[[ -r $ZSH_PLUGINS_DIR/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] &&
    source "$ZSH_PLUGINS_DIR/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
