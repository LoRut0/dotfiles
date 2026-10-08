"""Run with: python3 -m unittest discover -s tests -v"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


HELPER = Path(__file__).resolve().parents[1] / "home/.local/bin/arc-vscode"
COMPDB = HELPER.with_name("arc-compdb")
FAKE_YA = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
args = sys.argv[1:]
with open(os.environ["YA_CALLS"], "a") as stream:
    stream.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")
if os.environ.get("YA_FAILURE") == args[0]:
    sys.exit(9)
if args[0] == "make" and os.environ.get("YA_WAIT"):
    for _ in range(1000):
        if pathlib.Path(os.environ["YA_WAIT"]).exists():
            break
        time.sleep(0.01)
    else:
        sys.exit("Timed out waiting for test")
if args[0] == "dump":
    if os.environ.get("YA_FAILURE") == "invalid-json":
        print("incomplete database")
    elif os.environ.get("YA_FAILURE") == "empty-json":
        print("[]")
    elif os.environ.get("YA_FAILURE") == "invalid-entry":
        print('[{"directory":"relative","file":"main.cpp","command":"clang++ main.cpp"}]')
    else:
        build = next(a.split("=", 1)[1] for a in args if a.startswith("--cmd-build-root="))
        print(json.dumps([{"directory": os.getcwd(), "file": "src/main.cpp",
                           "arguments": ["/tools/clang++", "-I" + build, "src/main.cpp"]}]))
'''


class ArcVscodeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.make_checkout(self.base / "checkout with spaces")
        self.a = self.make_folder(self.root / "services/first")
        self.b = self.make_folder(self.root / "services/second")
        self.workspace = self.base / "editor.code-workspace"
        self.env = dict(os.environ, XDG_CACHE_HOME=str(self.base / "cache"),
                        XDG_DATA_HOME=str(self.base / "data"), YA_CALLS=str(self.base / "calls"))

    def make_checkout(self, path):
        (path / ".arc").mkdir(parents=True)
        (path / ".arc/HEAD").touch()
        (path / "ya").write_text(FAKE_YA)
        (path / "ya").chmod(0o755)
        return path

    def make_folder(self, path):
        path.mkdir(parents=True)
        (path / "ya.make").touch()
        return path

    def run_helper(self, *args, failure=None, ok=True, cwd=None, script=HELPER):
        env = self.env.copy()
        if failure:
            env["YA_FAILURE"] = failure
        result = subprocess.run([str(script), *map(str, args)], env=env,
                                cwd=cwd or self.root, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def init(self, *folders):
        self.run_helper("init", self.root, *folders, "--output", self.workspace,
                        "--clangd", "/usr/bin/true")

    def combined_path(self):
        return next((self.base / "cache").glob("arc-vscode/*/compdb/compile_commands.json"))

    def entry(self, file, flag):
        return {"directory": str(self.root), "file": str(file),
                "arguments": ["clang++", flag, str(file)]}

    def write_database(self, folder, entries):
        (folder / "compile_commands.json").write_text(json.dumps(entries))

    def test_prepare_uses_same_build_root_and_preserves_previous_database(self):
        self.write_database(self.a, [self.entry(self.a / "old.cpp", "-DOLD")])
        self.init(self.a)
        previous = (self.a / "compile_commands.json").read_bytes()
        self.run_helper("prepare", "services/first", "--workspace", self.workspace)
        calls = [json.loads(line) for line in (self.base / "calls").read_text().splitlines()]
        self.assertEqual([c["args"][0] for c in calls], ["make", "dump"])
        self.assertTrue(all(c["cwd"] == str(self.a) for c in calls))
        build = next(a.split("=", 1)[1] for a in calls[0]["args"] if a.startswith("--output="))
        self.assertIn("--cmd-build-root=" + build, calls[1]["args"])
        self.assertIn("--dont-strip-compiler-path", calls[1]["args"])
        self.assertIn("--no-src-links", calls[0]["args"])
        backup = next((self.base / "cache").rglob("previous_compile_commands.json"))
        self.assertEqual(backup.read_bytes(), previous)
        self.assertEqual(json.loads(self.combined_path().read_text()),
                         json.loads((self.a / "compile_commands.json").read_text()))

    def test_failed_generation_preserves_both_databases(self):
        self.write_database(self.a, [self.entry(self.a / "old.cpp", "-DOLD")])
        self.init(self.a)
        previous = (self.a / "compile_commands.json").read_bytes()
        combined = self.combined_path().read_bytes()
        for failure in ("make", "dump", "invalid-json", "empty-json", "invalid-entry"):
            with self.subTest(failure=failure):
                self.run_helper("prepare", self.a, "--workspace", self.workspace,
                                failure=failure, ok=False)
                self.assertEqual((self.a / "compile_commands.json").read_bytes(), previous)
                self.assertEqual(self.combined_path().read_bytes(), combined)
                self.assertEqual(list(self.a.glob(".compile_commands.*")), [])

    def test_standalone_defaults_to_current_folder_and_forwards_flags(self):
        self.run_helper("--jobs", "3", "--ya-arg=-DNAME=with spaces",
                        "--ya-arg=-DOTHER=yes", cwd=self.a, script=COMPDB)
        calls = [json.loads(line) for line in (self.base / "calls").read_text().splitlines()]
        self.assertEqual([c["args"][0] for c in calls], ["make", "dump"])
        for call in calls:
            self.assertEqual(call["cwd"], str(self.a))
            self.assertEqual(call["args"][call["args"].index("-j") + 1], "3")
            self.assertIn("-DNAME=with spaces", call["args"])
            self.assertIn("-DOTHER=yes", call["args"])
        self.assertTrue((self.a / "compile_commands.json").is_file())
        self.assertFalse(self.workspace.exists())

    def test_dry_run_does_not_build_or_change_databases(self):
        self.init(self.a)
        previous = self.combined_path().read_bytes()
        for script, args in ((COMPDB, [self.a]),
                             (HELPER, ["prepare", self.a, "--workspace", self.workspace])):
            result = self.run_helper(*args, "--dry-run", script=script)
            self.assertIn("--cmd-build-root=", result.stdout)
            self.assertIn("--add-protobuf-result", result.stdout)
            self.assertIn("--add-flatbuf-result", result.stdout)
        self.assertFalse((self.base / "calls").exists())
        self.assertFalse((self.a / "compile_commands.json").exists())
        self.assertFalse(list((self.base / "cache").rglob("targets")))
        self.assertEqual(self.combined_path().read_bytes(), previous)

    def test_init_without_refresh_preserves_databases_and_does_not_build(self):
        self.write_database(self.a, [self.entry(self.a / "old.cpp", "-DOLD")])
        self.init(self.a)
        combined = self.combined_path()
        previous = combined.read_bytes()
        source = (self.a / "compile_commands.json").read_bytes()
        other_workspace = self.base / "no-refresh.code-workspace"
        self.run_helper("init", self.root, self.a, self.b, "--output", other_workspace,
                        "--clangd", "/usr/bin/true", "--no-refresh")
        config = json.loads(other_workspace.read_text())
        self.assertEqual(config["settings"]["yandex.arcRoot"], str(self.root))
        self.assertIn("no-refresh", config["settings"]["window.title"])
        self.assertEqual(combined.read_bytes(), previous)
        self.assertEqual((self.a / "compile_commands.json").read_bytes(), source)
        self.assertFalse((self.b / "compile_commands.json").exists())
        self.assertFalse((self.base / "calls").exists())
        fresh_cache = self.base / "unused-cache"
        self.env["XDG_CACHE_HOME"] = str(fresh_cache)
        self.run_helper("init", self.root, self.a, "--output", self.base / "fresh.code-workspace",
                        "--clangd", "/usr/bin/true", "--no-refresh")
        self.assertFalse(fresh_cache.exists())

    def test_standalone_rejects_invalid_targets_and_options_before_build(self):
        no_make = self.a / "src"
        no_make.mkdir()
        for args in ([self.root], [self.base], [no_make], [self.a / "missing"],
                     [self.a, self.b], [self.a, "--unknown"], [self.a, "--jobs"],
                     [self.a, "--jobs=0"], [self.a, "--jobs", "no"],
                     [self.a, "--jobs", ""], [self.a, "--ya-arg"]):
            with self.subTest(args=args):
                self.run_helper(*args, script=COMPDB, ok=False)
        self.assertFalse((self.base / "calls").exists())

    def test_standalone_separates_worktree_caches(self):
        other = self.make_checkout(self.base / "other" / self.root.name)
        foreign = self.make_folder(other / "services/first")
        self.run_helper(self.a, script=COMPDB)
        self.run_helper(foreign, script=COMPDB)
        first = json.loads((self.a / "compile_commands.json").read_text())
        second = json.loads((foreign / "compile_commands.json").read_text())
        self.assertNotEqual(first[0]["arguments"][1], second[0]["arguments"][1])

    def test_generation_lock_covers_build_and_is_released_on_exit(self):
        release = self.base / "release-build"
        env = dict(self.env, YA_WAIT=str(release))
        with subprocess.Popen([str(COMPDB), str(self.a)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            try:
                deadline = time.monotonic() + 5
                while not (self.base / "calls").exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue((self.base / "calls").exists(), "Build did not start")
                result = self.run_helper(self.a, script=COMPDB, ok=False)
                self.assertIn("Another task", result.stderr)
                self.assertEqual(len((self.base / "calls").read_text().splitlines()), 1)
            finally:
                release.touch()
                stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.run_helper(self.a, script=COMPDB)

    def test_prepare_current_directory_from_terminal(self):
        self.init(self.a)
        self.run_helper("prepare", ".", "--workspace", self.workspace, cwd=self.a)
        self.assertTrue((self.a / "compile_commands.json").is_file())

    def test_merge_prefers_owning_folder_and_removes_unselected_entries(self):
        shared = self.root / "library/common.cpp"
        self.write_database(self.a, [self.entry(self.a / "main.cpp", "-DFIRST"),
                                    self.entry(shared, "-DFIRST")])
        self.write_database(self.b, [self.entry(self.a / "main.cpp", "-DSECOND"),
                                    self.entry(shared, "-DSECOND"),
                                    self.entry(self.b / "main.cpp", "-DSECOND")])
        os.utime(self.a / "compile_commands.json", (2000000000, 2000000000))
        self.init(self.a, self.b)
        records = {r["file"]: r for r in json.loads(self.combined_path().read_text())}
        self.assertEqual(len(records), 3)
        self.assertIn("-DFIRST", records[str(self.a / "main.cpp")]["arguments"])
        self.assertIn("-DFIRST", records[str(shared)]["arguments"])
        config = json.loads(self.workspace.read_text())
        config["folders"] = [{"path": str(self.a)}]
        config["settings"]["editor.fontSize"] = 17
        self.workspace.write_text(json.dumps(config))
        before = self.workspace.read_bytes()
        self.run_helper("refresh", self.workspace)
        self.assertEqual(self.workspace.read_bytes(), before)
        records = json.loads(self.combined_path().read_text())
        self.assertEqual(len(records), 2)
        self.assertTrue(all("-DFIRST" in r["arguments"] for r in records))

    def test_rejects_wrong_checkout_unselected_folder_and_root(self):
        self.init(self.a)
        other = self.make_checkout(self.base / "other")
        foreign = self.make_folder(other / "service")
        for target in (self.root, self.b, foreign):
            with self.subTest(target=target):
                self.run_helper("prepare", target, "--workspace", self.workspace, ok=False)
        self.assertFalse((self.base / "calls").exists())
        original = self.workspace.read_bytes()
        self.run_helper("init", self.root, self.b, "--output", self.workspace, ok=False)
        self.assertEqual(self.workspace.read_bytes(), original)

    def test_reads_vscode_comments_relative_folders_and_trailing_commas(self):
        self.init(self.a)
        config = json.loads(self.workspace.read_text())
        config["folders"] = [{"path": os.path.relpath(self.a, self.workspace.parent)}]
        config["settings"]["test.url"] = "https://example.invalid/a/*b*/"
        self.workspace.write_text("// a VS Code comment\n" + json.dumps(config)[:-1] + ",\n}")
        self.run_helper("refresh", self.workspace)

    def test_malformed_database_does_not_replace_combined_database(self):
        self.write_database(self.a, [self.entry(self.a / "main.cpp", "-DFIRST")])
        self.init(self.a)
        combined = self.combined_path().read_bytes()
        (self.a / "compile_commands.json").write_text('[{"directory":"relative"}]')
        self.run_helper("refresh", self.workspace, ok=False)
        self.assertEqual(self.combined_path().read_bytes(), combined)


if __name__ == "__main__":
    unittest.main()
