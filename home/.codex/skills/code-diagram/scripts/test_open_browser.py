"""Launcher checks without starting a browser or building/testing any service."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import open_browser


class BrowserLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="drawio-open-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "Схема ' & заказ.drawio"
        self.xml = '<mxfile><diagram id="overview"><mxGraphModel><root/></mxGraphModel></diagram>' \
            '<diagram id="compressed">compressed-page-data</diagram></mxfile>'
        self.source.write_text(self.xml, encoding="utf-8")
        self.cache = self.directory / "cache"

    def payload(self, html):
        return json.loads(re.search(r'<script id="diagram-data" type="application/json">(.*?)</script>', html, re.S)[1])

    def test_all_pages_preserved_and_regeneration_creates_a_new_snapshot(self):
        path = open_browser.prepare_launcher(self.source, self.cache)
        self.assertEqual(self.payload(path.read_text()), {"title": self.source.name, "xml": self.xml})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(open_browser.prepare_launcher(self.source, self.cache), path)
        self.source.write_text(self.xml.replace('id="overview"', 'id="new"'), encoding="utf-8")
        updated = open_browser.prepare_launcher(self.source, self.cache)
        self.assertNotEqual(path, updated)
        self.assertEqual(self.payload(path.read_text())["xml"], self.xml)
        self.assertNotEqual(self.payload(updated.read_text())["xml"], self.xml)

    def test_embedded_labels_cannot_break_out_of_script(self):
        xml = '<mxGraphModel><root><![CDATA[</script><script>alert("oops")</script> Кириллица &]]></root></mxGraphModel>'
        self.source.write_text(xml, encoding="utf-8")
        html = open_browser.launcher_html(self.source)
        self.assertNotIn('<script>alert', html)
        self.assertEqual(self.payload(html)["xml"], xml)

    def test_invalid_or_missing_input_does_not_make_a_launcher(self):
        for xml in ("<html/>", "<mxfile/>", "<mxfile>"):
            self.source.write_text(xml)
            with self.assertRaises((ValueError, ET.ParseError)):
                open_browser.prepare_launcher(self.source, self.cache)
        with self.assertRaises(FileNotFoundError):
            open_browser.prepare_launcher(self.directory / "missing.drawio", self.cache)
        self.assertFalse(self.cache.exists())

    def test_cli_no_open_and_os_dispatch(self):
        result = subprocess.run(
            [sys.executable, str(Path(open_browser.__file__)), str(self.source), "--no-open"],
            env={**os.environ, "XDG_CACHE_HOME": str(self.cache)}, capture_output=True, text=True, check=True,
        )
        launcher = Path(result.stdout.strip())
        self.assertTrue(launcher.is_file())
        for platform, opener in (("darwin", "open"), ("linux", "xdg-open")):
            with patch.object(open_browser.sys, "platform", platform), patch.object(open_browser.subprocess, "run") as run:
                open_browser.open_launcher(launcher)
                run.assert_called_once_with([opener, launcher.as_uri()], check=True)

    @unittest.skipUnless(shutil.which("node"), "Node is only needed to test the browser message bridge")
    def test_bridge_loads_and_saves_only_messages_from_its_editor(self):
        launcher = open_browser.prepare_launcher(self.source, self.cache)
        subprocess.run(["node", str(Path(__file__).with_suffix(".js")), str(launcher)], check=True)


if __name__ == "__main__":
    unittest.main()
