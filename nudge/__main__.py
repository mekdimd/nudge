from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from .config import load_config
from .core import safety
from .core.jev import JevClient, JevDecision
from .core.loop import NudgeLoop
from .core.models import Action, AppRef, Control, Snapshot
from .core.writer import Writer
from .ui.audio_settings import AudioSettings
from .ui.bar import Bar
from .ui.bridge import Bridge, Worker
from .ui.coords import logical_to_physical, physical_to_logical
from .ui.hotkeys import Hotkeys
from .ui.overlay import Overlay
from .ui.sounds import Sounds
from .ui.timeline import RunRecorder, Timeline

PEEK_INTERVAL = 1.0


class Nudge(QObject):
    sig_peeked = Signal(object)

    def __init__(self, adapter, jev, writer, vision=None, offline_goal: str | None = None, debug: bool = False, voice=None, wake=None, speaker=None, audio: AudioSettings | None = None):
        super().__init__()
        self.adapter, self.jev, self.writer, self.vision = adapter, jev, writer, vision
        self.voice = voice
        self.wake = wake
        self.speaker = speaker
        self.audio = audio if audio is not None else AudioSettings()
        self.audio.changed.connect(self.on_audio_changed)
        self.sounds = Sounds(self.audio)
        self.target: AppRef | None = None
        self.worker: Worker | None = None
        self.debug = False
        self.last_jev_ms = 0
        self.bridge = Bridge()
        self.timeline = Timeline()
        self.recorder = RunRecorder(self.timeline)
        self.bar = Bar(self.timeline)
        self.overlay = Overlay()
        self.hotkeys = Hotkeys()

        self.bar.set_target(None)
        self.bar.go_requested.connect(self.start)
        self.bar.stop_requested.connect(self.stop)
        self.bar.quit_requested.connect(self.quit)
        self.bar.peek_toggled.connect(self.set_debug)
        self.hotkeys.summon.connect(self.on_hotkey)
        self.hotkeys.escape.connect(self.stop)
        self.sig_peeked.connect(self.on_peeked)

        b = self.bridge
        b.sig_status.connect(self.recorder.status)
        b.sig_observed.connect(self.on_observed)
        b.sig_vision.connect(self.recorder.vision_used)
        b.sig_decided.connect(self.on_decided)
        b.sig_writer_started.connect(self.recorder.writer_started)
        b.sig_writer_used.connect(self.recorder.writer_used)
        b.sig_propose.connect(self.on_propose)
        b.sig_acted.connect(self.on_acted)
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

        if offline_goal is not None:
            self.set_target(adapter.app)
            self.bar.input.setText(offline_goal)
            self.bar.set_status("Offline rehearsal on a scripted screen. Nothing on your computer is touched.")
        else:
            self.tracker = QTimer()
            self.tracker.setInterval(400)
            self.tracker.timeout.connect(self.track)
            self.tracker.start()
            self.track()

        problem = adapter.permission_problem()
        if problem:
            self.bar.set_status(problem, tone="warn")
        elif jev is None:
            self.bar.set_status("Add TYPESAFE_API_KEY to .env to let Jev choose steps, then restart Nudge.", tone="warn")
        if voice is not None:
            voice.state.connect(self.on_voice_state)
            voice.heard.connect(lambda text: self.bar.set_status(f"Listening: {text}", during_run=True))
            voice.request.connect(self.on_voice_request)
            from .ui.mic import MicButton

            self.bar.add_mic(MicButton(self.audio))
            voice.level.connect(self.bar.orb.set_level)
        if speaker is not None:
            speaker.finished.connect(self.on_spoken_prompt)
            speaker.level.connect(self.bar.orb.set_level)
        if wake is not None:
            wake.detected.connect(self.on_wake)
            wake.failed.connect(lambda why: self.bar.set_status(f"Wake word is off ({why}).", tone="warn"))
            wake.start()
        self.bar.summon()
        if debug:
            self.bar.peek.setChecked(True)

    def on_wake(self) -> None:
        if (self.running and self.bar.spoken is None) or self.voice is None:
            return
        self.summon()
        self.voice.listen()

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
            "muted": "Mic is muted. Unmute it with the mic button.",
        }
        text = messages.get(state, f"Voice is off ({state.removeprefix('error: ')}).")
        self.bar.set_status(text, tone="warn" if state not in messages or state == "no_mic" else "muted", during_run=True)

    def prompt(self, show, *args, said: str = "", feed: str = "") -> None:
        """Show a question, read it aloud, then listen for the answer by voice as well."""
        show(*args)
        self.sounds.play("attention")
        if feed and self.running:
            self.recorder.waiting(feed)  # after show(): opening a panel closes the previous one, which settles waits
        if self.voice is None:
            return
        if self.speaker is not None and said and not self.audio.voice_muted:
            if self.wake is not None:
                self.wake.pause()  # don't let the speaker trigger the wake word
            self.speaker.say(said)
        else:
            self.voice.listen()
        self.sync_orb()

    def on_spoken_prompt(self) -> None:
        """The question has been read out (or couldn't be); the mic opens only now so it doesn't hear the speaker."""
        if self.voice is not None and self.running and self.bar.spoken is not None:
            self.voice.listen()
        elif self.wake is not None and not (self.voice is not None and self.voice.active):
            self.wake.start()
        self.sync_orb()

    def on_panel_closed(self) -> None:
        self.recorder.answered()
        if self.speaker is not None:
            self.speaker.stop()
        if self.voice is not None and self.running:
            self.voice.cancel()
        self.sync_orb()

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

    def on_voice_request(self, goal: str) -> None:
        if self.bar.spoken is not None:
            if not self.bar.spoken(goal):
                self.bar.set_status(f'Heard "{goal}", but not what to do with it. Try again or click.', during_run=True)
                self.voice.listen()
            return
        if self.running:
            return
        self.bar.input.setText(goal)
        self.summon()
        self.start(goal)

    def set_target(self, app: AppRef) -> None:
        self.target = app
        self.bar.set_target(app)

    def track(self) -> None:
        if self.running:
            return
        front = self.adapter.frontmost_app()
        if front is not None and front.pid != os.getpid() and front.name:
            if self.target is None or front.pid != self.target.pid:
                self.set_target(front)

    @property
    def running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def on_hotkey(self) -> None:
        self.summon()
        if self.voice is not None and (not self.running or self.bar.spoken is not None):
            self.voice.cancel() if self.voice.active else self.voice.listen()

    def summon(self) -> None:
        if not self.running:
            self.track()
        self.bar.summon()

    def start(self, goal: str) -> None:
        if self.running:
            return
        if self.jev is None:
            self.bar.set_status("Jev isn't set up. Add TYPESAFE_API_KEY to .env and restart Nudge.", tone="warn")
            return
        if self.target is None:
            self.bar.set_status("Click into the app you want help with first.", tone="warn")
            return
        if problem := self.adapter.permission_problem():
            self.bar.set_status(problem, tone="warn")
            return
        self.bridge.reset()
        loop = NudgeLoop(self.adapter, self.jev, self.writer, self.bridge, vision=self.vision)
        self.worker = Worker(loop, goal, self.target)
        self.bar.set_running(True)
        self.recorder.started(goal, self.target)
        self.sounds.play("start")
        self.sync_orb()
        self.overlay.appear()
        self.worker.start()

    def stop(self) -> None:
        if self.running:
            if self.voice is not None:
                self.voice.cancel()
            self.bridge.cancel()
            self.bar.clear_panel()
            self.bar.set_status("Stopping…", during_run=True)

    def quit(self) -> None:
        self.debug = False
        if self.running:
            self.bridge.cancel()
            self.worker.wait(1000)
        if self.speaker is not None:
            self.speaker.stop()
        if self.voice is not None:
            self.voice.cancel()
        if self.wake is not None:
            self.wake.close()
        QApplication.quit()

    # debug view

    def set_debug(self, on: bool) -> None:
        self.debug = on
        if not on:
            self.overlay.clear_boxes()
            return
        threading.Thread(target=self._peek_loop, name="peek", daemon=True).start()

    def _peek_loop(self) -> None:
        with self.adapter.thread_context():
            while self.debug:
                target = self.target
                if not self.running and target is not None:
                    try:
                        snapshot = self.adapter.snapshot(target)
                        vision_ms = None
                        if self.vision is not None and len(snapshot.pressables) < safety.SPARSE_TREE:
                            found, vision_ms = self.vision.find(snapshot)
                            snapshot.controls += found
                        if self.debug and not self.running:
                            self.sig_peeked.emit((snapshot, vision_ms))
                    except Exception:
                        pass
                time.sleep(PEEK_INTERVAL)

    def on_peeked(self, payload) -> None:
        snapshot, vision_ms = payload
        if not self.debug or self.running:
            return
        self.overlay.show_boxes(snapshot.controls)
        vision = sum(c.source == "vision" for c in snapshot.controls)
        found = f"{len(snapshot.controls) - vision} from the accessibility tree" + (f", {vision} from vision" if vision_ms is not None else "")
        timing = f"screen {snapshot.elapsed_ms} ms" + (f", vision {vision_ms} ms" if vision_ms is not None else "")
        self.bar.set_status(f"Peek: {found} in {snapshot.app.name} · {timing}")

    # run events

    def on_observed(self, snapshot: Snapshot) -> None:
        if self.debug:
            self.overlay.show_boxes(snapshot.controls)

    def on_decided(self, step: int, decision: JevDecision, labels: dict[str, str]) -> None:
        self.last_jev_ms = decision.milliseconds
        self.recorder.decided(decision, labels)
        self.bar.set_step(step)

    def on_acted(self, action: Action, changed: bool) -> None:
        self.recorder.acted(action, changed)
        if changed:
            self.sounds.play("tick")

    def on_switched(self, app: AppRef) -> None:
        self.bar.set_target(app)
        self.recorder.switched(app)

    def on_propose(self, action: Action, target: Control | None) -> None:
        self.recorder.proposed(action)
        warn = action.kind == "press" and safety.consequential_word(action.label) is not None
        bounds = target.bounds if target is not None else None
        if self.debug:
            self.overlay.pick_box(bounds)
        label = f"{action.describe()}  ·  Jev {self.last_jev_ms} ms"
        self.overlay.fly_to(bounds, label, warn=warn, on_landed=lambda: self.bridge.reply(True))

    def on_finished(self, ok: bool, message: str) -> None:
        self.recorder.finished(ok, message)
        self.sounds.play("success" if ok else "failure")
        self.bar.set_running(False)
        self.bar.show_result(ok)
        self.overlay.fade()
        self.sync_orb()


