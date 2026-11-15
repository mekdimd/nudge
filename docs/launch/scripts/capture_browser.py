"""Capture the real Nudge loop through a browser RPC adapter for the launch film.

The host answers request.json with response.json after reading or acting in its
owned browser tab. This adapter is for recording, not a shipped platform backend.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from PySide6.QtCore import QObject, QPoint, QSettings, QTimer, Signal, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
import nudge.__main__ as main
from nudge.core.jev import JevClient
from nudge.core.models import AppRef, Control, Rect, Snapshot
from nudge.core.writer import Writer
from nudge.ui.audio_settings import AudioSettings
from nudge.ui.console import Console

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "browser"


class RecordingHotkeys(QObject):
    summon = Signal()
    escape = Signal()


class BrowserCaptureAdapter:
    name = "Browser recording harness"

    def __init__(self, directory):
        self.directory = directory
        self.app = AppRef(name="Google Chrome", pid=999999)
        self.sequence = 0
        self.address = False
        self.pending_url = ""

    def rpc(self, operation, **values):
        self.sequence += 1
        request = {"id": self.sequence, "operation": operation, **values}
        temporary = self.directory / "request.tmp"
        temporary.write_text(json.dumps(request))
        temporary.replace(self.directory / "request.json")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            response = self.directory / "response.json"
            if response.exists():
                try:
                    reply = json.loads(response.read_text())
                except json.JSONDecodeError:
                    reply = {}
                if reply.get("id") == self.sequence:
                    if reply.get("error"):
                        raise RuntimeError(reply["error"])
                    return reply.get("value")
            time.sleep(0.02)
        raise TimeoutError("The recording host did not answer " + operation)

    def thread_context(self):
        return nullcontext()

    def permission_problem(self):
        return None

    def frontmost_app(self):
        return self.app

    def activate_app(self, app):
        pass

    def shell_controls(self, app):
        return []

    def snapshot(self, app):
        started = time.monotonic()
        page = self.rpc("snapshot")
        controls = []
        for item in page["controls"]:
            bounds = item.pop("bounds")
            item["is_text_field"] = item["role"] in (
                "text field",
                "search field",
                "text area",
            )
            controls.append(Control(**item, bounds=Rect(**bounds), ref=item["id"]))
        return Snapshot(
            app=app,
            window_title=page["title"],
            controls=controls,
            window_bounds=Rect(0, 0, page["width"], page["height"]),
            focused_id=page.get("focused"),
            loading=page.get("loading", False),
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )

    def press(self, control):
        self.rpc(
            "click",
            control_id=control.id,
            label=control.label,
            center=control.bounds.center,
        )

    def click(self, control, double=False):
        self.rpc(
            "click",
            control_id=control.id,
            label=control.label,
            center=control.bounds.center,
            count=2 if double else 1,
        )

    def set_text(self, control, text):
        self.rpc(
            "type",
            control_id=control.id,
            text=text,
            label=control.label,
            center=control.bounds.center,
        )

    def type_text(self, text):
        if self.address:
            self.pending_url = text
        else:
            self.rpc("type_focused", text=text)

    def scroll(self, direction, near, window):
        self.rpc("scroll", delta=550 if direction == "down" else -550)

    def key(self, name):
        if name == "address_bar":
            self.address = True
        elif name == "enter" and self.address:
            self.rpc("navigate", url=self.pending_url)
            self.address = False
        else:
            self.rpc("key", name=name)


def main_capture():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--rpc", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    load_dotenv(args.env_file)
    if not os.environ.get("TYPESAFE_API_KEY") or not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("The recording harness requires TypeSafe and Gemini keys.")
    args.rpc.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    qapp = QApplication([])
    main.Hotkeys = RecordingHotkeys
    main.Console = lambda timeline: Console(timeline, color=True)

    class RecordingLoop(main.NudgeLoop):
        def __init__(self, *values, **options):
            options["settle_timeout"] = 15
            super().__init__(*values, **options)

    main.NudgeLoop = RecordingLoop
    adapter = BrowserCaptureAdapter(args.rpc)
    processing_hold = float(os.environ.get("NUDGE_CAPTURE_PROCESSING_HOLD", "0"))

    class RecordingJev(JevClient):
        def decide(self, *values, **options):
            began = time.monotonic()
            result = super().decide(*values, **options)
            time.sleep(max(0, processing_hold - (time.monotonic() - began)))
            return result

    class RecordingWriter(Writer):
        def fill(self, *values, **options):
            began = time.monotonic()
            result = super().fill(*values, **options)
            time.sleep(max(0, processing_hold * 2 - (time.monotonic() - began)))
            return result

    trace = {
        "case": args.case,
        "goal": args.goal,
        "prompts": [],
        "events": [],
        "ui_frames": [],
        "outcome": None,
        "processing_hold_seconds": processing_hold,
    }
    started = time.monotonic()
    trace["epoch_started"] = time.time()

    with tempfile.TemporaryDirectory(prefix="nudge-browser-") as temporary:
        audio = AudioSettings(
            QSettings(str(Path(temporary) / "audio.ini"), QSettings.Format.IniFormat)
        )
        audio.set_sounds_muted(True)
        app = main.Nudge(
            adapter,
            RecordingJev(os.environ["TYPESAFE_API_KEY"]),
            RecordingWriter(os.environ["GEMINI_API_KEY"]),
            audio=audio,
        )
        app.overlay.setGeometry(0, 0, 1280, 800)
        app.bar.input.setText(args.goal)
        app.bar.input.deselect()
        app.bar.input.clearFocus()
        frames = args.rpc / "nudge-frames"
        frames.mkdir(exist_ok=True)
        frame_number = 0

        def event(kind, **values):
            trace["events"].append(
                {"kind": kind, "at": round(time.monotonic() - started, 3), **values}
            )

        def record_frame():
            nonlocal frame_number
            canvas = QImage(1400, 1540, QImage.Format.Format_RGB32)
            canvas.fill(QColor("#20252c"))
            painter = QPainter(canvas)
            frame = app.bar.grab().toImage()
            frame.setDevicePixelRatio(1)
            painter.drawImage(0, 0, frame)
            painter.end()
            canvas = canvas.scaled(910, 1001)
            assert canvas.save(str(frames / f"{frame_number:05d}.png"))
            trace["ui_frames"].append(round(time.monotonic() - started, 3))
            frame_number += 1

        recording = QTimer()
        recording.setInterval(50)
        recording.timeout.connect(record_frame)
        recording.start()
        app.bridge.sig_status.connect(lambda text: event("status", text=text))
        app.bridge.sig_propose.connect(
            lambda action, target: event(
                "propose",
                label=action.label,
                center=target.bounds.center if target and target.bounds else None,
            )
        )
        app.bridge.sig_acted.connect(
            lambda action, changed: event("acted", label=action.label, changed=changed)
        )

        def capture_peek(snapshot):
            if args.case != "jev" or not app.debug or "peek" in trace:
                return
            previous = app.overlay.alpha
            app.overlay.alpha = 0
            app.overlay.repaint()
            trace["peek"] = save("peek", app.overlay)
            app.overlay.alpha = previous
            event("peek", count=len(snapshot.controls))

        app.bridge.sig_observed.connect(capture_peek)

        def capture_choice(action, target):
            if args.case != "jev" or "choice" in trace:
                return

            def grab_choice():
                previous = app.overlay.alpha
                app.overlay.alpha = 0
                app.overlay.repaint()
                trace["choice"] = save("choice", app.overlay)
                app.overlay.alpha = previous
                event("choice", label=action.label)

            QTimer.singleShot(80, grab_choice)

        app.bridge.sig_propose.connect(capture_choice)

        def save(tag, widget=None):
            QApplication.processEvents()
            image = (widget or app.bar).grab().toImage()
            image.setDevicePixelRatio(1)
            path = ASSETS / (args.case + "-" + tag + ".png")
            assert image.save(str(path))
            return {"file": path.name, "width": image.width(), "height": image.height()}

        def prompt(kind):
            def capture_and_approve():
                record = {
                    "kind": kind,
                    "at": round(time.monotonic() - started, 3),
                    "panel": save(kind, app.bar.panel),
                    "bar": save(kind + "-bar"),
                }
                point = app.bar.panel.mapTo(app.bar, QPoint(0, 0))
                record["panel_rect"] = [
                    point.x() * 2,
                    point.y() * 2,
                    app.bar.panel.width() * 2,
                    app.bar.panel.height() * 2,
                ]
                trace["prompts"].append(record)
                if kind == "draft" and args.case == "mail":
                    fields = app.bar.panel.findChildren(QLineEdit)
                    if len(fields) > 1:

                        def edit_subject():
                            field = fields[1]
                            word = field.text().split()[0]
                            point = field.mapTo(app.bar, QPoint(0, 0))
                            width = field.fontMetrics().horizontalAdvance(word)
                            field.setFocus(Qt.FocusReason.OtherFocusReason)
                            field.setSelection(0, len(word))
                            event(
                                "edit-select",
                                start=[point.x() + 14, point.y() + field.height() / 2],
                                end=[
                                    point.x() + 14 + width,
                                    point.y() + field.height() / 2,
                                ],
                            )
                            record["selection"] = save("draft-selection", app.bar.panel)

                            def type_letter(index=0):
                                if index == 0:
                                    event("edit-typing")
                                field.insert("Missing"[index])
                                if index < 6:
                                    QTimer.singleShot(
                                        90, lambda: type_letter(index + 1)
                                    )
                                else:
                                    record["edited"] = save(
                                        "draft-edited", app.bar.panel
                                    )
                                    event("edit-subject")

                            QTimer.singleShot(650, type_letter)

                        QTimer.singleShot(1350, edit_subject)
                if kind == "confirm":
                    trace["confirmed_before_action"] = True
                if kind in ("draft", "url", "confirm"):
                    delay = (
                        4300
                        if kind == "draft" and args.case == "mail"
                        else 2000
                        if kind == "confirm"
                        else 900
                    )

                    def approve():
                        buttons = app.bar.panel.findChildren(QPushButton)
                        button = next(
                            b
                            for b in buttons
                            if b.text()
                            in ("Type it", "Yes, send", "Open it", "Yes, open")
                        )
                        point = button.mapTo(app.bar, button.rect().center())
                        event(
                            "approve",
                            prompt=kind,
                            label=button.text(),
                            center=[point.x(), point.y()],
                        )
                        app.bar.spoken("yes")

                    QTimer.singleShot(delay, approve)
                else:
                    app.stop()

            QTimer.singleShot(150, capture_and_approve)

        app.bridge.sig_draft.connect(lambda *_: prompt("draft"))
        app.bridge.sig_url.connect(lambda *_: prompt("url"))
        app.bridge.sig_confirm.connect(lambda *_: prompt("confirm"))
        app.bridge.sig_choose.connect(lambda *_: prompt("choice"))
        app.bridge.sig_ask.connect(lambda *_: prompt("ask"))
        app.bridge.sig_recover.connect(lambda *_: prompt("recover"))

        def finished(ok, message):
            app.bar.peek.setChecked(False)
            trace["outcome"] = {"ok": ok, "message": message}
            trace["done"] = save("done")
            trace["geometry"] = {}
            for name in ("input", "go", "stop", "peek", "orb", "feed", "panel"):
                widget = getattr(app.bar, name)
                point = widget.mapTo(app.bar, QPoint(0, 0))
                trace["geometry"][name] = [
                    point.x() * 2,
                    point.y() * 2,
                    widget.width() * 2,
                    widget.height() * 2,
                ]
            print(json.dumps({"finished": args.case, "ok": ok}), flush=True)
            QTimer.singleShot(1000, qapp.quit)

        app.bridge.sig_finished.connect(finished)
        QTimer.singleShot(300, lambda: trace.update(idle=save("idle")))
        QTimer.singleShot(700, lambda: app.start(args.goal))
        if args.case == "jev":
            QTimer.singleShot(720, lambda: app.bar.peek.setChecked(True))
        QTimer.singleShot(180000, app.stop)
        qapp.exec()
        recording.stop()
        (ASSETS / (args.case + "-trace.json")).write_text(
            json.dumps(trace, indent=2) + "\n"
        )
        manifest = frames / "frames.txt"
        lines = []
        for index, timestamp in enumerate(trace["ui_frames"]):
            duration = (
                trace["ui_frames"][index + 1] - timestamp
                if index + 1 < frame_number
                else 0.05
            )
            lines.extend(
                [f"file '{frames / f'{index:05d}.png'}'", f"duration {duration:.6f}"]
            )
        lines.append(f"file '{frames / f'{frame_number - 1:05d}.png'}'")
        manifest.write_text("\n".join(lines) + "\n")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-vf",
                "crop=910:1000:0:0,fps=20",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "17",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(ASSETS / (args.case + "-nudge.mp4")),
            ],
            check=True,
        )
        if app.worker:
            app.worker.wait(5000)
        assert trace["outcome"] and trace["outcome"]["ok"], trace["outcome"]


if __name__ == "__main__":
    main_capture()
