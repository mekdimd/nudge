from __future__ import annotations

import os
import sys

from .timeline import Entry, Timeline

NAMES = {"jev": "Jev", "gemini": "Gemini", "vision": "Vision", "nudge": "Nudge"}
COLORS = {"jev": "35", "gemini": "34", "vision": "36", "app": "32", "nudge": "37"}


class Console:
    """Prints the run to the terminal as it happens: one line per settled timeline entry."""

    def __init__(self, timeline: Timeline, stream=None, color: bool | None = None):
        self.timeline = timeline
        self.stream = stream or sys.stdout
        isatty = getattr(self.stream, "isatty", lambda: False)()
        self.color = color if color is not None else (isatty and "NO_COLOR" not in os.environ)
        self._printed: dict[int, str] = {}
        timeline.subscribe(self._on_change)

    def banner(self, features: dict[str, bool]) -> None:
        parts = [self._paint(name, "32") if on else self._paint(f"{name} off", "90") for name, on in features.items()]
        self._write("Nudge · " + "  ".join(parts))

    def note(self, text: str) -> None:
        self._write(self._paint(text, "90"))

    def format(self, entry: Entry) -> str:
        text = entry.verb + (f" “{entry.subject}”" if entry.subject else "")
        if entry.actor == "you":
            return self._paint(f"▶ {entry.verb}", "1") + (f" · {entry.app.name}" if entry.app else "")
        if entry.actor == "nudge" and entry.state != "waiting":
            mark = self._paint("✓", "32") if entry.state == "done" else self._paint("✕", "31")
            return f"{mark} {entry.verb}" + (f" · {entry.detail}" if entry.detail else "")
        name = entry.app.name if entry.actor == "app" and entry.app else NAMES.get(entry.actor, entry.actor)
        line = "  " + self._paint(f"{name:<9}", COLORS.get(entry.actor, "")) + " " + text
        if entry.detail:
            line += "  " + self._paint(entry.detail, "90")
        if entry.state == "failed":
            line += "  " + self._paint("✕", "31")
        if entry.state == "waiting":
            line += "  " + self._paint("waiting for you", "33")
        return line

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
        print(line, file=self.stream, flush=True)
