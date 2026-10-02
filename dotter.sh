#!/usr/bin/env bash
set -euo pipefail

dotfiles_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
profile="${1:-}"

case "$profile" in
    mac|linux-desktop|linux-vm|ai|vscode-arc) shift ;;
    *)
        echo "Usage: $0 {mac|linux-desktop|linux-vm|ai|vscode-arc} [Dotter options] deploy" >&2
        exit 2
        ;;
esac

if [[ $# -eq 0 ]]; then
    echo "Specify an action, for example: --dry-run deploy or deploy" >&2
    exit 2
fi

platform="$(uname -s)"
architecture="$(uname -m)"
case "$platform/$architecture" in
    Darwin/arm64)
        asset="dotter-macos-arm64.arm"
        expected_sha256="1de749c8ca106e164db3c63fcf3fd0cb7820645663ae6c4afe5c976779ba3738"
        ;;
    Linux/x86_64)
        asset="dotter-linux-x64-musl"
        expected_sha256="a79e1ef325d4ecb3e3fffe3dd961f6f854cc45e2eb82755d3be23cdfe0603211"
        ;;
    Linux/aarch64|Linux/arm64)
        asset="dotter-linux-arm64-musl"
        expected_sha256="6efc68bf72313db462a72810b9c2d33edcf04d9b10382f564c46f9aaf942c979"
        ;;
    *)
        echo "No pinned Dotter binary for $platform/$architecture" >&2
        exit 1
        ;;
esac

case "$profile/$platform" in
    mac/Darwin|linux-desktop/Linux|linux-vm/Linux|ai/Darwin|ai/Linux|vscode-arc/Darwin|vscode-arc/Linux) ;;
    *)
        echo "Profile $profile is not for $platform" >&2
        exit 2
        ;;
esac

dotter_options=(
    --global-config .dotter/global.toml
    --local-config ".dotter/profiles/$profile.toml"
)
if [[ "$profile" == ai || "$profile" == vscode-arc ]]; then
    dotter_options+=(--cache-file ".dotter/cache-$profile.toml" --cache-directory ".dotter/cache-$profile")
fi

dotter_bin_dir="$dotfiles_dir/.dotter/bin"
dotter_bin="$dotter_bin_dir/$asset"

if [[ ! -x "$dotter_bin" ]]; then
    mkdir -p "$dotter_bin_dir"
    download_tmp="$(mktemp "$dotter_bin_dir/.download.XXXXXX")"
    trap 'rm -f -- "$download_tmp"' EXIT

    curl -fsSL --retry 3 \
        "https://github.com/SuperCuber/dotter/releases/download/v0.13.5/$asset" \
        -o "$download_tmp"

    if [[ "$platform" == Darwin ]]; then
        actual_sha256="$(shasum -a 256 "$download_tmp" | awk '{print $1}')"
    else
        actual_sha256="$(sha256sum "$download_tmp" | awk '{print $1}')"
    fi

    if [[ "$actual_sha256" != "$expected_sha256" ]]; then
        echo "Dotter download checksum mismatch" >&2
        exit 1
    fi

    chmod 0755 "$download_tmp"
    mv "$download_tmp" "$dotter_bin"
    trap - EXIT
fi

cd "$dotfiles_dir"
export DOTFILES_PROFILE="$profile"
exec "$dotter_bin" \
    "${dotter_options[@]}" \
    "$@"
