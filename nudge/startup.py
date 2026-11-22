"""Startup output that prints before the heavy UI imports. Uses only the standard library."""

from __future__ import annotations

import os
import sys
import threading
import time

WORDMARK = r"""
                    __
   ____  __  ______/ /___ ____
  / __ \/ / / / __  / __ `/ _ \
 / / / / /_/ / /_/ / /_/ /  __/
/_/ /_/\__,_/\__,_/\__, /\___/
                  /____/
""".strip("\n")
CURSOR = """
⢻⣶⣤⣄⡀
 ⢿⣿⣿⣿⣿⣶⣤⣄⡀
 ⠈⣿⣿⣿⣿⣿⣿⣿⡿⠿⠒
  ⠘⣿⣿⣿⡟⠁
   ⠹⣿⡿
    ⢻⠃
""".strip("\n")
BANNER = "\n".join(f"{cursor:<12}   {word}" for cursor, word in zip(CURSOR.splitlines(), WORDMARK.splitlines()))
FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
ASCII_FRAMES = "|/-\\"
TICK = 0.08


class _Guard:
    """Wraps stdout or stderr so other output erases the spinner line before it prints."""

    def __init__(self, startup: Startup, stream):
        self._startup = startup
        self._stream = stream

    def write(self, text: str) -> int:
        with self._startup._lock:
            self._startup._erase()
            return self._stream.write(text)

    def __getattr__(self, name):
        return getattr(self._stream, name)


class Startup:
    """Prints the banner at once, then a spinner on a terminal or plain lines when output is redirected."""

    def __init__(self, version: str, stream=None):
        self.stream = stream or sys.stdout
        self.live = getattr(self.stream, "isatty", lambda: False)()
        self.color = self.live and "NO_COLOR" not in os.environ
        self.step_text = ""
        self.started = time.monotonic()
        self._lock = threading.RLock()
        self._shown = False
        self._done = threading.Event()
        self._thread = None
        self._saved = None
        if self.live:
            self._frames = FRAMES if _can_encode(self.stream, FRAMES) else ASCII_FRAMES
            if _can_encode(self.stream, CURSOR):
                for cursor, word in zip(CURSOR.splitlines(), WORDMARK.splitlines()):
                    self._print(self._paint(f"{cursor:<12}", "38;2;79;142;247") + "   " + word)
            else:
                self._print(self._paint(WORDMARK, "36"))
            self._print(self._paint(f"v{version}", "90") + "\n")
        else:
            self._print(f"Starting Nudge {version}")

    def step(self, text: str) -> None:
        with self._lock:
            if self._done.is_set():
                return
            self.step_text = text
            if not self.live:
                self._print(f"  {text}...")
                return
            if self._thread is None:
                self._saved = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = _Guard(self, sys.stdout), _Guard(self, sys.stderr)
                self._thread = threading.Thread(target=self._spin, name="startup-spinner", daemon=True)
                self._thread.start()
            self._draw()

    def ready(self) -> None:
        if self._stop():
            line = f"Ready in {time.monotonic() - self.started:.1f} s"
            if self.live and _can_encode(self.stream, "✓"):
                line = self._paint("✓", "32") + " " + line
            self._print(line)

    def fail(self) -> None:
        """Clears the spinner and names the step that failed. The caller prints the error itself."""
        if self._stop() and self.step_text:
            step = self.step_text[0].lower() + self.step_text[1:]
            print(f"Startup failed while {step}.", file=sys.stderr, flush=True)

    def close(self) -> None:
        self._stop()

    def _stop(self) -> bool:
        with self._lock:
            if self._done.is_set():
                return False
            self._done.set()
            self._erase()
            if self._saved is not None:
                sys.stdout, sys.stderr = self._saved
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        return True

    def _spin(self) -> None:
        while not self._done.wait(TICK):
            with self._lock:
                if not self._done.is_set():
                    self._draw()

    def _draw(self) -> None:
        frame = self._frames[int((time.monotonic() - self.started) / TICK) % len(self._frames)]
        elapsed = int(time.monotonic() - self.started)
        line = self._paint(frame, "36") + " " + self.step_text + (self._paint(f"  {elapsed}s", "90") if elapsed else "")
        self.stream.write("\r\033[2K" + line)
        self.stream.flush()
        self._shown = True

    def _erase(self) -> None:
        if self._shown:
            self.stream.write("\r\033[2K")
            self.stream.flush()
            self._shown = False

    def _paint(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def _print(self, line: str) -> None:
        self.stream.write(line + "\n")
        self.stream.flush()


def _can_encode(stream, text: str) -> bool:
    try:
        text.encode(getattr(stream, "encoding", None) or "ascii")
    except (LookupError, UnicodeEncodeError):
        return False
    return True
