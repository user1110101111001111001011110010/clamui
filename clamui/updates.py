"""Unprivileged freshclam updates in a private, atomically published database set."""
from collections import deque
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pwd
import shutil
import tempfile
import threading

from .core import safe_text
from .process import stream_process


class Updater:
    def __init__(self, store, executable=None):
        self.store = store
        self.executable = executable
        self.thread = None
        self.cancelled = threading.Event()
        self.lock = threading.Lock()
        self.lines = deque(maxlen=300)
        self.status = "idle"
        self.code = None

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def snapshot(self):
        with self.lock:
            return self.status, list(self.lines), self.code

    def append(self, text):
        with self.lock:
            self.lines.append(safe_text(text)[:4096])

    def start(self, config):
        config.validate()
        command = self.executable or shutil.which("freshclam")
        if not command:
            raise ValueError("freshclam не найден. Установите пакет clamav-freshclam")
        if not self.store.activity.acquire(blocking=False):
            raise ValueError("Дождитесь окончания проверки или обновления")
        try:
            self.cancelled.clear()
            with self.lock:
                self.status, self.code = "running", None
                self.lines.clear()
            self.thread = threading.Thread(target=self._run, args=(command, replace(config)), daemon=False)
            self.thread.start()
        except BaseException:
            self.store.activity.release()
            raise

    def cancel(self):
        self.cancelled.set()

    def join(self):
        if self.thread:
            self.thread.join()

    @staticmethod
    def configuration(config):
        config.validate()
        return config.sources() + (
            f"DatabaseOwner {pwd.getpwuid(os.getuid()).pw_name}\n"
            "TestDatabases yes\nConnectTimeout 10\nReceiveTimeout 60\nMaxAttempts 2\n"
            "Foreground yes\nLogTime yes\n")

    def _run(self, command, config):
        staging = None
        workspace = None
        destination = None
        runtime_config = None
        previous = None
        published = False
        code = None
        status = "failed"
        try:
            previous = self.store.active_database()
            # Mint/Ubuntu's freshclam AppArmor profile allows owner /tmp/**,
            # but not arbitrary XDG paths. Keep every file freshclam touches in
            # a private 0700 workspace. No profile changes or privilege elevation.
            workspace = Path(tempfile.mkdtemp(dir="/tmp", prefix="clamui-freshclam-"))
            staging = workspace / "databases"
            staging.mkdir(mode=0o700)
            self.append("Обновляем пользовательские базы ClamUI; системная служба не затрагивается.")
            self.append("Источники: " + ("официальные" if config.mode == "official" else config.primary + (", " + config.backup if config.backup else "")))
            if previous:
                self.append("Готовим копию текущих баз для безопасного обновления…")
                for file in previous.iterdir():
                    if self.cancelled.is_set():
                        break
                    if file.is_file() and not file.is_symlink():
                        shutil.copy2(file, staging / file.name)
            cooldown = self.store.data_dir / "freshclam.dat"
            if cooldown.exists():
                shutil.copy2(cooldown, staging / cooldown.name)
            fd, name = tempfile.mkstemp(dir=workspace, prefix="freshclam-", suffix=".conf")
            runtime_config = Path(name)
            with os.fdopen(fd, "w") as handle:
                handle.write(self.configuration(config))
            if self.cancelled.is_set():
                status = "cancelled"
            else:
                code = stream_process([command, f"--config-file={runtime_config}",
                                       f"--datadir={staging}", "--stdout", "--show-progress"],
                                      self.cancelled, self.append, use_pty=False)
                if self.cancelled.is_set():
                    status = "cancelled"
                elif code == 0:
                    # freshclam validates signatures and loadability before returning
                    # success. Do not activate an empty/incomplete download directory.
                    for name in ("main", "daily", "bytecode"):
                        if not any((staging / f"{name}.{ext}").is_file() for ext in ("cvd", "cld")):
                            raise ValueError(f"Не получена база {name}; прежние базы сохранены")
                    # /tmp and XDG_DATA_HOME can be on different filesystems.
                    # Copy first, then atomically publish a pointer on the target FS.
                    destination = Path(tempfile.mkdtemp(dir=self.store.data_dir, prefix="db-"))
                    self.append("Сохраняем проверенные базы в каталог ClamUI…")
                    for file in staging.iterdir():
                        if self.cancelled.is_set():
                            raise InterruptedError("Обновление отменено до подключения новых баз")
                        if file.is_file() and not file.is_symlink():
                            shutil.copy2(file, destination / file.name)
                    if self.cancelled.is_set():
                        raise InterruptedError("Обновление отменено до подключения новых баз")
                    pointer = self.store.data_dir / ".active-database.tmp"
                    with open(pointer, "w") as handle:
                        handle.write(destination.name + "\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(pointer, self.store.data_dir / "active-database")
                    published = True
                    status = "success"
                    self.append("Базы обновлены. Следующая проверка использует базы ClamUI.")
                else:
                    if any("Can't open/parse the config file" in line for line in self.snapshot()[1]):
                        self.append("freshclam не смог прочитать конфиг. Возможны ошибка синтаксиса или ограничения доступа/AppArmor; см. строки выше.")
                    self.append("Обновление не выполнено. Прежние базы сохранены; источники не переключены.")
        except InterruptedError as exc:
            status = "cancelled"
            self.append(str(exc))
        except Exception as exc:
            self.append(f"Ошибка обновления: {exc}")
        finally:
            # Preserve freshclam's backoff state even after a failed attempt.
            if staging and (staging / "freshclam.dat").exists():
                try:
                    shutil.copy2(staging / "freshclam.dat", self.store.data_dir / "freshclam.dat")
                except OSError as exc:
                    self.append(f"Не удалось сохранить интервал повторов freshclam: {exc}")
            if runtime_config:
                try:
                    runtime_config.unlink(missing_ok=True)
                except OSError as exc:
                    self.append(f"Не удалось удалить временный конфиг: {exc}")
            if workspace:
                shutil.rmtree(workspace, ignore_errors=True)
            if destination and not published:
                shutil.rmtree(destination, ignore_errors=True)
            if published and previous:
                # The store activity lock excludes scans while publishing/cleaning.
                shutil.rmtree(previous, ignore_errors=True)
            with self.lock:
                self.status, self.code = status, code
                result = {"time": datetime.now(timezone.utc).isoformat(), "status": status,
                          "code": code, "mode": config.mode, "output": list(self.lines)}
            try:
                (self.store.state_dir / "last-update.json").write_text(json.dumps(result, ensure_ascii=True))
            except OSError as exc:
                self.append(f"Не удалось записать результат: {exc}")
            finally:
                self.store.activity.release()
