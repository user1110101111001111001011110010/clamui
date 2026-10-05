import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clamui.core import Config, Store
from clamui.i18n import english
from clamui.tui import PROJECT_URL, TerminalUI


class InterfaceLanguageTests(unittest.TestCase):
    def test_english_is_default_and_translates_common_dynamic_text(self):
        self.assertEqual(Config().language, "en")
        self.assertEqual(english("Настройки"), "Settings")
        self.assertEqual(english("Максимальный размер файла: 100 МиБ"),
                         "Maximum file size: 100 MiB")
        self.assertEqual(english("Источники: официальные серверы"),
                         "Sources: official servers")

    def test_language_setting_toggles_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            ui = TerminalUI(None, store, store.load())
            ui.page = "settings"
            self.assertIn(("Interface language: English", "language"),
                          [(english(label), action) for label, action in ui.menu()])
            ui.activate("language")
            self.assertEqual(ui.config.language, "ru")
            self.assertEqual(store.load().language, "ru")
            self.assertIn(("Язык интерфейса: Русский", "language"), ui.menu())
            ui.activate("language")
            self.assertEqual(store.load().language, "en")
            store.close()

    def test_home_menu_opens_project_page(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            ui = TerminalUI(None, store, store.load())
            self.assertIn(("GitHub · clamui", "github"), ui.menu())
            with patch("clamui.tui.webbrowser.open", return_value=True) as open_browser:
                ui.activate("github")
            open_browser.assert_called_once_with(PROJECT_URL, new=2)
            self.assertIn("GitHub", ui.notice)
            store.close()


if __name__ == "__main__":
    unittest.main()
