# configs

## Dotter profiles

The repository defines independent application packages in
`.dotter/global.toml`. A machine selects a set of packages through one of the
versioned profiles in `.dotter/profiles/`:

| Profile | Purpose |
| --- | --- |
| `mac` | macOS workstation, including Karabiner, tmux and Arc mounts |
| `linux-desktop` | Full Linux desktop with Sway, Hyprland and bars |
| `linux-vm` | Linux VM with Zsh as the login shell and Arc worktrees; no automatic tmux startup |
| `ai` | Claude and Codex configuration on macOS or Linux |
| `vscode-arc` | Optional VS Code workspace helper for Arc checkouts on macOS or Linux |
| `nvim` | Optional Neovim configuration on macOS or Linux |

From the repository root, review a profile before deploying it:

```sh
bash dotter.sh linux-vm --dry-run deploy
bash dotter.sh linux-vm deploy
```

Deploying `linux-vm` also changes the current user's login shell to Zsh with
`chsh` when needed. The new shell is used from the next login, and the VM
profile marker keeps `.zshrc` from starting tmux automatically. When `chsh`
cannot update the account (for example, on an immutable VM image), the
deployment adds a small startup fallback to the existing Bash profile files
instead; interactive Bash is then replaced by a Zsh login shell while
non-interactive scripts stay in Bash.

The VM profile also deploys a minimal tmux configuration with mouse support for
scrolling pane history. After deploying it, apply it to an existing tmux server
with `tmux source-file ~/.config/tmux/tmux.conf`. New servers load it automatically.

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
Claude package links `~/.config/claude`. The profile also links the global
`~/.codex/AGENTS.md` and the shared `arc-pr-view`, `vm-cleanup`, and `dotfiles`
skills into `~/.agents/skills`. Claude Code receives the same skills through
links in `~/.claude/skills`. The `dotfiles` skill describes how to update this
repository through Dotter and commit and push completed changes to GitHub.
If the AI dry run reports existing regular files at those targets, reconcile
them before deploying; Dotter does not replace them without `--force`.

Before migrating an existing installation, inspect Dotter's dry run and the
existing links. The systemd timer in `sysd/` is a separate privileged
installation.

The machine profiles also deploy the vendored Zsh plugins from
`home/.config/zsh-plugins/`. Their pinned upstream revisions and licenses are
recorded there. Until that link is deployed, `.zshrc` can use the previous
`~/.zsh` copies. Syntax highlighting loads last, after other Zsh widgets and
local overrides.

## Neovim

The separate `nvim` profile links `home/.config/nvim` to `~/.config/nvim`,
including the LazyVim configuration, plugins, keybindings, and Arcadia search.
Install the Neovim executable separately, then deploy its configuration:

```sh
bash dotter.sh nvim --dry-run deploy
bash dotter.sh nvim deploy
```

It uses its own Dotter cache and can be deployed independently or alongside a
machine profile, `ai`, and `vscode-arc`. The `mac`, `linux-desktop`, and `linux-vm`
profiles no longer include Neovim.

When migrating an existing installation, deploy the current machine profile
first so Dotter releases the Neovim link from its shared cache, then deploy
`nvim`. For example, on a VM:

```sh
bash dotter.sh linux-vm deploy
bash dotter.sh nvim deploy
```

Subsequent deployments manage their links independently.

## Arc mounts at startup

The `mac` profile includes a LaunchAgent that restores `~/arcadia` and
`~/arcadia-wt/{first,second,third,fourth}` at login. The
`linux-vm` profile includes a user systemd service template for the four
worktrees, without the primary `~/arcadia` mount. The shared helper reads
`arc mount --list --json` and skips mounted paths. On first use, it creates
missing worktree slots as new branches from `trunk` with a shared object store
and no lifecycle hooks. Later starts remount the registered worktrees. It
retries failures for up to ten minutes and refuses to overwrite a non-empty
or symbolic mount path. The primary macOS `~/arcadia` must already be
registered.

Each machine needs `arc`, `ya`, Python 3.7+, valid Arc credentials, and network
access for the first mount.

Deploying `mac` also loads the LaunchAgent. To rerun an already loaded agent:

```sh
launchctl kickstart "gui/$(id -u)/com.lorut0.arc-autostart"
```

Deploying `linux-vm` enables all four user service instances. To start the
user manager at boot, before the first login, enable lingering once on the VM:

