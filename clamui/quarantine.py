"""Explicit, reversible quarantine operations for scan detections."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import uuid


@dataclass(frozen=True)
class QuarantineEntry:
    token: str
    original: str
    quarantined: Path
    created: str


class Quarantine:
    def __init__(self, store):
        self.root = store.data_dir / "quarantine"
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root.chmod(0o700)

    def entries(self):
        records = []
        for metadata in self.root.glob("*.json"):
            try:
                value = json.loads(metadata.read_text())
                token = metadata.stem
                payload = self.root / token
                if (len(token) == 32 and payload.is_file() and
                        not payload.is_symlink() and isinstance(value.get("original"), str)):
                    records.append(QuarantineEntry(token, value["original"], payload,
                                                   str(value.get("created", ""))))
            except (OSError, ValueError, AttributeError):
                continue
        return sorted(records, key=lambda record: record.created, reverse=True)

    @staticmethod
    def _copy_verified(source: Path, destination: Path, expected_hash: str | None = None):
        digest = hashlib.sha256()
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            source_info = os.fstat(fd)
            if not stat.S_ISREG(source_info.st_mode):
                raise ValueError("Выбранный путь больше не является обычным файлом")
            out_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "rb", closefd=False) as src, os.fdopen(out_fd, "wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        digest.update(chunk)
                        dst.write(chunk)
                    dst.flush()
                    os.fsync(dst.fileno())
                current = os.stat(source, follow_symlinks=False)
                if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                        source_info.st_dev, source_info.st_ino, source_info.st_size, source_info.st_mtime_ns):
                    raise ValueError("Файл изменился во время операции; повторите её")
            except BaseException:
                try:
                    os.close(out_fd)
                except OSError:
                    pass
                destination.unlink(missing_ok=True)
                raise
        finally:
            os.close(fd)
        actual = digest.hexdigest()
        if expected_hash and actual != expected_hash:
            destination.unlink(missing_ok=True)
            raise ValueError("Контрольная сумма файла не совпала")
        return actual, source_info.st_mode & 0o777

    @staticmethod
    def identity(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns

    @classmethod
    def verify_detection(cls, path: str | Path, expected_identity):
        source = Path(path).expanduser().absolute()
        try:
            info = source.lstat()
        except OSError as exc:
            raise ValueError(f"Файл больше недоступен: {exc}") from exc
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Выбранный путь больше не является обычным файлом")
        if expected_identity is None or cls.identity(info) != tuple(expected_identity):
            raise ValueError("Файл изменился после проверки; повторите проверку перед действием")
        return source, info

    def quarantine(self, path: str | Path, expected_identity=None) -> QuarantineEntry:
        source = Path(path).expanduser().absolute()
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("В карантин можно переместить только обычный файл")
        if expected_identity is not None and self.identity(info) != tuple(expected_identity):
            raise ValueError("Файл изменился после проверки; повторите проверку перед действием")
        token = uuid.uuid4().hex
        payload = self.root / token
        metadata = self.root / f"{token}.json"
        digest, mode = self._copy_verified(source, payload)
        value = {"original": str(source), "created": datetime.now(timezone.utc).isoformat(),
                 "sha256": digest, "mode": mode}
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(dir=self.root, prefix=".record-")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, metadata)
            # Recheck the path identity immediately before removal so a replaced
            # file is never silently removed after the scan.
            current = source.lstat()
            if self.identity(current) != self.identity(info):
                raise ValueError("Файл изменился после проверки; исходник оставлен на месте")
            if expected_identity is not None and self.identity(current) != tuple(expected_identity):
                raise ValueError("Файл изменился после проверки; исходник оставлен на месте")
            source.unlink()
        except BaseException:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
            metadata.unlink(missing_ok=True)
            payload.unlink(missing_ok=True)
            raise
        return QuarantineEntry(token, str(source), payload, value["created"])

    def delete(self, path: str | Path, expected_identity):
        source, info = self.verify_detection(path, expected_identity)
        current = source.lstat()
        if self.identity(current) != self.identity(info):
            raise ValueError("Файл изменился во время операции; исходник оставлен на месте")
        source.unlink()
        return source

    def restore(self, token: str) -> Path:
        if len(token) != 32 or any(char not in "0123456789abcdef" for char in token):
            raise ValueError("Некорректная запись карантина")
        metadata = self.root / f"{token}.json"
        payload = self.root / token
        value = json.loads(metadata.read_text())
        destination = Path(value["original"])
        if not destination.is_absolute() or not destination.parent.is_dir():
            raise ValueError("Исходный каталог отсутствует; файл оставлен в карантине")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Путь уже занят; файл оставлен в карантине: {destination}")
        fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".clamui-restore-")
        os.close(fd)
        Path(temporary).unlink()
        try:
            actual, _ = self._copy_verified(payload, Path(temporary), value.get("sha256"))
            os.chmod(temporary, int(value.get("mode", 0o600)) & 0o777)
            os.link(temporary, destination)
            Path(temporary).unlink()
            payload.unlink()
            metadata.unlink()
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return destination
