# Linux-only shell config, sourced from ~/.zshrc

# ssh-agent eval for correct ssh work
eval "$(ssh-agent -s)"

# starting firefox in wayland mode
export MOZ_ENABLE_WAYLAND=1

alias open="xdg-open"

# Override in ~/.zshrc.local if the proxy runs elsewhere
: ${ZSH_PROXY_URL:=http://127.0.0.1:10809}

# proxy applies ONLY when launching claude or forge
function claude() {
  HTTP_PROXY="$ZSH_PROXY_URL" \
  HTTPS_PROXY="$ZSH_PROXY_URL" \
  command claude "$@"
}
function forge() {
  HTTP_PROXY="$ZSH_PROXY_URL" \
  HTTPS_PROXY="$ZSH_PROXY_URL" \
  command forge "$@"
}

function prox() {
    case "$1" in
        on)
            export HTTP_PROXY="$ZSH_PROXY_URL"
            export HTTPS_PROXY="$ZSH_PROXY_URL"
            export http_proxy="$HTTP_PROXY"
            export https_proxy="$HTTPS_PROXY"
            echo "✅ Proxy enabled ($HTTP_PROXY)"
            ;;
        off)
            unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
            echo "❌ Proxy disabled"
            ;;
        status)
            if [ -n "$HTTP_PROXY" ]; then
                echo "✅ Proxy is ON: $HTTP_PROXY"
            else
                echo "❌ Proxy is OFF"
            fi
            ;;
        *)
            echo "Usage: proxy {on|off|status}"
            ;;
    esac
}

function protonup() {
    command "$HOME/.venvs/protonup/bin/protonup" "$@"
}
