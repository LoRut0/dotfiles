# macOS-only shell config, sourced from ~/.zshrc
# `open` is native here and ssh-agent is managed by launchd/Keychain.
# Keep the Arcadia CLI name available in interactive shells.
[[ -x /usr/local/bin/ya ]] && alias ya=/usr/local/bin/ya

# Homebrew keeps the .NET runtime outside the apphost's default search paths.
[[ -x /opt/homebrew/opt/dotnet/libexec/dotnet ]] &&
    export DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec
