from pathlib import Path
import curses
import io
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from clamui.core import Config, Scanner, Store
from clamui.paths import FileBrowser, complete_path
from clamui.package_managers import PackageManager
from clamui.tui import TerminalUI
from clamui.updates import Updater


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "app")
        self.store.acquire()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def executable(self, body):
        path = self.root / "fake-engine"
        path.write_text("#!/usr/bin/python3\n" + body)
        path.chmod(0o700)
        return str(path)

    def wait(self, worker):
        deadline = time.monotonic() + 6
        while worker.busy and time.monotonic() < deadline:
            time.sleep(.01)
        if worker.busy:
            worker.cancel()
            worker.join()
            self.fail("operation timed out")

    def test_browser_parent_hidden_files_and_folder_selection(self):
        (self.root / "directory").mkdir()
        (self.root / "a file.txt").touch()
        (self.root / ".hidden").touch()
        (self.root / "link").symlink_to(self.root / "directory")
        browser = FileBrowser()
        browser.open(self.root)
        names = [x[0] for x in browser.entries]
        self.assertNotIn(".hidden", names)
        self.assertLess(names.index("directory"), names.index("a file.txt"))
        self.assertEqual(next(e[2] for e in browser.entries if e[0] == "link"), "link")
        ui = TerminalUI(None, self.store, Config())
        ui.target = str(self.root)
        ui.activate("browse")
        index = next(i for i, e in enumerate(ui.browser.entries) if e[0] == "directory")
        ui.activate("entry:" + str(index))
        ui.activate("choose_dir")
        self.assertEqual(ui.target, str(self.root / "directory"))
        self.assertEqual(ui.page, "scan")

    def test_declining_engine_install_exits_clamui(self):
        missing = ["clamscan", "freshclam"]
        with patch("clamui.tui.missing_clamav_tools", return_value=missing):
            ui = TerminalUI(None, self.store, Config())
            self.assertEqual(ui.page, "engine_missing")
            self.assertEqual(ui.menu()[-1], ("Выйти из ClamUI", "exit"))
            ui.activate("exit")
            self.assertTrue(ui.exit_requested)

    def test_failed_package_install_reports_exit_code_and_missing_tools(self):
        missing = ["clamscan", "freshclam"]

        class Screen:
            def clear(self):
                pass

            def refresh(self):
                pass

            def get_wch(self):
                time.sleep(.01)
                raise curses.error

            def getmaxyx(self):
                return 24, 80

        class Process:
            stdout = io.StringIO("Чтение списков пакетов…\nE: Не хватает места на устройстве\n")

            def poll(self):
                return 100

            def wait(self):
                return 100

        manager = PackageManager("apt", "APT", "/usr/bin/apt-get", ("install", "-y"),
                                 ("clamav", "clamav-freshclam"))
        with (patch("clamui.tui.missing_clamav_tools", return_value=missing),
              patch("clamui.tui.detect_package_manager", return_value=manager),
              patch("clamui.tui.os.geteuid", return_value=1000),
              patch("clamui.tui.shutil.which", side_effect=lambda name: "/usr/bin/" + name),
              patch("clamui.tui.curses.def_prog_mode"),
              patch("clamui.tui.curses.endwin"),
              patch("clamui.tui.curses.reset_prog_mode"),
              patch("clamui.tui.subprocess.run", return_value=SimpleNamespace(returncode=0)),
              patch("clamui.tui.subprocess.Popen", return_value=Process()) as popen):
            ui = TerminalUI(Screen(), self.store, Config())
            ui.render = lambda: None
            ui.install_engine()

        self.assertIn("clamscan", ui.notice)
        self.assertIn("freshclam", ui.notice)
        self.assertIn("кодом 100", ui.notice)
        self.assertIn("E: Не хватает места на устройстве", ui.install_output)
        self.assertIn("-y", popen.call_args.args[0])
        self.assertIn("/usr/bin/apt-get", popen.call_args.args[0])
        self.assertNotIn("start_new_session", popen.call_args.kwargs)

    def test_termux_install_does_not_require_sudo(self):
        manager = PackageManager("termux", "Termux pkg", "pkg", ("install", "-y"), ("clamav",))
        with (patch("clamui.tui.missing_clamav_tools", side_effect=[["clamscan"], ["clamscan"], []]),
              patch("clamui.tui.detect_package_manager", return_value=manager),
              patch("clamui.tui.os.geteuid", return_value=1000),
              patch("clamui.tui.shutil.which", return_value=None),
              patch("clamui.tui.curses.def_prog_mode"),
              patch("clamui.tui.curses.endwin"),
              patch("clamui.tui.curses.reset_prog_mode"),
              patch("clamui.tui.TerminalUI._run_installer", return_value=0) as run_installer):
            ui = TerminalUI(None, self.store, Config())
            ui.win = SimpleNamespace(clear=lambda: None, refresh=lambda: None)
            ui.install_engine()

        run_installer.assert_called_once_with(None, manager)
        self.assertIn("установлены", ui.notice)

    def test_tab_completes_spaces_and_cycles_ambiguous_matches(self):
        (self.root / "My folder").mkdir()
        self.assertEqual(complete_path(str(self.root / "My"))[0], str(self.root / "My folder") + "/")
        (self.root / "My second").mkdir()
        ui = TerminalUI(None, self.store, Config())
        ui.begin_edit("path", "Path", str(self.root / "My"))
        ui.edit_key("\t")
        self.assertEqual(ui.edit[2], str(self.root / "My "))
        ui.edit_key("\t")
        self.assertEqual(ui.edit[2], str(self.root / "My folder") + "/")
        ui.edit_key("\t")
        self.assertEqual(ui.edit[2], str(self.root / "My second") + "/")

    def test_progress_counts_results_not_start_lines_or_duplicate_findings(self):
        scanner = Scanner(self.store)
        scanner.total = 3
        scanner.pending = {"/tmp/a: b", "/tmp/c", "/tmp/d"}
        scanner.phase = "loading"
        scanner._result_line("Scanning /tmp/a: b")
        self.assertEqual(scanner.progress()["percent"], 0)
        scanner._result_line("/tmp/a: b: OK")
        self.assertEqual(scanner.progress()["percent"], 33)
        scanner._result_line("/tmp/c: Test FOUND")
        scanner._result_line("/tmp/c: Test FOUND")
        self.assertEqual(scanner.progress()["percent"], 66)
        scanner._result_line("/tmp/d: Access denied")
        progress = scanner.progress()
        self.assertEqual((progress["percent"], progress["checked"], progress["errors"]), (100, 2, 1))

    def test_progress_does_not_invent_missing_results(self):
        target = self.root / "files"
        target.mkdir()
        (target / "a").write_text("a")
        (target / "b").write_text("b")
        command = self.executable("from pathlib import Path\nimport sys\nf=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--file-list='))).read_text().splitlines()\nprint(f[0] + ': OK')\n")
        scanner = Scanner(self.store, command)
        scanner.start(str(target), True)
        self.wait(scanner)
        self.assertEqual(scanner.snapshot()[0], "failed")
        self.assertEqual(scanner.progress()["percent"], 50)

    def test_manifest_skips_unrepresentable_names_and_does_not_recurse_when_disabled(self):
        target = self.root / "files"
        target.mkdir()
        (target / "good").write_text("a")
        (target / "bad\nname").write_text("a")
        (target / "folder").mkdir()
        (target / "folder" / "nested").write_text("a")
        scanner = Scanner(self.store)
        scanner.path = str(target)
        files = scanner._inventory(False)
        self.assertEqual(files, [str(target / "good")])
        self.assertEqual(scanner.errors, 1)
        self.assertEqual(scanner.total, 1)

    def test_empty_directory_is_not_reported_as_fully_scanned(self):
        target = self.root / "empty"
        target.mkdir()
        scanner = Scanner(self.store, self.executable("raise Exception('must not start')"))
        scanner.start(str(target), True)
        self.wait(scanner)
        self.assertEqual(scanner.snapshot()[0], "empty")
        self.assertIsNone(scanner.progress()["percent"])

    def update_engine(self, success=True):
        return self.executable("import sys\nfrom pathlib import Path\nd=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--datadir=')))\nc=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--config-file='))).read_text()\nassert 'PrivateMirror https://mirror.example.org' in c\nassert 'DatabaseMirror' not in c and 'DNSDatabaseInfo' not in c\nassert 'TestDatabases yes' in c\n" +
            ("for name in ('main','daily','bytecode'): (d/(name+'.cvd')).write_text('fake test fixture')\nprint('updated')\n" if success else
             "(d/'daily.cvd').write_text('partial')\n(d/'freshclam.dat').write_text('backoff fixture')\nsys.exit(17)\n"))

    def test_update_publishes_only_complete_set_and_scanner_uses_it(self):
        updater = Updater(self.store, self.update_engine())
        updater.start(Config(mode="private_only", primary="https://mirror.example.org"))
        self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "success")
        active = self.store.active_database()
        self.assertTrue((active / "daily.cvd").is_file())
        target = self.root / "target"
        target.write_text("a")
        command = self.executable(f"import sys\nfrom pathlib import Path\nassert '--database={active}' in sys.argv\nf=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--file-list='))).read_text().splitlines()\nprint(f[0]+': OK')\n")
        scanner = Scanner(self.store, command)
        scanner.start(str(target), True)
        self.wait(scanner)
        self.assertEqual(scanner.snapshot()[0], "clean")
        self.assertEqual(scanner.progress()["percent"], 100)

    def test_failed_update_preserves_previous_databases_and_backoff(self):
        config = Config(mode="private_only", primary="https://mirror.example.org")
        updater = Updater(self.store, self.update_engine())
        updater.start(config)
        self.wait(updater)
        previous = self.store.active_database()
        updater = Updater(self.store, self.update_engine(False))
        updater.start(config)
        self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "failed")
        self.assertEqual(self.store.active_database(), previous)
        self.assertEqual((previous / "daily.cvd").read_text(), "fake test fixture")
        self.assertEqual((self.store.data_dir / "freshclam.dat").read_text(), "backoff fixture")
        self.assertEqual(len(list(self.store.data_dir.glob("db-*"))), 1)

    def test_zero_exit_without_databases_does_not_activate(self):
        updater = Updater(self.store, self.executable("pass"))
        updater.start(Config())
        self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "failed")
        self.assertIsNone(self.store.active_database())

    def test_freshclam_only_sees_private_tmp_workspace(self):
        # Model Mint's profile: freshclam may open /tmp/**, not XDG paths.
        engine = self.executable("import sys, stat\nfrom pathlib import Path\nc=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--config-file=')))\nd=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--datadir=')))\nassert c.parent.parent == Path('/tmp')\nassert d.parent == c.parent\nassert c.parent.stat().st_mode & 0o777 == 0o700\nassert c.stat().st_mode & 0o777 == 0o600\nassert 'TestDatabases yes' in c.read_text()\nprint('workspace=' + str(c.parent),flush=True)\nfor name in ('main','daily','bytecode'): (d/(name+'.cvd')).write_text('fixture')\n")
        updater = Updater(self.store, engine)
        updater.start(Config())
        self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "success")
        work = next(x.split('=',1)[1] for x in updater.snapshot()[1] if x.startswith('workspace='))
        self.assertFalse(Path(work).exists())
        active = self.store.active_database()
        self.assertEqual(active.parent, self.store.data_dir)
        self.assertEqual((active / 'daily.cvd').read_text(), 'fixture')
        self.assertFalse(list(active.glob('*.conf')))

    def test_termux_update_uses_private_local_temporary_directory(self):
        engine = self.executable("import sys\nfrom pathlib import Path\nc=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--config-file=')))\nd=Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('--datadir=')))\nassert c.parent.parent.name == 'tmp'\nassert c.parent.parent.parent == Path(" + repr(str(self.store.state_dir)) + ")\nprint('workspace=' + str(c.parent),flush=True)\nfor name in ('main','daily','bytecode'): (d/(name+'.cvd')).write_text('fixture')\n")
        updater = Updater(self.store, engine)
        with patch("clamui.updates.is_termux", return_value=True):
            updater.start(Config())
            self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "success")
        work = next(x.split('=', 1)[1] for x in updater.snapshot()[1] if x.startswith('workspace='))
        self.assertFalse(Path(work).exists())

    def test_scans_exclude_clamui_configuration_state_and_databases(self):
        scan_root = self.root / "all-user-data"
        scan_root.mkdir()
        target = scan_root / "document.txt"
        target.write_text("safe")
        for directory in (self.store.config_dir, self.store.state_dir, self.store.data_dir):
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "internal.dat").write_text("ClamUI data")
        scanner = Scanner(self.store, "unused")
        scanner.path = str(scan_root)
        self.assertEqual(scanner._inventory(recursive=True), [str(target)])

    def test_scan_and_update_are_mutually_exclusive(self):
        self.store.activity.acquire()
        updater = Updater(self.store, self.executable("pass"))
        with self.assertRaises(ValueError):
            updater.start(Config())
        target = self.root / "target"
        target.touch()
        with self.assertRaises(ValueError):
            Scanner(self.store, "fake").start(str(target), True)
        self.store.activity.release()

    def test_cancel_update_never_activates_partial_download(self):
        updater = Updater(self.store, self.executable("import time\nprint('ready',flush=True)\ntime.sleep(60)"))
        updater.start(Config())
        deadline = time.monotonic() + 2
        while "ready" not in updater.snapshot()[1] and time.monotonic() < deadline:
            time.sleep(.01)
        updater.cancel()
        self.wait(updater)
        self.assertEqual(updater.snapshot()[0], "cancelled")
        self.assertIsNone(self.store.active_database())
        self.assertFalse(self.store.activity.locked())


if __name__ == "__main__":
    unittest.main()
