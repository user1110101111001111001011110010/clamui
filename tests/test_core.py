import os
from pathlib import Path
import tempfile
import time
import unittest

from clamui.core import Config, Scanner, Store, safe_text
from clamui.tui import TerminalUI


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "app")
        self.store.acquire()
        self.target = self.root / "file with spaces.txt"
        self.target.write_text("test")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_private_profile_survives_restart_and_has_no_official_fallback(self):
        config = Config(mode="private_only", primary="https://mirror.example.org/clamav",
                        backup="https://backup.example.org/clamav")
        self.store.save(config)
        saved = self.store.load()
        self.assertEqual(saved, config)
        self.assertNotIn("DatabaseMirror", saved.preview())
        self.assertNotIn("DNSDatabaseInfo", saved.preview())
        self.assertEqual(saved.preview().count("PrivateMirror "), 2)
        self.assertEqual(self.store.config_path.stat().st_mode & 0o777, 0o600)

    def test_invalid_profiles_never_replace_saved_settings(self):
        self.store.save(Config())
        before = self.store.config_path.read_bytes()
        for url in ("", "https://database.clamav.net", "https://CURRENT.CVD.CLAMAV.NET.",
                    "https://host/\nOnUpdateExecute evil", "file:///etc/passwd",
                    "https://user:pass@host", "https://host:99999", "https://host/?x=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.store.save(Config(mode="private_only", primary=url))
            self.assertEqual(self.store.config_path.read_bytes(), before)

    def test_lock_and_crash_recovery(self):
        job = self.store.begin(str(self.target))
        second = Store(self.root / "app")
        with self.assertRaises(RuntimeError):
            second.acquire()
        self.assertEqual(self.store.history()[0]["status"], "running")
        self.store.close()
        second.acquire()
        self.assertEqual(second.history()[0]["status"], "interrupted")
        second.close()

    def engine(self, body):
        path = self.root / "fake-clamscan"
        path.write_text("#!/usr/bin/python3\n" + body)
        path.chmod(0o700)
        return str(path)

    def wait(self, scanner):
        deadline = time.monotonic() + 6
        while scanner.busy and time.monotonic() < deadline:
            time.sleep(.02)
        if scanner.busy:
            scanner.cancel()
            scanner.join()
            self.fail("scanner did not finish within deadline")

    def test_exit_codes_output_safety_and_literal_path(self):
        for code, status in ((0, "clean"), (1, "found"), (2, "failed")):
            command = self.engine(f"import sys\nfrom pathlib import Path\nmanifest = next(x.split('=',1)[1] for x in sys.argv if x.startswith('--file-list='))\nassert Path(manifest).read_text().splitlines() == [{str(self.target)!r}]\nprint('\\x1b]0;bad title\\x07')\nprint('result')\nprint({str(self.target)!r} + ': ' + {('OK' if code == 0 else 'Test FOUND' if code == 1 else 'Test ERROR')!r})\nsys.exit({code})\n")
            scanner = Scanner(self.store, command)
            scanner.start(str(self.target), True)
            self.wait(scanner)
            result = self.store.history()[0]
            self.assertEqual(result["status"], status)
            self.assertEqual(result["code"], code)
            self.assertNotIn("\x1b", result["output"])
            self.assertIn("result", result["output"])

    def test_cancellation_escalates_and_saves_partial_result(self):
        command = self.engine("import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nprint('ready', flush=True)\ntime.sleep(60)\n")
        scanner = Scanner(self.store, command)
        scanner.start(str(self.target), False)
        deadline = time.monotonic() + 2
        while "ready" not in scanner.snapshot()[1] and time.monotonic() < deadline:
            time.sleep(.02)
        scanner.cancel()
        self.wait(scanner)
        self.assertEqual(self.store.history()[0]["status"], "cancelled")
        self.assertIn("ready", self.store.history()[0]["output"])

    def test_rejects_symlink_and_missing_path(self):
        link = self.root / "link"
        link.symlink_to(self.target)
        for path in (link, self.root / "missing"):
            with self.assertRaises(ValueError):
                Scanner(self.store).start(str(path), True)
        self.assertEqual(self.store.history(), [])

    def test_terminal_control_characters_are_escaped(self):
        self.assertEqual(safe_text("x\n\x1b[31m\u202ey"), "x\\u000a\\u001b[31m\\u202ey")

    def test_preview_back_keeps_unsaved_draft(self):
        ui = TerminalUI(None, self.store, Config())
        ui.go("mirrors")
        ui.draft.mode = "private_only"
        ui.draft.primary = "https://mirror.example.org"
        ui.go("preview")
        self.assertIn("PrivateMirror https://mirror.example.org", "\n".join(ui.document()))
        ui.go("mirrors")
        self.assertEqual(ui.draft.mode, "private_only")
        self.assertFalse(self.store.config_path.exists())
        ui.activate("save_mirrors")
        self.assertEqual(self.store.load().mode, "private_only")

    def test_bad_config_is_not_silently_replaced(self):
        self.store.config_path.write_text('schema_version = 999\n')
        with self.assertRaises(ValueError):
            self.store.load()
        self.assertIn("999", self.store.config_path.read_text())


if __name__ == "__main__":
    unittest.main()
