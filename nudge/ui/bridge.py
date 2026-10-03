from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QThread, Signal

from ..core.loop import NudgeLoop
from ..core.models import AppRef


class Bridge(QObject):
    """The loop's `Events`, called from the worker thread and answered from the UI thread."""

    sig_status = Signal(str)
    sig_decided = Signal(int, object, object)
    sig_writer_started = Signal()
    sig_writer_used = Signal(int)
    sig_propose = Signal(object, object)
    sig_hold = Signal(float)
    sig_choose = Signal(str, object)
    sig_draft = Signal(str, object)
    sig_url = Signal(object, str)
    sig_confirm = Signal(str)
    sig_recover = Signal(str)
    sig_ask = Signal(str)
    sig_finished = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self._cancel = threading.Event()
        self._ready = threading.Event()
        self._reply = None

    def reset(self) -> None:
        self._cancel.clear()
        self._ready.clear()
        self._reply = None

    def reply(self, value) -> None:
        self._reply = value
        self._ready.set()

    def cancel(self) -> None:
        self._cancel.set()
        self._ready.set()

    def _request(self, signal, *args, timeout: float | None = None):
        self._ready.clear()
        self._reply = None
        signal.emit(*args)
        started = time.monotonic()
        while not self._ready.wait(0.05):
            if timeout is not None and time.monotonic() - started > timeout:
                return None
        if self._cancel.is_set():
            return None
        return self._reply

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def status(self, text: str) -> None:
        self.sig_status.emit(text)

    def decided(self, step, decision, labels) -> None:
        self.sig_decided.emit(step, decision, labels)

    def writer_started(self) -> None:
        self.sig_writer_started.emit()

    def writer_used(self, milliseconds: int) -> None:
        self.sig_writer_used.emit(milliseconds)

    def propose(self, action, target) -> None:
        self._request(self.sig_propose, action, target, timeout=3.0)

    def hold(self, seconds: float) -> bool:
        self.sig_hold.emit(seconds)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._cancel.is_set():
                return False
            time.sleep(0.02)
        return not self._cancel.is_set()

    def choose(self, reason, options):
        return self._request(self.sig_choose, reason, options)

    def approve_draft(self, note, fields):
        return self._request(self.sig_draft, note, fields)

    def approve_url(self, url, fallback):
        return self._request(self.sig_url, url, fallback)

    def confirm(self, message) -> bool:
        return bool(self._request(self.sig_confirm, message))

    def recover(self, message):
        return self._request(self.sig_recover, message)

    def ask(self, message):
        return self._request(self.sig_ask, message)

    def finished(self, ok, message) -> None:
        self.sig_finished.emit(ok, message)


class Worker(QThread):
    def __init__(self, loop: NudgeLoop, goal: str, app: AppRef):
        super().__init__()
        self.loop, self.goal, self.app = loop, goal, app

    def run(self) -> None:
        self.loop.run(self.goal, self.app)
