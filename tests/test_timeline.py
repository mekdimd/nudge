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
