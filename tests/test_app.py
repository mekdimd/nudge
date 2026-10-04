import time

import pytest
from PySide6.QtCore import QObject, QSettings, Signal
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
def offline(qapp, monkeypatch, tmp_path):
    import nudge.__main__ as main
    from nudge.dev import GOALS, PATHS, OfflineJev, OfflineWriter
    from nudge.platform.fake import FakeAdapter
    from nudge.ui.audio_settings import AudioSettings

    monkeypatch.setattr(main, "Hotkeys", StubHotkeys)
    audio = AudioSettings(QSettings(str(tmp_path / "nudge.ini"), QSettings.Format.IniFormat))
    audio.set_sounds_muted(True)
    made = []

    def make(fixture, **extra):
        adapter = FakeAdapter.from_fixture(fixture)
        app = main.Nudge(adapter, OfflineJev(PATHS[fixture]), OfflineWriter(), offline_goal=GOALS[fixture], audio=audio, **extra)
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


class FakeVoice(QObject):
    state = Signal(str)
    heard = Signal(str)
    request = Signal(str)
    level = Signal(float)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.active = False

    def listen(self):
        if self.active:
            return
        if self.settings.mic_muted:
            self.state.emit("muted")
            return
        self.active = True
        self.state.emit("listening")

    def cancel(self, timed_out=False):
        if self.active:
            self.active = False
            self.state.emit("idle")


def with_voice(offline):
    app, _, _ = offline("live_caption", voice=FakeVoice(None))
    app.voice.settings = app.audio
    return app


def test_talk_button_starts_and_stops_listening(offline):
    app = with_voice(offline)
    app.bar.mic.talk.click()
    assert app.voice.active and app.bar.mic.talk.isChecked() and app.bar.orb.mode == "listening"
    app.bar.mic.talk.click()
    assert not app.voice.active and not app.bar.mic.talk.isChecked()


def test_talk_button_lights_up_when_the_wake_word_or_hotkey_listens(offline):
    app = with_voice(offline)
    app.on_wake()
    assert app.bar.mic.talk.isChecked()
    app.on_hotkey()
    assert not app.bar.mic.talk.isChecked()
    app.on_hotkey()
    assert app.bar.mic.talk.isChecked()


def test_talk_button_unmutes_a_muted_mic(offline):
    app = with_voice(offline)
    app.audio.set_mic_muted(True)
    app.bar.mic.talk.click()
    assert not app.audio.mic_muted and app.voice.active


def test_closing_quits_by_default(offline):
    app, _, _ = offline("live_caption")
    quits = []
    app.quit = lambda: quits.append(True)
    app.bar.close_button.click()
    assert quits == [True]


def test_persistent_close_hides_and_the_hotkey_brings_it_back(offline):
    app, _, _ = offline("live_caption", persistent=True)
    quits = []
    app.quit = lambda: quits.append(True)
    app.bar.summon()
    app.bar.close_button.click()
    assert quits == [] and not app.bar.isVisible()
    app.on_hotkey()
    assert app.bar.isVisible()
    assert "brings it back" in app.bar.close_button.toolTip()


def test_voice_states_play_listen_cues(offline):
    app, _, _ = offline("live_caption")
    played = []
    app.sounds.play = played.append
    app.on_voice_state("listening")
    app.on_voice_state("idle")
    app.on_voice_state("timeout")
    app.on_voice_state("listening")
    app.on_voice_state("muted")
    assert played == ["listen", "listen_off", "listen", "listen_off"]


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
