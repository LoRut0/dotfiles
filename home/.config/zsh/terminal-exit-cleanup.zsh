#!/bin/zsh -f
# Detached helper: wait for login to exit, then quit only its idle Terminal PID.
emulate -L zsh
terminal_pid=$1
terminal_started=$2
login_pid=$3
[[ $terminal_pid == <-> && $login_pid == <-> && -n $terminal_started ]] || exit 1

for attempt in {1..20}; do
    /bin/sleep 0.1
    snapshot=$(/bin/ps -axo pid=,ppid=) || exit 1
    if print -r -- "$snapshot" | /usr/bin/awk -v pid="$login_pid" \
        '$1 == pid { found=1 } END { exit !found }'; then
        continue
    fi

    # Any other child (another tab/window or a starting session) keeps it alive.
    if print -r -- "$snapshot" | /usr/bin/awk -v pid="$terminal_pid" \
        '$2 == pid { found=1 } END { exit !found }'; then
        exit 0
    fi
    current_started=$(/bin/ps -p "$terminal_pid" -o lstart=) || exit 0
    [[ $current_started == "$terminal_started" ]] || exit 0

    # AppKit addresses a PID and requests a normal quit without Apple Events
    # permissions. Do not use `tell application "Terminal"` with open -n.
    /usr/bin/osascript -l JavaScript - "$terminal_pid" <<'JAVASCRIPT'
ObjC.import('AppKit');
function run(argv) {
    const app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(Number(argv[0]));
    if (!app.isNil() && ObjC.unwrap(app.bundleIdentifier) === 'com.apple.Terminal') {
        app.terminate;
    }
}
JAVASCRIPT
    exit $?
done
