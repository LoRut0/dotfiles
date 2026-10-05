# macOS-only shell config, sourced from ~/.zshrc
# `open` is native here and ssh-agent is managed by launchd/Keychain.
# Keep the Arcadia CLI name available in interactive shells.
[[ -x /usr/local/bin/ya ]] && alias ya=/usr/local/bin/ya
