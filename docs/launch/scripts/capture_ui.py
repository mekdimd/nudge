"""Record Nudge's real Qt widgets against offline fixtures, without desktop access."""

from __future__ import annotations

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

from PySide6.QtCore import QObject, QPoint, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

import nudge.app as main
from nudge.dev import GOALS, PATHS, OfflineJev, OfflineWriter
from nudge.platform.fake import FakeAdapter
from nudge.ui.audio_settings import AudioSettings
from nudge.ui.overlay import POINTER
from nudge.ui.sounds import TONES, synth

ASSETS = Path(__file__).resolve().parents[1] / "assets"
FPS = 30
WIDTH, HEIGHT = 1600, 1000


class OfflineHotkeys(QObject):
    summon = Signal()
    escape = Signal()


def settle(seconds=0.15):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QApplication.processEvents()
        time.sleep(0.005)


def image_of(widget):
    if widget.objectName() == "card":
        parent = widget.parentWidget()
        image = parent.grab().toImage()
        ratio = image.devicePixelRatio()
        corner = widget.mapTo(parent, QPoint(0, 0))
        image = image.copy(
            round(corner.x() * ratio), round(corner.y() * ratio),
            round(widget.width() * ratio), round(widget.height() * ratio),
        )
    else:
        image = widget.grab().toImage()
    image.setDevicePixelRatio(1)
    return image


def still(widget, name):
    QApplication.processEvents()
    image = image_of(widget)
    assert image.save(str(ASSETS / f"{name}.png"))
    return {"width": image.width(), "height": image.height()}


def record(widget, name, seconds, action=None, until=None):
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "rgba",
        "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS),
        "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(ASSETS / f"{name}.mp4"),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    started = time.monotonic()
    frames = 0
    performed = False
    try:
        for frame in range(round(seconds * FPS)):
            settle(max(0.001, started + frame / FPS - time.monotonic()))
            if action and not performed and frame >= FPS * 1.5:
                action()
                performed = True
                QApplication.processEvents()
            canvas = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGBA8888)
            canvas.fill(QColor("#edece8"))
            image = image_of(widget)
            scale = min(1.0, (WIDTH - 80) / image.width(), (HEIGHT - 64) / image.height())
            if scale < 1:
                image = image.scaled(
                    round(image.width() * scale), round(image.height() * scale),
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
                )
            painter = QPainter(canvas)
            painter.drawImage(QPoint((WIDTH - image.width()) // 2, (HEIGHT - image.height()) // 2), image)
            painter.end()
            encoder.stdin.write(bytes(canvas.constBits()))
            frames += 1
            if until and until() and frames > FPS:
                break
    finally:
        encoder.stdin.close()
        status = encoder.wait()
        assert status == 0, f"ffmpeg exited with {status}"
    return {"file": f"{name}.mp4", "duration": frames / FPS, "fps": FPS, "width": WIDTH, "height": HEIGHT}


def panel_has(app, text):
    return app.bar.panel.isVisible() and any(
        text in button.text() for button in app.bar.panel.findChildren(QPushButton)
    )


def finished(app):
    return bool(app.timeline.entries and not app.running and app.timeline.entries[-1].state == "done")


def make_app(fixture, settings):
    adapter = FakeAdapter.from_fixture(fixture)
    audio = AudioSettings(QSettings(settings, QSettings.Format.IniFormat))
    audio.set_sounds_muted(True)
    app = main.Nudge(adapter, OfflineJev(PATHS[fixture]), OfflineWriter(), offline_goal=GOALS[fixture], audio=audio)
    settle()
    app.bar.input.deselect()
    app.bar.input.clearFocus()
    return app, adapter


def main_capture():
    ASSETS.mkdir(parents=True, exist_ok=True)
    qapp = QApplication.instance() or QApplication([])
    main.Hotkeys = OfflineHotkeys
    manifest = {"source": "Real Nudge Qt widgets using FakeAdapter and OfflineJev. No desktop access or API calls.", "clips": {}, "stills": {}}
    with tempfile.TemporaryDirectory(prefix="nudge-film-") as temporary:
        gmail, adapter = make_app("gmail", str(Path(temporary) / "audio.ini"))
        manifest["stills"]["idle"] = still(gmail.bar, "idle")
        gmail.start(GOALS["gmail"])
        manifest["clips"]["start"] = record(gmail.bar, "gmail-start", 12, until=lambda: panel_has(gmail, "Type it"))
        assert panel_has(gmail, "Type it"), "The actual draft review did not appear"
        settle()
        manifest["stills"]["draft"] = still(gmail.bar.panel, "draft")

        def edit_subject():
            editors = gmail.bar.panel.findChildren(QLineEdit)
            assert len(editors) >= 2
            editors[1].setText("Missing today's lecture")

        manifest["clips"]["draft"] = record(gmail.bar.panel, "gmail-draft", 4, action=edit_subject)
        assert gmail.bar.spoken("yes")
        manifest["clips"]["type"] = record(gmail.bar, "gmail-type", 12, until=lambda: panel_has(gmail, "Yes"))
        assert panel_has(gmail, "Yes"), "The actual Send confirmation did not appear"
        assert adapter.screen != "sent", "The rehearsal sent before confirmation"
        settle()
        manifest["stills"]["confirm"] = still(gmail.bar.panel, "confirm")
        manifest["stills"]["confirm-bar"] = still(gmail.bar, "confirm-bar")
        manifest["clips"]["confirm"] = record(gmail.bar.panel, "gmail-confirm", 3)
        assert gmail.bar.spoken("yes")
        manifest["clips"]["finish"] = record(gmail.bar, "gmail-finish", 12, until=lambda: finished(gmail))
        assert finished(gmail) and adapter.screen == "sent"
        settle()
        manifest["stills"]["done"] = still(gmail.bar, "done")
        manifest["gmail_actions"] = adapter.log
        gmail.bar.close()
        gmail.overlay.close()

        captions, adapter = make_app("live_caption", str(Path(temporary) / "captions.ini"))
        manifest["stills"]["captions-idle"] = still(captions.bar, "captions-idle")
        captions.start(GOALS["live_caption"])
        manifest["clips"]["captions"] = record(captions.bar, "captions", 20, until=lambda: finished(captions))
        assert finished(captions)
        assert any(control.label == "Live Caption" and control.value == "on" for control in adapter.snapshot(adapter.app).controls)
        settle()
        manifest["stills"]["captions-done"] = still(captions.bar, "captions-done")
        manifest["caption_actions"] = adapter.log
        captions.bar.close()
        captions.overlay.close()

    for name in ("start", "tick", "attention", "success"):
        (ASSETS / f"{name}.wav").write_bytes(synth(TONES[name]))
    pointer = QImage(240, 240, QImage.Format.Format_RGBA8888)
    pointer.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pointer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(10, 10)
    painter.setPen(QColor("#ffffff"))
    painter.setBrush(QColor("#4f8ef7"))
    painter.drawPath(POINTER)
    painter.end()
    assert pointer.save(str(ASSETS / "pointer.png"))
    (ASSETS / "capture.json").write_text(json.dumps(manifest, indent=2) + chr(10))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main_capture()
