# configs

## Dotter profiles

The repository defines independent application packages in
`.dotter/global.toml`. A machine selects a set of packages through one of the
versioned profiles in `.dotter/profiles/`:

| Profile | Purpose |
| --- | --- |
| `mac` | macOS workstation, including Karabiner, tmux, Arc mounts and `arc-compdb`; tmux starts automatically |
| `linux-desktop` | Full Linux desktop with Sway, Hyprland and bars |
| `linux-vm` | Linux VM with Zsh as the login shell, Arc worktrees and `arc-compdb`; no automatic tmux startup |
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

All three machine profiles deploy the shared tmux configuration described below.

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

The AI profile also deploys the `prpoll` Zsh function, its Python runtime,
and the Codex skills `arcanum-pr-agent-helper` (**PR agent helper**, 10-minute
polling with small authorized fixes) and `arcanum-auto-review` (**Auto review**,
15-minute polling for reviewing another author's PR without code changes).
Both create outgoing issues, comments and replies as Arcanum drafts. Publication
requires explicit approval of the prepared draft IDs/text; issue status changes
also require approval. Pending approval does not keep the poller's event in flight.
New shells load the function automatically when the shared Zsh configuration
is deployed. In an existing shell, load it with:

```sh
source ~/.config/zsh-ai/prpoll.zsh
prpoll status
prpoll status --human
prpoll check --pr 12345678 --dry-run
prpoll stop --pr 12345678
prpoll resume --pr 12345678
```

Replace the PR ID with your own. `check` without `--dry-run` can queue a model
turn when it finds changes. `status --human` displays a table with monitor
states with stop reasons, PR authors, skill modes, titles, intervals, local timestamps and errors.
Authors are shown by login/name, or UID when no login is available. Plain `status`
keeps JSON output with `title`, `author`, the skill slug in `skill`, its display
label in `mode`, and the saved `stop_reason` for stopped PRs. Mode is derived from
`skill_path`, not the polling interval or legacy state directory names.
Titles and authors are saved from normal full snapshots and updated
when PR metadata changes, without extra API requests for the status command.
Both read saved state only, without contacting Arcanum or checking scheduler health.
`stop --pr <ID>` records `user_request`; use `--reason author_ship`, `merged`, or
`closed` for a verified automatic stop. `ack --stop` accepts the same `--reason`.
For older records, status uses a matching terminal event from the local review
state; if evidence is missing, it displays “причина не сохранена”. `resume` clears
the previous stop reason.
The runtime requires Python 3.10+ and the locally
installed Arcanum/SkillStore authentication helpers. The review skills also
require `arcanum-review-pr`, `arcanum`, and `arc`, installed separately.

Only code and skill instructions belong in dotfiles. Monitor configuration,
PR state, events, logs, credentials, and the machine-specific scheduler stay
local under `~/.local/share/arcanum-pr-poller` and `~/Library/LaunchAgents`.
Deploying the AI profile does not register PRs or start a scheduler on a new
machine; use the review skill to set up monitoring after configuring its local
runtime. Existing macOS LaunchAgents continue using the deployed runtime path.
The AI deploy hook does not load or restart them.

When adopting an existing installation, back up regular files/directories
reported as conflicts and then deploy; do not force-replace monitor state.
The runtime is linked as one file so neighboring local data stays intact.
Run its tests with `python3 -B -m unittest discover -s scripts/arcanum-pr-poller`.

Before migrating an existing installation, inspect Dotter's dry run and the
existing links. The systemd timer in `sysd/` is a separate privileged
installation.

The machine profiles also deploy the vendored Zsh plugins from
`home/.config/zsh-plugins/`. Their pinned upstream revisions and licenses are
recorded there. Until that link is deployed, `.zshrc` can use the previous
`~/.zsh` copies. Syntax highlighting loads last, after other Zsh widgets and
local overrides.

## tmux

The `mac`, `linux-desktop`, and `linux-vm` profiles all link `home/.config/tmux`
to `~/.config/tmux`. This requires tmux 3.2+ and `/bin/zsh` and uses the same
settings on every system:

- `Ctrl+A` prefix; press it twice to send a literal `Ctrl+A` to the application.
- `/bin/zsh` for new shells, mouse support, window/pane numbering from 1,
  automatic window renumbering, and 50,000 lines of history for new panes.
- Prefix then `h/j/k/l` to select panes; `%` or `|` split side by side, and
  `"` or `-` split top and bottom, all in the active pane's current directory.
- Prefix then `r` to reload `~/.config/tmux/tmux.conf`.
- `screen-256color`, the truecolor override, and a 10 ms Escape delay.

Drag with the mouse to select text. Releasing the button freezes the selection
and leaves copy mode open. Double-click selects a word, triple-click selects a
line; neither copies nor closes the selection automatically.

| Copy-mode key | Action |
| --- | --- |
| `y` | Copy and keep the selection visible |
| `Enter` | Copy and exit copy mode |
| `Esc` or `q` | Exit without copying |
| `v` / `V` | Begin a selection / select a whole line |
| `Ctrl+V` | Toggle rectangular selection |

For keyboard selection, enter copy mode with prefix then `[`, navigate with
`h/j/k/l`, start selection with `v`, then copy. Prefix then `]` pastes the latest
tmux buffer; prefix then `=` opens the buffer chooser. `Cmd+C` belongs to the
terminal emulator; use `y` or `Enter` for a tmux selection.

The clipboard adapter uses `pbcopy` on macOS, `wl-copy` on Wayland, or
`xclip`/`xsel` with the X11 clipboard. Install the matching Linux utility separately
if needed. On headless hosts, tmux still keeps its own buffer and emits OSC 52
to the attached terminal. OSC 52 reception is enabled for applications such as
Neovim and nested tmux sessions, and a hook forwards received text to an available
local desktop clipboard.

On Mac and Linux desktop, ordinary interactive terminals automatically attach
to tmux. The VM profile leaves startup manual. Set `NO_TMUX=1` for a new terminal
to skip the local tmux, for example when you want **terminal on Mac → SSH → tmux
on VM** with a single tmux layer. See the Alacritty command below.

Copying with `y` or `Enter` in the VM's tmux requires a terminal that accepts
OSC 52 clipboard writes. The deployed Alacritty configuration explicitly enables
this with `terminal.osc52 = "OnlyCopy"`. For iTerm2, enable **Settings → General → Selection →
Applications in terminal may access clipboard**. The terminal then updates the
Mac clipboard directly over the existing SSH connection; no local tmux is
needed. See the [iTerm2 settings documentation](https://iterm2.com/documentation-preferences-general.html)
and [tmux clipboard documentation](https://github.com/tmux/tmux/wiki/Clipboard).

Terminal.app does not itself support OSC 52. To keep Terminal.app with only a
remote tmux, it needs a local clipboard adapter such as
[osc52pty](https://github.com/roy2220/osc52pty), installed separately. The existing
tmux clipboard hook also supports deliberately nested sessions: the outer tmux
on Mac receives the remote copy and passes it to `pbcopy`.

In nested tmux, the first `Ctrl+A` reaches the outer server. To send a command
to the inner server, press `Ctrl+A`, `Ctrl+A`, then the command key.

After deploying the machine profile, run
`tmux source-file ~/.config/tmux/tmux.conf` on each existing server; future servers
load it automatically. This does not replace shells already running in panes or
increase the history retained by existing panes on older tmux versions. The VM
profile leaves tmux startup manual.

### Alacritty on Mac

The `mac` profile already deploys `~/.config/alacritty/alacritty.toml`. Install
Alacritty separately using the DMG from the
[official releases](https://github.com/alacritty/alacritty/releases/latest),
moving `Alacritty.app` to `~/Applications` or `/Applications`, then apply the
`mac` profile.

A normal Alacritty window starts the local tmux automatically. To open an SSH
window without a local tmux, run this on Mac and then connect to the VM from it:

```sh
open -na Alacritty --args -o 'env.NO_TMUX="1"'
```

The `mac` profile also builds a small local URL handler in `~/Applications`
and registers it for `ssh://` links. It opens each link as `ssh` in a new
Alacritty window, without the local tmux auto-attach. To refresh just this
handler after editing it, run:

```sh
bash scripts/ssh-alacritty-url-handler/install.sh
```

In the VM's tmux, select text and press `y` or `Enter`; Alacritty writes the text
to the Mac clipboard through OSC 52. For visible text, holding `Shift` while
selecting bypasses application mouse reporting, so `Cmd+C` copies Alacritty's
own selection. This also works while tmux mouse support is enabled. See the
[Alacritty configuration reference](https://alacritty.org/config-alacritty.html).

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
access for the first mount. The helper also searches `~/arcadia` for `ya`, so
it works with the minimal PATH provided by systemd or launchd.

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

## Arc compilation databases

The `mac` and `linux-vm` profiles include the `arc_compdb` package, which links
the Bash script `arc-compdb` into `~/.local/bin`. Both profiles already add that
directory to Zsh's `PATH`. It requires Bash 3.2+, Python 3 and a mounted Arc
checkout with `ya`; it works independently of any editor or VS Code workspace.

Run it from a service/library directory containing `ya.make`, or pass that
directory explicitly:

```sh
arc-compdb
arc-compdb ~/arcadia/taxi/uservices/services/grocery-api --jobs 4
arc-compdb . --ya-arg=-DNAME=value --dry-run
```

It runs `ya make` to generate sources and headers, then `ya dump compile-commands`
to write `compile_commands.json` into the selected directory. This also works
for Neovim. `--dry-run` only prints commands. `--jobs N` overrides the default
of half the CPUs, with a minimum of one and a maximum of six workers. Repeat
`--ya-arg=FLAG` to pass additional arguments to both `ya` commands.

Generated headers and sources stay under
`~/.cache/arc-vscode/<checkout>-<hash>/targets/<service-path>/build`
(or `$XDG_CACHE_HOME/arc-vscode/...`). The existing cache name is retained so
previously generated databases keep working. Both commands use the same build
root, and the database retains the compiler's absolute path. There are no
generated-source links in the checkout. Concurrent generation for the same
target is rejected. A valid new database replaces the old one atomically;
the previous copy is saved beside the build directory as
`previous_compile_commands.json`. Build, dump or validation errors leave the
existing database in place.

Neovim selects an existing database automatically, including for dependency
headers outside the service directory. It first checks the file's ancestors
(and their `build/` directories), then the current working directory, then the
single database found among loaded C/C++ buffers. The latter two fallbacks stay
within the same Arc checkout or Git repository. The selected database is passed
explicitly to clangd, and its directory is used to share one LSP client between
the service and its dependency headers. No database is generated by Neovim.

Start Neovim from the service directory, or open a service source file before
navigating to its dependencies. If several projects are open and a shared header
has no database of its own, use `:cd /path/to/service` and `:LspRestart` to select
its context. Files with their own database keep using it. After updating this
Neovim configuration, restart Neovim once to load the new callbacks.

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

Open `~/workspaces/first.code-workspace` with **File → Open Workspace from File**
on the machine containing that checkout. For the main checkout,
`arc-vscode init ~/arcadia ...` creates `~/workspaces/main.code-workspace`.
Other worktrees use their directory name, such as `second.code-workspace`.
An existing workspace is never overwritten. Use `--output` to choose a different
location; existing workspace files and task definitions keep working.

To create only the workspace without creating or updating any compilation
database, add `--no-refresh`:

```sh
arc-vscode init ~/arcadia-wt/first \
  taxi/uservices/services/grocery-api --no-refresh
```

Workspace creation never builds a service. Without `--no-refresh`, it also
combines any databases already present in the selected folders.

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

VS Code tasks call `arc-vscode prepare`, which delegates generation to the same
`arc-compdb` script and then refreshes the workspace's combined database. Existing
workspaces and task definitions continue to work. The generator is located beside
the helper in the repository, so the optional `vscode-arc` profile can also run
these tasks without deploying a machine profile.

To generate and refresh the workspace from a terminal:

```sh
arc-vscode prepare ~/arcadia-wt/first/taxi/uservices/services/grocery-goals \
  --workspace ~/workspaces/first.code-workspace
```

`prepare` accepts the same `--jobs`, `--ya-arg` and `--dry-run` options.
After running standalone `arc-compdb`, use **Arcadia: Refresh workspace databases**
or `arc-vscode refresh ~/workspaces/first.code-workspace` if you also
want to update VS Code's combined database.

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
