import argparse
import sys
import threading
import time
import types
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtTest import QTest
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
    import nudge.app as main
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


def click_orb(app):
    QTest.mouseClick(app.bar.orb, Qt.MouseButton.LeftButton)


def test_clicking_the_orb_starts_and_stops_listening(offline):
    app = with_voice(offline)
    click_orb(app)
    assert app.voice.active and app.bar.orb.mode == "listening"
    click_orb(app)
    assert not app.voice.active and app.bar.orb.mode == "idle"


def test_the_orb_stops_what_the_wake_word_or_hotkey_started(offline):
    app = with_voice(offline)
    app.on_wake()
    assert app.bar.orb.mode == "listening"
    click_orb(app)
    assert not app.voice.active
    app.on_hotkey()
    assert app.bar.orb.mode == "listening"
    click_orb(app)
    assert not app.voice.active


def test_clicking_the_orb_unmutes_a_muted_mic(offline):
    app = with_voice(offline)
    app.audio.set_mic_muted(True)
    click_orb(app)
    assert not app.audio.mic_muted and app.voice.active


def test_the_mic_button_mutes_without_listening(offline):
    app = with_voice(offline)
    app.bar.mic.mute.click()
    assert app.audio.mic_muted and not app.voice.active


def test_the_orb_is_not_clickable_without_voice(offline):
    app, _, _ = offline("live_caption")
    click_orb(app)
    assert app.bar.orb.mode == "idle" and not app.bar.orb.clickable


def test_closing_quits_by_default(offline):
    app, _, _ = offline("live_caption")
    quits = []
    app.quit = lambda: quits.append(True)
    app.bar.close_button.click()
    assert quits == [True]


def test_keep_running_close_hides_and_the_hotkey_brings_it_back(offline):
    app, _, _ = offline("live_caption", keep_running=True)
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


def test_run_reports_steps_and_ready_only_after_the_owner_is_ready(qapp, monkeypatch):
    import nudge.app as main

    events = []

    class Progress:
        def step(self, text):
            events.append(text)

        def ready(self):
            events.append("ready")

    class Owner:
        stop_requested = threading.Event()

        def mark_ready(self):
            events.append("owner ready")

    window_system = Mock()
    window_system.exec.side_effect = lambda: events.append("exec") or 0
    monkeypatch.setattr(main, "QApplication", Mock(return_value=window_system))
    monkeypatch.setattr(main, "Hotkeys", StubHotkeys)
    monkeypatch.setattr(main.signal, "signal", Mock())
    monkeypatch.setitem(sys.modules, "nudge.ui.mac_window", types.SimpleNamespace(run_as_accessory=lambda: None))
    monkeypatch.setattr(main.os, "_exit", Mock(side_effect=SystemExit))
    args = argparse.Namespace(offline="live_caption", debug=False, keep_running=False, no_vision=True)
    with pytest.raises(SystemExit):
        main.run(args, Owner(), Progress())
    window_system._nudge.bar.close()
    window_system._nudge.overlay.close()
    assert events == ["Starting Qt", "Loading the offline rehearsal", "Opening the bar", "owner ready", "ready", "exec"]


def test_qt_fatal_messages_name_the_failed_step_before_qt_aborts(capsys):
    from PySide6.QtCore import QtMsgType

    from nudge.app import _qt_printer

    progress = Mock()
    show = _qt_printer(progress)
    show(QtMsgType.QtWarningMsg, types.SimpleNamespace(category="qt.qpa.plugin"), "plugin missing")
    progress.fail.assert_not_called()
    show(QtMsgType.QtFatalMsg, types.SimpleNamespace(category="default"), "no platform plugin")
    progress.fail.assert_called_once_with()
    assert capsys.readouterr().err == "qt.qpa.plugin: plugin missing\nno platform plugin\n"


def test_offline_run_omits_goal_in_logs_by_default_and_opts_in(offline, capsys):
    app, _, goal = offline("live_caption")
    app.start(goal)
    assert wait_until(lambda: finished(app))
    default_out = capsys.readouterr().out
    assert "▶ Task started · Google Chrome" in default_out
    assert goal not in default_out
    assert app.timeline.entries[0].verb == goal

    detailed_app, _, goal = offline("live_caption", detailed_logs=True)
    detailed_app.start(goal)
    assert wait_until(lambda: finished(detailed_app))
    detailed_out = capsys.readouterr().out
    assert f"▶ {goal} · Google Chrome" in detailed_out
