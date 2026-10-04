from __future__ import annotations

import math
import re
import sys
import time
from typing import Callable

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ..core.models import AppRef
from ..core.safety import MAX_STEPS
from ..core.spoken import match_choice, match_intent
from ..vision.screen import exclude_from_capture
from . import theme
from .feed import Feed
from .icons import actor_icon
from .orb import Orb
from .timeline import Timeline

WIDTH = 760
HOTKEY = "⌘⇧Space" if sys.platform == "darwin" else "Ctrl+Shift+Space"
GLOW = {"working": theme.BLUE, "waiting": theme.AMBER, "success": theme.GREEN}
QUOTED = re.compile(r"“(.+?)”")


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


class TargetChip(QWidget):
    def __init__(self):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 12, 4)
        row.setSpacing(6)
        self.icon = QLabel()
        self.icon.setFixedSize(16, 16)
        self.text = _label("", 13, weight=QFont.Weight.DemiBold)
        self.text.setWordWrap(False)
        row.addWidget(self.icon)
        row.addWidget(self.text)
        self.setToolTip("The app Nudge will act in. Click into another app to change it.")
        self.set(None)

    def set(self, app: AppRef | None) -> None:
        self.warn = app is None
        self.text.setText(f"in {app.name}" if app else "no app selected")
        self.text.setStyleSheet(f"color: {'#FFD58A' if self.warn else theme.TEXT.name()};")
        self.icon.setVisible(app is not None)
        if app is not None:
            self.icon.setPixmap(actor_icon("app", app, 16))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(245, 165, 36, 40) if self.warn else QColor(255, 255, 255, 16))
        box = QRectF(self.rect())
        p.drawRoundedRect(box, box.height() / 2, box.height() / 2)


class ChoiceButton(QPushButton):
    def __init__(self, number: int, label: str, probability: float):
        super().__init__()
        self.setProperty("kind", "choice")
        self.setMinimumHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(12)
        parts = [_label(str(number), 16, weight=QFont.Weight.Bold), _label(label, 16), _label(f"{probability:.0%}", 14, muted=True)]
        parts[0].setStyleSheet(f"color: {theme.BLUE.name()};")
        for i, part in enumerate(parts):
            part.setWordWrap(False)
            part.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(part, 1 if i == 1 else 0)


