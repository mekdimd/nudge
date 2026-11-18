from __future__ import annotations

import errno
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

if sys.platform == "darwin":
    STATE = Path.home() / "Library" / "Logs" / "Nudge"
elif sys.platform == "win32":
    STATE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Nudge"
else:
    STATE = Path.home() / ".nudge"


class ProcessError(RuntimeError):
    pass


def log_path() -> Path:
    return STATE / "nudge.log"


def child_args(argv: list[str]) -> list[str]:
    args = [a for a in argv if a not in ("--background", "--detach", "--keep-running")]
    return args + ["--keep-running"]


def _try_lock():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Never unlink this file. Every contender must lock the same file.
    fd = os.open(STATE / "nudge.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
            return None
        raise
    return fd


def _record():
    try:
        record = json.loads((STATE / "nudge.owner").read_text())
        if (isinstance(record, dict) and isinstance(record.get("pid"), int)
                and record["pid"] > 0 and isinstance(record.get("port"), int)
                and 0 < record["port"] < 65536 and isinstance(record.get("token"), str)
                and len(record["token"]) == 64):
            return record
    except (OSError, ValueError):
        pass
    return None


def _request(record, command, timeout=1.0):
    try:
        with socket.create_connection(("127.0.0.1", record["port"]), timeout=timeout) as connection:
            connection.sendall(json.dumps({"token": record["token"], "command": command}).encode() + b"\n")
            with connection.makefile("rb") as stream:
                reply = json.loads(stream.readline(4096))
            if reply.get("token") == record["token"] and reply.get("pid") == record["pid"]:
                return reply
    except (OSError, ValueError, AttributeError):
        pass
    return None


def owner_status():
    record = _record()
    return _request(record, "status") if record else None


def running_pid() -> int | None:
    status = owner_status()
    return status["pid"] if status else None


class Instance:
    def __init__(self, fd):
        self.fd = fd
        self.ready = False
        self.stop_requested = threading.Event()
        self.closed = threading.Event()
        self.server = socket.socket()
        try:
            self.server.bind(("127.0.0.1", 0))
            self.server.listen()
            self.server.settimeout(0.1)
            self.record = {"pid": os.getpid(), "port": self.server.getsockname()[1],
                           "token": secrets.token_hex(32), "launch": os.environ.get("NUDGE_LAUNCH", "")}
            record_path = STATE / "nudge.owner"
            with open(os.open(record_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as stream:
                json.dump(self.record, stream)
            self.thread = threading.Thread(target=self._serve, daemon=True)
            self.thread.start()
        except BaseException:
            self.server.close()
            os.close(fd)
            raise

    def _serve(self):
        while not self.closed.is_set():
            try:
                connection, _ = self.server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(1)
                try:
                    with connection.makefile("rb") as stream:
                        request = json.loads(stream.readline(4096))
                    token = request.get("token")
                    if not isinstance(token, str) or not secrets.compare_digest(token, self.record["token"]):
                        continue
                    command = request.get("command")
                    if command not in ("status", "stop"):
                        continue
                    connection.sendall(json.dumps({**self.record, "ready": self.ready}).encode() + b"\n")
                    if command == "stop":
                        self.stop_requested.set()
                        if not self.ready:
                            os._exit(0)  # Initialization can block before Qt can consume a stop request.
                except (OSError, ValueError, AttributeError):
                    continue

    def mark_ready(self):
        self.ready = True

    def close(self):
        self.closed.set()
        self.thread.join(timeout=2)
        self.server.close()
        if _record() == self.record:
            (STATE / "nudge.owner").unlink(missing_ok=True)
        os.close(self.fd)


def acquire() -> Instance | None:
    deadline = time.monotonic() + 5
    while True:
        fd = _try_lock()
        if fd is not None:
            return Instance(fd)
        if owner_status() is not None:
            return None
        if time.monotonic() >= deadline:
            raise ProcessError("Could not verify the Nudge owner holding the lock.")
        time.sleep(0.02)


def detach(argv: list[str], timeout: float = 30) -> int:
    """Wait for a detached child to acquire ownership and finish initialization."""
    STATE.mkdir(parents=True, exist_ok=True)
    launch = secrets.token_hex(32)
    with open(log_path(), "a", buffering=1) as log:
        options: dict = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT,
                         "env": {**os.environ, "NUDGE_LAUNCH": launch}}
        if sys.platform == "win32":
            options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        child = subprocess.Popen([sys.executable, "-m", "nudge", *child_args(argv)], **options)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = child.poll()
        status = owner_status()
        if status and status["ready"] and (code == 0 or (code is None and status["launch"] == launch)):
            return status["pid"]
        if code is not None and (code != 0 or not status):
            raise ProcessError(f"Nudge startup failed (exit {code}). See {log_path()}")
        time.sleep(0.02)
    if child.poll() is None:
        child.kill()
        child.wait(timeout=5)
    raise ProcessError(f"Nudge startup timed out. See {log_path()}")


def stop(timeout: float = 5) -> int | None:
    """Ask the authenticated owner to quit and wait for ownership to end."""
    deadline = time.monotonic() + timeout
    record = None
    while time.monotonic() < deadline:
        fd = _try_lock()
        if fd is not None:
            os.close(fd)
            return None
        record = _record()
        if record and _request(record, "stop", timeout=min(1, max(0.01, deadline - time.monotonic()))):
            break
        time.sleep(0.02)
    else:
        raise ProcessError("Could not contact the Nudge owner to stop it.")
    while time.monotonic() < deadline:
        fd = _try_lock()
        if fd is not None:
            os.close(fd)
            return record["pid"]
        current = _record()
        if current and current["token"] != record["token"]:
            return record["pid"]
        time.sleep(0.02)
    raise ProcessError(f"Nudge (pid {record['pid']}) did not exit within {timeout:g} seconds.")
