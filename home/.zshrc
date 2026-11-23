# ssh-agent eval for correct ssh work
# (macOS wires its own agent to Keychain, so the eval lives in linux.zsh)
clear

if [[ $OSTYPE == darwin* && -o interactive ]]; then
    source "$HOME/.config/zsh/terminal-exit.zsh"
fi

ZSH_PARTS="$HOME/.config/zsh"
ZSH_PLUGINS_DIR="$HOME/.config/zsh-plugins"
[[ -d $ZSH_PLUGINS_DIR ]] || ZSH_PLUGINS_DIR="$HOME/.zsh"

fpath+=~/.zfunc

# Init completion system (must be after fpath)
autoload -Uz compinit && compinit

export EDITOR=nvim

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

# Load fzf after vi-mode initializes so its key bindings are preserved.
_dotfiles_fzf_init() {
    if command -v fzf >/dev/null 2>&1; then
        source <(fzf --zsh)
    fi
}
if (( $+functions[zvm_init] )) && [[ ${ZVM_INIT_DONE:-false} != true ]]; then
    zvm_after_init_commands+=(_dotfiles_fzf_init)
else
    _dotfiles_fzf_init
fi

# Optional commands from the independently deployed AI profile.
[[ -r $HOME/.config/zsh-ai/prpoll.zsh ]] && source "$HOME/.config/zsh-ai/prpoll.zsh"

# Per-machine overrides (not tracked in git)
[[ -r $HOME/.zshrc.local ]] && source "$HOME/.zshrc.local"

# Must run after all other code that may register ZLE widgets.
[[ -r $ZSH_PLUGINS_DIR/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] &&
    source "$ZSH_PLUGINS_DIR/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
