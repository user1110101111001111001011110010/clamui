"""Configuration, history and scan jobs; independent of the terminal UI."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import threading
import time
import tomllib
import unicodedata
from urllib.parse import urlsplit

from .process import stream_process


def safe_text(value: object) -> str:
    """Render untrusted paths/output without terminal control sequences."""
    return "".join(c if not unicodedata.category(c).startswith("C") else
                   f"\\u{ord(c):04x}" for c in str(value))


@dataclass
class Config:
    language: str = "en"
    mode: str = "official"
    primary: str = ""
    backup: str = ""
    recursive: bool = True
    color: bool = True
    max_filesize_mib: int = 100
    max_scansize_mib: int = 400

    def validate(self) -> None:
        if self.language not in {"en", "ru"}:
            raise ValueError("Неизвестный язык интерфейса")
        if type(self.max_filesize_mib) is not int or not 1 <= self.max_filesize_mib <= 2048:
            raise ValueError("Максимальный размер файла должен быть от 1 до 2048 МиБ")
        if type(self.max_scansize_mib) is not int or not 1 <= self.max_scansize_mib <= 4096:
            raise ValueError("Максимальный объём сканирования должен быть от 1 до 4096 МиБ")
        if self.mode not in {"official", "private_only"}:
            raise ValueError("Неизвестный режим источников")
        for address in (self.primary, self.backup):
            if not address:
                continue
            if any(c.isspace() or unicodedata.category(c).startswith("C") for c in address):
                raise ValueError("В адресе зеркала недопустимы пробелы и управляющие символы")
            try:
                url = urlsplit(address)
                port = url.port
                valid = (url.scheme in {"http", "https"} and url.hostname
                         and not url.username and not url.password
                         and not url.query and not url.fragment and "\\" not in address
                         and (port is None or 0 < port <= 65535))
            except ValueError:
                valid = False
            if valid and self.mode == "private_only" and (url.hostname.rstrip(".").lower() == "clamav.net" or url.hostname.rstrip(".").lower().endswith(".clamav.net")):
                raise ValueError("В режиме своих зеркал адреса clamav.net запрещены")
            if not valid:
                raise ValueError("Нужен адрес http(s)://сервер[/путь], без пароля и параметров")
        if self.mode == "private_only" and not self.primary:
            raise ValueError("Для своих зеркал укажите основной адрес")
        if self.primary and self.primary == self.backup:
            raise ValueError("Основное и резервное зеркала должны отличаться")

    def sources(self) -> str:
        self.validate()
        if self.mode == "official":
            return "DatabaseMirror database.clamav.net\nDNSDatabaseInfo current.cvd.clamav.net\n"
        return "".join(f"PrivateMirror {url}\n" for url in (self.primary, self.backup) if url)

    def preview(self) -> str:
        return ("# Источники пользовательского обновления ClamUI\n"
                "# Системный freshclam.conf не меняется\n" + self.sources())


class Store:
    def __init__(self, root: Path | None = None):
        root = Path(root).expanduser().absolute() if root is not None else None
        home = Path.home()
        self.config_dir = root / "config" if root else Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config") / "clamui"
        self.state_dir = root / "state" if root else Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state") / "clamui"
        self.data_dir = root / "data" if root else Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share") / "clamui"
        self.activity = threading.Lock()
        for directory in (self.config_dir, self.state_dir, self.data_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        self.config_path = self.config_dir / "config.toml"
        self.db = self.state_dir / "history.sqlite3"
        self._lock = None
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, started TEXT NOT NULL, path TEXT NOT NULL, status TEXT NOT NULL, code INTEGER, output TEXT NOT NULL DEFAULT '')")
        self.db.chmod(0o600)

    def active_database(self):
        marker = self.data_dir / "active-database"
        if not marker.exists():
            return None
        name = marker.read_text().strip()
        if not name.startswith("db-") or Path(name).name != name:
            raise ValueError("Некорректный указатель локальных баз")
        directory = self.data_dir / name
        if not directory.is_dir():
            raise ValueError("Локальные базы отсутствуют. Запустите обновление")
        return directory

    def connect(self):
        return sqlite3.connect(self.db, timeout=2)

    def acquire(self):
        self._lock = open(self.state_dir / "instance.lock", "a")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._lock.close()
            self._lock = None
            raise RuntimeError("Другой экземпляр ClamUI уже работает") from exc
        with self.connect() as db:
            db.execute("UPDATE scans SET status='interrupted' WHERE status='running'")

    def close(self):
        if self._lock:
            self._lock.close()
            self._lock = None

    def load(self) -> Config:
        if not self.config_path.exists():
            return Config()
        try:
            values = tomllib.loads(self.config_path.read_text())
            if values.pop("schema_version", None) != 1:
                raise ValueError("Неизвестная версия настроек")
            known = set(Config.__dataclass_fields__)
            if not set(values) <= known:
                raise ValueError("Неверные поля настроек")
            # Older schema-v1 configurations predate scan size limits.
            values.setdefault("max_filesize_mib", 100)
            values.setdefault("max_scansize_mib", 400)
            for key, value in values.items():
                expected = (bool if key in {"recursive", "color"} else
                            int if key in {"max_filesize_mib", "max_scansize_mib"} else str)
                if type(value) is not expected:
                    raise ValueError("Неверный тип настройки: " + key)
            config = Config(**values)
            config.validate()
            return config
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Настройки повреждены: {exc}. Файл: {self.config_path}") from exc

    def save(self, config: Config):
        config.validate()
        content = "schema_version = 1\n" + "".join(
            f"{key} = {str(value).lower() if isinstance(value, bool) else json.dumps(value, ensure_ascii=False)}\n"
            for key, value in vars(config).items())
        fd, name = tempfile.mkstemp(dir=self.config_dir, prefix=".config-")
        try:
            with os.fdopen(fd, "w") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(name, self.config_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def begin(self, path: str) -> int:
        with self.connect() as db:
            row = db.execute("INSERT INTO scans(started,path,status) VALUES(?,?,'running')",
                             (datetime.now(timezone.utc).isoformat(timespec="seconds"), path))
            return row.lastrowid

    def finish(self, job: int, status: str, code: int | None, output: str):
        with self.connect() as db:
            db.execute("UPDATE scans SET status=?,code=?,output=? WHERE id=?", (status, code, output, job))

    def history(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 100")]


STATUS = {"empty": "Нет файлов для проверки", "running": "Проверка идёт", "clean": "Угроз не обнаружено в проверенных файлах",
          "found": "Обнаружены угрозы или предупреждения ClamAV", "failed": "Ошибка: проверка неполная",
          "cancelled": "Проверка отменена", "interrupted": "Проверка прервана"}

CLAMAV_EXECUTABLES = ("clamscan", "freshclam")


def missing_clamav_tools():
    """Return missing runtime ClamAV executables; package names vary by distro."""
    return [executable for executable in CLAMAV_EXECUTABLES if not shutil.which(executable)]


def engine_status(database=None) -> str:
    command = shutil.which("clamscan")
    if not command:
        return "ClamAV не найден. Установите пакет clamav."
    try:
        result = subprocess.run([command, "--version"] + ([f"--database={database}"] if database else []), capture_output=True, text=True, timeout=5)
        return safe_text((result.stdout or result.stderr).strip()) or "Версию ClamAV определить не удалось"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return safe_text(f"ClamAV: {exc}")


class Scanner:
    def __init__(self, store: Store, executable: str | None = None):
        self.store = store
        self.executable = executable
        self.cancelled = threading.Event()
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self.lines: deque[str] = deque()
        self.status = ""
        self.path = ""
        self.code: int | None = None
        self.started = 0.0
        self.elapsed = 0.0
        self.job: int | None = None
        self.phase = "idle"
        self.total = self.completed = self.checked = self.errors = self.skipped = self.found = 0
        self.current = ""
        self.pending = set()
        self.finding_lines = []

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def snapshot(self):
        with self.lock:
            return self.status, list(self.lines), self.path, self.code

    def progress(self):
        with self.lock:
            return {"phase": self.phase, "total": self.total, "completed": self.completed,
                    "checked": self.checked, "errors": self.errors, "skipped": self.skipped,
                    "found": self.found, "current": safe_text(self.current),
                    "percent": int(self.completed * 100 / self.total) if self.total and self.phase != "counting" else None}

    def findings_snapshot(self):
        with self.lock:
            return list(self.finding_lines)

    def append(self, line: str):
        with self.lock:
            self.lines.append(safe_text(line))

    def start(self, path: str, recursive: bool, max_filesize_mib: int = 100, max_scansize_mib: int = 400):
        if self.busy:
            raise ValueError("Дождитесь окончания текущей проверки")
        target = Path(path).expanduser().absolute()
        try:
            mode = target.lstat().st_mode
        except OSError as exc:
            raise ValueError(f"Путь недоступен: {exc.strerror}") from exc
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError("Выберите обычный файл или каталог, не ссылку или устройство")
        command = self.executable or shutil.which("clamscan")
        if not command:
            raise ValueError("clamscan не найден. Установите пакет clamav")
        if not self.store.activity.acquire(blocking=False):
            raise ValueError("Дождитесь окончания обновления или проверки")
        try:
            database = self.store.active_database()
            self.job = self.store.begin(str(target))
            self.cancelled.clear()
            with self.lock:
                self.lines.clear()
                self.path, self.status, self.code = str(target), "running", None
                self.total = self.completed = self.checked = self.errors = self.skipped = self.found = 0
                self.phase, self.current = "counting", ""
                self.pending = set()
                self.finding_lines = []
            self.started = time.monotonic()
            self.thread = threading.Thread(target=self._run, args=(command, recursive, database, max_filesize_mib, max_scansize_mib), daemon=False)
            self.thread.start()
        except BaseException:
            self.store.activity.release()
            raise

    def cancel(self):
        self.cancelled.set()

    def join(self):
        if self.thread:
            self.thread.join()

    def _omit(self, path, reason, error=False):
        with self.lock:
            self.skipped += 1
            if error:
                self.errors += 1
        self.append(f"Пропущено: {path}: {reason}")

    def _inventory(self, recursive):
        target = Path(self.path)
        root_device = target.stat().st_dev
        files = []
        excluded_roots = {path.absolute() for path in (
            self.store.config_dir, self.store.state_dir, self.store.data_dir
        )}

        def is_excluded(path):
            absolute = path.absolute()
            return any(absolute == root or root in absolute.parents for root in excluded_roots)

        if is_excluded(target):
            return files

        def add(path):
            if is_excluded(path):
                return
            try:
                mode = path.lstat()
                if not stat.S_ISREG(mode.st_mode):
                    self._omit(path, "не обычный файл")
                    return
                text = str(path)
                if "\n" in text or "\r" in text:
                    self._omit(path, "перевод строки в имени не поддерживается file-list", True)
                    return
                text.encode("utf-8")
                files.append(text)
                with self.lock:
                    self.total += 1
            except (OSError, UnicodeError) as exc:
                self._omit(path, str(exc), True)
        if target.is_file():
            add(target)
            return files
        def walk_error(exc):
            self._omit(exc.filename, exc.strerror, True)
        for directory, dirs, names in os.walk(target, followlinks=False, onerror=walk_error):
            if self.cancelled.is_set():
                break
            # Do not descend onto another filesystem or into symlink directories.
            allowed = []
            for name in dirs:
                if self.cancelled.is_set():
                    break
                path = Path(directory) / name
                if is_excluded(path):
                    continue
                try:
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or info.st_dev != root_device:
                        self._omit(path, "ссылка или другая файловая система")
                    elif recursive:
                        allowed.append(name)
                except OSError as exc:
                    self._omit(path, exc.strerror, True)
            dirs[:] = allowed
            for name in names:
                if self.cancelled.is_set():
                    break
                add(Path(directory) / name)
        return files

    def _result_line(self, line):
        # Strip terminal-mode toggles used by ClamAV's loading animation while
        # preserving every remaining non-empty line in the detailed log.
        line = re.sub(r"^(?:\x1b\[\?7[hl])+", "", line)
        if not line.strip():
            return
        if line.startswith("Scanning "):
            candidate = line[len("Scanning "):]
            with self.lock:
                if candidate in self.pending:
                    self.current, self.phase = candidate, "scanning"
        # Match the longest exact manifest path. Colons in filenames are legal.
        end = len(line)
        matched = None
        while (end := line.rfind(": ", 0, end)) != -1:
            candidate, result = line[:end], line[end + 2:]
            if candidate in self.pending:
                matched = candidate, result
                break
        if matched:
            candidate, result = matched
            clean = result in {"OK", "Empty file"}
            found = result.endswith(" FOUND")
            error = result.endswith(" ERROR") or result in {"Access denied", "Can't access file"}
            skipped = result.startswith("Excluded") or result == "Symbolic link"
            if clean or found or error or skipped:
                with self.lock:
                    self.pending.remove(candidate)
                    self.completed += 1
                    self.current, self.phase = candidate, "scanning"
                    if clean or found:
                        self.checked += 1
                    if found:
                        self.found += 1
                        self.finding_lines.append(safe_text(line))
                    if error:
                        self.errors += 1
                    if skipped:
                        self.skipped += 1
        self.append(line)

    def _run(self, command: str, recursive: bool, database, max_filesize_mib: int, max_scansize_mib: int):
        code = None
        status = "failed"
        manifest = None
        try:
            self.append("Составляем список файлов…")
            files = self._inventory(recursive)
            with self.lock:
                self.pending = set(files)
                self.phase = "loading"
            if self.cancelled.is_set():
                status = "cancelled"
            elif not files:
                self.append("Нет доступных обычных файлов для проверки")
                status = "failed" if self.errors else "empty"
            else:
                fd, manifest = tempfile.mkstemp(dir=self.store.state_dir, prefix="scan-", suffix=".list")
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(files) + "\n")
                args = [command, "--stdout", "--verbose", "--cross-fs=no",
                        "--follow-dir-symlinks=0", "--follow-file-symlinks=0",
                        f"--max-filesize={max_filesize_mib}M", f"--max-scansize={max_scansize_mib}M",
                        "--alert-exceeds-max=yes", "--recursive=no", f"--file-list={manifest}"]
                if database:
                    args.append(f"--database={database}")
                self.append(f"В списке {len(files)} файлов. Загружаем базы…")
                self.append(f"Базы: {database or 'системные'}")
                code = stream_process(args, self.cancelled, self._result_line)
                if self.cancelled.is_set():
                    status = "cancelled"
                elif code not in (0, 1) or self.errors or self.pending:
                    status = "failed"
                else:
                    status = "found" if code == 1 or self.found else "clean"
                if self.pending:
                    self.append(f"Не получен результат для {len(self.pending)} файлов; процент не доводится до 100 искусственно.")
        except Exception as exc:
            self.append(f"Ошибка сканирования: {exc}")
        finally:
            if manifest:
                try:
                    Path(manifest).unlink(missing_ok=True)
                except OSError as exc:
                    self.append(f"Не удалось удалить временный список: {exc}")
            self.elapsed = time.monotonic() - self.started
            with self.lock:
                self.status, self.code, self.phase = status, code, "finished"
            self.append(f"Обработано {self.completed}/{self.total}; проверено {self.checked}; находок {self.found}; ошибок {self.errors}; пропусков {self.skipped}.")
            try:
                self.store.finish(self.job, status, code, "\n".join(self.snapshot()[1]))
            except sqlite3.Error as exc:
                self.append(f"Не удалось сохранить историю: {exc}")
            finally:
                self.store.activity.release()