class Bar(QWidget):
    go_requested = Signal(str)
    stop_requested = Signal()
    quit_requested = Signal()
    panel_closed = Signal()
    peek_toggled = Signal(bool)

    def __init__(self, timeline: Timeline):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        super().__init__(None, flags)
        self.setObjectName("bar")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if sys.platform == "darwin":
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setStyleSheet(theme.STYLE)
        self.setFixedWidth(WIDTH)
        self._drag: QPoint | None = None
        self._anchor_bottom = QGuiApplication.primaryScreen().availableGeometry().bottom() - 40
        self._enter_action: Callable[[], None] | None = None
        self._number_actions: list[Callable[[], None]] = []
        self.spoken: Callable[[str], bool] | None = None  # answers the open prompt from speech; True if it understood
        self.running = False
        self.state = "idle"
        self._retry_goal: str | None = None
        self._glow = 0.0
        self._glow_kind = "working"
        self._flash_until = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(33)
        self._glow_timer.timeout.connect(self._tick_glow)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = _label("Nudge", 15, weight=QFont.Weight.Bold)
        title.setWordWrap(False)
        self.target = TargetChip()
        header.addWidget(title)
        header.addWidget(self.target)
        header.addStretch(1)
        self.peek = QPushButton("Peek")
        self.peek.setCheckable(True)
        self.peek.setToolTip("Show everything Nudge can see on screen (blue: accessibility, green: text fields, orange: vision)")
        self.peek.setFixedHeight(30)
        self.peek.setStyleSheet(
            "QPushButton { padding:0 12px; border-radius:15px; font-size:12px; }"
            f"QPushButton:checked {{ background:{theme.AMBER.name()}; color:#1b1300; border:none; }}"
        )
        self.peek.toggled.connect(self.peek_toggled.emit)
        header.addWidget(self.peek)
        close = QPushButton("✕")
        close.setToolTip("Quit Nudge")
        close.setFixedSize(30, 30)
        close.setStyleSheet("padding:0; border-radius:15px; font-size:13px;")
        close.clicked.connect(self.quit_requested.emit)
        header.addWidget(close)
        root.addLayout(header)

        self.feed = Feed(timeline)
        root.addWidget(self.feed)

        self.panel = QFrame()
        self.panel.setObjectName("card")
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(16, 14, 16, 16)
        self.panel_layout.setSpacing(10)
        self.panel.hide()
        root.addWidget(self.panel)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.orb = Orb()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask Nudge…  e.g. turn on Live Caption")
        self.input.setFont(theme.font(20))
        self.input.setMinimumHeight(54)
        self.input.returnPressed.connect(self._go)
        self.input.textEdited.connect(self._on_edited)
        self.mic_slot = QHBoxLayout()
        self.go = _button("Go", "primary", 112)
        self.go.setMinimumHeight(54)
        self.go.clicked.connect(self._go)
        self.stop = _button("Stop", "stop", 112)
        self.stop.setMinimumHeight(54)
        self.stop.clicked.connect(self.stop_requested.emit)
        self.stop.hide()
        row.addWidget(self.orb)
        row.addWidget(self.input, 1)
        row.addLayout(self.mic_slot)
        row.addWidget(self.go)
        row.addWidget(self.stop)
        root.addLayout(row)

        self.hint = _label("", 13, muted=True)
        root.addWidget(self.hint)
        self.set_status(f"Click into an app, then press {HOTKEY} or type here.")

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._escape)
        QShortcut(QKeySequence.StandardKey.Quit, self, activated=self.quit_requested.emit)
        timeline.subscribe(lambda *_: self._resize())

        self.adjustSize()
        self._place()

    # window chrome

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(10, 8, -10, -12)
        for i in range(8, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 6))
            p.drawRoundedRect(card.adjusted(-i, -i + 3, i, i + 3), 24 + i, 24 + i)
        path = QPainterPath()
        path.addRoundedRect(card, 24, 24)
        p.fillPath(path, theme.PANEL)
        p.setPen(QPen(theme.LINE, 1))
        p.drawPath(path)
        if self._glow > 0.01:
            pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 2 * math.pi / 1.6) if self._glow_kind == "working" else 1.0
            base = QColor(GLOW[self._glow_kind])
            for width, share in ((7, 0.22), (2, 1.0)):
                color = QColor(base)
                color.setAlpha(int(self._glow * (140 + 80 * pulse) * share))
                p.setPen(QPen(color, width))
                p.drawPath(path)

    def _set_state(self, state: str) -> None:
        self.state = state
        if state in GLOW:
            self._glow_kind = state
        self._glow_timer.start()

    def _tick_glow(self) -> None:
        flashing = time.monotonic() < self._flash_until
        target = 1.0 if self.state in ("working", "waiting") or flashing else 0.0
        self._glow += (target - self._glow) * 0.25
        if target == 0.0 and self._glow < 0.01:
            self._glow = 0.0
            self._glow_timer.stop()
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa":
            from .mac_window import float_over_everything

            float_over_everything(self, level=101)
        exclude_from_capture(self)

    def _place(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._anchor_bottom = screen.bottom() - 40
        self.move(screen.center().x() - self.width() // 2, self._anchor_bottom - self.height())

    def _screen_area(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _keep_anchored(self) -> None:
        """The bar grows upward from where its bottom edge sits, and never leaves the screen."""
        area = self._screen_area()
        bottom = min(self._anchor_bottom, area.bottom())
        y = max(area.top(), bottom - self.height())
        x = min(max(self.x(), area.left()), area.right() - self.width())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._drag is None:
            self._keep_anchored()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e) -> None:
        if self._drag is not None:
            self._anchor_bottom = self.geometry().bottom()
        self._drag = None

    def _resize(self) -> None:
        self.adjustSize()
        self._keep_anchored()

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

    def _on_edited(self, text: str) -> None:
        if self._retry_goal is not None and text.strip() != self._retry_goal:
            self._retry_goal = None
            self.go.setText("Go")

    def _escape(self) -> None:
        if self.running:
            self.stop_requested.emit()
        else:
            self.hide()

    def add_mic(self, widget: QWidget) -> None:
        self.mic_slot.addWidget(widget)

    def set_target(self, app: AppRef | None) -> None:
        self.target.set(app)

    def set_running(self, running: bool) -> None:
        self.running = running
        self.go.setVisible(not running)
        self.stop.setVisible(running)
        self.input.setReadOnly(running)
        if running:
            self._retry_goal = None
            self.go.setText("Go")
            self.hint.hide()
        else:
            self.clear_panel()
            self.set_status("")
        self._set_state("working" if running else "idle")
        self._resize()

    def set_status(self, text: str, tone: str = "muted", during_run: bool = False) -> None:
        """The hint line under the input: setup problems, voice state, Peek counts, and the step count."""
        self.hint.setText(text)
        self.hint.setStyleSheet(f"color: {(theme.AMBER if tone == 'warn' else theme.MUTED).name()};")
        self.hint.setVisible(bool(text) and (not self.running or during_run))
        self._resize()

    def set_step(self, step: int) -> None:
        self.set_status(f"Step {step} of {MAX_STEPS} · Esc stops", during_run=True)

    def show_result(self, ok: bool) -> None:
        """The outcome itself is the last feed entry; the bar flashes green, or offers Retry."""
        if ok:
            self._glow_kind = "success"
            self._flash_until = time.monotonic() + 0.9
            self._glow_timer.start()
            return
        self._retry_goal = self.input.text().strip() or None
        if self._retry_goal:
            self.go.setText("↻ Retry")

    # panels

    def clear_panel(self) -> None:
        self._enter_action = None
        self._number_actions = []
        self.spoken = None
        self.panel_closed.emit()
        _clear_layout(self.panel_layout)
        self.panel.hide()
        if self.running:
            self._set_state("working")
        self._resize()

    def _open_panel(self, title: str, tone: str = "", detail: str = "") -> None:
        self.clear_panel()
        heading = _label(title, 17, weight=QFont.Weight.DemiBold)
        if tone == "warn":
            heading.setStyleSheet(f"color: {theme.AMBER.name()};")
        self.panel_layout.addWidget(heading)
        if detail:
            self.panel_layout.addWidget(_label(detail, 14, muted=True))
        self.panel.show()
        if self.running:
            self._set_state("waiting")

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
            row.addWidget(b, 0 if kind == "link" else 1)
            made.append(b)
        self.panel_layout.addLayout(row)
        return made

    def _answer(self, callback: Callable[[], None]) -> None:
        self.clear_panel()
        callback()

    def _typing(self) -> bool:
        focus = self.focusWidget()
        return isinstance(focus, QPlainTextEdit) or (isinstance(focus, QLineEdit) and not focus.isReadOnly())

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._enter_action and not isinstance(self.focusWidget(), QPlainTextEdit):
            action, self._enter_action = self._enter_action, None
            self._answer(action)
            return
        index = e.key() - int(Qt.Key.Key_1)
        if self._number_actions and 0 <= index < len(self._number_actions) and not self._typing():
            self._answer(self._number_actions[index])
            return
        super().keyPressEvent(e)

    def show_choice(self, reason: str, options: list[tuple[str, str, float]], reply: Callable[[object], None]) -> None:
        self._open_panel(reason)
        first = None
        for number, (key, label, prob) in enumerate(options, 1):
            b = ChoiceButton(number, label, prob)
            pick = lambda k=key: reply(k)
            b.clicked.connect(lambda _=False, act=pick: self._answer(act))
            self._number_actions.append(pick)
            self.panel_layout.addWidget(b)
            first = first or b

        def spoken(text: str) -> bool:
            match = match_choice(text, [label for _, label, _ in options])
            if match is None:
                return False
            self._answer(lambda: reply(None if match == "stop" else options[match][0]))
            return True

        self.spoken = spoken
        self._finish_panel(first)

    def show_draft(self, note: str, fields: list[tuple[str, str, str]], reply: Callable[[object], None]) -> None:
        self._open_panel("Check what I'll type", detail=note)
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
                    editor.setPlaceholderText("Left blank. Type it here if needed")
            editors[field_id] = editor
            self.panel_layout.addWidget(editor)
            first = first or editor

        def values() -> dict[str, str]:
            return {fid: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text()) for fid, e in editors.items()}

        approve = lambda: reply(values())
        self._buttons([("Type it", "primary", approve)])
        self._enter_action = approve
        self.spoken = self._yes_or_stop(approve, lambda: reply(None))
        self._finish_panel(first)

    def show_url(self, url: str | None, fallback: str, reply: Callable[[object], None]) -> None:
        self._open_panel("Open this address?" if url else "I'm not sure of the address. Search for this instead?")
        editor = QLineEdit(url or fallback)
        editor.setFont(theme.font(17))
        editor.setMinimumHeight(48)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Open", "primary", go)])
        self._enter_action = go
        self.spoken = self._yes_or_stop(go, lambda: reply(None))
        self._finish_panel(editor)

    def show_confirm(self, message: str, reply: Callable[[object], None]) -> None:
        question, _, rest = message.partition("? ")
        title = f"{question}?" if rest else message
        detail = rest[:1].upper() + rest[1:] if rest else ""
        quoted = QUOTED.search(question)
        yes = f"Yes, {quoted.group(1).lower()}" if quoted else "Yes, do it"
        self._open_panel(title, tone="warn", detail=detail)
        self._buttons([(yes, "warn", lambda: reply(True)), ("Not yet", "", lambda: reply(False))])
        self.spoken = self._intents({"stop": lambda: reply(False), "no": lambda: reply(False), "yes": lambda: reply(True)})
        self._finish_panel(None)

    def show_recover(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        retry = lambda: reply("retry")
        first, *_ = self._buttons([
            ("↻ Retry", "primary", retry),
            ("Click it instead", "", lambda: reply("click")),
            ("Pick another…", "link", lambda: reply("other")),
        ])
        self._enter_action = retry
        self.spoken = self._intents({
            "stop": lambda: reply("stop"),
            "retry": retry,
            "click": lambda: reply("click"),
            "other": lambda: reply("other"),
        })
        self._finish_panel(first)

    def show_ask(self, message: str, reply: Callable[[object], None]) -> None:
        self._open_panel(message)
        editor = QLineEdit()
        editor.setPlaceholderText("Optional: add a detail")
        editor.setFont(theme.font(16))
        editor.setMinimumHeight(46)
        self.panel_layout.addWidget(editor)
        go = lambda: reply(editor.text())
        self._buttons([("Continue", "primary", go)])
        self._enter_action = go
        intents = self._intents({"stop": lambda: reply(None), "yes": go, "no": go})

        def spoken(text: str) -> bool:
            if not intents(text):  # anything else is the detail they were asked for
                editor.setText(text)
                self._answer(go)
            return True

        self.spoken = spoken
        self._finish_panel(editor)

    def _intents(self, actions: dict[str, Callable[[], None]]) -> Callable[[str], bool]:
        def spoken(text: str) -> bool:
            intent = match_intent(text, tuple(actions))
            if intent is None:
                return False
            self._answer(actions[intent])
            return True

        return spoken

    def _yes_or_stop(self, yes: Callable[[], None], stop: Callable[[], None]) -> Callable[[str], bool]:
        return self._intents({"stop": stop, "no": stop, "yes": yes})


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if widget := item.widget():
            widget.hide()
            widget.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
            item.layout().deleteLater()
