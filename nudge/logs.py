"""Bounded rotating log stream and API key redaction. Uses only the standard library."""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

MAX_LOG_BYTES = 1024 * 1024
LOG_BACKUPS = 3
REDACTED = "[REDACTED]"
SECRET_ENV_NAMES = (
    "TYPESAFE_API_KEY",
    "GEMINI_API_KEY",
    "ELEVENLABS_API_KEY",
    "GOOGLE_API_KEY",
)

_SECRET_PATTERNS = (
    re.compile(r"((?:TYPESAFE|GEMINI|ELEVENLABS|[A-Z0-9_]+)_API_KEY\s*=\s*)([^\s'\"`]+)"),
    re.compile(
        r"((?:authorization|x-goog-api-key|xi-api-key|x-api-key)\s*[:=]\s*(?:Bearer\s+)?)([^\s'\",;}\]]+)",
        re.IGNORECASE,
    ),
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-+/=]{8,})"),
    re.compile(r"([?&](?:api_key|apikey|key|token|access_token)=)([^&\s'\"#]+)", re.IGNORECASE),
    re.compile(r"\b(AIza[0-9A-Za-z\-_]{16,})\b"),
    re.compile(r"\b(sk[_-][A-Za-z0-9\-_]{16,})\b"),
)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def active_secrets(extra: Iterable[str] = ()) -> list[str]:
    values: set[str] = set()
    for name, value in os.environ.items():
        if name in SECRET_ENV_NAMES or name.endswith("_API_KEY"):
            stripped = value.strip()
            if len(stripped) >= 4:
                values.add(stripped)
    for value in extra:
        stripped = (value or "").strip()
        if len(stripped) >= 4:
            values.add(stripped)
    expanded: set[str] = set(values)
    for secret in values:
        encoded = quote(secret, safe="")
        if encoded != secret and len(encoded) >= 4:
            expanded.add(encoded)
    return sorted(expanded, key=len, reverse=True)


def redact_secrets(text: str, extra: Iterable[str] = ()) -> str:
    if not text:
        return text
    result = text
    for secret in active_secrets(extra):
        if secret in result:
            result = result.replace(secret, REDACTED)
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 2:
            result = pattern.sub(rf"\1{REDACTED}", result)
        else:
            result = pattern.sub(REDACTED, result)
    return result


def log_files(path: Path) -> list[Path]:
    """Return existing active and numbered rotated log files, newest first."""
    found: list[Path] = []
    if path.exists():
        found.append(path)
    if path.parent.exists():
        prefix = f"{path.name}."
        numbered: list[tuple[int, Path]] = []
        for entry in path.parent.iterdir():
            if entry.name.startswith(prefix):
                suffix = entry.name[len(prefix):]
                if suffix.isdigit():
                    numbered.append((int(suffix), entry))
        numbered.sort(key=lambda item: item[0])
        found.extend(entry for _, entry in numbered)
    return found


def _utf8_chunks(data: bytes, limit: int) -> list[bytes]:
    if len(data) <= limit:
        return [data]
    if limit < 4:
        return [data[i : i + limit] for i in range(0, len(data), limit)]
    chunks: list[bytes] = []
    start = 0
    total = len(data)
    while start < total:
        end = min(start + limit, total)
        if end < total:
            while end > start and (data[end] & 0xC0) == 0x80:
                end -= 1
            if end == start:
                end = min(start + limit, total)
        chunks.append(data[start:end])
        start = end
    return chunks


def _trim_tail_utf8(data: bytes, limit: int) -> bytes:
    if len(data) <= limit:
        return data
    tail = data[-limit:]
    if limit >= 4:
        offset = 0
        while offset < len(tail) and (tail[offset] & 0xC0) == 0x80:
            offset += 1
        if offset < len(tail):
            tail = tail[offset:]
    return tail


@contextmanager
def _file_lock(lock_path: Path):
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    locked = False
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        locked = True
        yield
    finally:
        if locked:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)


def _replace_with_retry(src: Path, dst: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.01)


class RotatingLogStream:
    """Thread-safe, size-bounded file stream that rotates logs and redacts API keys."""

    is_log_file = True
    encoding = "utf-8"

    def __init__(
        self,
        path: Path,
        max_bytes: int = MAX_LOG_BYTES,
        backup_count: int = LOG_BACKUPS,
        errors: str = "backslashreplace",
    ):
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if backup_count < 0:
            raise ValueError("backup_count must be non-negative")
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.errors = errors
        self._lock = threading.Lock()
        self._buffer = ""
        self.closed = False

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            text = str(text)
        if not text or self.closed:
            return 0
        with self._lock:
            self._buffer += text
            if "\n" in self._buffer:
                head, tail = self._buffer.rsplit("\n", 1)
                self._buffer = tail
                self._emit(head + "\n")
            elif len(self._buffer.encode(self.encoding, self.errors)) >= self.max_bytes:
                pending, self._buffer = self._buffer, ""
                self._emit(pending)
        return len(text)

    def flush(self) -> None:
        with self._lock:
            if self._buffer:
                pending, self._buffer = self._buffer, ""
                self._emit(pending)

    def close(self) -> None:
        self.flush()
        self.closed = True

    def isatty(self) -> bool:
        return False

    def writable(self) -> bool:
        return not self.closed

    def reconfigure(self, *, errors: str | None = None, **kwargs) -> None:
        if errors is not None:
            self.errors = errors

    def _emit(self, text: str) -> None:
        clean = redact_secrets(text)
        data = clean.encode(self.encoding, self.errors)
        if not data:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.path.parent / "log.lock"
        with _file_lock(lock_path):
            self._write_locked(data)

    def _write_locked(self, data: bytes) -> None:
        total_budget = (self.backup_count + 1) * self.max_bytes
        if len(data) > total_budget:
            data = _trim_tail_utf8(data, total_budget)
        for chunk in _utf8_chunks(data, self.max_bytes):
            current_size = self._current_size()
            if current_size > 0 and current_size + len(chunk) > self.max_bytes:
                self._rotate()
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0)
            fd = os.open(self.path, flags, 0o600)
            try:
                view = memoryview(chunk)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
            finally:
                os.close(fd)

    def _current_size(self) -> int:
        try:
            return self.path.stat().st_size
        except FileNotFoundError:
            return 0

    def _backup_path(self, index: int) -> Path:
        return self.path.with_name(f"{self.path.name}.{index}")

    def _rotate(self) -> None:
        if self.backup_count == 0:
            self.path.unlink(missing_ok=True)
            self._prune_extra_backups()
            return
        self._backup_path(self.backup_count).unlink(missing_ok=True)
        for index in range(self.backup_count - 1, 0, -1):
            src = self._backup_path(index)
            if src.exists():
                _replace_with_retry(src, self._backup_path(index + 1))
        if self.path.exists():
            _replace_with_retry(self.path, self._backup_path(1))
        self._prune_extra_backups()

    def _prune_extra_backups(self) -> None:
        prefix = f"{self.path.name}."
        for entry in self.path.parent.iterdir():
            if entry.name.startswith(prefix):
                suffix = entry.name[len(prefix):]
                if suffix.isdigit() and int(suffix) > self.backup_count:
                    entry.unlink(missing_ok=True)
