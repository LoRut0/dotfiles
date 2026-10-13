#!/usr/bin/env bash
set -euo pipefail

preferences="$(mktemp "${TMPDIR:-/tmp}/finder-grid.XXXXXX")"
trap 'rm -f -- "$preferences"' EXIT

defaults export com.apple.finder - > "$preferences"
changed="$(python3 - "$preferences" <<'PY'
import plistlib
import sys

path = sys.argv[1]
with open(path, "rb") as file:
    settings = plistlib.load(file)

changed = False
for view_name in (
    "DesktopViewSettings",
    "StandardViewSettings",
    "FK_StandardViewSettings",
):
    icons = settings.setdefault(view_name, {}).setdefault("IconViewSettings", {})
    if icons.get("arrangeBy") != "grid":
        icons["arrangeBy"] = "grid"
        changed = True

if changed:
    with open(path, "wb") as file:
        plistlib.dump(settings, file)
    print("changed")
PY
)"

if [[ "$changed" == changed ]]; then
    defaults import com.apple.finder "$preferences"
    if killall Finder 2>/dev/null; then
        echo 'Enabled snap to grid for Finder icons and the desktop; restarted Finder.'
    else
        echo 'Enabled snap to grid for Finder icons and the desktop; restart Finder to apply it.' >&2
    fi
fi
