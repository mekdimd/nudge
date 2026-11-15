"""Record the actual listening UI by replaying voice callbacks, without a microphone."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import onnxruntime
from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

import nudge.__main__ as main
from nudge.dev import OfflineJev, OfflineWriter
from nudge.platform.fake import FakeAdapter
from nudge.ui.audio_settings import AudioSettings
from nudge.ui.sounds import TONES, synth

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class RecordingHotkeys(QObject):
    summon = Signal()
    escape = Signal()


class ReplayedVoice(QObject):
    state = Signal(str)
    heard = Signal(str)
    request = Signal(str)
    level = Signal(float)
    active = False

    def listen(self):
        self.active = True
        self.state.emit("listening")

    def cancel(self):
        self.active = False
        self.state.emit("idle")


def capture():
    model = ROOT / "models/hey_nudge.onnx"
    session = onnxruntime.InferenceSession(
        str(model), providers=["CPUExecutionProvider"]
    )
    qapp = QApplication([])
    main.Hotkeys = RecordingHotkeys
    voice = ReplayedVoice()
    trace = {
        "ui_frames": [],
        "ui_sizes": [],
        "events": [],
        "wake_model": str(model.relative_to(ROOT)),
        "model_loaded": bool(session.get_inputs()),
        "voice_input": "replayed callbacks, no microphone or transcription test",
    }
    with tempfile.TemporaryDirectory(prefix="nudge-wake-") as temporary:
        folder = Path(temporary)
        audio = AudioSettings(
            QSettings(str(folder / "audio.ini"), QSettings.Format.IniFormat)
        )
        audio.set_sounds_muted(True)
        app = main.Nudge(
            FakeAdapter({"bank": {"controls": []}}, "bank"),
            OfflineJev([]),
            OfflineWriter(),
            voice=voice,
            audio=audio,
        )
        began = time.monotonic()

        def record():
            frame = app.bar.grab().toImage()
            frame.setDevicePixelRatio(1)
            canvas = QImage(1400, 1540, QImage.Format.Format_ARGB32_Premultiplied)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.drawImage(0, 0, frame)
            painter.end()
            number = len(trace["ui_frames"])
            canvas.scaled(910, 1000).save(str(folder / f"{number:05d}.png"))
            trace["ui_frames"].append(round(time.monotonic() - began, 3))
            trace["ui_sizes"].append([frame.width(), frame.height()])

        timer = QTimer()
        timer.setInterval(50)
        timer.timeout.connect(record)
        timer.start()

        def wake():
            trace["events"].append(
                {"kind": "wake", "at": round(time.monotonic() - began, 3)}
            )
            app.on_wake()

        QTimer.singleShot(850, wake)
        phrase = "download my October bank statement"
        words = phrase.split()
        for i in range(len(words)):
            QTimer.singleShot(
                2100 + i * 380,
                lambda i=i: (
                    voice.heard.emit(" ".join(words[: i + 1])),
                    voice.level.emit(0.45 + (i % 3) * 0.15),
                ),
            )
        QTimer.singleShot(4500, lambda: app.bar.input.setText(phrase))
        QTimer.singleShot(5750, qapp.quit)
        qapp.exec()
        timer.stop()
        manifest = folder / "frames.txt"
        lines = []
        for i, at in enumerate(trace["ui_frames"]):
            duration = (
                trace["ui_frames"][i + 1] - at
                if i + 1 < len(trace["ui_frames"])
                else 0.05
            )
            lines.extend(
                [f"file '{folder / f'{i:05d}.png'}'", f"duration {duration:.6f}"]
            )
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
                "fps=20",
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "17",
                "-pix_fmt",
                "yuv420p",
                str(ASSETS / "browser/wake-nudge.mp4"),
            ],
            check=True,
        )
    (ASSETS / "browser/wake-trace.json").write_text(json.dumps(trace, indent=2) + "\n")
    (ASSETS / "sounds/listen.wav").write_bytes(synth(TONES["listen"]))
    print("Recorded Nudge's listening UI and loaded the Hey Nudge model.")


if __name__ == "__main__":
    capture()
