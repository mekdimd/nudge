from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme

WIDTH = 760


def _button(text: str, kind: str = "", min_width: int = 0) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setFont(theme.font(16, QFont.Weight.DemiBold))
    b.setMinimumHeight(48)
    if min_width:
        b.setMinimumWidth(min_width)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _label(text: str = "", size: int = 16, muted: bool = False, weight=QFont.Weight.Normal) -> QLabel:
    l = QLabel(text)
    l.setFont(theme.font(size, weight))
    l.setWordWrap(True)
    if muted:
        l.setProperty("muted", "true")
    return l


class Badge(QLabel):
    def __init__(self, tooltip: str):
        super().__init__()
        self.setFont(theme.font(13, QFont.Weight.DemiBold))
        self.setToolTip(tooltip)
        self.set("", "off")

    def set(self, text: str, state: str) -> None:
        colors = {
            "off": ("rgba(255,255,255,0.06)", theme.MUTED.name()),
            "idle": ("rgba(79,142,247,0.16)", "#BFD5FF"),
            "busy": (theme.BLUE.name(), "white"),
            "warn": ("rgba(245,165,36,0.18)", "#FFD58A"),
        }
        bg, fg = colors[state]
        self.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:10px; padding:4px 10px;")
        self.setText(text)


class Bars(QWidget):
    """Jev's top options for the current step, as probability bars."""

    def __init__(self):
        super().__init__()
        self.rows: list[tuple[str, float, bool]] = []
        self.setFixedHeight(0)

    def set_rows(self, rows: list[tuple[str, float, bool]]) -> None:
        self.rows = rows[:3]
        self.setFixedHeight(26 * len(self.rows) + (6 if self.rows else 0))
        self.update()

    def paintEvent(self, _event) -> None:
        if not self.rows:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(theme.font(13))
        w = self.width()
        label_w = int(w * 0.44)
        for i, (label, prob, chosen) in enumerate(self.rows):
            y = i * 26 + 3
            p.setPen(theme.TEXT if chosen else theme.MUTED)
            text = p.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, label_w - 8)
            p.drawText(QRectF(0, y, label_w, 20), Qt.AlignmentFlag.AlignVCenter, text)
            track = QRectF(label_w, y + 6, w - label_w - 52, 8)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 22))
            p.drawRoundedRect(track, 4, 4)
            fill = QRectF(track.x(), track.y(), max(track.width() * prob, 3), track.height())
            p.setBrush(theme.BLUE if chosen else QColor(255, 255, 255, 70))
            p.drawRoundedRect(fill, 4, 4)
            p.setPen(theme.TEXT if chosen else theme.MUTED)
            p.drawText(QRectF(w - 48, y, 48, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{prob:.0%}")


class Bar(QWidget):
    go_requested = Signal(str)
    stop_requested = Signal()
    quit_requested = Signal()

    def __init__(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        super().__init__(None, flags)
        self.setObjectName("bar")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setStyleSheet(theme.STYLE)
        self.setFixedWidth(WIDTH)
        self._drag: QPoint | None = None
        self._enter_action: Callable[[], None] | None = None
        self.running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = _label("Nudge", 15, weight=QFont.Weight.Bold)
        title.setWordWrap(False)
        self.target = Badge("The app Nudge will act in. Click into another app to change it.")
        self.jev = Badge("Jev receives the labels of on-screen controls to choose the next step. Screenshots never leave your computer.")
        self.gemini = Badge("Gemini receives only your goal and the names of empty text fields, and only when text must be written.")
        header.addWidget(title)
        header.addWidget(self.target)
        header.addStretch(1)
        header.addWidget(self.jev)
        header.addWidget(self.gemini)
        close = QPushButton("✕")
        close.setToolTip("Quit Nudge")
        close.setFixedSize(30, 30)
        close.setStyleSheet("padding:0; border-radius:15px; font-size:13px;")
        close.clicked.connect(self.quit_requested.emit)
        header.addWidget(close)
        root.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("What do you want to do?  e.g. turn on Live Caption")
        self.input.setFont(theme.font(20))
        self.input.setMinimumHeight(54)
        self.input.returnPressed.connect(self._go)
        self.go = _button("Go", "primary", 96)
        self.go.setMinimumHeight(54)
        self.go.clicked.connect(self._go)
        self.stop = _button("Stop", "danger", 112)
        self.stop.setMinimumHeight(54)
        self.stop.clicked.connect(self.stop_requested.emit)
        self.stop.hide()
        row.addWidget(self.input, 1)
        row.addWidget(self.go)
        row.addWidget(self.stop)
        root.addLayout(row)

        status_row = QHBoxLayout()
        self.status = _label("Click into an app, then press " + ("⌘⇧Space" if sys.platform == "darwin" else "Ctrl+Shift+Space") + " or type here.", 17)
        self.step = _label("", 13, muted=True)
        self.step.setWordWrap(False)
        self.step.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.step)
        root.addLayout(status_row)

        self.bars = Bars()
        root.addWidget(self.bars)

        self.panel = QWidget()
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(0, 6, 0, 0)
        self.panel_layout.setSpacing(10)
        self.panel.hide()
        root.addWidget(self.panel)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._escape)
        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.quit_requested.emit)

        self.adjustSize()
        self._place()

    # window chrome

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(10, 8, -10, -12)
        for i in range(8, 0, -1):
            shadow = QColor(0, 0, 0, 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(shadow)
            p.drawRoundedRect(card.adjusted(-i, -i + 3, i, i + 3), 24 + i, 24 + i)
        path = QPainterPath()
        path.addRoundedRect(card, 24, 24)
        p.fillPath(path, theme.PANEL)
        p.setPen(QPen(theme.LINE, 1))
        p.drawPath(path)
        accent = QColor(theme.BLUE)
        accent.setAlpha(200 if self.running else 0)
        if self.running:
            p.setPen(QPen(accent, 2))
            p.drawPath(path)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "darwin":
            from .mac_window import float_over_everything

            float_over_everything(self, level=101)

    def _place(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.bottom() - self.height() - 40)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag = None

    def _resize(self) -> None:
        bottom = self.geometry().bottom()
        self.adjustSize()
        self.move(self.x(), bottom - self.height())

    def summon(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        if not self.running:
            self.input.setFocus()
            self.input.selectAll()

    # state

    def _go(self) -> None:
        text = self.input.text().strip()
        if text and not self.running:
            self.go_requested.emit(text)

    def _escape(self) -> None:
        if self.running:
            self.stop_requested.emit()
        else:
            self.hide()

    def set_target(self, name: str | None) -> None:
        self.target.set(f"in {name}" if name else "no app selected", "idle" if name else "warn")

    def set_running(self, running: bool) -> None:
        self.running = running
        self.go.setVisible(not running)
        self.stop.setVisible(running)
        self.input.setReadOnly(running)
        if running:
            self.bars.set_rows([])
            self.step.setText("")
        else:
            self.clear_panel()
        self.update()
        self._resize()

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_jev(self, step: int, milliseconds: int, rows: list[tuple[str, float, bool]], done: float) -> None:
        self.jev.set(f"Jev · {milliseconds} ms", "idle")
        self.step.setText(f"step {step} · done {done:.0%}")
        self.bars.set_rows(rows)
        self._resize()

    def set_jev_idle(self, ok: bool) -> None:
        self.jev.set("Jev · sends control labels" if ok else "Jev · add TYPESAFE_API_KEY", "idle" if ok else "warn")

    def set_gemini(self, state: str, milliseconds: int = 0) -> None:
        if state == "off":
            self.gemini.set("Gemini off", "off")
        elif state == "busy":
            self.gemini.set("Gemini · sending goal + field names", "busy")
        elif state == "done":
            self.gemini.set(f"Gemini · {milliseconds / 1000:.1f} s", "idle")
        else:
            self.gemini.set("Gemini · only for typing", "off")

    def show_result(self, ok: bool, message: str) -> None:
        self.status.setText(("✓ " if ok else "") + message)

    # panels

    def clear_panel(self) -> None:
        self._enter_action = None
        _clear_layout(self.panel_layout)
        self.panel.hide()
        self._resize()

    def _open_panel(self, title: str, tone: str = "") -> None:
        self.clear_panel()
        heading = _label(title, 18, weight=QFont.Weight.DemiBold)
        if tone == "warn":
            heading.setStyleSheet(f"color: {theme.AMBER.name()};")
        self.panel_layout.addWidget(heading)
        self.panel.show()

    def _finish_panel(self, focus: QWidget | None = None) -> None:
        self._resize()
        self.summon()
        if focus is not None:
            focus.setFocus()

    def _buttons(self, specs: list[tuple[str, str, Callable[[], None]]]) -> list[QPushButton]:
        row = QHBoxLayout()
        row.setSpacing(10)
        made = []
        for text, kind, callback in specs:
            b = _button(text, kind)
            b.clicked.connect(lambda _=False, cb=callback: self._answer(cb))
            row.addWidget(b, 1)
            made.append(b)
        self.panel_layout.addLayout(row)
        return made

    def _answer(self, callback: Callable[[], None]) -> None:
        self.clear_panel()
        callback()

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._enter_action and not isinstance(self.focusWidget(), QPlainTextEdit):
            action, self._enter_action = self._enter_action, None
            self._answer(action)
            return
        super().keyPressEvent(e)

    def show_choice(self, reason: str, options: list[tuple[str, str, float]], reply: Callable[[object], None]) -> None:
        self._open_panel(reason)
        first = None
        for key, label, prob in options:
            b = _button(f"{label}    {prob:.0%}", "choice")
            b.setMinimumHeight(56)
            b.clicked.connect(lambda _=False, k=key: self._answer(lambda: reply(k)))
            self.panel_layout.addWidget(b)
            first = first or b
        self._buttons([("Stop", "danger", lambda: reply(None))])
        self._finish_panel(first)

    def show_draft(self, note: str, fields: list[tuple[str, str, str]], reply: Callable[[object], None]) -> None:
        self._open_panel("Check what I'll type")
        self.panel_layout.addWidget(_label(note, 14, muted=True))
        editors: dict[str, QLineEdit | QPlainTextEdit] = {}
        first = None
        for field_id, label, text in fields:
            self.panel_layout.addWidget(_label(label, 13, muted=True))
            multiline = "body" in label.lower() or "message" in label.lower() or len(text) > 80
            if multiline:
                editor = QPlainTextEdit(text)
                editor.setFont(theme.font(16))
                editor.setFixedHeight(130)
            else:
                editor = QLineEdit(text)
                editor.setFont(theme.font(16))
                editor.setMinimumHeight(44)
                if not text:
                    editor.setPlaceholderText("left blank — type it here if needed")
            editors[field_id] = editor
            self.panel_layout.addWidget(editor)
            first = first or editor

        def values() -> dict[str, str]:
            return {fid: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text()) for fid, e in editors.items()}

        approve = lambda: reply(values())
        self._buttons([("Type it", "primary", approve), ("Stop", "danger", lambda: reply(None))])
        self._enter_action = approve
        self._finish_panel(first)

    def show_url(self, url: str | None, fallback: str, reply: Callable[[object], None]) -> None:
        self._open_panel("Go to this address?" if url else "I'm not sure of the address. Search for this instead?")
        editor = QLineEdit(url or fallback)
        editor.setFont(theme.font(17))
        editor.setMinimumHeight(48)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Go", "primary", go), ("Stop", "danger", lambda: reply(None))])
        self._enter_action = go
        self._finish_panel(editor)

    def show_confirm(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message, tone="warn")
        yes, _ = self._buttons([("Yes, do it", "warn", lambda: reply(True)), ("No", "", lambda: reply(False))])
        self._finish_panel(None)

    def show_recover(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        retry, *_ = self._buttons([
            ("Try again", "primary", lambda: reply("retry")),
            ("Click it instead", "", lambda: reply("click")),
            ("Pick something else", "", lambda: reply("other")),
            ("Stop", "danger", lambda: reply("stop")),
        ])
        self._finish_panel(retry)

    def show_ask(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        editor = QLineEdit()
        editor.setPlaceholderText("Optional: add a detail")
        editor.setFont(theme.font(16))
        editor.setMinimumHeight(46)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Continue", "primary", go), ("Stop", "danger", lambda: reply(None))])
        self._enter_action = go
        self._finish_panel(editor)


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if widget := item.widget():
            widget.hide()
            widget.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
            item.layout().deleteLater()
