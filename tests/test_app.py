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
