# configs

## Dotter profiles

The repository defines independent application packages in
`.dotter/global.toml`. A machine selects a set of packages through one of the
versioned profiles in `.dotter/profiles/`:

| Profile | Purpose |
| --- | --- |
| `mac` | macOS workstation, including Karabiner and macOS tmux |
| `linux-desktop` | Full Linux desktop with Sway, Hyprland and bars |
| `linux-vm` | Minimal Linux VM with Zsh and Neovim |
| `ai` | Claude and Codex configuration on macOS or Linux |

From the repository root, review a profile before deploying it:

```sh
bash dotter.sh linux-vm --dry-run deploy
bash dotter.sh linux-vm deploy
```

Replace `linux-vm` with the desired profile. The wrapper downloads a pinned
Dotter v0.13.5 executable for macOS ARM64 or Linux x86_64/ARM64 on first use,
checks its SHA-256 digest, and keeps it in the ignored `.dotter/bin/` directory.
No separate manual Dotter installation is needed. The profile's selected
packages can be edited directly in its TOML file. Dotter's cache is also
machine-local and ignored by Git.

The `ai` profile is optional and deployed separately from a machine profile:

```sh
bash dotter.sh mac deploy
bash dotter.sh ai deploy
```

Use `linux-desktop` or `linux-vm` instead of `mac` on Linux. On an existing
installation, deploy the machine profile first so Dotter removes the AI links
from its old shared cache; then deploy `ai` to put them under its own cache.
Subsequent deployments of either profile leave the other's links alone. The
Claude package currently links `~/.config/claude`, and Codex links files into
`~/.codex/skills`.

The old `install_cfg.sh` remains available for existing installations. It
does not use the Dotter profiles. Do not run both installers for the same
destination during migration; first inspect Dotter's dry run and the existing
links. The systemd timer in `sysd/` is a separate privileged installation.

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
