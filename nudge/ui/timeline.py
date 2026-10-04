from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape
from typing import Callable

from ..core import safety
from ..core.jev import JevDecision
from ..core.models import Action, AppRef


@dataclass
class Entry:
    """One line of the run: who did it, what they did, and whether it's still going."""

    actor: str  # you | jev | gemini | vision | app | nudge
    verb: str
    subject: str = ""
    state: str = "done"  # running | done | failed | waiting
    detail: str = ""
    app: AppRef | None = None

    def plain(self) -> str:
        return f"{self.verb} {self.subject}" if self.subject else self.verb

    def html(self) -> str:
        return escape(self.verb) + (f" <b>{escape(self.subject)}</b>" if self.subject else "")


class Timeline:
    """The run as an ordered list of entries. Listeners get (index, added), and (-1, False) when cleared."""

    def __init__(self):
        self.entries: list[Entry] = []
        self._listeners: list[Callable[[int, bool], None]] = []

    def subscribe(self, listener: Callable[[int, bool], None]) -> None:
        self._listeners.append(listener)

    def clear(self) -> None:
        self.entries = []
        self._notify(-1, False)

    def add(self, entry: Entry) -> int:
        self.entries.append(entry)
        index = len(self.entries) - 1
        self._notify(index, True)
        return index

    def set(self, index: int, entry: Entry) -> None:
        self.entries[index] = entry
        self._notify(index, False)

    def last(self, actor: str, state: str) -> int | None:
        for index in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[index]
            if entry.actor == actor and entry.state == state:
                return index
        return None

    def _notify(self, index: int, added: bool) -> None:
        for listener in self._listeners:
            listener(index, added)


PRESENT = {"press": "Pressing", "fill": "Typing into", "scroll": "Scrolling", "key": "Pressing", "go_to_url": "Opening"}
PAST = {"press": "Pressed", "fill": "Typed into", "scroll": "Scrolled", "key": "Pressed", "go_to_url": "Opened"}


def _subject(action: Action) -> str:
    if action.kind == "fill":
        return action.label or "the empty fields"
    if action.kind == "scroll":
        return action.direction or "down"
    if action.kind == "go_to_url":
        return action.url or "a website"
    return action.label


def _verb(action: Action, table: dict[str, str]) -> str:
    if action.kind == "press" and action.double:
        return "Double-clicking" if table is PRESENT else "Double-clicked"
    return table.get(action.kind, action.kind)


class RunRecorder:
    """Turns the loop's events, as the bar receives them, into timeline entries."""

    def __init__(self, timeline: Timeline):
        self.timeline = timeline
        self.app: AppRef | None = None
        self._gemini_result = "Wrote the text"

    def started(self, goal: str, app: AppRef) -> None:
        self.app = app
        self.timeline.clear()
        self.timeline.add(Entry("you", goal, app=app))

    def status(self, text: str) -> None:
        if text.startswith("Jev is choosing"):
            self._begin("jev", "Choosing the next step")
        elif text == "Looking at the screen":
            self._begin("vision", "Looking at the screen")
        elif text.startswith("Gemini is drafting"):
            self._gemini_result = "Wrote the text"
            self._begin("gemini", "Writing the text")
        elif text.startswith("Gemini is finding"):
            self._gemini_result = "Found the address"
            self._begin("gemini", "Finding the address")

    def decided(self, decision: JevDecision, labels: dict[str, str]) -> None:
        ms = f"{decision.milliseconds} ms"
        if safety.is_done(decision):
            entry = Entry("jev", "Says the task is done", detail=f"{decision.done:.0%} · {ms}")
        elif decision.chose_none:
            entry = Entry("jev", "Can't see the next control here", detail=ms)
        elif safety.is_unsure(decision):
            entry = Entry("jev", "Isn't sure what's next", detail=f"top {decision.top_probability:.0%} · {ms}")
        else:
            entry = Entry("jev", "Picked", labels.get(decision.choice, decision.choice), detail=f"{decision.top_probability:.0%} · {ms}")
        self._finish(entry)

    def vision_used(self, milliseconds: int, found: int) -> None:
        self._finish(Entry("vision", "Looked at the screen", detail=f"{found} controls · {milliseconds} ms"))

    def writer_started(self) -> None:
        if self.timeline.last("gemini", "running") is None:
            self._begin("gemini", "Writing the text")

    def writer_used(self, milliseconds: int) -> None:
        self._finish(Entry("gemini", self._gemini_result, detail=f"{milliseconds / 1000:.1f} s"))

    def proposed(self, action: Action) -> None:
        self._begin("app", _verb(action, PRESENT), _subject(action))

    def acted(self, action: Action, changed: bool) -> None:
        verb, subject = _verb(action, PAST), _subject(action)
        if changed:
            self._finish(Entry("app", verb, subject, app=self.app))
        else:
            self._finish(Entry("app", verb, subject, state="failed", detail="nothing changed", app=self.app))

    def switched(self, app: AppRef) -> None:
        self.app = app
        self.timeline.add(Entry("app", "Switched to", app.name, app=app))

    def waiting(self, text: str) -> None:
        self.timeline.add(Entry("nudge", text, state="waiting"))

    def answered(self) -> None:
        index = self.timeline.last("nudge", "waiting")
        if index is not None:
            self.timeline.set(index, replace(self.timeline.entries[index], state="done"))

    def finished(self, ok: bool, message: str) -> None:
        for index, entry in enumerate(self.timeline.entries):
            if entry.state in ("running", "waiting"):
                state = "done" if ok else "failed"
                self.timeline.set(index, replace(entry, state=state, detail=entry.detail or ("" if ok else "stopped")))
        verb, _, detail = message.partition(" · ")
        self.timeline.add(Entry("nudge", verb, state="done" if ok else "failed", detail=detail))

    def _begin(self, actor: str, verb: str, subject: str = "") -> None:
        self.timeline.add(Entry(actor, verb, subject, state="running", app=self.app if actor == "app" else None))

    def _finish(self, entry: Entry) -> None:
        index = self.timeline.last(entry.actor, "running")
        if entry.actor == "app" and entry.app is None:
            entry = replace(entry, app=self.app)
        if index is None:
            self.timeline.add(entry)
        else:
            self.timeline.set(index, entry)
