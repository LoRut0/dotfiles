#!/bin/bash

TERMINAL="alacritty"

# Получаем PID сфокусированного окна
PID=$(swaymsg -t get_tree | jq '.. | select(.focused? == true).pid')

# Если нет PID — просто открываем терминал
if [ -z "$PID" ]; then
    exec $TERMINAL
fi

TARGET_PID=$(pgrep -P "$PID" | head -n1)

# Получаем cwd конечного процесса
if [ -d "/proc/$TARGET_PID/cwd" ]; then
    DIR=$(readlink "/proc/$TARGET_PID/cwd")
else
    DIR="$HOME"
fi

exec $TERMINAL --working-directory "$DIR"
