---
name: arc-pr-view
description: Create a disposable local Arc branch that exposes all committed changes of a PR as unstaged working-tree changes for IDE gutter review, navigation, and Go To Definition. Use when a user wants to inspect a whole Arcadia PR in the normal editor rather than only in a diff viewer.
---

# Arc PR View

Use Arc only. The outcome is a local, never-pushed view branch whose `HEAD` is
the PR merge base while its working tree retains the PR result. Modified lines
then appear in the editor gutter, and the files remain ordinary local files for
LSP navigation.

## Enter view mode

1. Inspect `arc info --json`, `arc status`, `arc diff`, and
   `arc diff --cached`. Record the original local branch and its full HEAD hash.
2. Stop and ask before proceeding if there are tracked staged or unstaged
   changes. Existing unrelated untracked files may remain, but report them and
   do not delete or stage them.
3. Determine the actual PR target branch. Do not assume `trunk` for a stacked
   PR. Update the target ref only when that is within the user's request.
4. Compute the full merge-base hash with
   `arc merge-base <target-branch> <original-head>`.
5. Choose an unprefixed local name such as `<original-branch>-pr-view`. If it
   already exists, do not overwrite or delete it; choose a distinct name or ask.
6. Create the branch at the saved PR head:

   ```bash
   arc checkout -b <view-branch> <original-head>
   ```

7. Convert the PR snapshot into working-tree changes:

   ```bash
   arc reset --mixed <full-merge-base-hash>
   ```

   This must be `--mixed`, never `--hard`: tracked file contents remain at the
   PR result, modified files become unstaged, and files added by the PR become
   untracked.
8. Verify that `HEAD` equals the merge base, the cached diff is empty, and the
   expected PR files appear through `arc diff` plus `arc status`. New PR files
   do not appear in ordinary `arc diff`; verify their `??` entries separately.
9. Tell the user the active view branch, original branch, saved PR head, and the
   command that returns to the original branch. Explicitly state that the view
   branch must not be committed or pushed.

Do not run codegen merely to enter view mode. Existing generated files and the
compilation database remain usable because the working files retain the PR
contents.

## Working in view mode

Treat the branch as read-only. Gutter decorations compare the PR result with
the merge base, while Go To Definition and other LSP operations continue to use
the real files.

If the user wants to edit the implementation, recommend returning to the
original branch first. Otherwise new edits are visually mixed with the PR
changes and are difficult to distinguish.

Never commit, push, publish, or create a PR from the view branch.

## Leave view mode

First try the non-destructive checkout of the recorded original branch:

```bash
arc checkout <original-branch>
```

If Arc refuses because files added by the PR are now untracked, stop. Inspect
the working tree and determine whether the user edited anything while in view
mode. Do not delete files or use a hard reset automatically.

When the view is unchanged and the user explicitly authorizes discarding the
disposable view state, restore it to the recorded PR head, then switch back and
delete only the local view branch:

```bash
arc reset --hard <recorded-original-head>
arc checkout <original-branch>
arc branch -d <view-branch>
```

Before `--hard`, warn that it discards every staged and unstaged change in the
view branch. If the user edited files, preserve or transfer those edits instead
of running the reset; ask how they want to proceed.
