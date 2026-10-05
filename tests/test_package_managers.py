import unittest

from clamui.package_managers import PACKAGE_MANAGERS, detect_package_manager, manual_install_command


class PackageManagerTests(unittest.TestCase):
    def test_detects_first_available_manager(self):
        selected = detect_package_manager(lambda name: "/usr/bin/" + name if name in {"dnf", "pacman"} else None)
        self.assertEqual(selected.key, "dnf")

    def test_no_supported_manager_is_reported(self):
        self.assertIsNone(detect_package_manager(lambda _name: None))

    def test_commands_use_native_package_names_and_noninteractive_flags(self):
        expected = {
            "apt": ["apt-get", "install", "-y", "clamav", "clamav-freshclam"],
            "dnf": ["dnf", "install", "-y", "clamav", "clamav-update"],
            "zypper": ["zypper", "install", "-y", "clamav"],
            "pacman": ["pacman", "-S", "--needed", "--noconfirm", "clamav"],
            "apk": ["apk", "add", "clamav-scanner"],
            "pkg": ["pkg", "install", "-y", "clamav"],
        }
        managers = {manager.key: manager for manager in PACKAGE_MANAGERS}
        for key, command in expected.items():
            with self.subTest(manager=key):
                self.assertEqual(managers[key].command(), command)

    def test_manual_command_can_be_prefixed_with_sudo(self):
        apt = next(manager for manager in PACKAGE_MANAGERS if manager.key == "apt")
        self.assertEqual(manual_install_command(apt),
                         "sudo apt-get install -y clamav clamav-freshclam")
        self.assertEqual(manual_install_command(apt, sudo=False),
                         "apt-get install -y clamav clamav-freshclam")


if __name__ == "__main__":
    unittest.main()
