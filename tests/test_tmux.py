"""Clipboard adapter tests and copy-mode tests against an isolated tmux server."""

import base64
import fcntl
import os
from pathlib import Path
import pty
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "home/.config/tmux/tmux.conf"
CLIPBOARD = CONFIG.with_name("clipboard.sh")
TMUX = shutil.which("tmux")
FAKE_COPY = '''#!/bin/sh
printf '%s\\n' "$@" > "$TMUX_COPY_TEST_ARGS"
/bin/cat > "$TMUX_COPY_TEST_FILE"
'''


class ClipboardAdapterTest(unittest.TestCase):
    def test_native_backends_and_headless_fallback(self):
        payload = "clipboard text\nтест\n".encode()
        cases = [
            ("pbcopy", {}, []),
            ("wl-copy", {"WAYLAND_DISPLAY": "wayland-test"}, []),
            ("xclip", {"DISPLAY": ":test"}, ["-selection", "clipboard", "-in"]),
            ("xsel", {"DISPLAY": ":test"}, ["--clipboard", "--input"]),
            ("wl-copy", {}, None),  # An installed binary alone is not a desktop.
            ("xclip", {}, None),
        ]
        for name, display, expected_args in cases:
            with self.subTest(backend=name, display=display), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                binary = path / name
                binary.write_text(FAKE_COPY)
                binary.chmod(0o755)
                (path / "cat").symlink_to("/bin/cat")
                env = dict(os.environ, PATH=directory,
                           TMUX_COPY_TEST_FILE=str(path / "clipboard"),
                           TMUX_COPY_TEST_ARGS=str(path / "args"))
                env.pop("DISPLAY", None)
                env.pop("WAYLAND_DISPLAY", None)
                env.update(display)
                result = subprocess.run(["/bin/sh", str(CLIPBOARD)], input=payload,
                                        env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b"")
                if expected_args is None:
                    self.assertFalse((path / "clipboard").exists())
                else:
                    self.assertEqual((path / "clipboard").read_bytes(), payload)
                    self.assertEqual((path / "args").read_text().split(), expected_args)


