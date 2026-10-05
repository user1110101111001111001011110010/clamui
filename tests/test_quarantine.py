import tempfile
import unittest
from pathlib import Path

from clamui.core import Config, Store
from clamui.quarantine import Quarantine
from clamui.tui import TerminalUI


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "app")
        self.quarantine = Quarantine(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_quarantine_and_restore_preserves_content_without_overwrite(self):
        source = Path(self.temp.name) / "suspicious file.bin"
        source.write_bytes(b"test detection payload")
        source.chmod(0o640)
        entry = self.quarantine.quarantine(source)
        self.assertFalse(source.exists())
        self.assertEqual(entry.quarantined.read_bytes(), b"test detection payload")
        self.assertEqual(self.quarantine.entries(), [entry])

        source.write_text("new file created after quarantine")
        with self.assertRaises(FileExistsError):
            self.quarantine.restore(entry.token)
        self.assertTrue(entry.quarantined.exists())
        source.unlink()

        restored = self.quarantine.restore(entry.token)
        self.assertEqual(restored, source)
        self.assertEqual(source.read_bytes(), b"test detection payload")
        self.assertEqual(source.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.quarantine.entries(), [])

    def test_non_regular_files_are_rejected(self):
        directory = Path(self.temp.name) / "folder"
        directory.mkdir()
        with self.assertRaises(ValueError):
            self.quarantine.quarantine(directory)

    def test_action_is_refused_if_detected_file_was_replaced(self):
        source = Path(self.temp.name) / "changed.bin"
        source.write_bytes(b"first")
        info = source.lstat()
        identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        source.unlink()
        source.write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "изменился после проверки"):
            self.quarantine.delete(source, identity)
        self.assertEqual(source.read_bytes(), b"replacement")

    def test_detection_action_requires_explicit_confirmation_and_is_reversible(self):
        source = Path(self.temp.name) / "detected.bin"
        source.write_bytes(b"manual action")
        ui = TerminalUI(None, self.store, Config())
        ui.page = "scan"
        ui.scanner.finding_lines = [f"{source}: Test FOUND"]
        ui.scanner.finding_paths = [str(source)]
        info = source.lstat()
        ui.scanner.finding_identities = {
            str(source): (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        }
        self.assertIn(("Действия с находками · 1", "detections"), ui.menu())

        ui.activate("detections")
        ui.activate("detection:0")
        ui.activate("quarantine_confirm")
        self.assertTrue(source.exists())
        ui.activate("confirm_quarantine")
        self.assertFalse(source.exists())
        self.assertEqual(ui.scanner.finding_paths_snapshot(), [])

        ui.go("quarantine")
        ui.activate("quarantine:0")
        ui.activate("restore_confirm")
        ui.activate("confirm_restore")
        self.assertEqual(source.read_bytes(), b"manual action")

    def test_delete_is_manual_and_requires_confirmation(self):
        source = Path(self.temp.name) / "delete-me.bin"
        source.write_bytes(b"delete manually")
        ui = TerminalUI(None, self.store, Config())
        ui.page = "scan"
        ui.scanner.finding_lines = [f"{source}: Test FOUND"]
        ui.scanner.finding_paths = [str(source)]
        info = source.lstat()
        ui.scanner.finding_identities[str(source)] = (
            info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        ui.activate("detections")
        ui.activate("detection:0")
        ui.activate("delete_confirm")
        self.assertTrue(source.exists())
        ui.activate("confirm_delete")
        self.assertFalse(source.exists())

    def test_allowlist_skips_only_exact_paths_and_can_be_removed(self):
        root = Path(self.temp.name) / "scan-root"
        root.mkdir()
        ignored = root / "ignored.bin"
        included = root / "included.bin"
        ignored.write_text("ignore")
        included.write_text("scan")
        self.store.ignore_path(ignored)
        self.assertEqual(self.store.ignored_paths(), [str(ignored)])
        from clamui.core import Scanner
        scanner = Scanner(self.store, "unused")
        scanner.path = str(root)
        self.assertEqual(scanner._inventory(True, self.store.ignored_paths()), [str(included)])
        ui = TerminalUI(None, self.store, Config())
        ui.go("ignore_list")
        ui.activate("ignored:0")
        ui.activate("confirm_unignore")
        self.assertEqual(self.store.ignored_paths(), [])


if __name__ == "__main__":
    unittest.main()
