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
            p.setPen(QPen(QColor(106, 160, 255, int(150 * (1 - phase))), 1.5))
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
                if i == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            p.drawPath(path)
        else:
            p.drawEllipse(c, radius, radius)
