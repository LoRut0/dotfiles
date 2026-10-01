---
name: dotfiles
description: >-
  Work on the personal configuration repository at ~/.config/dotfiles, managed
  with Dotter. Use for changes to its configurations, packages, profiles, or
  deployment setup, and publish completed repository updates to GitHub.
---

# Dotfiles

The repository is `~/.config/dotfiles`. Read its `README.md` and the relevant files before editing. `.dotter/global.toml` maps packages to targets; `.dotter/profiles/{mac,linux-desktop,linux-vm,ai}.toml` selects packages. `home/` is shared, while `home-macos/` and `home-linux/` hold platform-specific files. Most configuration directories are linked as whole directories, so editing an installed link edits the repository source.

## Update a configuration

1. Check the current branch, upstream, `git status --short`, and relevant existing changes. Preserve unrelated work, including untracked files.
2. Edit the source in this repository and update the Dotter package/profile mapping when adding a deployed file. Keep machine-specific settings in the matching platform tree. The `ai` profile is deployed separately and has its own Dotter cache.
3. Check the changed files with the relevant parser or tool where practical. For mapping or profile changes, run `bash dotter.sh <profile> --dry-run deploy` on a compatible machine and inspect the planned links. Run the actual deploy when the task calls for applying the configuration. Be aware that `.dotter/post_deploy.sh` starts the macOS LaunchAgent or enables Linux VM services.

## Commit and push repository updates

For a completed update to this repository, create a commit and push it to GitHub unless the user asks to keep it local. A request only to inspect or explain files does not call for a commit.

- Review the final diff and status. Stage only files or hunks belonging to the current task; never include pre-existing unrelated changes. If a required file already has user edits, preserve them and stage only clearly attributable hunks. If that cannot be done reliably, leave the ambiguous file uncommitted and explain the blocker instead of publishing someone else's work.
- Use a short, specific commit message. Confirm the staged diff contains exactly the intended changes before committing.
- Push the new commit with a normal `git push` to the current branch's configured GitHub upstream. Do not force-push, change branches, or add a new remote as a workaround. If there is no unambiguous upstream, the remote has diverged, or push fails, stop and report the state; do not rewrite or discard commits automatically.
- Report the commit hash and push result. Never claim publication succeeded until the remote push succeeds.
