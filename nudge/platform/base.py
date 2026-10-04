from __future__ import annotations

import re
import sys
from contextlib import AbstractContextManager
from typing import Callable, Literal, Protocol

from ..core.models import AppRef, Control, Snapshot

KeyName = Literal["enter", "escape", "tab", "back", "address_bar", "find", "paste"]


BIDI_MARKS = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def clean_text(text: str | None) -> str:
    return " ".join(BIDI_MARKS.sub("", text or "").split())


class AdapterError(RuntimeError):
    pass


class Adapter(Protocol):
    """Everything Nudge needs from an operating system. Coordinates are Qt logical pixels."""

    name: str

    def thread_context(self) -> AbstractContextManager: ...

    def permission_problem(self) -> str | None: ...

    def frontmost_app(self) -> AppRef | None: ...

    def activate_app(self, app: AppRef) -> None: ...

    def snapshot(self, app: AppRef) -> Snapshot: ...

    def press(self, control: Control) -> None: ...

    def click(self, control: Control, double: bool = False) -> None: ...

    def set_text(self, control: Control, text: str) -> None: ...

    def type_text(self, text: str) -> None: ...

    def scroll(self, direction: Literal["up", "down"], near: Control | None, window: Snapshot) -> None: ...

    def key(self, name: KeyName) -> None: ...


ToLogical = Callable[[float, float, float, float], tuple[float, float, float, float]]


def load_adapter(to_logical: ToLogical | None = None, to_physical: ToLogical | None = None) -> Adapter:
    if sys.platform == "darwin":
        from .mac import MacAdapter

        return MacAdapter()
    if sys.platform == "win32":
        from .win import WinAdapter

        return WinAdapter(to_logical=to_logical, to_physical=to_physical)
    raise AdapterError(f"Nudge supports macOS and Windows, not {sys.platform}")
