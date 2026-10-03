from __future__ import annotations

import argparse
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .config import load_config
from .core import safety
from .core.jev import JevClient, JevDecision
from .core.loop import NudgeLoop
from .core.models import Action, AppRef, Control
from .core.writer import Writer
from .ui.bar import Bar
from .ui.bridge import Bridge, Worker
from .ui.coords import physical_to_logical
from .ui.hotkeys import Hotkeys
from .ui.overlay import Overlay


class Nudge:
    def __init__(self, adapter, jev, writer, offline_goal: str | None = None):
        self.adapter, self.jev, self.writer = adapter, jev, writer
        self.target: AppRef | None = None
        self.worker: Worker | None = None
        self.bridge = Bridge()
        self.bar = Bar()
        self.overlay = Overlay()
        self.hotkeys = Hotkeys()

        self.bar.set_jev_idle(jev is not None)
        self.bar.set_gemini("off" if writer is None else "idle")
        self.bar.set_target(None)
        self.bar.go_requested.connect(self.start)
        self.bar.stop_requested.connect(self.stop)
        self.bar.quit_requested.connect(self.quit)
        self.hotkeys.summon.connect(self.summon)
        self.hotkeys.escape.connect(self.stop)

        b = self.bridge
        b.sig_status.connect(self.bar.set_status)
        b.sig_decided.connect(self.on_decided)
        b.sig_writer_started.connect(lambda: self.bar.set_gemini("busy"))
        b.sig_writer_used.connect(lambda ms: self.bar.set_gemini("done", ms))
        b.sig_propose.connect(self.on_propose)
        b.sig_hold.connect(self.overlay.start_hold)
        b.sig_choose.connect(lambda reason, options: self.bar.show_choice(reason, options, b.reply))
        b.sig_draft.connect(lambda note, fields: self.bar.show_draft(note, fields, b.reply))
        b.sig_url.connect(lambda url, fallback: self.bar.show_url(url, fallback, b.reply))
        b.sig_confirm.connect(lambda message: self.bar.show_confirm(message, b.reply))
        b.sig_recover.connect(lambda message: self.bar.show_recover(message, b.reply))
        b.sig_ask.connect(lambda message: self.bar.show_ask(message, b.reply))
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
            self.bar.set_status(problem)
        elif jev is None:
            self.bar.set_status("Add TYPESAFE_API_KEY to .env to let Jev choose steps, then restart Nudge.")
        self.bar.summon()

    def set_target(self, app: AppRef) -> None:
        self.target = app
        self.bar.set_target(app.name)

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

    def summon(self) -> None:
        if not self.running:
            self.track()
        self.bar.summon()

    def start(self, goal: str) -> None:
        if self.running:
            return
        if self.jev is None:
            self.bar.set_status("Jev isn't set up. Add TYPESAFE_API_KEY to .env and restart Nudge.")
            return
        if self.target is None:
            self.bar.set_status("Click into the app you want help with first.")
            return
        if problem := self.adapter.permission_problem():
            self.bar.set_status(problem)
            return
        self.bridge.reset()
        loop = NudgeLoop(self.adapter, self.jev, self.writer, self.bridge)
        self.worker = Worker(loop, goal, self.target)
        self.bar.set_running(True)
        self.bar.set_gemini("off" if self.writer is None else "idle")
        self.overlay.appear()
        self.worker.start()

    def stop(self) -> None:
        if self.running:
            self.bridge.cancel()
            self.bar.clear_panel()
            self.bar.set_status("Stopping…")

    def quit(self) -> None:
        if self.running:
            self.bridge.cancel()
            self.worker.wait(3000)
        QApplication.quit()

    def on_decided(self, step: int, decision: JevDecision, labels: dict[str, str]) -> None:
        rows = [(labels.get(k, k), p, k == decision.choice) for k, p in decision.top(3, include_none=True)]
        self.bar.set_jev(step, decision.milliseconds, rows, decision.done)

    def on_propose(self, action: Action, target: Control | None) -> None:
        warn = action.kind == "press" and safety.consequential_word(action.label) is not None
        bounds = target.bounds if target is not None else None
        self.overlay.fly_to(bounds, action.describe(), warn=warn, on_landed=lambda: self.bridge.reply(True))

    def on_finished(self, ok: bool, message: str) -> None:
        self.bar.set_running(False)
        self.bar.show_result(ok, message)
        self.overlay.flash(message, ok)


def main() -> None:
    parser = argparse.ArgumentParser(prog="nudge", description="Type a goal; Nudge points to and presses each step.")
    parser.add_argument("--offline", choices=["live_caption", "gmail"], help="rehearse the UI on a scripted screen, no keys needed")
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

        controller = Nudge(FakeAdapter.from_fixture(args.offline), OfflineJev(PATHS[args.offline]), OfflineWriter(), GOALS[args.offline])
    else:
        from .platform.base import load_adapter

        config = load_config()
        jev = JevClient(config.typesafe_api_key) if config.typesafe_api_key else None
        writer = Writer(config.gemini_api_key) if config.gemini_api_key else None
        controller = Nudge(load_adapter(physical_to_logical), jev, writer)

    app._nudge = controller
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