@unittest.skipUnless(TMUX, "tmux is not installed")
class TmuxCopyModeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tmux-copy-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.clipboard = self.path / "clipboard"
        binary = self.path / "pbcopy"
        binary.write_text(FAKE_COPY)
        binary.chmod(0o755)
        self.env = dict(os.environ, TERM="xterm-256color",
                        PATH=str(self.path) + os.pathsep + os.environ.get("PATH", os.defpath),
                        TMUX_COPY_TEST_FILE=str(self.clipboard),
                        TMUX_COPY_TEST_ARGS=str(self.path / "args"))
        self.env.pop("TMUX", None)
        self.command = [TMUX, "-S", str(self.path / "test.sock")]
        config = self.path / "tmux.conf"
        # Exercise the actual adapter without requiring Dotter to be deployed.
        config.write_text(CONFIG.read_text().replace("$HOME/.config/tmux/clipboard.sh", str(CLIPBOARD)))
        app = shlex.join([sys.executable, "-u", "-c",
                          "import time; print('alpha beta gamma'); print('second line'); time.sleep(60)"])
        self.pane = self.run_tmux("-f", config, "new-session", "-d", "-P", "-F", "#{pane_id}",
                                  "-s", "copy-test", "-x", "80", "-y", "24", app).strip()
        self.addCleanup(self.stop_server)
        self.master, slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        self.client = subprocess.Popen(self.command + ["attach-session", "-t", "copy-test"],
                                       stdin=slave, stdout=slave, stderr=slave, env=self.env,
                                       start_new_session=True,
                                       preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
        os.close(slave)
        self.addCleanup(self.stop_client)
        os.set_blocking(self.master, False)
        self.output = b""
        self.wait_for(lambda: "alpha beta gamma" in self.run_tmux("capture-pane", "-p", "-t", self.pane)
                      and bool(self.run_tmux("list-clients", "-F", "#{client_name}").strip()))
        self.wait_for(lambda: b"?1006h" in self.output)

    def run_tmux(self, *args):
        result = subprocess.run(self.command + list(map(str, args)), env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def stop_client(self):
        if self.client.poll() is None:
            self.client.terminate()
        self.client.wait(timeout=5)

    def stop_server(self):
        subprocess.run(self.command + ["kill-server"], env=self.env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def drain(self):
        while True:
            try:
                chunk = os.read(self.master, 65536)
                if not chunk:
                    break
                self.output += chunk
            except (BlockingIOError, OSError):
                break

    def wait_for(self, predicate):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            self.drain()
            if predicate():
                return
            time.sleep(0.02)
        self.fail("Timed out waiting for tmux state; output tail: " + repr(self.output[-500:]))

    def state(self):
        return self.run_tmux("display-message", "-p", "-t", self.pane,
                             "#{pane_in_mode}:#{selection_present}:#{selection_active}").strip()

    def mouse(self, data):
        os.write(self.master, data)

    def test_mouse_release_and_y_keep_selection_enter_finishes(self):
        self.mouse(b"\x1b[<0;1;1M\x1b[<32;5;1M\x1b[<0;5;1m")
        self.wait_for(lambda: self.state() == "1:1:0")
        self.assertFalse(self.clipboard.exists())
        self.mouse(b"y")
        self.wait_for(lambda: self.clipboard.exists() and self.clipboard.read_bytes() == b"alpha")
        self.assertEqual(self.state(), "1:1:0")
        self.assertEqual(self.run_tmux("show-buffer"), "alpha")
        self.wait_for(lambda: b"]52;" in self.output and base64.b64encode(b"alpha") in self.output)
        self.mouse(b"\r")
        self.wait_for(lambda: self.state().startswith("0:"))
        self.assertEqual(self.run_tmux("show-buffer"), "alpha")

    def test_double_and_triple_click_keep_selection(self):
        click = b"\x1b[<0;7;1M\x1b[<0;7;1m"
        self.mouse(click + click)
        self.wait_for(lambda: self.state() == "1:1:0")
        # Let the old default's delayed copy-and-cancel fire if it is still bound.
        time.sleep(0.4)
        self.drain()
        self.assertEqual(self.state(), "1:1:0")
        self.assertFalse(self.clipboard.exists())
        self.mouse(b"y")
        self.wait_for(lambda: self.clipboard.exists() and self.clipboard.read_bytes() == b"beta")
        self.mouse(b"q")
        self.wait_for(lambda: self.state().startswith("0:"))
        time.sleep(0.4)
        self.mouse(click + click + click)
        self.wait_for(lambda: self.state() == "1:1:0")
        time.sleep(0.4)
        self.assertEqual(self.state(), "1:1:0")
        self.mouse(b"y")
        self.wait_for(lambda: self.clipboard.read_bytes().rstrip(b"\n") == b"alpha beta gamma")

    def test_incoming_osc52_reaches_native_clipboard_and_reload_is_stable(self):
        payload = b"copy from nested tmux\n"
        sequence = b"\x1b]52;c;" + base64.b64encode(payload) + b"\x07"
        code = "import os,time; os.write(1, %r); time.sleep(30)" % sequence
        self.run_tmux("new-window", "-t", "copy-test", shlex.join([sys.executable, "-c", code]))
        self.wait_for(lambda: self.clipboard.exists() and self.clipboard.read_bytes() == payload)
        self.assertEqual(self.run_tmux("show-buffer"), payload.decode())
        before = self.run_tmux("show-options", "-s", "terminal-features")
        hooks = self.run_tmux("show-hooks", "-g", "pane-set-clipboard")
        status = self.run_tmux("show-options", "-gv", "status-right")
        self.run_tmux("set-option", "-g", "status-right", "stale-linux-battery-command")
        self.run_tmux("source-file", self.path / "tmux.conf")
        self.assertEqual(self.run_tmux("show-options", "-s", "terminal-features"), before)
        self.assertEqual(self.run_tmux("show-hooks", "-g", "pane-set-clipboard"), hooks)
        self.assertEqual(self.run_tmux("show-options", "-gv", "status-right"), status)
        self.assertEqual(self.run_tmux("show-options", "-gv", "default-shell").strip(), "/bin/zsh")


if __name__ == "__main__":
    unittest.main()
