# ssh-agent eval for correct ssh work
eval "$(ssh-agent -s)"
clear

fpath+=~/.zfunc
# PATH changing
export PATH=$HOME/.cargo/bin:$PATH
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
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats '%b'
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