```sh
sudo loginctl enable-linger "$USER"
```

On macOS, see `~/.local/state/arc-autostart.log`; on Linux, use
`journalctl --user -u arc-autostart@first.service` (or another slot). To retry
a failed mount without rebooting, run `~/.local/bin/arc-autostart mac` on macOS
or `~/.local/bin/arc-autostart linux-vm --slot first` on the VM, replacing
`first` with the affected slot name.

## VS Code in Arcadia

The separate `vscode-arc` profile installs `~/.local/bin/arc-vscode`:

```sh
bash dotter.sh vscode-arc --dry-run deploy
bash dotter.sh vscode-arc deploy
```

It has its own Dotter cache, so it can be deployed alongside any machine profile
and `ai`. When migrating an installation previously managed by `linux-vm`, deploy
`linux-vm` first to release the helper from its old cache, then deploy `vscode-arc`.
Subsequent deployments manage their links independently.

The helper creates a persistent multi-root workspace for each Arc checkout.
Only add the services and libraries
you need; the checkout root is used for Arc integration, not as an Explorer or
search folder. The workspace uses `ya tool clangd`, disables competing C/C++
IntelliSense, and enables file watching for the selected folders.

Create a workspace once (folder paths are relative to the checkout):

```sh
arc-vscode init ~/arcadia-wt/first \
  taxi/uservices/services/grocery-goals \
  taxi/uservices/services/grocery-api
```

Open `/codenv/workspace/arcadia-first.code-workspace` with **File → Open
Workspace from File** in the VS Code window connected to the VM. For the main
checkout, `arc-vscode init ~/arcadia ...` creates `arcadia.code-workspace`.
An existing workspace is never overwritten. New workspaces default to
`/codenv/workspace` when that directory exists, otherwise
`$XDG_DATA_HOME/arc-vscode` (normally `~/.local/share/arc-vscode`). Use `--output`
to choose a different location.

To work in another service in that checkout:

1. Use **File → Add Folder to Workspace**, selecting that service's directory
   containing `ya.make`. Save the workspace if VS Code prompts.
2. Open a source file in the folder and press **Ctrl+Shift+B**. The default task,
   **Arcadia: Generate compilation database (current folder)**, builds generated
   headers and sources, writes `compile_commands.json` in that folder, and
   refreshes the database used by VS Code. Run it again after changes to build
   definitions or generated-code inputs.
3. If necessary, run **clangd: Restart language server** from the Command Palette.

With no file open, use **Tasks: Run Task → Arcadia: Generate compilation database
(choose folder)** and enter the folder path relative to the checkout. After
removing folders, or adding a folder with an already working database, run
**Arcadia: Refresh workspace databases**. Only folders belonging to that checkout
are accepted. These C++ tasks do not configure Python analysis or debugger launches.

The same generation is available from a terminal, including for Neovim:

```sh
arc-vscode prepare ~/arcadia-wt/first/taxi/uservices/services/grocery-goals \
  --workspace /codenv/workspace/arcadia-first.code-workspace
# Inspect commands without running a build:
arc-vscode prepare . --dry-run
```

`--workspace` is optional when only the local database is needed. Use `--jobs N`
to change the default limit of six workers, or repeat `--ya-arg=-DNAME=value` to
pass build flags to both `ya make` and `ya dump compile-commands`.

Generated headers and sources live under
`~/.cache/arc-vscode/<checkout>-<hash>/targets/<service-path>/build`. Both `ya`
commands use that same build root, and the database retains the compiler's
absolute path. There are no generated-source links in the checkout. A valid new
database replaces the old one atomically; the previous copy is saved beside the
build directory as `previous_compile_commands.json`.

VS Code reads a combined database in that checkout's cache, built from the
selected folders' databases. This includes their transitive dependencies, so
navigation into shared libraries retains compiler flags. Each service's own
database takes precedence for its files; duplicate dependency entries use the
last prepared service, or the newest service database on a manual refresh.
Clangd indexes these dependencies too; selecting folders limits Explorer/search
and file watching, but indexing cost still depends on the selected targets.
New folders need generation first. Existing databases are reused as-is; regenerate
older databases if they point at missing generated headers (for example `.gen`).

Workspaces, build outputs, and compilation databases are machine-local; dotfiles
stores the helper and its tests. Run the tests with
`python3 -B -m unittest discover -s tests -v`.

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
