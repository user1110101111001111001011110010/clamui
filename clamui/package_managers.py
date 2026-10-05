"""Supported system package managers and their ClamAV package names."""
from __future__ import annotations

from dataclasses import dataclass
import os
import shutil


@dataclass(frozen=True)
class PackageManager:
    key: str
    label: str
    executable: str
    install_args: tuple[str, ...]
    packages: tuple[str, ...]

    def command(self) -> list[str]:
        return [self.executable, *self.install_args, *self.packages]


# RPM systems use dnf/yum/zypper to resolve repository dependencies; `rpm` itself
# is a low-level package tool and cannot safely resolve ClamAV's dependencies.
PACKAGE_MANAGERS = (
    PackageManager("termux", "Termux pkg", "pkg", ("install", "-y"), ("clamav",)),
    PackageManager("apt", "APT", "apt-get", ("install", "-y"),
                   ("clamav", "clamav-freshclam")),
    PackageManager("dnf", "DNF (RPM)", "dnf", ("install", "-y"),
                   ("clamav", "clamav-update")),
    PackageManager("yum", "YUM (RPM)", "yum", ("install", "-y"),
                   ("clamav", "clamav-update")),
    PackageManager("zypper", "Zypper (RPM)", "zypper", ("install", "-y"),
                   ("clamav",)),
    PackageManager("pacman", "Pacman", "pacman", ("-S", "--needed", "--noconfirm"),
                   ("clamav",)),
    PackageManager("apk", "APK", "apk", ("add",), ("clamav-scanner",)),
    PackageManager("pkg", "pkg", "pkg", ("install", "-y"), ("clamav",)),
    PackageManager("pkgin", "pkgin", "pkgin", ("-y", "install"), ("clamav",)),
    PackageManager("pkg_add", "pkg_add", "pkg_add", ("-I",), ("clamav",)),
    PackageManager("emerge", "Portage", "emerge", ("--ask=n",), ("clamav",)),
)


def is_termux(environ=None) -> bool:
    """Detect the Termux app environment without relying on Android root access."""
    environ = os.environ if environ is None else environ
    prefix = environ.get("PREFIX", "")
    return bool(environ.get("TERMUX_VERSION") or "/com.termux/files/usr" in prefix)


def detect_package_manager(which=shutil.which, environ=None) -> PackageManager | None:
    """Return the first supported manager available on this system."""
    if is_termux(environ) and which("pkg"):
        return next(manager for manager in PACKAGE_MANAGERS if manager.key == "termux")
    return next((manager for manager in PACKAGE_MANAGERS if which(manager.executable)), None)


def manual_install_command(manager: PackageManager, *, sudo: bool = True) -> str:
    command = manager.command()
    return " ".join((["sudo"] if sudo else []) + command)
