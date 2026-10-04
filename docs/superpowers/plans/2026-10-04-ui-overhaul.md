# Nudge UI/UX Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bar's status line and badges with an activity feed (who did what, with real icons), a voice orb, one Stop button, Retry, soft sounds, a mic menu, and a colored terminal log, without changing how runs behave.

**Architecture:** A plain-Python `Timeline` holds entries; a `RunRecorder` turns the bridge's existing signals (plus two new loop events, `acted` and `switched`) into entries. The bar's `Feed` widget and the terminal `Console` both subscribe to the same timeline. Everything else (orb, icons, sounds, audio settings) is a small self-contained module the bar or `Nudge` controller wires in.

**Tech Stack:** Python 3.12, PySide6 6.11 (QtWidgets, QtSvg, QtMultimedia), numpy (already installed via openwakeword), PyObjC AppKit on macOS, pytest with Qt's `offscreen` platform.

**Spec:** `docs/superpowers/specs/2026-10-04-ui-overhaul-design.md`

## Global Constraints

- Branch: `feat/ui-overhaul`, based on `origin/main` at `9e37d0b`.
- No regressions: `uv run pytest -q` passes after every task (baseline: 54 passed). Task 1's characterization tests must keep passing unchanged through Task 7 (only the explicitly listed edits are allowed).
- Run behaviour is unchanged: the loop's decisions, safety rules, prompts' reply values, voice replies (`bar.spoken`), Esc, and hotkeys behave as today.
- Risky-action confirmation has no Enter shortcut (as today); it must be clicked or answered by voice.
- Exactly one Stop button (in the input row). Question cards never contain Stop.
- Qt widgets are tested headless: `QT_QPA_PLATFORM=offscreen`. macOS window calls only run when `QGuiApplication.platformName() == "cocoa"`.
- Commits follow Conventional Commits. Do not add a `Co-authored-by: Cursor` trailer: build commits with `git write-tree` / `git commit-tree` and `git reset --soft`, then check `git log -1 --format=%B`. The helper in Task 1 Step 7 does this.
- Code style: match the repo (`from __future__ import annotations`, type hints, short docstrings, few comments).

## File Structure

| File | Responsibility |
| --- | --- |
| `nudge/ui/timeline.py` (new) | `Entry`, `Timeline` (observable list), `RunRecorder` (loop events to entries) |
| `nudge/ui/feed.py` (new) | `Feed` scroll area, `EntryRow`, `Spinner`, `Shimmer` |
| `nudge/ui/orb.py` (new) | `Orb` voice avatar widget |
| `nudge/ui/icons.py` (new) | `actor_icon()`, `svg_pixmap()`, real app icons |
| `nudge/ui/assets/*.svg` (new) | `gemini.svg`, `typesafe.svg`, `eye.svg`, `mic.svg`, `mic-off.svg` |
| `nudge/ui/levels.py` (new) | `rms_level()`, `envelope()` for orb levels |
| `nudge/ui/audio_settings.py` (new) | `AudioSettings` (input device, mutes, persisted) |
| `nudge/ui/mic.py` (new) | `MicButton` with the input/mute menu |
| `nudge/ui/sounds.py` (new) | `synth()`, `Sounds` |
| `nudge/ui/console.py` (new) | `Console` terminal log |
| `nudge/ui/bar.py` | Layout, states, hint line, prompts as cards, Retry |
| `nudge/ui/theme.py` | New button kinds, card and feed styles |
| `nudge/ui/bridge.py` | `acted`, `switched` |
| `nudge/ui/voice.py`, `speaker.py`, `wake.py` | Levels, selected device, mute |
| `nudge/ui/overlay.py` | Cocoa guard, drop `flash` |
| `nudge/core/loop.py` | `acted`, `switched` events; recover copy |
| `nudge/__main__.py` | Wiring |
| `tests/conftest.py`, `tests/helpers.py` | `qapp` fixture, new event recording |
| `tests/test_bar.py`, `test_timeline.py`, `test_widgets.py`, `test_audio.py`, `test_console.py`, `test_app.py` (new) | Tests |

---

### Task 1: Headless Qt test harness and bar characterization tests

Freeze today's bar behaviour before changing it.

**Files:**
- Modify: `tests/conftest.py`
- Modify: `nudge/ui/bar.py:230-236` (`showEvent`)
- Modify: `nudge/ui/overlay.py:82-88` (`showEvent`)
- Create: `tests/test_bar.py`
- Create: `scripts/commit.sh`

**Interfaces:**
- Produces: pytest fixture `qapp` (session-scoped `QApplication`); helper `panel_buttons(bar, kind=None) -> list[QPushButton]` in `tests/test_bar.py`; `scripts/commit.sh "<message>"` (commits staged changes without the Cursor trailer).

- [ ] **Step 1: Add the `qapp` fixture**

Replace `tests/conftest.py` with:

```python
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
```

- [ ] **Step 2: Write the characterization tests**

Create `tests/test_bar.py`:

```python
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLineEdit, QPushButton

OPTIONS = [("k1", "Search", 0.41), ("k2", "Home", 0.33), ("k3", "Your Library", 0.12)]


@pytest.fixture
def bar(qapp):
    from nudge.ui.bar import Bar

    b = Bar()
    b.show()
    yield b
    b.close()
    b.deleteLater()


def panel_buttons(bar, kind=None):
    return [
        b for b in bar.panel.findChildren(QPushButton)
        if b.isVisibleTo(bar.panel) and (kind is None or b.property("kind") == kind)
    ]


def test_choice_spoken_number_replies_with_key(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("two") is True
    assert got == ["k2"]
    assert not bar.panel.isVisible()


def test_choice_spoken_stop_replies_none(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_choice_unrecognised_speech_keeps_prompt_open(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("banana bread") is False
    assert got == []
    assert bar.panel.isVisible()


@pytest.mark.parametrize("said,expected", [("yes", True), ("no", False), ("stop", False)])
def test_confirm_by_voice(bar, said, expected):
    got = []
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", got.append)
    assert bar.spoken(said) is True
    assert got == [expected]


@pytest.mark.parametrize("said,expected", [("try again", "retry"), ("click it", "click"), ("something else", "other"), ("stop", "stop")])
def test_recover_by_voice(bar, said, expected):
    got = []
    bar.show_recover("Pressing “Play” didn't change anything.", got.append)
    assert bar.spoken(said) is True
    assert got == [expected]


def test_draft_enter_types_the_edited_values(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Missing lecture")], got.append)
    editor = next(e for e in bar.panel.findChildren(QLineEdit) if e.isVisibleTo(bar.panel))
    editor.setText("Sick today")
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == [{"f1": "Sick today"}]


def test_draft_primary_button_types(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Hi")], got.append)
    panel_buttons(bar, "primary")[0].click()
    assert got == [{"f1": "Hi"}]


def test_draft_spoken_stop_replies_none(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Hi")], got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_url_spoken_yes_replies_with_the_address(bar):
    got = []
    bar.show_url("https://www.sfu.ca", "sfu", got.append)
    assert bar.spoken("yes") is True
    assert got == ["https://www.sfu.ca"]


def test_ask_spoken_detail_becomes_the_reply(bar):
    got = []
    bar.show_ask("I can't see the control.", got.append)
    assert bar.spoken("the blue one at the top") is True
    assert got == ["the blue one at the top"]


def test_ask_spoken_stop_replies_none(bar):
    got = []
    bar.show_ask("I can't see the control.", got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_answering_closes_the_panel_and_says_so(bar):
    closed = []
    bar.panel_closed.connect(lambda: closed.append(True))
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", lambda _: None)
    closed.clear()
    bar.spoken("yes")
    assert closed and not bar.panel.isVisible() and bar.spoken is None


def test_running_swaps_go_for_stop_and_locks_the_input(bar):
    bar.set_running(True)
    assert bar.stop.isVisible() and not bar.go.isVisible() and bar.input.isReadOnly()
    bar.set_running(False)
    assert bar.go.isVisible() and not bar.stop.isVisible() and not bar.input.isReadOnly()


def test_go_emits_the_goal(bar):
    goals = []
    bar.go_requested.connect(goals.append)
    bar.input.setText("turn on Live Caption")
    bar.go.click()
    assert goals == ["turn on Live Caption"]


def test_go_does_nothing_while_running(bar):
    goals = []
    bar.go_requested.connect(goals.append)
    bar.input.setText("x")
    bar.set_running(True)
    bar._go()
    assert goals == []


def test_stop_button_requests_stop(bar):
    stops = []
    bar.stop_requested.connect(lambda: stops.append(True))
    bar.set_running(True)
    bar.stop.click()
    assert stops == [True]


def test_escape_while_running_requests_stop(bar):
    stops = []
    bar.stop_requested.connect(lambda: stops.append(True))
    bar.set_running(True)
    bar._escape()
    assert stops == [True]
```

- [ ] **Step 3: Run them and watch the crash**

Run: `uv run pytest tests/test_bar.py -q`
Expected: the process crashes with a segfault (exit 139). `Bar.showEvent` calls the AppKit window code with an offscreen window ID.

- [ ] **Step 4: Guard the macOS window calls**

In `nudge/ui/bar.py`, change `showEvent` to:

```python
    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa":
            from .mac_window import float_over_everything

            float_over_everything(self, level=101)
        exclude_from_capture(self)
```

