from pathlib import Path
import tempfile
import unittest

from clamui.core import Config, Store
from clamui.mirrors import MIRRORS
from clamui.tui import TerminalUI


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.ui = TerminalUI(None, self.store, Config())

    def tearDown(self):
        self.temp.cleanup()

    def choose(self, key, action):
        self.ui.go("mirror_catalog")
        index = next(i for i, m in enumerate(MIRRORS) if m.key == key)
        self.ui.activate("preset:" + str(index))
        self.ui.activate(action)

    def test_microsoft_and_reserve_survive_catalog_navigation(self):
        self.ui.go("mirrors")
        self.choose("microsoft", "preset_primary")
        self.assertEqual(self.ui.draft.primary, "https://packages.microsoft.com/clamav")
        self.assertEqual(self.ui.draft.mode, "private_only")
        self.choose("truenetwork", "preset_backup")
        self.assertEqual(self.ui.draft.primary, "https://packages.microsoft.com/clamav")
        self.assertEqual(self.ui.draft.backup, "https://mirror.truenetwork.ru/clamav")
        self.assertFalse(self.store.config_path.exists())
        self.ui.activate("save_mirrors")
        saved = self.store.load()
        self.assertEqual(saved, self.ui.draft)
        self.assertNotIn("DatabaseMirror", saved.sources())
        self.assertNotIn("DNSDatabaseInfo", saved.sources())

    def test_official_is_an_explicit_mode_not_a_private_fallback(self):
        self.ui.go("mirrors")
        self.choose("microsoft", "preset_primary")
        self.choose("official", "preset_official")
        self.assertEqual(self.ui.draft.mode, "official")
        self.assertIn("DatabaseMirror database.clamav.net", self.ui.draft.sources())
        self.assertNotIn("PrivateMirror", self.ui.draft.sources())

    def test_duplicate_reserve_is_rejected(self):
        self.ui.go("mirrors")
        self.choose("microsoft", "preset_primary")
        with self.assertRaises(ValueError):
            self.choose("microsoft", "preset_backup")

    def test_all_private_presets_are_valid(self):
        for mirror in MIRRORS:
            if mirror.mode == "private_only":
                Config(mode=mirror.mode, primary=mirror.url).validate()
