# ssh-agent eval for correct ssh work
# (macOS wires its own agent to Keychain, so the eval lives in linux.zsh)
clear

ZSH_PARTS="$HOME/.config/dotfiles/home/.config/zsh"

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
source $HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh
source $HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
# zsh-vi-mode
source $HOME/.zsh/zsh-vi-mode/zsh-vi-mode.plugin.zsh

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
