from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

if sys.platform == "darwin":
    STATE = Path.home() / "Library" / "Logs" / "Nudge"
elif sys.platform == "win32":
    STATE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Nudge"
else:
    STATE = Path.home() / ".nudge"


def log_path() -> Path:
    return STATE / "nudge.log"


def _pid_file() -> Path:
    return STATE / "nudge.pid"


def child_args(argv: list[str]) -> list[str]:
    args = [a for a in argv if a not in ("--background", "--persistent")]
    return args + ["--persistent"]


def _alive(pid: int) -> bool:
    if sys.platform == "win32":  # os.kill(pid, 0) would terminate the process here
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except (OSError, SystemError):
        return False
    return True


def running_pid() -> int | None:
    try:
        pid = int(_pid_file().read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if _alive(pid) else None


def write_pid() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    _pid_file().write_text(str(os.getpid()))


def clear_pid() -> None:
    try:
        if int(_pid_file().read_text().strip()) == os.getpid():
            _pid_file().unlink()
    except (OSError, ValueError):
        pass


def detach(argv: list[str]) -> int:
    """Start Nudge again without a terminal attached; its output goes to the log file."""
    STATE.mkdir(parents=True, exist_ok=True)
    log = open(log_path(), "a", buffering=1)
    options: dict = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True  # Ctrl+C or closing the terminal won't reach it
    return subprocess.Popen([sys.executable, "-m", "nudge", *child_args(argv)], **options).pid


def stop() -> int | None:
    pid = running_pid()
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
    return pid
