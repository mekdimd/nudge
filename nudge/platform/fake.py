from __future__ import annotations

import copy
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Literal

from ..core.models import AppRef, Control, Rect, Snapshot

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


class FakeAdapter:
    """A scripted app for tests and offline UI work.

    Each screen lists controls. A control may `goto` another screen when pressed,
    or `toggle` between two values. Text fields keep whatever is set into them.
    """

    name = "fake"

    def __init__(self, screens: dict, start: str, app: AppRef | None = None):
        self.screens = copy.deepcopy(screens)
        self.screen = start
        self.app = app or AppRef(name="Google Chrome", pid=4242)
        self.log: list[str] = []

    @classmethod
    def from_fixture(cls, name: str) -> FakeAdapter:
        data = json.loads((FIXTURES / f"{name}.json").read_text())
        return cls(data["screens"], data["start"], AppRef(name=data.get("app", "Google Chrome"), pid=4242))

    def thread_context(self):
        return nullcontext()

    def permission_problem(self) -> str | None:
        return None

    def frontmost_app(self) -> AppRef | None:
        return self.app

    def activate_app(self, app: AppRef) -> None:
        pass

    def _raw(self, control_id: str) -> dict:
        for raw in self.screens[self.screen]["controls"]:
            if raw["id"] == control_id:
                return raw
        raise KeyError(control_id)

    def snapshot(self, app: AppRef) -> Snapshot:
        screen = self.screens[self.screen]
        controls = []
        for i, raw in enumerate(screen["controls"]):
            x, y, w, h = raw.get("bounds", [40 + (i % 6) * 120, 80 + (i // 6) * 50, 100, 32])
            controls.append(
                Control(
                    id=raw["id"],
                    label=raw.get("label", ""),
                    role=raw.get("role", "button"),
                    enabled=raw.get("enabled", True),
                    bounds=Rect(x, y, w, h),
                    context=raw.get("context", ""),
                    value=raw.get("value"),
                    is_text_field=raw.get("text", False),
                )
            )
        return Snapshot(app=self.app, window_title=screen.get("title", self.screen), controls=controls)

    def press(self, control: Control) -> None:
        raw = self._raw(control.id)
        self.log.append(f"press {control.id}")
        if "toggle" in raw:
            a, b = raw["toggle"]
            raw["value"] = b if raw.get("value") == a else a
        if "goto" in raw:
            self.screen = raw["goto"]

    def click(self, control: Control) -> None:
        self.press(control)

    def set_text(self, control: Control, text: str) -> None:
        self.log.append(f"set {control.id}={text!r}")
        self._raw(control.id)["value"] = text

    def type_text(self, text: str) -> None:
        self.log.append(f"type {text!r}")

    def scroll(self, direction: Literal["up", "down"], near: Control | None, window: Snapshot) -> None:
        self.log.append(f"scroll {direction}")

    def key(self, name: str) -> None:
        self.log.append(f"key {name}")