def spoken_choice(reason: str, options: list[tuple[str, str, float]]) -> str:
    names = ", ".join(f"{number}, {label}" for number, (_, label, _) in enumerate(options, 1))
    return f"{reason} Say a number: {names}."


def load_vision():
    try:
        import ultralytics  # noqa: F401  (optional "vision" extra)
    except ImportError:
        return None
    from .vision.parser import ScreenParser

    return ScreenParser(to_physical=logical_to_physical if sys.platform == "win32" else None)


def main() -> None:
    parser = argparse.ArgumentParser(prog="nudge", description="Type a goal; Nudge points to and presses each step.")
    parser.add_argument("--offline", choices=["live_caption", "gmail"], help="rehearse the UI on a scripted screen, no keys needed")
    parser.add_argument("--debug", action="store_true", help="start with Peek on: box every element Nudge can see")
    parser.add_argument("--no-vision", action="store_true", help="never use the screenshot fallback")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Nudge")
    app.setQuitOnLastWindowClosed(False)
    if sys.platform == "darwin":
        from .ui.mac_window import run_as_accessory

        run_as_accessory()

    if args.offline:
        from .dev import GOALS, PATHS, OfflineJev, OfflineWriter
        from .platform.fake import FakeAdapter

        adapter = FakeAdapter.from_fixture(args.offline)
        controller = Nudge(adapter, OfflineJev(PATHS[args.offline]), OfflineWriter(), offline_goal=GOALS[args.offline], debug=args.debug)
    else:
        from .platform.base import load_adapter

        config = load_config()
        audio = AudioSettings()
        jev = JevClient(config.typesafe_api_key) if config.typesafe_api_key else None
        writer = Writer(config.gemini_api_key) if config.gemini_api_key else None
        voice = None
        if config.elevenlabs_api_key:
            from .ui.voice import Voice

            voice = Voice(config.elevenlabs_api_key, audio)
        speaker = None
        if voice is not None:
            from .ui.speaker import Speaker

            speaker = Speaker(config.elevenlabs_api_key, config.elevenlabs_voice_id)
        wake = None
        if voice is not None and config.wake_word:
            from .ui.wake import WakeWord

            try:
                wake = WakeWord(config.wake_word, config.wake_threshold, settings=audio)
            except Exception as exc:  # missing model file, or no network on the first download
                print(f"Wake word disabled: {exc}", file=sys.stderr)
        vision = None if args.no_vision else load_vision()
        controller = Nudge(load_adapter(physical_to_logical), jev, writer, vision, debug=args.debug, voice=voice, wake=wake, speaker=speaker, audio=audio)

    app._nudge = controller
    signal.signal(signal.SIGINT, lambda *_: controller.quit())
    heartbeat = QTimer()  # Qt's loop blocks Python signal handlers unless Python code runs now and then
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(200)
    code = app.exec()
    os._exit(code)  # a run may be stuck in a network call; don't wait for it


if __name__ == "__main__":
    main()
