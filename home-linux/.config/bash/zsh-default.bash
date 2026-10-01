# Fallback for VM images whose immutable user database prevents chsh.
case $- in
    *i*) ;;
    *) return ;;
esac

# A login Bash may source .bashrc before the rest of .bash_profile. Let the
# profile finish first; its own invocation of this file will then start Zsh.
if [[ ${1:-} == bashrc ]] && shopt -q login_shell; then
    return
fi

zsh_path="$(command -v zsh 2>/dev/null)" || return
current_shell="$(getent passwd "$(id -un)" | cut -d: -f7)"
if [[ "$(readlink -f -- "$current_shell")" == "$(readlink -f -- "$zsh_path")" ]]; then
    return
fi

export SHELL="$zsh_path"
exec "$zsh_path" -l
