# Lean zsh config for AI-agent-spawned shells (ZDOTDIR=~/.config/zsh-agent).
# No vi-mode, prompt, ssh-agent, or interactive plugins - kept fast and quiet.

fpath+=~/.zfunc

HISTFILE=~/.histfile_agent
HISTSIZE=1000
SAVEHIST=1000
unsetopt autocd extendedglob

alias ll="ls -lh"
alias open="xdg-open"

# Prompt tweaking
# Loading version control system
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats '%b'
# Show cwd + current branch + prompt symbol
setopt PROMPT_SUBST
PROMPT='%F{green}%n%f %F{blue}%~%f%F{red}${vcs_info_msg_0_:+ (${vcs_info_msg_0_})}%f> '

# Completion sys
source $HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh
source $HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Enable colors
autoload -U colors && colors

eval "$(zoxide init zsh)"

# >>> forge initialize >>>
# !! Contents within this block are managed by 'forge zsh setup' !!
# !! Do not edit manually - changes will be overwritten !!

# Add required zsh plugins if not already present
if [[ ! " ${plugins[@]} " =~ " zsh-autosuggestions " ]]; then
    plugins+=(zsh-autosuggestions)
fi
if [[ ! " ${plugins[@]} " =~ " zsh-syntax-highlighting " ]]; then
    plugins+=(zsh-syntax-highlighting)
fi

# Load forge shell plugin (commands, completions, keybindings) if not already loaded
if [[ -z "$_FORGE_PLUGIN_LOADED" ]]; then
    eval "$(forge zsh plugin)"
fi

# Load forge shell theme (prompt with AI context) if not already loaded
if [[ -z "$_FORGE_THEME_LOADED" ]]; then
    eval "$(forge zsh theme)"
fi

# Disable Nerd Fonts (set during setup - icons not displaying correctly)
# To re-enable: remove this line and install a Nerd Font from https://www.nerdfonts.com/
export NERD_FONT=0
# <<< forge initialize <<<
