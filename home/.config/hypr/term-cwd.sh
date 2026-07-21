#!/usr/bin/env bash
# Open a new alacritty. If the currently focused window is already an
# alacritty terminal, open the new one in that terminal's current directory.

term="alacritty"

active=$(hyprctl activewindow -j 2>/dev/null)
class=$(printf '%s' "$active" | jq -r '.class // empty')
pid=$(printf '%s' "$active" | jq -r '.pid // empty')

cwd=""
if [ "$class" = "Alacritty" ] && [ -n "$pid" ]; then
	# Walk down to the newest leaf descendant (the active shell / program)
	# and read its working directory.
	child=$pid
	while next=$(pgrep -P "$child" -n) && [ -n "$next" ]; do
		child=$next
	done
	cwd=$(readlink -e "/proc/$child/cwd" 2>/dev/null)
fi

if [ -n "$cwd" ]; then
	exec "$term" --working-directory "$cwd"
else
	exec "$term"
fi
