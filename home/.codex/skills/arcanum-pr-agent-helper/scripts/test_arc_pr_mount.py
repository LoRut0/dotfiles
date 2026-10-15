"""Offline safety checks for the temporary PR mount helper."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import arc_pr_mount as helper


class ArcPrMountTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.patchers = [
            mock.patch.object(helper, "MOUNT_BASE", self.base / "mounts"),
            mock.patch.object(helper, "STATE_DIR", self.base / "receipts"),
            mock.patch.object(helper, "OBJECT_STORE", self.base / "objects"),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        helper.MOUNT_BASE.mkdir()
        helper.OBJECT_STORE.mkdir()
        self.pr = "16455286"
        self.token = "0123456789abcdef"
        self.path = helper.mount_path(self.pr, self.token)
        self.store = str(self.base / "store")

    def entry(self):
        return {
            "mount": str(self.path), "status": "mounted", "tenant": "arcadia",
            "object-store": str(helper.OBJECT_STORE), "store": self.store, "pid": 12345,
        }

    def receipt(self):
        self.path.mkdir()
        helper.STATE_DIR.mkdir()
        data = {
            "pr": self.pr, "token": self.token, "mount": str(self.path),
            "store": self.store, "object_store": str(helper.OBJECT_STORE),
            "pid": 12345,
        }
        helper.receipt_path(self.pr, self.token).write_text(json.dumps(data))

    def test_mount_uses_generated_path_and_fixed_object_store(self):
        with mock.patch.object(helper.secrets, "token_hex", return_value=self.token), \
                mock.patch.object(helper, "run_arc", side_effect=["", json.dumps([self.entry()])]) as arc:
            helper.mount(self.pr)
        arc.assert_any_call("mount", str(self.path), "--object-store", str(helper.OBJECT_STORE))
        self.assertEqual(json.loads(helper.receipt_path(self.pr, self.token).read_text())["mount"], str(self.path))

    def test_unmount_refuses_working_changes(self):
        self.receipt()
        with mock.patch.object(helper, "run_arc", side_effect=[json.dumps([self.entry()]), " M changed.cpp"]) as arc:
            with self.assertRaisesRegex(RuntimeError, "working-tree changes"):
                helper.unmount(self.pr, self.token)
        self.assertEqual(arc.call_count, 2)
        self.assertTrue(helper.receipt_path(self.pr, self.token).exists())

    def test_unmount_refuses_unpublished_commit(self):
        self.receipt()
        info = {"hash": "a" * 40, "remote_head": "b" * 40}
        with mock.patch.object(helper, "run_arc", side_effect=[json.dumps([self.entry()]), "", json.dumps(info)]) as arc:
            with self.assertRaisesRegex(RuntimeError, "remote head"):
                helper.unmount(self.pr, self.token)
        self.assertEqual(arc.call_count, 3)
        self.assertTrue(helper.receipt_path(self.pr, self.token).exists())

    def test_unmount_checks_store_identity(self):
        self.receipt()
        entry = self.entry()
        entry["store"] = str(self.base / "other-store")
        with mock.patch.object(helper, "run_arc", return_value=json.dumps([entry])) as arc:
            with self.assertRaisesRegex(RuntimeError, "store differs"):
                helper.unmount(self.pr, self.token)
        self.assertEqual(arc.call_count, 1)

    def test_unmount_checks_mount_process_identity(self):
        self.receipt()
        entry = self.entry()
        entry["pid"] = 54321
        with mock.patch.object(helper, "run_arc", return_value=json.dumps([entry])) as arc:
            with self.assertRaisesRegex(RuntimeError, "process differs"):
                helper.unmount(self.pr, self.token)
        self.assertEqual(arc.call_count, 1)


if __name__ == "__main__":
    unittest.main()
