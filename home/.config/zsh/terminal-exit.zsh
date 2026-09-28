# Only the shell directly owned by Terminal's login process gets the hook.
# Nested shells and tmux panes must never quit the terminal application.
[[ $TERM_PROGRAM == Apple_Terminal && -z $TMUX ]] || return
(( ${+_dotfiles_terminal_pid} )) && return

() {
    local parent_command terminal_pid terminal_command terminal_started
    parent_command=$(/bin/ps -p "$PPID" -o comm= 2>/dev/null) || return
    [[ ${parent_command:t} == login ]] || return
    terminal_pid=$(/bin/ps -p "$PPID" -o ppid= 2>/dev/null) || return
    terminal_pid=${terminal_pid//[[:space:]]/}
    [[ $terminal_pid == <-> ]] || return
    terminal_command=$(/bin/ps -p "$terminal_pid" -o comm= 2>/dev/null) || return
    [[ $terminal_command == /System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal ]] || return
    terminal_started=$(/bin/ps -p "$terminal_pid" -o lstart= 2>/dev/null) || return

    typeset -g _dotfiles_terminal_pid=$terminal_pid
    typeset -g _dotfiles_terminal_started=$terminal_started
    typeset -g _dotfiles_terminal_login=$PPID
}
(( ${+_dotfiles_terminal_pid} )) || return

_dotfiles_terminal_exit() {
    /usr/bin/nohup /bin/zsh -f \
        "$HOME/.config/zsh/terminal-exit-cleanup.zsh" \
        "$_dotfiles_terminal_pid" "$_dotfiles_terminal_started" \
        "$_dotfiles_terminal_login" </dev/null >/dev/null 2>&1 &!
}
autoload -Uz add-zsh-hook
add-zsh-hook zshexit _dotfiles_terminal_exit
