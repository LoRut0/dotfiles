# Loaded only when the separately deployed AI profile is present.
prpoll() {
    local poller_script="$HOME/.local/share/arcanum-pr-poller/poller.py"
    if [[ ! -r "$poller_script" ]]; then
        print -u2 -- "prpoll: deploy the Dotter ai profile to install $poller_script"
        return 1
    fi
    command python3 "$poller_script" "$@"
}
