# configs

## Terminal on macOS

New Terminal shells register an exit hook before attaching to tmux. When the
outer shell exits (including after tmux detaches), a detached helper waits for
its `login` process to end and requests a normal quit of that Terminal PID only
if it has no remaining child processes. This also handles separate instances
started by Karabiner with `open -n`; other windows with live sessions keep their
instance running. Nested shells and tmux panes do not register the hook.

The configuration takes effect in newly opened terminals; existing tmux clients
started with `exec` need their Terminal instance closed manually once.

## packages

```bash
grim
flameshot
helvum
pavucontrol

# big file manager
dolphin

# reading pdf, fb2, etc
foliate
xournalpp

# media
vlc

p7zip

# yazi is the file manager, else is helpers for it
yazi ffmpegthumbnailer jq poppler fd ripgrep fzf zoxide mediainfo imagemagick
# tool for rendering images inside terminal (works in alacritty)
chafa
# fast compression and decompression tool
ouch

# adb etc
android-tools
# java developer toolkit
jdk-openjdk
# for reverse engineering
jadx
# apktool (download from https://apktool.org/)

# ai stuff
# forgecode (https://github.com/tailcallhq/forgecode)
forgecode
claude

# utility for updating pacman mirrors (sudo systemctl enable --now reflector.timer)
reflector

# conspectus
obsidian

# Monitoring state of PC
htop
btop
nvtop

# Tool for cleaning up file names
detox
```
