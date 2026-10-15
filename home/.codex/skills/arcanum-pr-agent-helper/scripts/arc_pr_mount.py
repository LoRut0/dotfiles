#!/usr/bin/python3
"""Create and remove isolated Arc mounts for inspecting one Arcanum PR."""

import argparse
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import subprocess
import sys


ARC = "/usr/local/libexec/codex-arc-pr-bin"
USER_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
OBJECT_STORE = USER_HOME / "projects/arc_obj_store"
STATE_DIR = USER_HOME / ".local/state/codex-arcanum-pr-mounts"
MOUNT_BASE = Path("/private/tmp")
PR_RE = re.compile(r"[1-9][0-9]{7}\Z")
TOKEN_RE = re.compile(r"[0-9a-f]{16}\Z")
SAFE_ENV = {
    "HOME": str(USER_HOME),
    "PATH": "/usr/bin:/bin:/usr/local/bin",
    "USER": os.environ.get("USER", ""),
}
if os.environ.get("SSH_AUTH_SOCK"):
    SAFE_ENV["SSH_AUTH_SOCK"] = os.environ["SSH_AUTH_SOCK"]


def fail(message):
    raise RuntimeError(message)


def run_arc(*args, cwd=None):
    result = subprocess.run(
        [ARC, *args], cwd=cwd or str(MOUNT_BASE), env=SAFE_ENV,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        fail("arc {} failed: {}".format(args[0], result.stderr.strip() or result.stdout.strip()))
    return result.stdout


def mount_path(pr, token):
    return MOUNT_BASE / "codex-arcanum-pr-{}-{}".format(pr, token)


def receipt_path(pr, token):
    return STATE_DIR / "{}-{}.json".format(pr, token)


def mounted_entry(path):
    entries = json.loads(run_arc("mount", "--list", "--json"))
    matches = [entry for entry in entries if entry.get("mount") == str(path)]
    if len(matches) != 1:
        fail("expected exactly one Arc mount at {}".format(path))
    entry = matches[0]
    if entry.get("status") != "mounted" or entry.get("tenant") != "arcadia":
        fail("Arc mount is not an active Arcadia mount: {}".format(path))
    if entry.get("object-store") != str(OBJECT_STORE):
        fail("Arc mount uses an unexpected object store: {}".format(path))
    if not isinstance(entry.get("pid"), int) or entry["pid"] <= 0:
        fail("Arc mount has no valid process ID: {}".format(path))
    return entry


def mount(pr):
    if not OBJECT_STORE.is_dir():
        fail("shared Arc object store is missing: {}".format(OBJECT_STORE))
    token = secrets.token_hex(8)
    path = mount_path(pr, token)
    if os.path.lexists(str(path)):
        fail("mount path already exists: {}".format(path))
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE_DIR.is_symlink() or not STATE_DIR.is_dir():
        fail("state directory is not a regular directory")
    run_arc("mount", str(path), "--object-store", str(OBJECT_STORE))
    entry = mounted_entry(path)
    receipt = {
        "pr": pr,
        "token": token,
        "mount": str(path),
        "store": entry.get("store"),
        "pid": entry["pid"],
        "object_store": str(OBJECT_STORE),
    }
    output = receipt_path(pr, token)
    descriptor = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file:
        json.dump(receipt, file)
        file.write("\n")
    print(json.dumps(receipt, ensure_ascii=False))


def unmount(pr, token):
    path = mount_path(pr, token)
    receipt_file = receipt_path(pr, token)
    if receipt_file.is_symlink() or not receipt_file.is_file():
        fail("mount receipt is missing or invalid: {}".format(receipt_file))
    receipt = json.loads(receipt_file.read_text())
    if (receipt.get("pr"), receipt.get("token"), receipt.get("mount"),
            receipt.get("object_store")) != (pr, token, str(path), str(OBJECT_STORE)):
        fail("mount receipt does not match the requested PR and path")
    if path.is_symlink() or not path.is_dir():
        fail("mount path is missing or is a symlink: {}".format(path))
    entry = mounted_entry(path)
    if not receipt.get("store") or receipt["store"] != entry.get("store"):
        fail("Arc store differs from the mount receipt")
    if receipt.get("pid") != entry["pid"]:
        fail("Arc mount process differs from the mount receipt")
    if run_arc("status", "--short", cwd=str(path)).strip():
        fail("mount has working-tree changes; preserve them before removal")
    info = json.loads(run_arc("info", "--json", cwd=str(path)))
    if not info.get("hash") or info.get("hash") != info.get("remote_head"):
        fail("mount has commits not confirmed at its remote head")
    run_arc("unmount", "--force", "--forget", str(path))
    receipt_file.unlink()
    print(json.dumps({"pr": pr, "unmounted": str(path)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("mount")
    create.add_argument("pr")
    remove = subparsers.add_parser("unmount")
    remove.add_argument("pr")
    remove.add_argument("token")
    args = parser.parse_args()
    if not PR_RE.fullmatch(args.pr):
        parser.error("PR must be an eight-digit Arcanum ID")
    if args.command == "unmount" and not TOKEN_RE.fullmatch(args.token):
        parser.error("token must be the 16-character value returned by mount")
    try:
        if args.command == "mount":
            mount(args.pr)
        else:
            unmount(args.pr, args.token)
    except (OSError, ValueError, RuntimeError) as error:
        print("arc-pr-mount: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