In `nudge/ui/overlay.py`, change `showEvent` the same way (add `QGuiApplication` to the `PySide6.QtGui` import if it isn't there):

```python
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa":
            from .mac_window import float_over_everything

            float_over_everything(self, level=1000, ignore_mouse=True)
        exclude_from_capture(self)
```

- [ ] **Step 5: Run the bar tests**

Run: `uv run pytest tests/test_bar.py -q`
Expected: all pass. If a voice phrase fails (for example `"click it"`), check `match_intent` in `nudge/core/spoken.py` and use a phrase it accepts today; the point is to record current behaviour, not to change it.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: 54 existing + the new tests pass.

- [ ] **Step 7: Add the commit helper and commit**

Create `scripts/commit.sh`:

```bash
#!/usr/bin/env bash
# Commit what's staged without the trailer Cursor's shell adds to `git commit`.
set -euo pipefail
msg_file=$(mktemp)
printf '%s\n' "$@" > "$msg_file"
tree=$(git write-tree)
commit=$(git commit-tree "$tree" -p HEAD -F "$msg_file")
git reset --soft "$commit"
rm -f "$msg_file"
git log -1 --format=%B
```

Run:

```bash
chmod +x scripts/commit.sh
git add tests/conftest.py tests/test_bar.py nudge/ui/bar.py nudge/ui/overlay.py scripts/commit.sh
scripts/commit.sh "test(ui): pin current bar behaviour with headless tests" "" "- qapp fixture on Qt's offscreen platform" "- skip AppKit window calls when Qt isn't on cocoa" "- scripts/commit.sh commits without the Cursor trailer"
```

Expected: the printed message has no `Co-authored-by` line.

---

### Task 2: `acted` and `switched` loop events

**Files:**
- Modify: `nudge/core/loop.py` (Events protocol, `_check_app`, `_act`, `_read_following_front`, `_follow_front`, recover copy)
- Modify: `nudge/ui/bridge.py`
- Modify: `tests/helpers.py`
- Test: `tests/test_loop.py`

**Interfaces:**
- Produces: `Events.acted(action: Action, changed: bool) -> None`, called once per execution attempt after the loop knows whether the screen changed. `Events.switched(app: AppRef) -> None`, called whenever the loop starts working in a different app. `Bridge.sig_acted = Signal(object, bool)`, `Bridge.sig_switched = Signal(object)`. `RecordingEvents.acted_log: list[tuple[str, bool]]`, `RecordingEvents.switched_log: list[str]`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_loop.py`:

```python
def test_acted_reports_every_press_that_worked():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents()
    make_loop(adapter, ScriptedJev(LIVE_CAPTION), events).run("turn on Live Caption", adapter.app)
    assert events.acted_log == [
        ("Press “Chrome”", True),
        ("Press “Settings”", True),
        ("Press “Accessibility”", True),
        ("Press “Live Caption”", True),
    ]


def test_acted_reports_no_change_before_asking_to_recover():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents(recover_answers=["stop"])
    make_loop(adapter, ScriptedJev(["Reload"]), events).run("reload", adapter.app)
    assert events.acted_log == [("Press “Reload”", False)]
    assert events.log[-1] == "recover Press “Reload” didn't change anything."


def test_switched_reports_the_app_a_taskbar_press_brought_forward():
    adapter = shell_adapter()
    events = RecordingEvents()
    make_loop(adapter, ScriptedJev(["Spotify"]), events).run("open Spotify from the taskbar", adapter.app)
    assert events.switched_log == ["Spotify"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_loop.py -q -k "acted or switched"`
Expected: FAIL with `AttributeError: 'RecordingEvents' object has no attribute 'acted_log'`.

- [ ] **Step 3: Record the new events in the test double**

In `tests/helpers.py`, add two fields to `RecordingEvents` after `result`:

```python
    acted_log: list = field(default_factory=list)
    switched_log: list = field(default_factory=list)
```

and two methods after `propose`:

```python
    def acted(self, action, changed):
        self.acted_log.append((action.describe(), changed))

    def switched(self, app):
        self.switched_log.append(app.name)
```

- [ ] **Step 4: Emit the events from the loop**

In `nudge/core/loop.py`, add to the `Events` protocol after `propose`:

```python
    def acted(self, action: Action, changed: bool) -> None: ...

    def switched(self, app: AppRef) -> None: ...
```

Add a helper method to `NudgeLoop` (next to `_read_following_front`):

```python
    def _switch_to(self, front: AppRef) -> None:
        self.app = front
        self.events.status(f"Working in {front.name}")
        self.events.switched(front)
```

Use it in the three places that currently set `self.app = front` and emit `Working in …`:

```python
    # _check_app
            if time.monotonic() - self.last_acted < FOLLOW_GRACE:
                # our own action launched or raised it, just after the settle check gave up waiting
                self._switch_to(front)
                self.fresh = None
                return

    # _read_following_front
        if front is not None and front.pid not in (self.app.pid, self.own_pid):
            self._switch_to(front)
        return self.adapter.snapshot(self.app)

    # _follow_front
            if front is not None and front.pid not in (self.app.pid, self.own_pid):
                self._switch_to(front)
                return True
```

In `_act`, report each attempt. The `while True` body becomes:

```python
        while True:
            self._execute(action, snapshot, by_click)
            self.last_acted = time.monotonic()
            if self._is_shell_press(action, snapshot) and self._follow_front():
                self.events.acted(action, True)
                self.history.append(f"{action.describe()}: worked")
                self.excluded.clear()
                self._pause_then_refetch()
                return
            after, changed = wait_for_change(
                self._read_following_front,
                before,
                timeout=self.settle_timeout * (3 if action.kind == "go_to_url" else 1),
                expect_load=action.kind == "go_to_url",
                cancelled=self.events.cancelled,
            )
            self.events.acted(action, changed)
            if changed:
                self.history.append(f"{action.describe()}: worked")
                self.excluded.clear()
                self._pause_then_refetch()
                return
            choice = self.events.recover(f"{action.describe()} didn't change anything.")
```

(The rest of the loop body is unchanged. The recover copy drops the doubled quotes: `“Press “Play”” didn't seem…` becomes `Press “Play” didn't change anything.`)

- [ ] **Step 5: Forward them through the bridge**

In `nudge/ui/bridge.py`, add signals after `sig_propose`:

```python
    sig_acted = Signal(object, bool)
    sig_switched = Signal(object)
```

and methods after `propose`:

```python
    def acted(self, action, changed) -> None:
        self.sig_acted.emit(action, changed)

    def switched(self, app) -> None:
        self.sig_switched.emit(app)
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass, including the three new tests.

- [ ] **Step 7: Commit**

```bash
git add nudge/core/loop.py nudge/ui/bridge.py tests/helpers.py tests/test_loop.py
scripts/commit.sh "feat(loop): report each action's outcome and app switches" "" "- Events.acted(action, changed) after every attempt" "- Events.switched(app) when the loop follows a new front app" "- clearer recover copy without doubled quotes"
```

---

### Task 3: Timeline model and run recorder

**Files:**
- Create: `nudge/ui/timeline.py`
- Test: `tests/test_timeline.py`

**Interfaces:**
- Consumes: `Events` methods from Task 2; `JevDecision` (`choice`, `chose_none`, `done`, `top_probability`, `milliseconds`); `safety.is_done`, `safety.is_unsure`; `Action`; `AppRef`.
- Produces:
  - `Entry(actor: str, verb: str, subject: str = "", state: str = "done", detail: str = "", app: AppRef | None = None)` with `.plain() -> str`, `.html() -> str`. `actor` is one of `you | jev | gemini | vision | app | nudge`; `state` is one of `running | done | failed | waiting`.
  - `Timeline` with `.entries: list[Entry]`, `.subscribe(listener: Callable[[int, bool], None])` (listener gets `(index, added)`, and `(-1, False)` on clear), `.clear()`, `.add(entry) -> int`, `.set(index, entry)`.
  - `RunRecorder(timeline)` with `.started(goal, app)`, `.status(text)`, `.decided(decision, labels)`, `.vision_used(ms, found)`, `.writer_started()`, `.writer_used(ms)`, `.proposed(action)`, `.acted(action, changed)`, `.switched(app)`, `.waiting(text)`, `.answered()`, `.finished(ok, message)`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_timeline.py`:

```python
from nudge.core.loop import NudgeLoop
from nudge.platform.fake import FakeAdapter
from nudge.ui.timeline import Entry, RunRecorder, Timeline

from helpers import FakeWriter, RecordingEvents, ScriptedJev
from test_loop import DRAFT, EMAIL_GOAL, LIVE_CAPTION, make_loop


class TimelineEvents(RecordingEvents):
    """RecordingEvents that also feeds a RunRecorder, the way the bridge does in the app."""

    def __init__(self, recorder, **kwargs):
        super().__init__(**kwargs)
        self.recorder = recorder

    def status(self, text):
        self.recorder.status(text)

    def decided(self, step, decision, labels):
        super().decided(step, decision, labels)
        self.recorder.decided(decision, labels)

    def writer_started(self):
        self.recorder.writer_started()

    def writer_used(self, ms):
        super().writer_used(ms)
        self.recorder.writer_used(ms)

    def vision_used(self, ms, found):
        super().vision_used(ms, found)
        self.recorder.vision_used(ms, found)

    def propose(self, action, target):
        super().propose(action, target)
        self.recorder.proposed(action)

    def acted(self, action, changed):
        super().acted(action, changed)
        self.recorder.acted(action, changed)

    def switched(self, app):
        super().switched(app)
        self.recorder.switched(app)

    def _ask(self, text, answer):
        self.recorder.waiting(text)
        value = answer()
        self.recorder.answered()
        return value

    def approve_draft(self, note, fields):
        return self._ask("Check the text before I type it", lambda: super(TimelineEvents, self).approve_draft(note, fields))

    def confirm(self, message):
        return self._ask("Waiting for your OK", lambda: super(TimelineEvents, self).confirm(message))

    def recover(self, message):
        return self._ask("That didn't work. What next?", lambda: super(TimelineEvents, self).recover(message))

    def finished(self, ok, message):
        super().finished(ok, message)
        self.recorder.finished(ok, message)


def run(fixture, script, goal, writer=None, **kwargs):
    adapter = FakeAdapter.from_fixture(fixture)
    timeline = Timeline()
    recorder = RunRecorder(timeline)
    recorder.started(goal, adapter.app)
    events = TimelineEvents(recorder, **kwargs)
    make_loop(adapter, ScriptedJev(script), events, writer).run(goal, adapter.app)
    return timeline, adapter


def test_timeline_notifies_adds_updates_and_clears():
    timeline, seen = Timeline(), []
    timeline.subscribe(lambda index, added: seen.append((index, added)))
    i = timeline.add(Entry("jev", "Choosing the next step", state="running"))
    timeline.set(i, Entry("jev", "Picked", "Settings"))
    timeline.clear()
    assert seen == [(0, True), (0, False), (-1, False)]
    assert timeline.entries == []


def test_entry_html_escapes_and_bolds_the_subject():
    assert Entry("app", "Pressed", "<Send>").html() == "Pressed <b>&lt;Send&gt;</b>"
    assert Entry("app", "Pressed", "Send").plain() == "Pressed Send"


def test_live_caption_run_reads_as_you_then_jev_and_app_turns():
    timeline, _ = run("live_caption", LIVE_CAPTION, "turn on Live Caption")
    entries = timeline.entries
    assert entries[0].actor == "you" and entries[0].verb == "turn on Live Caption"
    pressed = [e.subject for e in entries if e.actor == "app"]
    assert pressed == ["Chrome", "Settings", "Accessibility", "Live Caption"]
    assert all(e.verb == "Pressed" and e.state == "done" for e in entries if e.actor == "app")
    picked = [e for e in entries if e.actor == "jev" and e.verb == "Picked"]
    assert [e.subject for e in picked] == LIVE_CAPTION
    assert picked[0].detail.endswith("90 ms")
    assert entries[-1].actor == "nudge" and entries[-1].state == "done" and entries[-1].verb.startswith("Done in 4 steps")
    assert not [e for e in entries if e.state in ("running", "waiting")]


def test_gmail_run_shows_gemini_and_the_answered_questions():
    timeline, adapter = run("gmail", ["Compose", "fill", "Send"], EMAIL_GOAL, FakeWriter(DRAFT))
    entries = timeline.entries
    assert adapter.screen == "sent"
    gemini = [e for e in entries if e.actor == "gemini"]
    assert len(gemini) == 1 and gemini[0].verb == "Wrote the text" and gemini[0].detail == "0.8 s"
    questions = [e for e in entries if e.actor == "nudge" and e is not entries[-1]]
    assert [e.verb for e in questions] == ["Check the text before I type it", "Waiting for your OK"]
    assert all(e.state == "done" for e in questions)
    assert [e.subject for e in entries if e.actor == "app"][-1] == "Send"


def test_a_step_that_changed_nothing_is_marked_failed():
    timeline, _ = run("live_caption", ["Reload"], "reload", recover_answers=["stop"])
    failed = [e for e in timeline.entries if e.actor == "app"]
    assert failed[-1].state == "failed" and failed[-1].detail == "nothing changed"
    assert timeline.entries[-1].actor == "nudge" and timeline.entries[-1].state == "failed"


def test_stopping_marks_unfinished_entries_failed():
    timeline = Timeline()
    recorder = RunRecorder(timeline)
    adapter = FakeAdapter.from_fixture("live_caption")
    recorder.started("x", adapter.app)
    recorder.status("Jev is choosing from 12 options")
    recorder.finished(False, "Stopped.")
    assert timeline.entries[1].state == "failed" and timeline.entries[1].detail == "stopped"
    assert timeline.entries[-1].verb == "Stopped."


def test_switching_apps_adds_an_entry_and_later_presses_use_the_new_app():
    from nudge.core.models import Action, AppRef

    timeline = Timeline()
    recorder = RunRecorder(timeline)
    recorder.started("open Spotify", AppRef("Notes", 1))
    spotify = AppRef("Spotify", 9)
    recorder.switched(spotify)
    recorder.proposed(Action(kind="press", option_key="k", label="Play"))
    assert timeline.entries[1].verb == "Switched to" and timeline.entries[1].subject == "Spotify"
    assert timeline.entries[2].app == spotify and timeline.entries[2].state == "running"
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_timeline.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.timeline'`.

- [ ] **Step 3: Implement the timeline**

Create `nudge/ui/timeline.py`:

```python
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
```

- [ ] **Step 4: Run the timeline tests**

Run: `uv run pytest tests/test_timeline.py -q`
Expected: all pass. If `test_live_caption_run…` fails on `picked[0].detail`, print `timeline.entries` and confirm `ScriptedJev` reports 90 ms; adjust only the expectation, never the recorder's mapping table, unless the mapping is wrong against the spec.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add nudge/ui/timeline.py tests/test_timeline.py
scripts/commit.sh "feat(ui): timeline model fed by loop events" "" "- Entry, observable Timeline, and RunRecorder" "- tested against real loop runs on the fake adapter"
```

---

### Task 4: Icons and SVG assets

**Files:**
- Create: `nudge/ui/assets/gemini.svg`, `typesafe.svg`, `eye.svg`, `mic.svg`, `mic-off.svg`
- Create: `nudge/ui/icons.py`
- Modify: `pyproject.toml` (ship assets in the wheel)
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes: `AppRef`.
- Produces: `actor_icon(actor: str, app: AppRef | None = None, size: int = 18) -> QPixmap` (never null; cached); `svg_pixmap(name: str, size: int) -> QPixmap` (`name` without `.svg`); `ASSETS: Path`.

- [ ] **Step 1: Fetch the logos**

```bash
mkdir -p nudge/ui/assets
curl -sLo nudge/ui/assets/gemini.svg https://svgl.app/library/gemini.svg
curl -sLo nudge/ui/assets/typesafe.svg https://svgl.app/library/typesafe-ai-dark.svg
head -c 80 nudge/ui/assets/gemini.svg nudge/ui/assets/typesafe.svg
```

Expected: both start with `<svg`. (`typesafe-ai-dark.svg` is the white mark meant for dark backgrounds.)

- [ ] **Step 2: Write the three line icons**

`nudge/ui/assets/eye.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#FFB45C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>
```

`nudge/ui/assets/mic.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#F4F6FB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v1a7 7 0 0 0 14 0v-1"/><path d="M12 18v4"/></svg>
```

`nudge/ui/assets/mic-off.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><g stroke="#9AA3B5"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v1a7 7 0 0 0 14 0v-1"/><path d="M12 18v4"/></g><path d="M3 3l18 18" stroke="#F2545B"/></svg>
```

- [ ] **Step 3: Write failing tests**

Create `tests/test_widgets.py`:

```python
import os

import pytest

from nudge.core.models import AppRef


@pytest.mark.parametrize("actor", ["you", "jev", "gemini", "vision", "nudge", "app"])
def test_every_actor_has_an_icon(qapp, actor):
    from nudge.ui.icons import actor_icon

    pixmap = actor_icon(actor, AppRef("Google Chrome", 999999), 18)
    assert not pixmap.isNull()
    assert pixmap.deviceIndependentSize().width() == 18


def test_unknown_app_falls_back_to_a_letter_avatar(qapp):
    from nudge.ui.icons import actor_icon

    assert not actor_icon("app", AppRef("Zed", 999998)).isNull()
    assert not actor_icon("app", None).isNull()


def test_icons_are_cached(qapp):
    from nudge.ui.icons import actor_icon

    assert actor_icon("jev").cacheKey() == actor_icon("jev").cacheKey()


def test_running_process_icon_loads(qapp):
    from nudge.ui.icons import actor_icon

    assert not actor_icon("app", AppRef("Python", os.getpid()), 32).isNull()


def test_bundled_svgs_render(qapp):
    from nudge.ui.icons import ASSETS, svg_pixmap

    for path in ASSETS.glob("*.svg"):
        image = svg_pixmap(path.stem, 24).toImage()
        assert any(image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height())), path.name
```

- [ ] **Step 4: Run them to see them fail**

Run: `uv run pytest tests/test_widgets.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.icons'`.

- [ ] **Step 5: Implement icons**

Create `nudge/ui/icons.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QFileInfo, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap, QRadialGradient
from PySide6.QtSvg import QSvgRenderer

from ..core.models import AppRef
from . import theme

ASSETS = Path(__file__).parent / "assets"
SVGS = {"jev": "typesafe", "gemini": "gemini", "vision": "eye"}
LETTERS = {"you": ("You", QColor("#2A2F3A"))}
_cache: dict[tuple, QPixmap] = {}


def _ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 2.0


def _canvas(size: int) -> tuple[QPixmap, float]:
    ratio = _ratio()
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap, ratio


def svg_pixmap(name: str, size: int) -> QPixmap:
    key = ("svg", name, size)
    if key not in _cache:
        pixmap, _ = _canvas(size)
        renderer = QSvgRenderer(str(ASSETS / f"{name}.svg"))
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        _cache[key] = pixmap
    return _cache[key]


def _letter(text: str, color: QColor, size: int) -> QPixmap:
    pixmap, _ = _canvas(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    painter.setPen(theme.TEXT)
    painter.setFont(theme.font(max(7, int(size * (0.42 if len(text) > 1 else 0.55))), theme.QFont.Weight.Bold))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return pixmap


def _dot(size: int) -> QPixmap:
    pixmap, _ = _canvas(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QRadialGradient(size * 0.35, size * 0.3, size * 0.7)
    gradient.setColorAt(0.0, QColor("#D4E4FF"))
    gradient.setColorAt(0.45, QColor("#6AA0FF"))
    gradient.setColorAt(1.0, QColor("#2F3F8F"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    painter.end()
    return pixmap


def _mac_app_icon(pid: int) -> QPixmap | None:
    from AppKit import NSBitmapImageRep, NSRunningApplication

    running = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    image = running.icon() if running is not None else None
    if image is None:
        return None
    rep = NSBitmapImageRep.imageRepWithData_(image.TIFFRepresentation())
    png = rep.representationUsingType_properties_(4, {})  # NSBitmapImageFileTypePNG
    pixmap = QPixmap()
    return pixmap if png is not None and pixmap.loadFromData(bytes(png)) else None


def _windows_exe(pid: int) -> str | None:
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        return buffer.value if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle(handle)


def _windows_app_icon(pid: int, size: int) -> QPixmap | None:
    from PySide6.QtWidgets import QFileIconProvider

    path = _windows_exe(pid)
    if not path:
        return None
    pixmap = QFileIconProvider().icon(QFileInfo(path)).pixmap(size)
    return None if pixmap.isNull() else pixmap


def _app_icon(app: AppRef, size: int) -> QPixmap | None:
    try:
        if sys.platform == "darwin":
            raw = _mac_app_icon(app.pid)
        elif sys.platform == "win32":
            raw = _windows_app_icon(app.pid, size * 2)
        else:
            raw = None
    except Exception:
        return None
    if raw is None or raw.isNull():
        return None
    ratio = _ratio()
    scaled = raw.scaled(int(size * ratio), int(size * ratio), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(ratio)
    return scaled


def actor_icon(actor: str, app: AppRef | None = None, size: int = 18) -> QPixmap:
    """The small avatar shown next to a timeline entry. Never null: unknown things get a letter."""
    key = (actor, app.pid if actor == "app" and app else None, size)
    if key in _cache:
        return _cache[key]
    if actor in SVGS:
        pixmap = svg_pixmap(SVGS[actor], size)
    elif actor == "nudge":
        pixmap = _dot(size)
    elif actor == "app":
        pixmap = (_app_icon(app, size) if app else None) or _letter((app.name[:1] if app else "?").upper(), QColor("#34405A"), size)
    else:
        text, color = LETTERS.get(actor, (actor[:1].upper(), QColor("#2A2F3A")))
        pixmap = _letter(text, color, size)
    _cache[key] = pixmap
    return pixmap
```

`theme` needs to re-export `QFont` for `_letter`; it already imports it (`from PySide6.QtGui import QColor, QFont`), so `theme.QFont.Weight.Bold` works.

- [ ] **Step 6: Ship the assets in the wheel**

In `pyproject.toml`, under `[tool.hatch.build.targets.wheel]`, the `packages = ["nudge"]` line already includes every file inside `nudge/`, including `nudge/ui/assets/*.svg`. Confirm:

Run: `uv build --wheel -o /tmp/nudge-wheel && unzip -l /tmp/nudge-wheel/*.whl | grep assets`
Expected: the five SVGs are listed. If they aren't, add under `[tool.hatch.build.targets.wheel]`: `include = ["nudge/**/*.py", "nudge/ui/assets/*.svg"]`.

- [ ] **Step 7: Run tests**

Run: `uv run pytest tests/test_widgets.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add nudge/ui/assets nudge/ui/icons.py tests/test_widgets.py pyproject.toml
scripts/commit.sh "feat(ui): actor icons with real app, Gemini, and TypeSafe logos" "" "- app icons from the running process on macOS and Windows" "- Gemini and TypeSafe SVGs from svgl.app" "- letter avatars as the fallback"
```

---

### Task 5: Voice orb

**Files:**
- Create: `nudge/ui/orb.py`
- Test: `tests/test_widgets.py` (append)

**Interfaces:**
- Produces: `Orb(QWidget)` with `MODES = ("idle", "listening", "thinking", "speaking")`, `.mode: str`, `.level: float`, `.set_mode(mode: str)`, `.set_level(value: float)`, `._step()` (one smoothing tick; used by tests), fixed size `Orb.SIZE = 36`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_widgets.py`:

```python
def test_orb_modes_paint_without_errors(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    for mode in Orb.MODES:
        orb.set_mode(mode)
        orb.set_level(0.8)
        assert not orb.grab().isNull()


def test_orb_rejects_unknown_modes(qapp):
    from nudge.ui.orb import Orb

    with pytest.raises(ValueError):
        Orb().set_mode("dancing")


def test_orb_level_rises_fast_and_falls_slowly(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    orb.set_level(1.0)
    orb._step()
    risen = orb.level
    orb.set_level(0.0)
    orb._step()
    assert risen == pytest.approx(0.5)
    assert orb.level == pytest.approx(0.5 - 0.5 * 0.15)


def test_orb_level_is_clamped(qapp):
    from nudge.ui.orb import Orb

    orb = Orb()
    orb.set_level(7.0)
    assert orb._target == 1.0
    orb.set_level(-1.0)
    assert orb._target == 0.0
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_widgets.py -q -k orb`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.orb'`.

- [ ] **Step 3: Implement the orb**

Create `nudge/ui/orb.py`:

```python
from __future__ import annotations

import math
import time

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

ATTACK, RELEASE = 0.5, 0.15


class Orb(QWidget):
    """Nudge's avatar: breathes when idle, ripples while listening, swirls while thinking, wobbles with its voice."""

    SIZE = 36
    MODES = ("idle", "listening", "thinking", "speaking")

    def __init__(self):
        super().__init__()
        self.setFixedSize(self.SIZE, self.SIZE)
        self.mode = "idle"
        self.level = 0.0
        self._target = 0.0
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_mode(self, mode: str) -> None:
        if mode not in self.MODES:
            raise ValueError(f"unknown orb mode {mode!r}")
        self.mode = mode
        if mode in ("idle", "thinking"):
            self._target = 0.0
        self.update()

    def set_level(self, value: float) -> None:
        self._target = min(1.0, max(0.0, float(value)))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def _step(self) -> None:
        rate = ATTACK if self._target > self.level else RELEASE
        self.level += (self._target - self.level) * rate

    def _tick(self) -> None:
        self._step()
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = time.monotonic() - self._t0
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self.SIZE * 0.34
        p.setPen(Qt.PenStyle.NoPen)

        if self.mode == "listening":
            phase = (t % 1.4) / 1.4
            ring = QColor(106, 160, 255, int(150 * (1 - phase)))
            p.setPen(QPen(ring, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, r * (1 + 0.45 * phase), r * (1 + 0.45 * phase))
            p.setPen(Qt.PenStyle.NoPen)

        if self.mode == "idle":
            scale, opacity = 1 + 0.04 * math.sin(2 * math.pi * t / 4), 0.75
        elif self.mode == "listening":
            scale, opacity = 1 + 0.05 * math.sin(2 * math.pi * t / 1.2) + 0.22 * self.level, 1.0
        else:
            scale, opacity = 1.0 + (0.14 * self.level if self.mode == "speaking" else 0.0), 1.0
        radius = r * scale
        p.setOpacity(opacity)

        if self.mode == "thinking":
            brush = QConicalGradient(c, -360 * t / 2)
            for stop, color in ((0.0, "#6AA0FF"), (0.33, "#A78BFA"), (0.66, "#3B5BDB"), (1.0, "#6AA0FF")):
                brush.setColorAt(stop, QColor(color))
        else:
            brush = QRadialGradient(QPointF(c.x() - radius * 0.35, c.y() - radius * 0.4), radius * 1.6)
            for stop, color in ((0.0, "#D4E4FF"), (0.4, "#6AA0FF"), (0.7, "#3B5BDB"), (1.0, "#1B2A6B")):
                brush.setColorAt(stop, QColor(color))
        p.setBrush(brush)

        if self.mode == "speaking":
            amp = 0.04 + 0.12 * self.level
            path = QPainterPath()
            for i in range(65):
                a = 2 * math.pi * i / 64
                rr = radius * (1 + amp * (0.6 * math.sin(3 * a + 6 * t) + 0.4 * math.sin(2 * a - 4 * t)))
                point = QPointF(c.x() + rr * math.cos(a), c.y() + rr * math.sin(a))
                path.moveTo(point) if i == 0 else path.lineTo(point)
            p.drawPath(path)
        else:
            p.drawEllipse(c, radius, radius)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_widgets.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add nudge/ui/orb.py tests/test_widgets.py
scripts/commit.sh "feat(ui): animated voice orb" "" "- idle breathe, listening ripple, thinking swirl, speaking wobble" "- level smoothing with fast attack and slow release"
```

---

### Task 6: Activity feed widget

**Files:**
- Create: `nudge/ui/feed.py`
- Modify: `nudge/ui/theme.py` (feed styles)
- Test: `tests/test_widgets.py` (append)

**Interfaces:**
- Consumes: `Timeline`, `Entry` (Task 3); `actor_icon` (Task 4).
- Produces: `Feed(QScrollArea)` constructed as `Feed(timeline)`, with `.rows: list[EntryRow]` and `MAX_HEIGHT = 260`; `EntryRow` with `.mark: QLabel`, `.spinner: Spinner`, `.shimmer: Shimmer`, `.text: QLabel`, `.detail: QLabel`, `.set_entry(entry)`; `PRIVACY: dict[str, str]` (tooltips).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_widgets.py`:

```python
def test_feed_shows_rows_and_updates_in_place(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    assert not feed.isVisible()
    timeline.add(Entry("you", "turn on Live Caption"))
    i = timeline.add(Entry("jev", "Choosing the next step", state="running"))
    assert feed.isVisible() and len(feed.rows) == 2
    row = feed.rows[i]
    assert row.spinner.isVisibleTo(row) and row.shimmer.isVisibleTo(row) and not row.text.isVisibleTo(row)
    timeline.set(i, Entry("jev", "Picked", "Settings", detail="92% · 130 ms"))
    assert len(feed.rows) == 2
    assert not row.spinner.isVisibleTo(row) and row.text.text() == "Picked <b>Settings</b>"
    assert row.mark.text() == "✓" and row.detail.text() == "92% · 130 ms"


def test_feed_marks_failures_and_waits(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    timeline.add(Entry("app", "Pressed", "Play", state="failed", detail="nothing changed"))
    timeline.add(Entry("nudge", "Waiting for your OK", state="waiting"))
    assert [r.mark.text() for r in feed.rows] == ["✕", "•"]


def test_feed_clears_and_hides(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    feed.show()
    timeline.add(Entry("you", "x"))
    timeline.clear()
    assert feed.rows == [] and not feed.isVisible()


def test_feed_stops_growing_and_scrolls(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    feed.show()
    for n in range(30):
        timeline.add(Entry("jev", "Picked", f"Option {n}"))
    assert feed.height() <= Feed.MAX_HEIGHT


def test_jev_and_gemini_icons_explain_what_they_receive(qapp):
    from nudge.ui.feed import Feed
    from nudge.ui.timeline import Entry, Timeline

    timeline = Timeline()
    feed = Feed(timeline)
    timeline.add(Entry("jev", "Picked", "Settings"))
    timeline.add(Entry("gemini", "Wrote the text"))
    assert "labels" in feed.rows[0].icon.toolTip()
    assert "goal" in feed.rows[1].icon.toolTip()
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_widgets.py -q -k feed`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.feed'`.

- [ ] **Step 3: Add feed styles**

Append inside the `STYLE` f-string in `nudge/ui/theme.py` (before the closing `"""`):

```python
QScrollArea#feed, QWidget#feedBody {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.16); border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
```

- [ ] **Step 4: Implement the feed**

Create `nudge/ui/feed.py`:

```python
from __future__ import annotations

import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from . import theme
from .icons import actor_icon
from .timeline import Entry, Timeline

PRIVACY = {
    "jev": "Jev receives your goal and the labels of on-screen controls to choose the next step. Screenshots never leave your computer.",
    "gemini": "Gemini receives only your goal and the names of empty text fields, and only when text must be written.",
    "vision": "Vision runs on this computer. The screenshot never leaves it; only the labels it finds go to Jev.",
}
MARKS = {"done": ("✓", theme.GREEN), "failed": ("✕", theme.RED), "waiting": ("•", theme.AMBER)}


class Spinner(QWidget):
    def __init__(self, size: int = 12):
        super().__init__()
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._spin)

    def _spin(self) -> None:
        self._angle = (self._angle + 9) % 360
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        p.setPen(QPen(QColor(255, 255, 255, 50), 2))
        p.drawEllipse(box)
        p.setPen(QPen(theme.BLUE, 2, cap=Qt.PenCapStyle.RoundCap))
        p.drawArc(box, -self._angle * 16, 100 * 16)


class Shimmer(QWidget):
    """A running entry's text: muted, with a bright band sweeping across it."""

    def __init__(self):
        super().__init__()
        self.text = ""
        self.setFont(theme.font(14))
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)

    def set_text(self, text: str) -> None:
        self.text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self.text) + 4, metrics.height() + 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = max(self.width(), 1)
        x = ((time.monotonic() % 1.6) / 1.6) * (w + 160) - 80
        gradient = QLinearGradient(x - 70, 0, x + 70, 0)
        gradient.setColorAt(0.0, theme.MUTED)
        gradient.setColorAt(0.5, QColor("#FFFFFF"))
        gradient.setColorAt(1.0, theme.MUTED)
        p.setPen(QPen(gradient, 1))
        text = self.fontMetrics().elidedText(self.text, Qt.TextElideMode.ElideRight, w)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class EntryRow(QWidget):
    def __init__(self, entry: Entry):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 4, 0)
        row.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        self.spinner = Spinner()
        self.shimmer = Shimmer()
        self.text = QLabel()
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.text.setFont(theme.font(14))
        self.detail = QLabel()
        self.detail.setFont(theme.font(12))
        self.detail.setProperty("muted", "true")
        self.mark = QLabel()
        self.mark.setFont(theme.font(13, QFont.Weight.Bold))
        for widget in (self.icon, self.spinner, self.shimmer, self.text, self.detail):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(self.mark)
        self.set_entry(entry)

    def set_entry(self, entry: Entry) -> None:
        self.icon.setPixmap(actor_icon(entry.actor, entry.app))
        self.icon.setToolTip(PRIVACY.get(entry.actor, entry.app.name if entry.app else ""))
        running = entry.state == "running"
        self.spinner.setVisible(running)
        self.shimmer.setVisible(running)
        self.text.setVisible(not running)
        if running:
            self.shimmer.set_text(entry.plain())
        else:
            self.text.setText(entry.html())
        self.detail.setText(entry.detail)
        self.detail.setVisible(bool(entry.detail))
        mark, color = MARKS.get(entry.state, ("", theme.MUTED))
        self.mark.setText(mark)
        self.mark.setStyleSheet(f"color: {color.name()};")


class Feed(QScrollArea):
    """The run so far, newest at the bottom. Hidden when there's nothing to show."""

    MAX_HEIGHT = 260

    def __init__(self, timeline: Timeline):
        super().__init__()
        self.setObjectName("feed")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline = timeline
        self.body = QWidget()
        self.body.setObjectName("feedBody")
        self.rows_layout = QVBoxLayout(self.body)
        self.rows_layout.setContentsMargins(0, 2, 0, 2)
        self.rows_layout.setSpacing(8)
        self.setWidget(self.body)
        self.rows: list[EntryRow] = []
        timeline.subscribe(self._on_change)
        self.hide()

    def _on_change(self, index: int, added: bool) -> None:
        if index < 0:
            for row in self.rows:
                row.hide()
                row.deleteLater()
            self.rows = []
            self.hide()
            return
        entry = self.timeline.entries[index]
        if added:
            row = EntryRow(entry)
            self.rows_layout.addWidget(row)
            self.rows.append(row)
            self._fade_in(row)
        else:
            self.rows[index].set_entry(entry)
        self.show()
        self._fit()
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def _fit(self) -> None:
        self.body.adjustSize()
        self.setFixedHeight(min(self.body.sizeHint().height(), self.MAX_HEIGHT))

    def _fade_in(self, row: EntryRow) -> None:
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", row)
        animation.setDuration(180)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: row.setGraphicsEffect(None))
        animation.start()
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_widgets.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add nudge/ui/feed.py nudge/ui/theme.py tests/test_widgets.py
scripts/commit.sh "feat(ui): activity feed with spinners and shimmering running steps" "" "- one row per timeline entry, updated in place" "- privacy tooltips on the Jev, Gemini, and vision icons" "- capped height with auto-scroll"
```

---

### Task 7: Bar redesign (layout, states, prompts, Retry) and minimal controller update

The bar keeps its public API so the controller and Task 1's tests keep working. Removed methods (`set_jev`, `set_timing`, `set_jev_idle`, `set_gemini`) are replaced in `__main__.py` in this same task, so the app runs after every commit.

**Files:**
- Modify: `nudge/ui/bar.py` (rewrite)
- Modify: `nudge/ui/theme.py` (button kinds, card)
- Modify: `nudge/__main__.py` (constructor and calls that the bar API change touches)
- Modify: `tests/test_bar.py` (fixture passes a timeline; new tests)

**Interfaces:**
- Consumes: `Timeline` (Task 3), `Feed` (Task 6), `Orb` (Task 5), `actor_icon` (Task 4), `AppRef`, `safety.MAX_STEPS`.
- Produces (kept): `Bar` signals `go_requested(str)`, `stop_requested()`, `quit_requested()`, `panel_closed()`, `peek_toggled(bool)`; attributes `input`, `go`, `stop`, `peek`, `panel`, `panel_layout`, `spoken`, `running`; methods `summon()`, `set_running(bool)`, `set_status(text)`, `clear_panel()`, `show_choice`, `show_draft`, `show_url`, `show_confirm`, `show_recover`, `show_ask` (same arguments and reply values as today), `_go()`, `_escape()`.
- Produces (changed/new): `Bar(timeline: Timeline)`; `set_target(app: AppRef | None)` (was a name); `set_status(text: str, tone: str = "muted", during_run: bool = False)`; `set_step(step: int)`; `show_result(ok: bool)`; `orb: Orb`; `feed: Feed`; `hint: QLabel`; `state: str` (`idle | working | waiting`); `add_mic(widget: QWidget)`.

- [ ] **Step 1: Update the bar fixture and add tests for the new behaviour**

In `tests/test_bar.py`, change the fixture to pass a timeline:

```python
@pytest.fixture
def bar(qapp):
    from nudge.ui.bar import Bar
    from nudge.ui.timeline import Timeline

    b = Bar(Timeline())
    b.show()
    yield b
    b.close()
    b.deleteLater()
```

Append:

```python
PROMPTS = [
    ("show_choice", ("Pick one:", OPTIONS)),
    ("show_draft", ("Check the draft.", [("f1", "Subject", "Hi")])),
    ("show_url", ("https://www.sfu.ca", "sfu")),
    ("show_confirm", ("Press “Send”? This will send and may not be undoable.",)),
    ("show_recover", ("Press “Play” didn't change anything.",)),
    ("show_ask", ("I can't see the control.",)),
]


@pytest.mark.parametrize("method,args", PROMPTS)
def test_question_cards_never_have_their_own_stop(bar, method, args):
    bar.set_running(True)
    getattr(bar, method)(*args, lambda _: None)
    assert not [b for b in panel_buttons(bar) if b.property("kind") in ("danger", "stop") or "Stop" in b.text()]
    assert bar.stop.isVisible()


@pytest.mark.parametrize("method,args", PROMPTS)
def test_waiting_for_an_answer_turns_the_bar_amber_and_back(bar, method, args):
    bar.set_running(True)
    getattr(bar, method)(*args, lambda _: None)
    assert bar.state == "waiting"
    bar.clear_panel()
    assert bar.state == "working"


def test_confirm_names_the_action(bar):
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", lambda _: None)
    texts = [b.text() for b in panel_buttons(bar)]
    assert texts == ["Yes, send", "Not yet"]


def test_confirm_has_no_enter_shortcut(bar):
    got = []
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", got.append)
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == []


def test_recover_enter_retries(bar):
    got = []
    bar.show_recover("Press “Play” didn't change anything.", got.append)
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == ["retry"]


def test_choice_number_keys_pick(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    QTest.keyClick(bar, Qt.Key.Key_3)
    assert got == ["k3"]


def test_failed_run_offers_retry_until_the_goal_is_edited(bar):
    bar.input.setText("turn on Live Caption")
    bar.set_running(True)
    bar.set_running(False)
    bar.show_result(False)
    assert "Retry" in bar.go.text()
    QTest.keyClicks(bar.input, "!")
    assert bar.go.text() == "Go"


def test_successful_run_keeps_go(bar):
    bar.input.setText("x")
    bar.set_running(True)
    bar.set_running(False)
    bar.show_result(True)
    assert bar.go.text() == "Go"


def test_target_chip_shows_the_app(bar):
    from nudge.core.models import AppRef

    bar.set_target(AppRef("Google Chrome", 4242))
    assert bar.target.text.text() == "in Google Chrome"
    bar.set_target(None)
    assert bar.target.text.text() == "no app selected"


def test_hint_is_hidden_during_a_run_unless_asked(bar):
    bar.set_running(True)
    bar.set_status("Peek: 12 controls")
    assert not bar.hint.isVisible()
    bar.set_status("Listening: open settings", during_run=True)
    assert bar.hint.isVisible()
    bar.set_running(False)
    bar.set_status("Add TYPESAFE_API_KEY to .env", tone="warn")
    assert bar.hint.isVisible()


def test_step_count_shows_in_the_hint(bar):
    bar.set_running(True)
    bar.set_step(3)
    assert bar.hint.isVisible() and bar.hint.text().startswith("Step 3 of 12")
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_bar.py -q`
Expected: FAIL with `TypeError: Bar.__init__() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Add theme styles**

In `nudge/ui/theme.py`, append inside `STYLE` (before the closing `"""`):

```python
QFrame#card {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; }}
QPushButton[kind="stop"] {{ background: transparent; border: 1px solid rgba(242,84,91,0.6); color: #F2A0A4; }}
QPushButton[kind="stop"]:hover {{ background: rgba(242,84,91,0.14); }}
QPushButton[kind="link"] {{ background: transparent; border: none; color: {MUTED.name()}; padding: 10px 6px; }}
QPushButton[kind="link"]:hover {{ color: {TEXT.name()}; }}
QPushButton[kind="choice"] {{ text-align: left; padding: 0; }}
```

and delete the old `QPushButton[kind="choice"] {{ text-align: left; padding: 14px 18px; }}` line (the new choice button lays out its own labels).

- [ ] **Step 4: Rewrite the bar**

Replace `nudge/ui/bar.py` with:

```python
from __future__ import annotations

import math
import re
import sys
import time
from typing import Callable

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ..core.models import AppRef
from ..core.safety import MAX_STEPS
from ..core.spoken import match_choice, match_intent
from ..vision.screen import exclude_from_capture
from . import theme
from .feed import Feed
from .icons import actor_icon
from .orb import Orb
from .timeline import Timeline

WIDTH = 760
HOTKEY = "⌘⇧Space" if sys.platform == "darwin" else "Ctrl+Shift+Space"
GLOW = {"working": theme.BLUE, "waiting": theme.AMBER, "success": theme.GREEN}
QUOTED = re.compile(r"“(.+?)”")


def _button(text: str, kind: str = "", min_width: int = 0) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setFont(theme.font(16, QFont.Weight.DemiBold))
    b.setMinimumHeight(48)
    if min_width:
        b.setMinimumWidth(min_width)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _label(text: str = "", size: int = 16, muted: bool = False, weight=QFont.Weight.Normal) -> QLabel:
    l = QLabel(text)
    l.setFont(theme.font(size, weight))
    l.setWordWrap(True)
    if muted:
        l.setProperty("muted", "true")
    return l


class TargetChip(QWidget):
    def __init__(self):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 12, 4)
        row.setSpacing(6)
        self.icon = QLabel()
        self.icon.setFixedSize(16, 16)
        self.text = _label("", 13, weight=QFont.Weight.DemiBold)
        self.text.setWordWrap(False)
        row.addWidget(self.icon)
        row.addWidget(self.text)
        self.setToolTip("The app Nudge will act in. Click into another app to change it.")
        self.set(None)

    def set(self, app: AppRef | None) -> None:
        self.warn = app is None
        self.text.setText(f"in {app.name}" if app else "no app selected")
        self.text.setStyleSheet(f"color: {'#FFD58A' if self.warn else theme.TEXT.name()};")
        self.icon.setVisible(app is not None)
        if app is not None:
            self.icon.setPixmap(actor_icon("app", app, 16))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(245, 165, 36, 40) if self.warn else QColor(255, 255, 255, 16))
        box = QRectF(self.rect())
        p.drawRoundedRect(box, box.height() / 2, box.height() / 2)


class ChoiceButton(QPushButton):
    def __init__(self, number: int, label: str, probability: float):
        super().__init__()
        self.setProperty("kind", "choice")
        self.setMinimumHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(12)
        parts = [_label(str(number), 16, weight=QFont.Weight.Bold), _label(label, 16), _label(f"{probability:.0%}", 14, muted=True)]
        parts[0].setStyleSheet(f"color: {theme.BLUE.name()};")
        for i, part in enumerate(parts):
            part.setWordWrap(False)
            part.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(part, 1 if i == 1 else 0)


class Bar(QWidget):
    go_requested = Signal(str)
    stop_requested = Signal()
    quit_requested = Signal()
    panel_closed = Signal()
    peek_toggled = Signal(bool)

    def __init__(self, timeline: Timeline):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        super().__init__(None, flags)
        self.setObjectName("bar")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setStyleSheet(theme.STYLE)
        self.setFixedWidth(WIDTH)
        self._drag: QPoint | None = None
        self._anchor_bottom = QGuiApplication.primaryScreen().availableGeometry().bottom() - 40
        self._enter_action: Callable[[], None] | None = None
        self._number_actions: list[Callable[[], None]] = []
        self.spoken: Callable[[str], bool] | None = None  # answers the open prompt from speech; True if it understood
        self.running = False
        self.state = "idle"
        self._retry_goal: str | None = None
        self._glow = 0.0
        self._glow_kind = "working"
        self._flash_until = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(33)
        self._glow_timer.timeout.connect(self._tick_glow)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = _label("Nudge", 15, weight=QFont.Weight.Bold)
        title.setWordWrap(False)
        self.target = TargetChip()
        header.addWidget(title)
        header.addWidget(self.target)
        header.addStretch(1)
        self.peek = QPushButton("Peek")
        self.peek.setCheckable(True)
        self.peek.setToolTip("Show everything Nudge can see on screen (blue: accessibility, green: text fields, orange: vision)")
        self.peek.setFixedHeight(30)
        self.peek.setStyleSheet(
            "QPushButton { padding:0 12px; border-radius:15px; font-size:12px; }"
            f"QPushButton:checked {{ background:{theme.AMBER.name()}; color:#1b1300; border:none; }}"
        )
        self.peek.toggled.connect(self.peek_toggled.emit)
        header.addWidget(self.peek)
        close = QPushButton("✕")
        close.setToolTip("Quit Nudge")
        close.setFixedSize(30, 30)
        close.setStyleSheet("padding:0; border-radius:15px; font-size:13px;")
        close.clicked.connect(self.quit_requested.emit)
        header.addWidget(close)
        root.addLayout(header)

        self.feed = Feed(timeline)
        root.addWidget(self.feed)

        self.panel = QFrame()
        self.panel.setObjectName("card")
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(16, 14, 16, 16)
        self.panel_layout.setSpacing(10)
        self.panel.hide()
        root.addWidget(self.panel)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.orb = Orb()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask Nudge…  e.g. turn on Live Caption")
        self.input.setFont(theme.font(20))
        self.input.setMinimumHeight(54)
        self.input.returnPressed.connect(self._go)
        self.input.textEdited.connect(self._on_edited)
        self.mic_slot = QHBoxLayout()
        self.go = _button("Go", "primary", 112)
        self.go.setMinimumHeight(54)
        self.go.clicked.connect(self._go)
        self.stop = _button("Stop", "stop", 112)
        self.stop.setMinimumHeight(54)
        self.stop.clicked.connect(self.stop_requested.emit)
        self.stop.hide()
        row.addWidget(self.orb)
        row.addWidget(self.input, 1)
        row.addLayout(self.mic_slot)
        row.addWidget(self.go)
        row.addWidget(self.stop)
        root.addLayout(row)

        self.hint = _label("", 13, muted=True)
        root.addWidget(self.hint)
        self.set_status(f"Click into an app, then press {HOTKEY} or type here.")

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._escape)
        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.quit_requested.emit)
        timeline.subscribe(lambda *_: self._resize())

        self.adjustSize()
        self._place()

    # window chrome

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(10, 8, -10, -12)
        for i in range(8, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 6))
            p.drawRoundedRect(card.adjusted(-i, -i + 3, i, i + 3), 24 + i, 24 + i)
        path = QPainterPath()
        path.addRoundedRect(card, 24, 24)
        p.fillPath(path, theme.PANEL)
        p.setPen(QPen(theme.LINE, 1))
        p.drawPath(path)
        if self._glow > 0.01:
            pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 2 * math.pi / 1.6) if self._glow_kind == "working" else 1.0
            base = QColor(GLOW[self._glow_kind])
            for width, share in ((7, 0.22), (2, 1.0)):
                color = QColor(base)
                color.setAlpha(int(self._glow * (140 + 80 * pulse) * share))
                p.setPen(QPen(color, width))
                p.drawPath(path)

    def _set_state(self, state: str) -> None:
        self.state = state
        if state in GLOW:
            self._glow_kind = state
        self._glow_timer.start()

    def _tick_glow(self) -> None:
        flashing = time.monotonic() < self._flash_until
        target = 1.0 if self.state in ("working", "waiting") or flashing else 0.0
        self._glow += (target - self._glow) * 0.25
        if target == 0.0 and self._glow < 0.01:
            self._glow = 0.0
            self._glow_timer.stop()
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa":
            from .mac_window import float_over_everything

            float_over_everything(self, level=101)
        exclude_from_capture(self)

    def _place(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._anchor_bottom = screen.bottom() - 40
        self.move(screen.center().x() - self.width() // 2, self._anchor_bottom - self.height())

    def _screen_area(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _keep_anchored(self) -> None:
        """The bar grows upward from where its bottom edge sits, and never leaves the screen."""
        area = self._screen_area()
        bottom = min(self._anchor_bottom, area.bottom())
        y = max(area.top(), bottom - self.height())
        x = min(max(self.x(), area.left()), area.right() - self.width())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._drag is None:
            self._keep_anchored()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e) -> None:
        if self._drag is not None:
            self._anchor_bottom = self.geometry().bottom()
        self._drag = None

    def _resize(self) -> None:
        self.adjustSize()
        self._keep_anchored()

    def summon(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        if not self.running:
            self.input.setFocus()
            self.input.selectAll()

    # state

    def _go(self) -> None:
        text = self.input.text().strip()
        if text and not self.running:
            self.go_requested.emit(text)

    def _on_edited(self, text: str) -> None:
        if self._retry_goal is not None and text.strip() != self._retry_goal:
            self._retry_goal = None
            self.go.setText("Go")

    def _escape(self) -> None:
        if self.running:
            self.stop_requested.emit()
        else:
            self.hide()

    def add_mic(self, widget: QWidget) -> None:
        self.mic_slot.addWidget(widget)

    def set_target(self, app: AppRef | None) -> None:
        self.target.set(app)

    def set_running(self, running: bool) -> None:
        self.running = running
        self.go.setVisible(not running)
        self.stop.setVisible(running)
        self.input.setReadOnly(running)
        if running:
            self._retry_goal = None
            self.go.setText("Go")
            self.hint.hide()
        else:
            self.clear_panel()
            self.set_status("")
        self._set_state("working" if running else "idle")
        self._resize()

    def set_status(self, text: str, tone: str = "muted", during_run: bool = False) -> None:
        """The hint line under the input: setup problems, voice state, Peek counts, and the step count."""
        self.hint.setText(text)
        self.hint.setStyleSheet(f"color: {(theme.AMBER if tone == 'warn' else theme.MUTED).name()};")
        self.hint.setVisible(bool(text) and (not self.running or during_run))
        self._resize()

    def set_step(self, step: int) -> None:
        self.set_status(f"Step {step} of {MAX_STEPS} · Esc stops", during_run=True)

    def show_result(self, ok: bool) -> None:
        """The outcome itself is the last feed entry; the bar flashes green, or offers Retry."""
        if ok:
            self._glow_kind = "success"
            self._flash_until = time.monotonic() + 0.9
            self._glow_timer.start()
            return
        self._retry_goal = self.input.text().strip() or None
        if self._retry_goal:
            self.go.setText("↻ Retry")

    # panels

    def clear_panel(self) -> None:
        self._enter_action = None
        self._number_actions = []
        self.spoken = None
        self.panel_closed.emit()
        _clear_layout(self.panel_layout)
        self.panel.hide()
        if self.running:
            self._set_state("working")
        self._resize()

    def _open_panel(self, title: str, tone: str = "", detail: str = "") -> None:
        self.clear_panel()
        heading = _label(title, 17, weight=QFont.Weight.DemiBold)
        if tone == "warn":
            heading.setStyleSheet(f"color: {theme.AMBER.name()};")
        self.panel_layout.addWidget(heading)
        if detail:
            self.panel_layout.addWidget(_label(detail, 14, muted=True))
        self.panel.show()
        if self.running:
            self._set_state("waiting")

    def _finish_panel(self, focus: QWidget | None = None) -> None:
        self._resize()
        self.summon()
        if focus is not None:
            focus.setFocus()

    def _buttons(self, specs: list[tuple[str, str, Callable[[], None]]]) -> list[QPushButton]:
        row = QHBoxLayout()
        row.setSpacing(10)
        made = []
        for text, kind, callback in specs:
            b = _button(text, kind)
            b.clicked.connect(lambda _=False, cb=callback: self._answer(cb))
            row.addWidget(b, 0 if kind == "link" else 1)
            made.append(b)
        self.panel_layout.addLayout(row)
        return made

    def _answer(self, callback: Callable[[], None]) -> None:
        self.clear_panel()
        callback()

    def _typing(self) -> bool:
        focus = self.focusWidget()
        return isinstance(focus, QPlainTextEdit) or (isinstance(focus, QLineEdit) and not focus.isReadOnly())

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._enter_action and not isinstance(self.focusWidget(), QPlainTextEdit):
            action, self._enter_action = self._enter_action, None
            self._answer(action)
            return
        index = e.key() - int(Qt.Key.Key_1)
        if self._number_actions and 0 <= index < len(self._number_actions) and not self._typing():
            self._answer(self._number_actions[index])
            return
        super().keyPressEvent(e)

    def show_choice(self, reason: str, options: list[tuple[str, str, float]], reply: Callable[[object], None]) -> None:
        self._open_panel(reason)
        first = None
        for number, (key, label, prob) in enumerate(options, 1):
            b = ChoiceButton(number, label, prob)
            pick = lambda k=key: reply(k)
            b.clicked.connect(lambda _=False, act=pick: self._answer(act))
            self._number_actions.append(pick)
            self.panel_layout.addWidget(b)
            first = first or b

        def spoken(text: str) -> bool:
            match = match_choice(text, [label for _, label, _ in options])
            if match is None:
                return False
            self._answer(lambda: reply(None if match == "stop" else options[match][0]))
            return True

        self.spoken = spoken
        self._finish_panel(first)

    def show_draft(self, note: str, fields: list[tuple[str, str, str]], reply: Callable[[object], None]) -> None:
        self._open_panel("Check what I'll type", detail=note)
        editors: dict[str, QLineEdit | QPlainTextEdit] = {}
        first = None
        for field_id, label, text in fields:
            self.panel_layout.addWidget(_label(label, 13, muted=True))
            multiline = "body" in label.lower() or "message" in label.lower() or len(text) > 80
            if multiline:
                editor = QPlainTextEdit(text)
                editor.setFont(theme.font(16))
                editor.setFixedHeight(130)
            else:
                editor = QLineEdit(text)
                editor.setFont(theme.font(16))
                editor.setMinimumHeight(44)
                if not text:
                    editor.setPlaceholderText("Left blank. Type it here if needed")
            editors[field_id] = editor
            self.panel_layout.addWidget(editor)
            first = first or editor

        def values() -> dict[str, str]:
            return {fid: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text()) for fid, e in editors.items()}

        approve = lambda: reply(values())
        self._buttons([("Type it", "primary", approve)])
        self._enter_action = approve
        self.spoken = self._yes_or_stop(approve, lambda: reply(None))
        self._finish_panel(first)

    def show_url(self, url: str | None, fallback: str, reply: Callable[[object], None]) -> None:
        self._open_panel("Open this address?" if url else "I'm not sure of the address. Search for this instead?")
        editor = QLineEdit(url or fallback)
        editor.setFont(theme.font(17))
        editor.setMinimumHeight(48)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Open", "primary", go)])
        self._enter_action = go
        self.spoken = self._yes_or_stop(go, lambda: reply(None))
        self._finish_panel(editor)

    def show_confirm(self, message: str, reply: Callable[[object], None]) -> None:
        question, _, rest = message.partition("? ")
        title = f"{question}?" if rest else message
        detail = rest[:1].upper() + rest[1:] if rest else ""
        quoted = QUOTED.search(question)
        yes = f"Yes, {quoted.group(1).lower()}" if quoted else "Yes, do it"
        self._open_panel(title, tone="warn", detail=detail)
        self._buttons([(yes, "warn", lambda: reply(True)), ("Not yet", "", lambda: reply(False))])
        self.spoken = self._intents({"stop": lambda: reply(False), "no": lambda: reply(False), "yes": lambda: reply(True)})
        self._finish_panel(None)

    def show_recover(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        retry = lambda: reply("retry")
        first, *_ = self._buttons([
            ("↻ Retry", "primary", retry),
            ("Click it instead", "", lambda: reply("click")),
            ("Pick another…", "link", lambda: reply("other")),
        ])
        self._enter_action = retry
        self.spoken = self._intents({
            "stop": lambda: reply("stop"),
            "retry": retry,
            "click": lambda: reply("click"),
            "other": lambda: reply("other"),
        })
        self._finish_panel(first)

    def show_ask(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        editor = QLineEdit()
        editor.setPlaceholderText("Optional: add a detail")
        editor.setFont(theme.font(16))
        editor.setMinimumHeight(46)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Continue", "primary", go)])
        self._enter_action = go
        intents = self._intents({"stop": lambda: reply(None), "yes": go, "no": go})

        def spoken(text: str) -> bool:
            if not intents(text):  # anything else is the detail they were asked for
                editor.setText(text)
                self._answer(go)
            return True

        self.spoken = spoken
        self._finish_panel(editor)

    def _intents(self, actions: dict[str, Callable[[], None]]) -> Callable[[str], bool]:
        def spoken(text: str) -> bool:
            intent = match_intent(text, tuple(actions))
            if intent is None:
                return False
            self._answer(actions[intent])
            return True

        return spoken

    def _yes_or_stop(self, yes: Callable[[], None], stop: Callable[[], None]) -> Callable[[str], bool]:
        return self._intents({"stop": stop, "no": stop, "yes": yes})


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if widget := item.widget():
            widget.hide()
            widget.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
            item.layout().deleteLater()
```

Note: `summon()` and `_finish_panel()` above match the current `main` versions exactly (`activateWindow()` always; focus only when not running). Don't fold in the discarded "don't steal focus during a run" change here; it's a separate behaviour change.

- [ ] **Step 5: Run the bar tests**

Run: `uv run pytest tests/test_bar.py -q`
Expected: all pass, including every Task 1 test unchanged apart from the fixture.

- [ ] **Step 6: Update the controller for the bar's API**

In `nudge/__main__.py`:

Add the import:

```python
from .ui.timeline import RunRecorder, Timeline
```

In `Nudge.__init__`, replace `self.bar = Bar()` with:

```python
        self.timeline = Timeline()
        self.recorder = RunRecorder(self.timeline)
        self.bar = Bar(self.timeline)
```

Delete these two lines:

```python
        self.bar.set_jev_idle(jev is not None)
        self.bar.set_gemini("off" if writer is None else "idle")
```

Replace the two `writer` signal connections with no-ops for now (Task 8 wires the recorder):

```python
        b.sig_writer_started.connect(lambda: None)
        b.sig_writer_used.connect(lambda ms: None)
```

Change `set_target`:

```python
    def set_target(self, app: AppRef) -> None:
        self.target = app
        self.bar.set_target(app)
```

In `start()`, delete `self.bar.set_timing({})` and `self.bar.set_gemini(...)`.

Change `on_observed`, `on_vision`, and `on_decided` to stop calling removed bar methods:

```python
    def on_observed(self, snapshot: Snapshot) -> None:
        if self.debug:
            self.overlay.show_boxes(snapshot.controls)

    def on_vision(self, milliseconds: int, found: int) -> None:
        pass

    def on_decided(self, step: int, decision: JevDecision, labels: dict[str, str]) -> None:
        self.last_jev_ms = decision.milliseconds
        self.bar.set_step(step)
```

In `on_peeked`, replace the `set_timing` + `set_status` pair with one hint:

```python
    def on_peeked(self, payload) -> None:
        snapshot, vision_ms = payload
        if not self.debug or self.running:
            return
        self.overlay.show_boxes(snapshot.controls)
        vision = sum(c.source == "vision" for c in snapshot.controls)
        found = f"{len(snapshot.controls) - vision} from the accessibility tree" + (f", {vision} from vision" if vision_ms is not None else "")
        timing = f"screen {snapshot.elapsed_ms} ms" + (f", vision {vision_ms} ms" if vision_ms is not None else "")
        self.bar.set_status(f"Peek: {found} in {snapshot.app.name} · {timing}")
```

In `on_finished`, replace the body with:

```python
    def on_finished(self, ok: bool, message: str) -> None:
        self.bar.set_running(False)
        self.bar.show_result(ok)
        self.bar.set_status(message, tone="muted" if ok else "warn")
        self.overlay.flash(message, ok)
```

(The status line keeps showing the result until Task 8 moves it into the feed.)

Delete the now-unused `self.timing: dict[str, int] = {}` line in `__init__`. Keep the `safety` import (`_peek_loop` uses `safety.SPARSE_TREE` and `on_propose` uses `safety.consequential_word`).

- [ ] **Step 7: Smoke-test the app offline**

Run: `uv run nudge --offline live_caption`, then press Go.
Expected: the bar shows the orb, a Chrome chip, the goal; the border glows blue during the run; four presses happen; the result shows under the input; Go returns. Then run `uv run nudge --offline gmail`: the draft card has "Type it" and no Stop; the Send card shows "Yes, send" and "Not yet" in amber. Quit with ✕.

- [ ] **Step 8: Run the full suite and commit**

Run: `uv run pytest -q`
Expected: all pass.

```bash
git add nudge/ui/bar.py nudge/ui/theme.py nudge/__main__.py tests/test_bar.py
scripts/commit.sh "feat(ui): redesign the bar around the feed, orb, and one Stop" "" "- target chip with the app's icon; badges move into feed tooltips" "- blue glow while working, amber while waiting, green flash on success" "- question cards without Stop; named confirm buttons; Retry first" "- Retry after a failed run, number keys for choices, hint line"
```

---

### Task 8: Feed the timeline from the run, and an end-to-end test

**Files:**
- Modify: `nudge/__main__.py`
- Modify: `nudge/ui/overlay.py` (remove `flash`)
- Create: `tests/test_app.py`

**Interfaces:**
- Consumes: `RunRecorder` methods (Task 3); `Bridge.sig_acted`, `sig_switched` (Task 2); `Bar.set_step`, `show_result`, `orb`, `set_status(during_run=…)` (Task 7).
- Produces: `Nudge.prompt(show, *args, said: str = "", feed: str = "")`; `Nudge.sync_orb()`; `Nudge.on_switched(app)`; `Nudge.timeline`, `Nudge.recorder`.

- [ ] **Step 1: Write the failing end-to-end tests**

Create `tests/test_app.py`:

```python
import time

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


class StubHotkeys(QObject):
    summon = Signal()
    escape = Signal()


def wait_until(condition, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def offline(qapp, monkeypatch):
    import nudge.__main__ as main
    from nudge.dev import GOALS, PATHS, OfflineJev, OfflineWriter
    from nudge.platform.fake import FakeAdapter

    monkeypatch.setattr(main, "Hotkeys", StubHotkeys)
    made = []

    def make(fixture):
        adapter = FakeAdapter.from_fixture(fixture)
        app = main.Nudge(adapter, OfflineJev(PATHS[fixture]), OfflineWriter(), offline_goal=GOALS[fixture])
        made.append(app)
        return app, adapter, GOALS[fixture]

    yield make
    for app in made:
        if app.running:
            app.bridge.cancel()
            app.worker.wait(3000)
        app.bar.close()
        app.overlay.close()


def finished(app):
    entries = app.timeline.entries
    return not app.running and entries and entries[-1].actor == "nudge" and entries[-1].state != "waiting"


def test_offline_live_caption_run_fills_the_feed(offline):
    app, adapter, goal = offline("live_caption")
    app.start(goal)
    assert wait_until(lambda: finished(app))
    entries = app.timeline.entries
    assert entries[0].actor == "you" and entries[0].verb == goal
    assert [e.subject for e in entries if e.actor == "app"] == ["Chrome", "Settings", "Accessibility", "Live Caption"]
    assert entries[-1].state == "done" and entries[-1].verb.startswith("Done in 4 steps")
    assert app.bar.go.isVisible() and app.bar.go.text() == "Go" and app.bar.state == "idle"
    assert len(app.bar.feed.rows) == len(entries)


def test_offline_gmail_run_answers_prompts_by_voice(offline):
    app, adapter, goal = offline("gmail")
    app.start(goal)

    def answer_and_check():
        if app.bar.spoken is not None:
            app.bar.spoken("yes")
        return finished(app)

    assert wait_until(answer_and_check)
    assert adapter.screen == "sent"
    verbs = [e.verb for e in app.timeline.entries]
    assert "Wrote the text" in verbs and "Waiting for your OK" in verbs


def test_stopping_mid_run_marks_the_feed_and_offers_retry(offline):
    app, adapter, goal = offline("live_caption")
    app.start(goal)
    assert wait_until(lambda: any(e.actor == "app" for e in app.timeline.entries))
    app.stop()
    assert wait_until(lambda: finished(app))
    assert app.timeline.entries[-1].state == "failed"
    assert "Retry" in app.bar.go.text()
```

- [ ] **Step 2: Run them to see what fails**

Run: `uv run pytest tests/test_app.py -q`
Expected: FAIL. The feed stays empty (nothing feeds the recorder yet), so `entries[0]` raises `IndexError`, or `wait_until` returns False.

- [ ] **Step 3: Wire the recorder and the orb in the controller**

In `nudge/__main__.py`, replace the bridge wiring block in `Nudge.__init__` (from `b = self.bridge` to `b.sig_finished.connect(self.on_finished)`) with:

```python
        b = self.bridge
        b.sig_status.connect(self.recorder.status)
        b.sig_observed.connect(self.on_observed)
        b.sig_vision.connect(self.recorder.vision_used)
        b.sig_decided.connect(self.on_decided)
        b.sig_writer_started.connect(self.recorder.writer_started)
        b.sig_writer_used.connect(self.recorder.writer_used)
        b.sig_propose.connect(self.on_propose)
        b.sig_acted.connect(self.recorder.acted)
        b.sig_switched.connect(self.on_switched)
        b.sig_hold.connect(self.overlay.start_hold)
        self.bar.panel_closed.connect(self.on_panel_closed)
        b.sig_choose.connect(lambda reason, options: self.prompt(self.bar.show_choice, reason, options, b.reply, said=spoken_choice(reason, options), feed="Pick the next step below"))
        b.sig_draft.connect(lambda note, fields: self.prompt(self.bar.show_draft, note, fields, b.reply, said="Check what I'll type, then say yes to type it, or stop.", feed="Check the text before I type it"))
        b.sig_url.connect(lambda url, fallback: self.prompt(self.bar.show_url, url, fallback, b.reply, said="Open this address?" if url else "I'm not sure of the address. Search for this instead?", feed="Check the address"))
        b.sig_confirm.connect(lambda message: self.prompt(self.bar.show_confirm, message, b.reply, said=message, feed="Waiting for your OK"))
        b.sig_recover.connect(lambda message: self.prompt(self.bar.show_recover, message, b.reply, said=message, feed="That didn't work. What next?"))
        b.sig_ask.connect(lambda message: self.prompt(self.bar.show_ask, message, b.reply, said=message, feed="Waiting for your help"))
        b.sig_finished.connect(self.on_finished)
```

Replace `prompt`:

```python
    def prompt(self, show, *args, said: str = "", feed: str = "") -> None:
        """Show a question, read it aloud, then listen for the answer by voice as well."""
        show(*args)
        if feed and self.running:
            self.recorder.waiting(feed)  # after show(): opening a panel closes the previous one, which settles waits
        if self.voice is None:
            return
        if self.speaker is not None and said:
            if self.wake is not None:
                self.wake.pause()  # don't let the speaker trigger the wake word
            self.speaker.say(said)
        else:
            self.voice.listen()
        self.sync_orb()
```

Add `self.sync_orb()` as the last line of `on_spoken_prompt` and of `on_voice_state` (before its early `return` too, so put it first):

```python
    def on_voice_state(self, state: str) -> None:
        self.sync_orb()
        if self.wake is not None:
            self.wake.pause() if state == "listening" else self.wake.start()
        if self.running and self.bar.spoken is None:
            return
        messages = {
            "listening": "Listening… say your request.",
            "idle": "",
            "timeout": "Didn't hear anything. Press the hotkey to try again.",
            "no_mic": "No microphone found, so voice is off.",
        }
        text = messages.get(state, f"Voice is off ({state.removeprefix('error: ')}).")
        self.bar.set_status(text, tone="warn" if state not in messages or state == "no_mic" else "muted", during_run=True)
```

Change the `heard` connection (in the `if voice is not None:` block) to keep the transcript visible while answering during a run:

```python
            voice.heard.connect(lambda text: self.bar.set_status(f"Listening: {text}", during_run=True))
```

Add `on_panel_closed`'s recorder call:

```python
    def on_panel_closed(self) -> None:
        self.recorder.answered()
        if self.speaker is not None:
            self.speaker.stop()
        if self.voice is not None and self.running:
            self.voice.cancel()
        self.sync_orb()
```

Add the orb and app-switch helpers:

```python
    def sync_orb(self) -> None:
        if self.speaker is not None and self.speaker.speaking:
            mode = "speaking"
        elif self.voice is not None and self.voice.active:
            mode = "listening"
        elif self.running:
            mode = "thinking"
        else:
            mode = "idle"
        self.bar.orb.set_mode(mode)

    def on_switched(self, app: AppRef) -> None:
        self.bar.set_target(app)
        self.recorder.switched(app)
```

In `start()`, after `self.bar.set_running(True)`:

```python
        self.recorder.started(goal, self.target)
        self.sync_orb()
```

Change `on_decided`:

```python
    def on_decided(self, step: int, decision: JevDecision, labels: dict[str, str]) -> None:
        self.last_jev_ms = decision.milliseconds
        self.recorder.decided(decision, labels)
        self.bar.set_step(step)
```

Change `on_propose` to add the running entry first:

```python
    def on_propose(self, action: Action, target: Control | None) -> None:
        self.recorder.proposed(action)
        warn = action.kind == "press" and safety.consequential_word(action.label) is not None
        bounds = target.bounds if target is not None else None
        if self.debug:
            self.overlay.pick_box(bounds)
        label = f"{action.describe()}  ·  Jev {self.last_jev_ms} ms"
        self.overlay.fly_to(bounds, label, warn=warn, on_landed=lambda: self.bridge.reply(True))
```

Replace `on_finished` (the recorder goes first, so `set_running(False)` closing the panel doesn't mark a cancelled wait as answered):

```python
    def on_finished(self, ok: bool, message: str) -> None:
        self.recorder.finished(ok, message)
        self.bar.set_running(False)
        self.bar.show_result(ok)
        self.overlay.fade()
        self.sync_orb()
```

Delete the `on_vision` method (now unused).

Mark setup problems as warnings. Change these calls to pass `tone="warn"`:
- `self.bar.set_status(problem)` (both in `__init__` and `start()`)
- `self.bar.set_status("Add TYPESAFE_API_KEY to .env to let Jev choose steps, then restart Nudge.")`
- `self.bar.set_status("Jev isn't set up. Add TYPESAFE_API_KEY to .env and restart Nudge.")`
- `self.bar.set_status("Click into the app you want help with first.")`
- `wake.failed.connect(lambda why: self.bar.set_status(f"Wake word is off ({why}).", tone="warn"))`

Change `stop()`'s message so it shows during the run:

```python
            self.bar.set_status("Stopping…", during_run=True)
```

Change `on_voice_request`'s unrecognised-reply message to `during_run=True`:

```python
                self.bar.set_status(f'Heard "{goal}", but not what to do with it. Try again or click.', during_run=True)
```

- [ ] **Step 4: Remove the overlay's result bubble**

In `nudge/ui/overlay.py`, delete the `flash` method (lines `def flash(self, text: str, ok: bool) -> None:` through `self.fade(2200)`). Then confirm nothing else calls it:

Run: `rg -n "\.flash\(" nudge`
Expected: no matches.

- [ ] **Step 5: Run the end-to-end tests**

Run: `uv run pytest tests/test_app.py -q`
Expected: 3 passed (the live caption run takes several seconds because the real hold and step delays apply).

If `test_offline_gmail…` hangs, print `app.bar.panel.isVisible()` and `app.timeline.entries` inside `answer_and_check`. A missing `spoken` means the prompt didn't open; compare `prompt()` with the old version.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 7: Manual offline check**

Run `uv run nudge --offline gmail`, press Go, approve the draft, press "Yes, send".
Expected feed order: You (goal), Jev picked Compose, Chrome pressed Compose, Jev picked "Type into the empty fields", Gemini wrote the text, "Check the text before I type it" ✓, typing entry, Jev picked Send, pressing Send, "Waiting for your OK" ✓, pressed Send ✓, Jev says done, "Done in 3 steps". The orb swirls while working and breathes after.

- [ ] **Step 8: Commit**

```bash
git add nudge/__main__.py nudge/ui/overlay.py tests/test_app.py
scripts/commit.sh "feat(ui): feed the timeline from live runs" "" "- recorder wired to every bridge signal, including acted and switched" "- prompts add a waiting entry that settles when answered" "- orb follows speaking, listening, and running" "- result lives in the feed; overlay just fades" "- end-to-end offline tests for Live Caption, Gmail, and Stop"
```

---

### Task 9: Mic menu, input device, mutes, and orb levels

**Files:**
- Create: `nudge/ui/levels.py`, `nudge/ui/audio_settings.py`, `nudge/ui/mic.py`
- Modify: `nudge/ui/voice.py`, `nudge/ui/speaker.py`, `nudge/ui/wake.py`, `nudge/ui/theme.py`, `nudge/__main__.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Consumes: `svg_pixmap` (Task 4); `Bar.add_mic`, `Bar.orb` (Task 7); `Nudge.sync_orb` (Task 8).
- Produces:
  - `rms_level(pcm: bytes) -> float` (0..1), `envelope(pcm: bytes, rate: int, window_ms: int = 30) -> list[float]`.
  - `AudioSettings(store: QSettings | None = None)` with signal `changed`, properties `mic_muted`, `voice_muted`, `sounds_muted` (bool), setters `set_mic_muted(bool)`, `set_voice_muted(bool)`, `set_sounds_muted(bool)`, `input_device() -> QAudioDevice`, `set_input(device: QAudioDevice | None)`, attribute `missing_saved_input: bool`.
  - `MicButton(settings: AudioSettings)` (a `QToolButton`), `.menu_: QMenu`, `._rebuild()`.
  - `Voice(api_key, settings=None)` with new signal `level(float)` and state `"muted"`; `Speaker.level(float)`; `WakeWord(model, threshold=0.5, settings=None)`.
  - `Nudge(..., audio: AudioSettings | None = None)`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_audio.py`:

```python
import numpy as np
import pytest
from PySide6.QtCore import QSettings


@pytest.fixture
def settings(qapp, tmp_path):
    from nudge.ui.audio_settings import AudioSettings

    return AudioSettings(QSettings(str(tmp_path / "nudge.ini"), QSettings.Format.IniFormat))


def tone(amplitude, samples=1600):
    return (np.sin(np.linspace(0, 40 * np.pi, samples)) * amplitude * 32767).astype("<i2").tobytes()


def test_rms_level_is_zero_for_silence_and_rises_with_volume():
    from nudge.ui.levels import rms_level

    assert rms_level(b"") == 0.0
    assert rms_level(tone(0.0)) == 0.0
    assert 0 < rms_level(tone(0.05)) < rms_level(tone(0.2)) <= 1.0


def test_envelope_has_one_value_per_window():
    from nudge.ui.levels import envelope

    pcm = tone(0.2, samples=24000)  # one second at 24 kHz
    assert len(envelope(pcm, 24000, 30)) == 34


def test_settings_round_trip(settings, tmp_path):
    from nudge.ui.audio_settings import AudioSettings

    changes = []
    settings.changed.connect(lambda: changes.append(True))
    settings.set_mic_muted(True)
    settings.set_voice_muted(True)
    settings.set_sounds_muted(True)
    again = AudioSettings(QSettings(str(tmp_path / "nudge.ini"), QSettings.Format.IniFormat))
    assert again.mic_muted and again.voice_muted and again.sounds_muted
    assert len(changes) == 3


def test_setting_the_same_value_twice_emits_once(settings):
    changes = []
    settings.changed.connect(lambda: changes.append(True))
    settings.set_mic_muted(True)
    settings.set_mic_muted(True)
    assert len(changes) == 1


def test_missing_saved_input_falls_back_to_default(settings):
    from PySide6.QtMultimedia import QMediaDevices

    settings._store.setValue("audio/input", "deadbeef")
    device = settings.input_device()
    assert device.id() == QMediaDevices.defaultAudioInput().id()
    assert settings.missing_saved_input is True
    settings.set_input(None)
    settings.input_device()
    assert settings.missing_saved_input is False


def test_muted_voice_never_opens_the_mic(settings):
    from nudge.ui.voice import Voice

    voice = Voice("key", settings)
    states = []
    voice.state.connect(states.append)
    settings.set_mic_muted(True)
    voice.listen()
    assert states == ["muted"] and not voice.active


def test_mic_button_toggles_mute_and_lists_toggles(settings):
    from nudge.ui.mic import MicButton

    button = MicButton(settings)
    button.click()
    assert settings.mic_muted
    button._rebuild()
    texts = [a.text() for a in button.menu_.actions() if not a.isSeparator()]
    assert {"Mute mic", "Mute Nudge's voice", "Sound effects"} <= set(texts)
    next(a for a in button.menu_.actions() if a.text() == "Sound effects").trigger()
    assert settings.sounds_muted
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_audio.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.levels'`.

- [ ] **Step 3: Implement levels**

Create `nudge/ui/levels.py`:

```python
from __future__ import annotations

import numpy as np

GAIN = 4.0  # speech RMS sits around 0.05 to 0.2 of full scale


def rms_level(pcm: bytes) -> float:
    """Loudness of 16-bit mono PCM, scaled to 0..1 for the orb."""
    samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32)
    if samples.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(samples * samples))) / 32768.0
    return min(1.0, rms * GAIN)


def envelope(pcm: bytes, rate: int, window_ms: int = 30) -> list[float]:
    size = max(1, rate * window_ms // 1000) * 2
    return [rms_level(pcm[i : i + size]) for i in range(0, len(pcm), size)]
```

- [ ] **Step 4: Implement audio settings**

Create `nudge/ui/audio_settings.py`:

```python
from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices


class AudioSettings(QObject):
    """Which microphone to use and what's muted. Remembered between launches."""

    changed = Signal()

    def __init__(self, store: QSettings | None = None):
        super().__init__()
        self._store = store if store is not None else QSettings("Nudge", "Nudge")
        self.missing_saved_input = False

    @property
    def mic_muted(self) -> bool:
        return self._flag("audio/mic_muted")

    @property
    def voice_muted(self) -> bool:
        return self._flag("audio/voice_muted")

    @property
    def sounds_muted(self) -> bool:
        return self._flag("audio/sounds_muted")

    def set_mic_muted(self, on: bool) -> None:
        self._set("audio/mic_muted", bool(on))

    def set_voice_muted(self, on: bool) -> None:
        self._set("audio/voice_muted", bool(on))

    def set_sounds_muted(self, on: bool) -> None:
        self._set("audio/sounds_muted", bool(on))

    def input_device(self) -> QAudioDevice:
        saved = self._store.value("audio/input", "", type=str)
        if saved:
            for device in QMediaDevices.audioInputs():
                if bytes(device.id()).hex() == saved:
                    self.missing_saved_input = False
                    return device
        self.missing_saved_input = bool(saved)
        return QMediaDevices.defaultAudioInput()

    def set_input(self, device: QAudioDevice | None) -> None:
        self._store.setValue("audio/input", bytes(device.id()).hex() if device is not None else "")
        self.changed.emit()

    def _flag(self, key: str) -> bool:
        return self._store.value(key, False, type=bool)

    def _set(self, key: str, value: bool) -> None:
        if self._flag(key) == value:
            return
        self._store.setValue(key, value)
        self.changed.emit()
```

- [ ] **Step 5: Implement the mic button**

Create `nudge/ui/mic.py`:

```python
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QActionGroup, QIcon, QKeySequence
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QMenu, QToolButton

from .audio_settings import AudioSettings
from .icons import svg_pixmap


class MicButton(QToolButton):
    """Click to mute or unmute the mic; the arrow picks a microphone and the other audio toggles."""

    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.setObjectName("mic")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.setFixedHeight(54)
        self.setMinimumWidth(72)
        self.setIconSize(QSize(22, 22))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to mute the mic. Use the arrow to pick a microphone.")
        self.menu_ = QMenu(self)
        self.setMenu(self.menu_)
        self.menu_.aboutToShow.connect(self._rebuild)
        self.clicked.connect(lambda: settings.set_mic_muted(not settings.mic_muted))
        settings.changed.connect(self._refresh)
        self._refresh()
        self._rebuild()

    def _refresh(self) -> None:
        self.setIcon(QIcon(svg_pixmap("mic-off" if self.settings.mic_muted else "mic", 22)))

    def _rebuild(self) -> None:
        menu = self.menu_
        menu.clear()
        heading = menu.addAction("Microphone")
        heading.setEnabled(False)
        group = QActionGroup(menu)
        group.setExclusive(True)
        current = self.settings.input_device()
        for device in QMediaDevices.audioInputs():
            action = menu.addAction(device.description())
            action.setCheckable(True)
            action.setChecked(device.id() == current.id())
            group.addAction(action)
            action.triggered.connect(lambda _=False, d=device: self.settings.set_input(d))
        if self.settings.missing_saved_input:
            note = menu.addAction("Saved mic not found. Using the default")
            note.setEnabled(False)
        menu.addSeparator()
        self._toggle("Mute mic", self.settings.mic_muted, self.settings.set_mic_muted, QKeySequence("Ctrl+M"))
        self._toggle("Mute Nudge's voice", self.settings.voice_muted, self.settings.set_voice_muted)
        self._toggle("Sound effects", not self.settings.sounds_muted, lambda on: self.settings.set_sounds_muted(not on))

    def _toggle(self, text: str, checked: bool, setter: Callable[[bool], None], shortcut: QKeySequence | None = None) -> None:
        action = self.menu_.addAction(text)
        action.setCheckable(True)
        action.setChecked(checked)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.toggled.connect(setter)
```

Append mic and menu styles inside `STYLE` in `nudge/ui/theme.py`:

```python
QToolButton#mic {{ background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 0 22px 0 12px; }}
QToolButton#mic:hover {{ background: rgba(255,255,255,0.14); }}
QToolButton#mic::menu-button {{ border: none; width: 20px; }}
QMenu {{ background: #1A1F2A; color: {TEXT.name()}; border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: rgba(79,142,247,0.22); }}
QMenu::item:disabled {{ color: {MUTED.name()}; }}
QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.08); margin: 4px 6px; }}
```

- [ ] **Step 6: Use the settings and report levels in voice, speaker, and wake word**

`nudge/ui/voice.py`:

```python
# imports: add
from .levels import rms_level

class Voice(QObject):
    state = Signal(str)  # listening | idle | muted | no_mic | error: <detail>
    heard = Signal(str)  # live partial transcript
    request = Signal(str)  # the finished request
    level = Signal(float)  # mic loudness while listening, 0..1

    def __init__(self, api_key: str, settings=None):
        super().__init__()
        self.api_key = api_key
        self.settings = settings
        # (rest unchanged)

    def listen(self) -> None:
        if self.active:
            return
        if self.settings is not None and self.settings.mic_muted:
            self.state.emit("muted")
            return
        device = self.settings.input_device() if self.settings is not None else QMediaDevices.defaultAudioInput()
        # (rest unchanged from `if device.isNull():`)
```

In `_close`, add `self.level.emit(0.0)` as the last line. In `_read_mic`:

```python
    def _read_mic(self) -> None:
        data = bytes(self._io.readAll())
        if data and self.active:
            self._audio.put(data)
            self.level.emit(rms_level(data))
```

`nudge/ui/speaker.py`:

```python
# imports: add
from .levels import envelope

class Speaker(QObject):
    finished = Signal()
    level = Signal(float)  # loudness of what's playing, 0..1

    # in __init__, after self._data = None:
        self._envelope: list[float] = []
        self._meter = QTimer(self)
        self._meter.setInterval(30)
        self._meter.timeout.connect(self._emit_level)
```

In `_play`, after `self._sink.start(self._buffer)`:

```python
        self._envelope = envelope(pcm, SAMPLE_RATE, 30)
        self._meter.start()
```

Add:

```python
    def _emit_level(self) -> None:
        if self._sink is None:
            return
        index = int(self._sink.processedUSecs() / 30000)
        self.level.emit(self._envelope[index] if index < len(self._envelope) else 0.0)
```

At the start of `_release`:

```python
        self._meter.stop()
        self.level.emit(0.0)
```

`nudge/ui/wake.py`:

```python
    def __init__(self, model: str, threshold: float = 0.5, settings=None):
        super().__init__()
        self.settings = settings
        # (rest unchanged)

    def start(self) -> None:
        if self._source is not None:
            return
        if self.settings is not None and self.settings.mic_muted:
            return
        device = self.settings.input_device() if self.settings is not None else QMediaDevices.defaultAudioInput()
        # (rest unchanged from `fmt = QAudioFormat()`)
```

- [ ] **Step 7: Wire it in the controller**

In `nudge/__main__.py`:

```python
# imports: add
from .ui.audio_settings import AudioSettings
```

`Nudge.__init__` gets a new keyword argument `audio: AudioSettings | None = None` (after `speaker=None`), and near the top of the body:

```python
        self.audio = audio if audio is not None else AudioSettings()
        self.audio.changed.connect(self.on_audio_changed)
```

After the existing `if voice is not None:` block's connections, add:

```python
            from .ui.mic import MicButton

            self.bar.add_mic(MicButton(self.audio))
            voice.level.connect(self.bar.orb.set_level)
        if speaker is not None:
            speaker.finished.connect(self.on_spoken_prompt)
            speaker.level.connect(self.bar.orb.set_level)
```

(Merge with the existing `if speaker is not None:` block rather than duplicating it.)

Add the `"muted"` message in `on_voice_state`'s `messages` dict:

```python
            "muted": "Mic is muted. Unmute it with the mic button.",
```

In `prompt`, skip reading aloud when Nudge's voice is muted:

```python
        if self.speaker is not None and said and not self.audio.voice_muted:
```

Add:

```python
    def on_audio_changed(self) -> None:
        if self.audio.mic_muted and self.voice is not None:
            self.voice.cancel()
        if self.audio.voice_muted and self.speaker is not None and self.speaker.speaking:
            self.speaker.stop()
            self.on_spoken_prompt()
        if self.wake is not None:
            self.wake.pause()
            if not (self.voice is not None and self.voice.active):
                self.wake.start()  # re-reads the chosen mic; does nothing while muted
        self.sync_orb()
```

In `main()`, create the settings once and pass them everywhere:

```python
        config = load_config()
        audio = AudioSettings()
        # ...
            voice = Voice(config.elevenlabs_api_key, audio)
        # ...
                wake = WakeWord(config.wake_word, config.wake_threshold, settings=audio)
        # ...
        controller = Nudge(load_adapter(physical_to_logical), jev, writer, vision, debug=args.debug, voice=voice, wake=wake, speaker=speaker, audio=audio)
```

- [ ] **Step 8: Run tests**

Run: `uv run pytest tests/test_audio.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 9: Manual check with voice (needs `ELEVENLABS_API_KEY`)**

Run: `uv run nudge`. Open the mic menu's arrow: your microphones are listed with the current one checked. Pick another and say the wake word; it works through the new mic. Click the mic: the icon crosses out and the hotkey shows "Mic is muted…". Toggle "Mute Nudge's voice": prompts stop being read aloud and the mic opens straight away. Quit and relaunch: the choices are remembered. While Nudge reads a prompt, the orb wobbles with the voice; while you talk, it swells with your voice.

- [ ] **Step 10: Commit**

```bash
git add nudge/ui/levels.py nudge/ui/audio_settings.py nudge/ui/mic.py nudge/ui/voice.py nudge/ui/speaker.py nudge/ui/wake.py nudge/ui/theme.py nudge/__main__.py tests/test_audio.py
scripts/commit.sh "feat(voice): mic picker, mutes, and orb levels" "" "- mic button mutes; its menu picks the input and toggles voice and sounds" "- choices persist with QSettings and fall back to the default mic" "- voice, wake word, and speaker use the chosen mic and report loudness"
```

---

### Task 10: Sound effects

**Files:**
- Create: `nudge/ui/sounds.py`
- Modify: `nudge/__main__.py`
- Test: `tests/test_audio.py` (append)

**Interfaces:**
- Consumes: `AudioSettings.sounds_muted` (Task 9).
- Produces: `TONES: dict[str, list[tuple[float, float]]]` with keys `start`, `tick`, `attention`, `success`, `failure`; `synth(notes) -> bytes` (a WAV file); `Sounds(settings, folder: Path | None = None)` with `.play(name: str)` and `.effects: dict[str, QSoundEffect]`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_audio.py`:

```python
def test_synth_writes_a_short_mono_wav():
    import io
    import wave

    from nudge.ui.sounds import RATE, synth

    with wave.open(io.BytesIO(synth([(880.0, 0.08), (880.0, 0.08)]))) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, RATE)
        assert 0.18 <= w.getnframes() / RATE <= 0.22


def test_sounds_are_generated_once_into_the_folder(settings, tmp_path):
    from nudge.ui.sounds import TONES, Sounds

    folder = tmp_path / "sounds"
    Sounds(settings, folder)
    files = sorted(p.name for p in folder.iterdir())
    assert files == sorted(f"{name}-v1.wav" for name in TONES)
    stamp = (folder / "tick-v1.wav").stat().st_mtime_ns
    Sounds(settings, folder)
    assert (folder / "tick-v1.wav").stat().st_mtime_ns == stamp


def test_muted_sounds_do_not_play(settings, tmp_path):
    from nudge.ui.sounds import Sounds

    played = []

    class Effect:
        def play(self):
            played.append(True)

    sounds = Sounds(settings, tmp_path / "sounds")
    sounds.effects = {"tick": Effect()}
    sounds.play("tick")
    settings.set_sounds_muted(True)
    sounds.play("tick")
    sounds.play("unknown")
    assert played == [True]
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_audio.py -q -k "synth or sounds"`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.sounds'`.

- [ ] **Step 3: Implement sounds**

Create `nudge/ui/sounds.py`:

```python
from __future__ import annotations

import io
import sys
import wave
from pathlib import Path

import numpy as np
from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtMultimedia import QSoundEffect

RATE = 44100
VOLUME = 0.35
VERSION = "v1"  # bump to regenerate cached files after changing TONES
TONES = {
    "start": [(1046.5, 0.06), (1318.5, 0.06)],
    "tick": [(2000.0, 0.015)],
    "attention": [(880.0, 0.08), (880.0, 0.08)],
    "success": [(1046.5, 0.07), (1318.5, 0.07), (1568.0, 0.12)],
    "failure": [(329.6, 0.09), (261.6, 0.14)],
}


def synth(notes: list[tuple[float, float]]) -> bytes:
    """Soft sine notes with a quick attack and exponential decay, as a 16-bit mono WAV."""
    parts = []
    for frequency, seconds in notes:
        t = np.arange(int(RATE * seconds)) / RATE
        shape = np.minimum(1.0, t / 0.003) * np.exp(-t / (seconds / 3))
        parts.append(np.sin(2 * np.pi * frequency * t) * shape)
        parts.append(np.zeros(int(RATE * 0.015)))
    samples = (np.concatenate(parts) * 0.6 * 32767).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(samples)
    return buffer.getvalue()


class Sounds:
    """Short UI sounds for run start, each press, needing you, success, and failure."""

    def __init__(self, settings, folder: Path | None = None):
        self.settings = settings
        self.effects: dict[str, QSoundEffect] = {}
        try:
            folder = folder or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / "sounds"
            folder.mkdir(parents=True, exist_ok=True)
            for name, notes in TONES.items():
                path = folder / f"{name}-{VERSION}.wav"
                if not path.exists():
                    path.write_bytes(synth(notes))
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(VOLUME)
                self.effects[name] = effect
        except Exception as exc:  # sounds are a nicety; never block startup
            print(f"Sound effects are off: {exc}", file=sys.stderr)
            self.effects = {}

    def play(self, name: str) -> None:
        if self.settings.sounds_muted:
            return
        effect = self.effects.get(name)
        if effect is not None:
            effect.play()
```

- [ ] **Step 4: Play them from the controller**

In `nudge/__main__.py`:

```python
# imports: add
from .ui.sounds import Sounds
```

In `Nudge.__init__`, after `self.audio` is set:

```python
        self.sounds = Sounds(self.audio)
```

Replace `b.sig_acted.connect(self.recorder.acted)` with `b.sig_acted.connect(self.on_acted)` and add:

```python
    def on_acted(self, action: Action, changed: bool) -> None:
        self.recorder.acted(action, changed)
        if changed:
            self.sounds.play("tick")
```

In `start()`, after `self.recorder.started(...)`: `self.sounds.play("start")`.
In `prompt()`, after `show(*args)`: `self.sounds.play("attention")`.
In `on_finished()`, after `self.recorder.finished(...)`: `self.sounds.play("success" if ok else "failure")`.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_audio.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Manual check**

Run `uv run nudge --offline gmail` and press Go. You hear: a rising two-note start, a tick per completed step, a double note when the draft card and the Send card appear, and a three-note chime at the end. Press Stop on a second run: a low falling pair. Turn off "Sound effects" in the mic menu (needs a voice key) or set it in the settings file, and the sounds stop.

- [ ] **Step 7: Commit**

```bash
git add nudge/ui/sounds.py nudge/__main__.py tests/test_audio.py
scripts/commit.sh "feat(ui): soft sound effects for run events" "" "- five short tones synthesised once into the cache folder" "- start, each completed step, needs you, success, and failure" "- respects the Sound effects toggle"
```

---

### Task 11: Colored terminal log

**Files:**
- Create: `nudge/ui/console.py`
- Modify: `nudge/__main__.py`
- Test: `tests/test_console.py`

**Interfaces:**
- Consumes: `Timeline`, `Entry`, `RunRecorder` (Task 3).
- Produces: `Console(timeline, stream=None, color: bool | None = None)` with `.format(entry) -> str` and `.banner(features: dict[str, bool])`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_console.py`:

```python
import io

from nudge.core.models import Action, AppRef
from nudge.ui.console import Console
from nudge.ui.timeline import Entry, RunRecorder, Timeline

CHROME = AppRef("Google Chrome", 1)


def console():
    timeline, stream = Timeline(), io.StringIO()
    return timeline, Console(timeline, stream, color=False), stream


def test_prints_settled_entries_once_and_skips_running_ones():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("turn on Live Caption", CHROME)
    recorder.proposed(Action(kind="press", option_key="k", label="Settings"))
    recorder.acted(Action(kind="press", option_key="k", label="Settings"), True)
    recorder.finished(True, "Done in 1 step · 1.2 s · Jev 130 ms per decision")
    assert stream.getvalue().splitlines() == [
        "▶ turn on Live Caption · Google Chrome",
        "  Google Chrome Pressed “Settings”",
        "✓ Done in 1 step · 1.2 s · Jev 130 ms per decision",
    ]


def test_formats_failures_waits_and_details():
    _, out, _ = console()
    assert out.format(Entry("jev", "Picked", "Menu", detail="92% · 130 ms")) == "  Jev       Picked “Menu”  92% · 130 ms"
    assert out.format(Entry("app", "Pressed", "Play", state="failed", detail="nothing changed", app=CHROME)).endswith("nothing changed  ✕")
    assert out.format(Entry("nudge", "Waiting for your OK", state="waiting")).endswith("waiting for you")
    assert out.format(Entry("nudge", "Stopped.", state="failed")) == "✕ Stopped."


def test_a_wait_that_gets_answered_is_not_printed_twice():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("x", CHROME)
    recorder.waiting("Waiting for your OK")
    recorder.answered()
    assert stream.getvalue().count("Waiting for your OK") == 1


def test_clearing_starts_a_fresh_run():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("first", CHROME)
    recorder.started("second", CHROME)
    assert "▶ second" in stream.getvalue()


def test_banner_lists_features():
    _, out, stream = console()
    out.banner({"Jev": True, "Gemini": False})
    assert stream.getvalue().strip() == "Nudge · Jev  Gemini off"


def test_color_is_off_when_not_a_terminal():
    timeline = Timeline()
    assert Console(timeline, io.StringIO()).color is False
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_console.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'nudge.ui.console'`.

- [ ] **Step 3: Implement the console**

Create `nudge/ui/console.py`:

```python
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
```

Note `f"{name:<9}"` pads short names ("Jev" becomes `Jev      `) and lets long app names run on, which is what `test_prints_settled_entries…` expects (`"  Google Chrome Pressed …"`).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_console.py -q`
Expected: all pass. If the padding assertion is off by one, fix the test's expected spacing to match `{name:<9}` plus one space; don't change the width.

- [ ] **Step 5: Start the console with the app**

In `nudge/__main__.py`:

```python
# imports: add
from .ui.console import Console
```

In `Nudge.__init__`, right after the recorder is created:

```python
        self.console = Console(self.timeline)
        self.console.banner({
            "Jev": jev is not None,
            "Gemini": writer is not None,
            "voice": voice is not None,
            "wake word": wake is not None,
            "vision": vision is not None,
        })
```

- [ ] **Step 6: Run the full suite and check the terminal**

Run: `uv run pytest -q`
Expected: all pass.

Run: `uv run nudge --offline live_caption`, press Go.
Expected terminal output: the banner line, `▶ turn on Live Caption · Google Chrome`, alternating Jev / Google Chrome lines with timings, and `✓ Done in 4 steps · …`, in color.

- [ ] **Step 7: Commit**

```bash
git add nudge/ui/console.py nudge/__main__.py tests/test_console.py
scripts/commit.sh "feat(cli): colored live log of each run" "" "- one line per settled timeline entry: who, what, timing" "- startup banner shows which features are on" "- plain text when not a terminal or NO_COLOR is set"
```

---

### Task 12: Docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-10-04-ui-overhaul-design.md` (record what changed during planning)

- [ ] **Step 1: Update the README**

In `README.md`:
- In "You stay in control", replace "**Stop** is always on the bar, and **Esc** stops from anywhere." with "**Stop** is always next to the input, and **Esc** stops from anywhere. The bar glows blue while Nudge works and amber when it needs you."
- Replace "If a step doesn't change anything, Nudge never retries on its own. You choose: try again, click it instead, pick something else, or stop." with "If a step doesn't change anything, Nudge never retries on its own. You choose Retry, Click it instead, or Pick another. After a failed run, Go becomes Retry."
- In "How it works" step 2, replace "The bar shows each step's screen, vision, and Jev time." with "The bar's feed shows each step in order, with who did it (you, Jev, Gemini, the app) and how long it took. The terminal prints the same log."
- In "Limitations", delete "Typed input only. No voice." (voice exists).
- In "Use", add a step after step 2: "With an ElevenLabs key, the mic button next to the input mutes the mic; its arrow picks a microphone and toggles Nudge's voice and sound effects."
- In "For developers", replace "52 tests" with the new count from `uv run pytest -q`.

- [ ] **Step 2: Record planning changes in the spec**

In the spec:
- Under "Animations", replace the bar-height bullet with "Bar height changes are immediate (animating a bottom-anchored frameless window's height caused jitter risk); feed rows fade in over 180 ms." and drop "and slide up 6 px".
- Under "Prompts", in the Confirm bullet, replace "(… amber, Enter)" with "(… amber; no Enter shortcut, so a stray Enter can't send)".
- Under "Bar layout", add to the hint line paragraph: "During a run it shows 'Step N of 12 · Esc stops'."
- Under "Entry model", replace the `TimelineEntry(actor, text, detail, state, ms)` definition with `Entry(actor, verb, subject, state, detail, app)`; the bold part is `subject`.
- Under "Core change", add `switched(app)`.

- [ ] **Step 3: Full verification**

Run: `uv run pytest -q`
Expected: every test passes (54 original plus all new ones).

Run each, press Go, and check the listed behaviour:
- `uv run nudge --offline live_caption`: blue glow, feed with Chrome icon and TypeSafe icon, four ✓ presses, green flash, "Done in 4 steps", sounds, terminal log.
- `uv run nudge --offline gmail`: Gemini icon on "Wrote the text", draft card with "Type it", amber Send card with "Yes, send" / "Not yet", one Stop button throughout.
- Same, but press Stop mid-run: running rows turn ✕ "stopped", the feed ends with "Stopped.", and the button reads "↻ Retry"; editing the goal turns it back to Go.
- `uv run nudge --debug` with real keys in Chrome: Peek counts show on the hint line; a live run shows the real Chrome icon in the chip and feed.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-10-04-ui-overhaul-design.md
scripts/commit.sh "docs: describe the new bar, feed, voice controls, and terminal log"
```

- [ ] **Step 5: Push the branch**

Run: `git push -u origin feat/ui-overhaul`
