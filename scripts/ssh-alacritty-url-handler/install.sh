#!/usr/bin/env bash
set -euo pipefail

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
app_dir="$HOME/Applications/SSH in Alacritty.app"
executable="$app_dir/Contents/MacOS/ssh-alacritty-url-handler"
lsregister=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister

if [[ ! -d "$HOME/Applications/Alacritty.app" && ! -d /Applications/Alacritty.app ]]; then
    echo 'Install Alacritty before registering the SSH URL handler' >&2
    exit 1
fi

if [[ -e "$app_dir" ]]; then
    existing_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app_dir/Contents/Info.plist")
    if [[ "$existing_id" != com.lorut0.ssh-alacritty-url-handler ]]; then
        echo "Refusing to replace another application: $app_dir" >&2
        exit 1
    fi
fi

mkdir -p "$app_dir/Contents/MacOS"
install -m 0644 "$source_dir/Info.plist" "$app_dir/Contents/Info.plist"
xcrun clang -fobjc-arc -framework AppKit -framework CoreServices \
    "$source_dir/main.m" -o "$executable"
codesign --force --sign - "$app_dir"
"$lsregister" -f "$app_dir"
"$executable" --register
