from __future__ import annotations

import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from . import theme
from .icons import actor_icon
from .timeline import Entry, Timeline

PRIVACY = {
    "jev": "Jev receives your goal and the labels of on-screen controls to choose the next step. Screenshots never leave your computer.",
    "gemini": "Gemini receives only your goal and the names of empty text fields, and only when text must be written.",
    "vision": "Vision runs on this computer. The screenshot never leaves it; only the labels it finds go to Jev.",
}
MARKS = {"done": ("✓", theme.GREEN), "failed": ("✕", theme.RED), "waiting": ("•", theme.AMBER)}


class Spinner(QWidget):
    def __init__(self, size: int = 12):
        super().__init__()
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._spin)

    def _spin(self) -> None:
        self._angle = (self._angle + 9) % 360
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        p.setPen(QPen(QColor(255, 255, 255, 50), 2))
        p.drawEllipse(box)
        pen = QPen(theme.BLUE, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(box, -self._angle * 16, 100 * 16)


class Shimmer(QWidget):
    """A running entry's text: muted, with a bright band sweeping across it."""

    def __init__(self):
        super().__init__()
        self.text = ""
        self.setFont(theme.font(13))
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)

    def set_text(self, text: str) -> None:
        self.text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self.text) + 4, metrics.height() + 2)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = max(self.width(), 1)
        x = ((time.monotonic() % 1.6) / 1.6) * (w + 160) - 80
        gradient = QLinearGradient(x - 70, 0, x + 70, 0)
        gradient.setColorAt(0.0, theme.MUTED)
        gradient.setColorAt(0.5, QColor("#FFFFFF"))
        gradient.setColorAt(1.0, theme.MUTED)
        p.setPen(QPen(gradient, 1))
        text = self.fontMetrics().elidedText(self.text, Qt.TextElideMode.ElideRight, w)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class EntryRow(QWidget):
    def __init__(self, entry: Entry):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 4, 0)
        row.setSpacing(8)
        self.icon = QLabel()
        self.icon.setFixedSize(18, 18)
        self.spinner = Spinner()
        self.shimmer = Shimmer()
        self.text = QLabel()
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.text.setFont(theme.font(13))
        self.detail = QLabel()
        self.detail.setFont(theme.font(12))
        self.detail.setProperty("muted", "true")
        self.mark = QLabel()
        self.mark.setFont(theme.font(13, QFont.Weight.Bold))
        for widget in (self.icon, self.spinner, self.shimmer, self.text, self.detail):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(self.mark)
        self.set_entry(entry)

    def set_entry(self, entry: Entry) -> None:
        self.icon.setPixmap(actor_icon(entry.actor, entry.app))
        self.icon.setToolTip(PRIVACY.get(entry.actor, entry.app.name if entry.app else ""))
        running = entry.state == "running"
        self.spinner.setVisible(running)
        self.shimmer.setVisible(running)
        self.text.setVisible(not running)
        if running:
            self.shimmer.set_text(entry.plain())
        else:
            self.text.setText(entry.html())
        self.detail.setText(entry.detail)
        self.detail.setVisible(bool(entry.detail))
        mark, color = MARKS.get(entry.state, ("", theme.MUTED))
        self.mark.setText(mark)
        self.mark.setStyleSheet(f"color: {color.name()};")


class Feed(QScrollArea):
    """The run so far, newest at the bottom. Hidden when there's nothing to show."""

    MAX_HEIGHT = 260

    def __init__(self, timeline: Timeline):
        super().__init__()
        self.setObjectName("feed")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline = timeline
        self.body = QWidget()
        self.body.setObjectName("feedBody")
        self.rows_layout = QVBoxLayout(self.body)
        self.rows_layout.setContentsMargins(0, 2, 0, 2)
        self.rows_layout.setSpacing(6)
        self.setWidget(self.body)
        self.rows: list[EntryRow] = []
        timeline.subscribe(self._on_change)
        self.hide()

    def _on_change(self, index: int, added: bool) -> None:
        if index < 0:
            for row in self.rows:
                row.hide()
                row.deleteLater()
            self.rows = []
            self.hide()
            return
        entry = self.timeline.entries[index]
        if added:
            row = EntryRow(entry)
            self.rows_layout.addWidget(row)
            row.show()
            self.rows.append(row)
            self._fade_in(row)
        else:
            self.rows[index].set_entry(entry)
        self.show()
        self._fit()
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def _fit(self) -> None:
        self.rows_layout.activate()
        self.setFixedHeight(min(self.body.sizeHint().height(), self.MAX_HEIGHT))

    def _fade_in(self, row: EntryRow) -> None:
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", row)
        animation.setDuration(180)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: row.setGraphicsEffect(None))
        animation.start()
