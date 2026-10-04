from __future__ import annotations

import math
import sys
import time
from collections import deque
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..core.models import Rect
from ..vision.screen import exclude_from_capture
from . import theme

CURSOR_SIZE = 52
TIP = QPointF(4.3, 4.3)


def _pointer_path() -> QPainterPath:
    """Lucide mouse-pointer-2 in a 24x24 box, the same silhouette TipTour uses."""
    p = QPainterPath()
    p.moveTo(4.037, 4.688)
    p.quadTo(3.90, 3.90, 4.688, 4.037)
    p.lineTo(20.688, 10.537)
    p.quadTo(21.42, 10.84, 20.625, 11.484)
    p.lineTo(14.501, 13.064)
    p.quadTo(13.43, 13.34, 13.063, 14.499)
    p.lineTo(11.484, 20.625)
    p.quadTo(11.17, 21.42, 10.537, 20.688)
    p.closeSubpath()
    return p


POINTER = _pointer_path()


def _ease(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


class Overlay(QWidget):
    """Full-screen, click-through layer with Nudge's enlarged cursor, target ring, and label bubble."""

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())

        self.pos_ = QPointF(-200, -200)
        self.scale = 1.0
        self.alpha = 0.0
        self.alpha_target = 0.0
        self.trail: deque[tuple[QPointF, float]] = deque(maxlen=40)
        self.flight: dict | None = None
        self.target: QRectF | None = None
        self.ring_alpha = 0.0
        self.bubble = ""
        self.bubble_color = theme.BLUE
        self.hold: tuple[float, float] | None = None
        self.on_landed: Callable[[], None] | None = None
        self.boxes: list[tuple[QRectF, str, str]] = []
        self.picked: QRectF | None = None

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa":
            from .mac_window import float_over_everything

            float_over_everything(self, level=1000, ignore_mouse=True)
        exclude_from_capture(self)

    def _local(self, x: float, y: float) -> QPointF:
        origin = self.geometry().topLeft()
        return QPointF(x - origin.x(), y - origin.y())

    def appear(self) -> None:
        if self.alpha <= 0.01:
            g = QCursor.pos()
            self.pos_ = self._local(g.x(), g.y())
            self.trail.clear()
        self.alpha_target = 1.0
        if not self.isVisible():
            self.show()
        self._animate()

    def fade(self, delay_ms: int = 0) -> None:
        def go():
            self.alpha_target = 0.0
            self.target = None
            self.bubble = ""
            self.hold = None
            self._animate()

        QTimer.singleShot(delay_ms, go) if delay_ms else go()

    def fly_to(self, rect: Rect | None, label: str, warn: bool = False, on_landed: Callable[[], None] | None = None) -> None:
        self.appear()
        self.bubble = label
        self.bubble_color = theme.AMBER if warn else theme.BLUE
        self.hold = None
        self.on_landed = on_landed
        if rect is None:
            self.target = None
            self.flight = None
            self._land()
            return
        tl = self._local(rect.x, rect.y)
        self.target = QRectF(tl.x(), tl.y(), rect.w, rect.h).adjusted(-6, -6, 6, 6)
        self.ring_alpha = 0.0
        cx, cy = rect.center
        end = self._local(cx, cy)
        start = QPointF(self.pos_)
        dx, dy = end.x() - start.x(), end.y() - start.y()
        dist = math.hypot(dx, dy)
        if dist < 2:
            self.flight = None
            self.pos_ = end
            self._land()
            return
        ux, uy = dx / dist, dy / dist
        nx, ny = -uy, ux
        direction = -1 if start.x() <= end.x() else 1
        arc = min(max(dist * 0.08, 18), 58) * direction
        reach = dist * 0.3
        self.flight = {
            "start": start,
            "cp1": QPointF(start.x() + ux * reach + nx * arc, start.y() + uy * reach + ny * arc),
            "cp2": QPointF(end.x() - ux * reach - nx * arc * 0.65, end.y() - uy * reach - ny * arc * 0.65),
            "end": end,
            "t0": time.monotonic(),
            "duration": min(max(0.22 + dist / 3600, 0.22), 0.5),
        }
        self._animate()

    def show_boxes(self, controls) -> None:
        """Debug view: every element Nudge can see, coloured by where it came from."""
        self.boxes = []
        for c in controls:
            if c.bounds is None or c.bounds.is_empty:
                continue
            tl = self._local(c.bounds.x, c.bounds.y)
            kind = "vision" if c.source == "vision" else ("field" if c.is_text_field else "tree")
            self.boxes.append((QRectF(tl.x(), tl.y(), c.bounds.w, c.bounds.h), f"{c.id} {c.label}"[:40], kind))
        self.picked = None
        if self.boxes and not self.isVisible():
            self.show()
        self.update()

    def pick_box(self, rect: Rect | None) -> None:
        if rect is not None:
            tl = self._local(rect.x, rect.y)
            self.picked = QRectF(tl.x(), tl.y(), rect.w, rect.h)
            self.update()

    def clear_boxes(self) -> None:
        self.boxes, self.picked = [], None
        self.update()
        self._animate()

    def start_hold(self, seconds: float) -> None:
        self.hold = (time.monotonic(), seconds)
        self._animate()

    def _land(self) -> None:
        callback, self.on_landed = self.on_landed, None
        if callback:
            callback()

    def _animate(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def _tick(self) -> None:
        now = time.monotonic()
        busy = False
        if self.flight:
            f = self.flight
            t = min((now - f["t0"]) / f["duration"], 1.0)
            e = _ease(t)
            o = 1 - e
            p0, p1, p2, p3 = f["start"], f["cp1"], f["cp2"], f["end"]
            self.pos_ = QPointF(
                o**3 * p0.x() + 3 * o * o * e * p1.x() + 3 * o * e * e * p2.x() + e**3 * p3.x(),
                o**3 * p0.y() + 3 * o * o * e * p1.y() + 3 * o * e * e * p2.y() + e**3 * p3.y(),
            )
            self.scale = 1.0 + 0.3 * math.sin(math.pi * t)
            self.trail.append((QPointF(self.pos_), now))
            busy = True
            if t >= 1.0:
                self.flight = None
                self.scale = 1.0
                self._land()
        while self.trail and now - self.trail[0][1] > 0.22:
            self.trail.popleft()
            busy = True
        if self.trail:
            busy = True
        if self.target is not None and self.flight is None and self.ring_alpha < 1:
            self.ring_alpha = min(1.0, self.ring_alpha + 0.12)
            busy = True
        if abs(self.alpha - self.alpha_target) > 0.01:
            self.alpha += (self.alpha_target - self.alpha) * 0.2
            busy = True
        else:
            self.alpha = self.alpha_target
        if self.hold is not None:
            busy = True
            if now - self.hold[0] > self.hold[1] + 0.3:
                self.hold = None
        if self.target is not None:
            busy = True
        self.update()
        if not busy:
            self.timer.stop()
            if self.alpha <= 0.01 and not self.boxes:
                self.hide()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_boxes(painter)
        if self.alpha <= 0.01:
            return
        painter.setOpacity(self.alpha)
        self._paint_ring(painter)
        self._paint_trail(painter)
        self._paint_cursor(painter)
        self._paint_hold(painter)
        self._paint_bubble(painter)

    def _paint_boxes(self, painter: QPainter) -> None:
        if not self.boxes:
            return
        colors = {"tree": QColor(79, 142, 247), "field": QColor(52, 199, 123), "vision": QColor(245, 165, 36)}
        painter.setFont(theme.font(10, theme.QFont.Weight.DemiBold))
        metrics = painter.fontMetrics()
        for rect, label, kind in self.boxes:
            color = colors[kind]
            fill = QColor(color)
            fill.setAlpha(28)
            painter.setBrush(fill)
            painter.setPen(QPen(color, 1.2))
            painter.drawRect(rect)
            text = metrics.elidedText(label, Qt.TextElideMode.ElideRight, max(int(rect.width()), 60))
            chip = QRectF(rect.x(), rect.y() - metrics.height() - 2, metrics.horizontalAdvance(text) + 8, metrics.height() + 2)
            if chip.y() < 0:
                chip.moveTop(rect.y())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(chip)
            painter.setPen(QColor("#10131a") if kind == "vision" else QColor("white"))
            painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, text)
        if self.picked is not None:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("white"), 3))
            painter.drawRect(self.picked.adjusted(-2, -2, 2, 2))

    def _paint_ring(self, painter: QPainter) -> None:
        if self.target is None or self.ring_alpha <= 0:
            return
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 5)
        color = QColor(self.bubble_color)
        for width, alpha in ((14, 30), (8, 55), (3, 230)):
            c = QColor(color)
            c.setAlpha(int(alpha * self.ring_alpha * (0.8 + 0.2 * pulse)))
            painter.setPen(QPen(c, width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.target, 10, 10)
        fill = QColor(color)
        fill.setAlpha(int(34 * self.ring_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(self.target, 10, 10)

    def _paint_trail(self, painter: QPainter) -> None:
        if len(self.trail) < 2:
            return
        now = time.monotonic()
        points = list(self.trail)
        for (a, ta), (b, _) in zip(points, points[1:]):
            life = max(0.0, 1 - (now - ta) / 0.22)
            for width, alpha in ((16 * life, 40), (7 * life, 130)):
                c = QColor(theme.BLUE)
                c.setAlpha(int(alpha * life))
                pen = QPen(c, max(width, 0.5))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(a, b)

    def _paint_cursor(self, painter: QPainter) -> None:
        size = CURSOR_SIZE * self.scale
        k = size / 24
        painter.save()
        painter.translate(self.pos_.x() - TIP.x() * k, self.pos_.y() - TIP.y() * k)
        painter.scale(k, k)
        for width, alpha in ((5.0, 35), (3.0, 60), (1.6, 90)):
            c = QColor(theme.BLUE)
            c.setAlpha(alpha)
            pen = QPen(c, width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(POINTER)
        painter.setBrush(theme.BLUE)
        outline = QPen(QColor("white"), 1.3)
        outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline)
        painter.drawPath(POINTER)
        painter.restore()

    def _paint_hold(self, painter: QPainter) -> None:
        if self.hold is None or self.flight is not None:
            return
        t0, seconds = self.hold
        progress = min((time.monotonic() - t0) / max(seconds, 0.01), 1.0)
        center = QPointF(self.pos_.x() + 14, self.pos_.y() + 14)
        r = 26
        box = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
        track = QColor(255, 255, 255, 60)
        painter.setPen(QPen(track, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(box)
        pen = QPen(QColor(self.bubble_color), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(box, 90 * 16, int(-360 * 16 * progress))

    def _paint_bubble(self, painter: QPainter) -> None:
        if not self.bubble:
            return
        painter.setFont(theme.font(16, theme.QFont.Weight.DemiBold))
        metrics = painter.fontMetrics()
        text = metrics.elidedText(self.bubble, Qt.TextElideMode.ElideRight, 420)
        w = metrics.horizontalAdvance(text) + 28
        h = metrics.height() + 16
        x = self.pos_.x() + 30
        y = self.pos_.y() + 30
        bounds = self.rect()
        if x + w > bounds.width() - 8:
            x = self.pos_.x() - w - 12
        if y + h > bounds.height() - 8:
            y = self.pos_.y() - h - 12
        box = QRectF(x, y, w, h)
        shadow = QColor(0, 0, 0, 90)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawRoundedRect(box.translated(0, 3), h / 2, h / 2)
        painter.setBrush(self.bubble_color)
        painter.drawRoundedRect(box, h / 2, h / 2)
        dark_text = self.bubble_color in (theme.AMBER,)
        painter.setPen(QColor("#1b1300") if dark_text else QColor("white"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
