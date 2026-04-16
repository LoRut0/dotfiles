#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

SRC_SCRIPT="$SCRIPT_DIR/sysd/update-v2ray-geo.sh"
SRC_SERVICE="$SCRIPT_DIR/sysd/update-v2ray-geo.service"
SRC_TIMER="$SCRIPT_DIR/sysd/update-v2ray-geo.timer"

DST_SCRIPT="/usr/local/bin/update-v2ray-geo.sh"
DST_SERVICE="/etc/systemd/system/update-v2ray-geo.service"
DST_TIMER="/etc/systemd/system/update-v2ray-geo.timer"

require_file() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        echo "File not found: $path" >&2
        exit 1
    fi
}

echo "Checking source files..."
require_file "$SRC_SCRIPT"
require_file "$SRC_SERVICE"
require_file "$SRC_TIMER"

echo "Installing script..."
sudo install -m 0755 "$SRC_SCRIPT" "$DST_SCRIPT"

echo "Installing systemd service..."
sudo install -m 0644 "$SRC_SERVICE" "$DST_SERVICE"

echo "Installing systemd timer..."
sudo install -m 0644 "$SRC_TIMER" "$DST_TIMER"

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling timer..."
sudo systemctl enable --now update-v2ray-geo.timer

echo "Installation complete."
echo "INFO: Useful commands:"
echo "  systemctl status update-v2ray-geo.timer"
