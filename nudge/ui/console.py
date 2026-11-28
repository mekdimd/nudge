from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from ..logs import redact_secrets
from .timeline import Entry, Timeline

NAMES = {"jev": "Jev", "gemini": "Gemini", "vision": "Vision", "nudge": "Nudge"}
COLORS = {"jev": "35", "gemini": "34", "vision": "36", "app": "32", "nudge": "37"}


def _safe_subject(entry: Entry) -> str:
    if entry.actor == "app" and entry.verb in ("Opening", "Opened") and entry.subject:
        parsed = urlparse(entry.subject)
        if parsed.scheme in ("http", "https") and parsed.hostname:
            port = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme}://{parsed.hostname}{port}"
        return "a website"
    return entry.subject


class Console:
    """Prints the run to the terminal as it happens: one line per settled timeline entry."""

    def __init__(self, timeline: Timeline, stream=None, color: bool | None = None, detailed: bool = False):
        self.timeline = timeline
        self.stream = stream or sys.stdout
        isatty = getattr(self.stream, "isatty", lambda: False)()
        self.color = color if color is not None else (isatty and "NO_COLOR" not in os.environ)
        self.detailed = detailed
        self._printed: dict[int, str] = {}
        timeline.subscribe(self._on_change)

    def banner(self, features: dict[str, bool]) -> None:
        parts = [self._paint(name, "32") if on else self._paint(f"{name} off", "90") for name, on in features.items()]
        self._write("")
        self._write("Nudge · " + "  ".join(parts))

    def note(self, text: str) -> None:
        self._write(self._paint(text, "90"))

    def format(self, entry: Entry) -> str:
        if entry.actor == "you":
            label = entry.verb if self.detailed else "Task started"
            line = self._paint(f"▶ {label}", "1") + (f" · {entry.app.name}" if entry.app else "")
            return redact_secrets(line)
        if entry.actor == "nudge" and entry.state != "waiting":
            mark = self._paint("✓", "32") if entry.state == "done" else self._paint("✕", "31")
            line = f"{mark} {entry.verb}" + (f" · {entry.detail}" if entry.detail else "")
            return redact_secrets(line)
        subject = entry.subject if self.detailed else _safe_subject(entry)
        text = entry.verb + (f" “{subject}”" if subject else "")
        name = entry.app.name if entry.actor == "app" and entry.app else NAMES.get(entry.actor, entry.actor)
        line = "  " + self._paint(f"{name:<9}", COLORS.get(entry.actor, "")) + " " + text
        if entry.detail:
            line += "  " + self._paint(entry.detail, "90")
        if entry.state == "failed":
            line += "  " + self._paint("✕", "31")
        if entry.state == "waiting":
            line += "  " + self._paint("waiting for you", "33")
        return redact_secrets(line)

    def _on_change(self, index: int, added: bool) -> None:
        if index < 0:
            self._printed = {}
            return
        entry = self.timeline.entries[index]
        before = self._printed.get(index)
        if entry.state == "running" or before == entry.state:
            return
        self._printed[index] = entry.state
        if before == "waiting" and entry.state == "done":
            return
        self._write(self.format(entry))

    def _paint(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color and code else text

    def _write(self, line: str) -> None:
        print(redact_secrets(line), file=self.stream, flush=True)
