from __future__ import annotations

import os
import time
import traceback
from dataclasses import dataclass
from typing import Protocol

from . import safety
from .actions import OptionSet, build_options, field_key, fillable, option_label, to_action
from .jev import JevClient, JevDecision, JevError
from .models import Action, AppRef, Control, Snapshot
from .verify import fingerprint, wait_for_change
from .writer import Writer, WriterError


class Events(Protocol):
    """How the loop talks to the person. Blocking methods return None when the run is cancelled."""

    def cancelled(self) -> bool: ...

    def status(self, text: str) -> None: ...

    def decided(self, step: int, decision: JevDecision, labels: dict[str, str]) -> None: ...

    def writer_started(self) -> None: ...

    def writer_used(self, milliseconds: int) -> None: ...

    def propose(self, action: Action, target: Control | None) -> None: ...

    def hold(self, seconds: float) -> bool: ...

    def choose(self, reason: str, options: list[tuple[str, str, float]]) -> str | None: ...

    def approve_draft(self, note: str, fields: list[tuple[str, str, str]]) -> dict[str, str] | None: ...

    def approve_url(self, url: str | None, fallback: str) -> str | None: ...

    def confirm(self, message: str) -> bool: ...

    def recover(self, message: str) -> str | None: ...

    def ask(self, message: str) -> str | None: ...

    def finished(self, ok: bool, message: str) -> None: ...


@dataclass
class Outcome:
    ok: bool
    reason: str
    message: str
    actions: int


class Stop(Exception):
    def __init__(self, reason: str, message: str, ok: bool = False):
        super().__init__(message)
        self.reason, self.message, self.ok = reason, message, ok


