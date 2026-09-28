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
# Отключить: NO_TMUX=1. На linux-vm это делает маркер профиля Dotter.
# Сменить базу: TMUX_BASE_SESSION=имя.
if [[ -o interactive && -z $TMUX && -t 1 && -z $NO_TMUX && ! -e "$HOME/.dotter-linux-vm" && "$TERM_PROGRAM" != "vscode" ]] && (( $+commands[tmux] )); then
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

ZSH_PARTS="$HOME/.config/zsh"

# arc-zsh completions must land on fpath before compinit
[[ -d $HOME/.zsh/arc-zsh ]] && fpath=($HOME/.zsh/arc-zsh $fpath)
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
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats '%b'

if [[ -d $HOME/.zsh/arc-zsh ]]; then
    source $HOME/.zsh/arc-zsh/arc-zsh.plugin.zsh
    zstyle ':vcs_info:*' enable git arc
    zstyle ':vcs_info:arc:*' formats '%b'
    zstyle ':vcs_info:arc:*' check-for-changes true
else
    zstyle ':vcs_info:*' enable git
fi

# Show cwd + current branch + prompt symbol
setopt PROMPT_SUBST
PROMPT='%F{green}%n%f %F{blue}%~%f%F{red}${vcs_info_msg_0_:+ (${vcs_info_msg_0_})}%f> '

# autoload vigo command from ~/.zfunc
autoload -Uz vigo

# Completion sys
ZSH_PLUGINS_DIR="$HOME/.config/zsh-plugins"
[[ -d $ZSH_PLUGINS_DIR ]] || ZSH_PLUGINS_DIR="$HOME/.zsh"
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
