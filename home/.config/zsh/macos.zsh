# macOS-only shell config, sourced from ~/.zshrc
# `open` is native here and ssh-agent is managed by launchd/Keychain.
# Homebrew's Yazi also installs `ya`; keep the existing Arcadia CLI name.
[[ -x /usr/local/bin/ya ]] && alias ya=/usr/local/bin/ya
[[ -x /opt/homebrew/bin/ya ]] && alias yazi-pkg='/opt/homebrew/bin/ya pkg'