class NudgeLoop:
    def __init__(
        self,
        adapter,
        jev: JevClient,
        writer: Writer | None,
        events: Events,
        max_steps: int = safety.MAX_STEPS,
        hold_seconds: float = safety.HOLD_SECONDS,
        own_pid: int | None = None,
        settle_timeout: float = 2.5,
        startup_delay: float = 0.3,
    ):
        self.adapter = adapter
        self.jev = jev
        self.writer = writer
        self.events = events
        self.max_steps = max_steps
        self.hold_seconds = hold_seconds
        self.own_pid = own_pid if own_pid is not None else os.getpid()
        self.settle_timeout = settle_timeout
        self.startup_delay = startup_delay

    def run(self, goal: str, app: AppRef) -> Outcome:
        self.goal = goal
        self.app = app
        self.history: list[str] = []
        self.excluded: set[str] = set()
        self.drafted_fields: set[str] = set()
        try:
            with self.adapter.thread_context():
                message = self._run()
            outcome = Outcome(True, "done", message, len(self.history))
        except Stop as stop:
            outcome = Outcome(stop.ok, stop.reason, stop.message, len(self.history))
        except (JevError, WriterError) as exc:
            outcome = Outcome(False, "model_error", str(exc), len(self.history))
        except Exception as exc:  # adapters talk to live OS APIs; never crash the bar
            traceback.print_exc()
            outcome = Outcome(False, "error", f"{type(exc).__name__}: {exc}", len(self.history))
        self.events.finished(outcome.ok, outcome.message)
        return outcome

    def _check(self) -> None:
        if self.events.cancelled():
            raise Stop("cancelled", "Stopped.")

    def _check_app(self) -> None:
        front = self.adapter.frontmost_app()
        if front is not None and front.pid not in (self.app.pid, self.own_pid):
            raise Stop("app_changed", f"{front.name} came to the front, so I stopped. Start again in the app you want.")

    def _run(self) -> str:
        self.events.status(f"Working in {self.app.name}")
        self.adapter.activate_app(self.app)
        time.sleep(self.startup_delay)
        rounds = 0
        while True:
            rounds += 1
            if rounds > self.max_steps * 3:
                raise Stop("step_budget", "That took too many rounds, so I stopped.")
            self._check()
            self._check_app()

            snapshot = self.adapter.snapshot(self.app)
            options = build_options(snapshot, self.excluded, self.drafted_fields)
            self.events.status(f"Jev is choosing from {len(options.criteria)} options")
            decision = self.jev.decide(self.goal, snapshot, self.history, options)
            self._check()
            labels = {k: option_label(k, snapshot) for k, _ in decision.top(5, include_none=True)}
            self.events.decided(len(self.history) + 1, decision, labels)

            if safety.is_done(decision):
                return f"Done after {len(self.history)} step{'s' if len(self.history) != 1 else ''}."
            if len(self.history) >= self.max_steps:
                raise Stop("step_budget", f"Stopped after {self.max_steps} steps.")

            key = self._choose_key(decision, snapshot, options)
            if key is None:
                continue
            action = to_action(key, snapshot, self.drafted_fields)
            if not self._prepare(action, snapshot):
                continue
            self._act(action, snapshot)

    def _choose_key(self, decision: JevDecision, snapshot: Snapshot, options: OptionSet) -> str | None:
        if decision.chose_none:
            self._ask_for_help("I can't see the control for the next step.")
            return None
        if safety.is_unsure(decision):
            choices = [(k, option_label(k, snapshot), p) for k, p in decision.top(3)]
            picked = self.events.choose("I'm not sure which is next. Pick one:", choices)
            if picked is None:
                raise Stop("cancelled", "Stopped.")
            return picked
        return decision.choice

    def _ask_for_help(self, problem: str) -> None:
        answer = self.events.ask(
            f"{problem} You can open it yourself or add a detail, then press Continue."
        )
        if answer is None:
            raise Stop("cancelled", "Stopped.")
        if answer.strip():
            self.goal = f"{self.goal} (note from user: {answer.strip()})"
        self.excluded.clear()

    def _prepare(self, action: Action, snapshot: Snapshot) -> bool:
        """Get any text the action needs. Returns False to re-plan instead of acting."""
        if action.kind == "fill":
            fields = fillable(snapshot, self.drafted_fields)
            values: dict[str, str] = {f.id: "" for f in fields}
            note = "Check the draft, edit anything, then approve."
            if self.writer is not None:
                self.events.status("Gemini is drafting the text")
                self.events.writer_started()
                draft = self.writer.fill(self.goal, fields)
                self.events.writer_used(draft.milliseconds)
                values = draft.values
                if draft.rejected:
                    note = "I left some fields blank because the goal didn't include them. " + note
            else:
                note = "Gemini is off, so type the text yourself, then approve."
            self._check()
            approved = self.events.approve_draft(note, [(f.id, f.label or f.role, values.get(f.id, "")) for f in fields])
            if approved is None:
                raise Stop("cancelled", "Stopped.")
            action.text_by_field = {k: v for k, v in approved.items() if v.strip()}
            self.drafted_fields |= {field_key(f) for f in fields}
            action.label = ", ".join(f.label or f.role for f in fields if f.id in action.text_by_field)
            if not action.text_by_field:
                self.excluded.add(action.option_key)
                return False
            return True
        if action.kind == "go_to_url":
            url = None
            if self.writer is not None:
                self.events.status("Gemini is finding the address")
                self.events.writer_started()
                url, ms = self.writer.url(self.goal)
                self.events.writer_used(ms)
            text = self.events.approve_url(url, self.goal)
            if text is None:
                raise Stop("cancelled", "Stopped.")
            action.url = text.strip()
            return bool(action.url)
        return True

    def _target(self, action: Action, snapshot: Snapshot) -> Control | None:
        if action.kind == "press" and action.target_id:
            return snapshot.by_id(action.target_id)
        if action.kind == "fill" and action.text_by_field:
            return snapshot.by_id(next(iter(action.text_by_field)))
        return None

    def _needs_confirm(self, action: Action, snapshot: Snapshot) -> str | None:
        if action.kind == "press":
            return safety.consequential_word(action.label)
        if action.kind == "key" and action.key == "enter" and snapshot.focused_id:
            focused = snapshot.by_id(snapshot.focused_id)
            return safety.consequential_word(focused.label) if focused else None
        return None

    def _act(self, action: Action, snapshot: Snapshot) -> None:
        target = self._target(action, snapshot)
        self.events.status(action.describe())
        self.events.propose(action, target)
        self._check()

        word = self._needs_confirm(action, snapshot)
        if word:
            if not self.events.confirm(f"{action.describe()}? This will {word} and may not be undoable."):
                raise Stop("declined", "Okay, I didn't do it.")
        elif not self.events.hold(self.hold_seconds):
            raise Stop("cancelled", "Stopped.")
        self._check()
        self._check_app()

        before = fingerprint(snapshot)
        by_click = False
        while True:
            self._execute(action, snapshot, by_click)
            after, changed = wait_for_change(
                lambda: self.adapter.snapshot(self.app),
                before,
                timeout=self.settle_timeout,
                cancelled=self.events.cancelled,
            )
            if changed:
                self.history.append(f"{action.describe()}: worked")
                self.excluded.clear()
                return
            choice = self.events.recover(f"“{action.describe()}” didn't seem to change anything.")
            if choice in ("retry", "click"):
                by_click = choice == "click" and action.kind == "press"
                continue
            if choice == "other":
                self.excluded.add(target.describe() if action.kind == "press" and target else action.option_key)
                return
            raise Stop("no_change", "Stopped because the last step didn't work.")

    def _execute(self, action: Action, snapshot: Snapshot, by_click: bool = False) -> None:
        adapter = self.adapter
        adapter.activate_app(self.app)
        if action.kind == "press":
            control = snapshot.by_id(action.target_id or "")
            if control is None:
                raise Stop("missing", "That control disappeared before I could press it.")
            if by_click:
                adapter.click(control)
                return
            try:
                adapter.press(control)
            except Exception:
                adapter.click(control)
        elif action.kind == "fill":
            for field_id, text in action.text_by_field.items():
                control = snapshot.by_id(field_id)
                if control is not None:
                    adapter.set_text(control, text)
        elif action.kind == "scroll":
            adapter.scroll(action.direction or "down", None, snapshot)
        elif action.kind == "key":
            adapter.key(action.key)
        elif action.kind == "go_to_url":
            adapter.key("address_bar")
            time.sleep(0.15)
            adapter.type_text(action.url or "")
            time.sleep(0.1)
            adapter.key("enter")
