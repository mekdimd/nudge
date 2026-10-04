from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPen
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QHBoxLayout, QMenu, QStyleFactory, QToolButton, QWidget

from . import theme
from .audio_settings import AudioSettings
from .icons import svg_pixmap

HEIGHT = 44
TALK_W = 40
ARROW_W = 24
RADIUS = 10


class MicButton(QWidget):
    """One rounded control: the mic talks to Nudge, the chevron opens the audio menu (mute lives there)."""

    talk_requested = Signal()

    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.listening = False
        self.setObjectName("mic")
        self.setFixedSize(TALK_W + ARROW_W, HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(1, 1, 1, 1)
        row.setSpacing(0)

        self.talk = self._half("micTalk", TALK_W - 1, "")
        self.talk.setCheckable(True)
        self.talk.clicked.connect(self._on_talk)
        self.arrow = self._half("micArrow", ARROW_W - 1, "Choose a microphone, or mute")
        self.arrow.setIcon(QIcon(svg_pixmap("chevron", 12)))
        self.arrow.setIconSize(QSize(12, 12))
        self.arrow.clicked.connect(self._popup)
        row.addWidget(self.talk)
        row.addWidget(self.arrow)

        self.menu_ = QMenu(self)
        self.menu_.aboutToShow.connect(self._rebuild)
        settings.changed.connect(self._refresh)
        self._refresh()
        self._rebuild()

    def _half(self, name: str, width: int, tip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(name)
        style = QStyleFactory.create("Fusion")
        style.setParent(button)
        button.setStyle(style)
        button.setFixedSize(width, HEIGHT - 2)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tip)
        return button

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        border = QColor(theme.BLUE) if self.listening else QColor(255, 255, 255, 26)
        painter.setPen(QPen(border, 1))
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawRoundedRect(box, RADIUS, RADIUS)
        painter.setPen(QPen(QColor(255, 255, 255, 32), 1))
        split = self.talk.geometry().right() + 1
        painter.drawLine(QPoint(split, 12), QPoint(split, self.height() - 12))

    def _on_talk(self) -> None:
        self.talk.setChecked(self.listening)  # the voice state decides, so the button never drifts from it
        self.talk_requested.emit()

    def set_listening(self, on: bool) -> None:
        self.listening = on
        self.talk.setChecked(on)
        self._refresh()
        self.update()

    def _refresh(self) -> None:
        muted = self.settings.mic_muted
        self.talk.setIcon(QIcon(svg_pixmap("mic-off" if muted and not self.listening else "mic", 18)))
        self.talk.setIconSize(QSize(18, 18))
        if self.listening:
            tip = "Stop listening"
        elif muted:
            tip = "Talk to Nudge (unmutes the mic)"
        else:
            tip = "Talk to Nudge, or say the wake word"
        self.talk.setToolTip(tip)

    def _popup(self) -> None:
        self.menu_.popup(self.arrow.mapToGlobal(QPoint(0, self.arrow.height() + 4)))

    def _rebuild(self) -> None:
        menu = self.menu_
        menu.clear()
        heading = menu.addAction("Microphone")
        heading.setEnabled(False)
        group = QActionGroup(menu)
        group.setExclusive(True)
        current = self.settings.input_device()
        for device in QMediaDevices.audioInputs():
            action = menu.addAction(device.description())
            action.setCheckable(True)
            action.setChecked(device.id() == current.id())
            group.addAction(action)
            action.triggered.connect(lambda _=False, d=device: self.settings.set_input(d))
        if self.settings.missing_saved_input:
            note = menu.addAction("Saved mic not found. Using the default")
            note.setEnabled(False)
        menu.addSeparator()
        self._toggle("Mute mic", self.settings.mic_muted, self.settings.set_mic_muted, QKeySequence("Ctrl+M"))
        self._toggle("Mute Nudge's voice", self.settings.voice_muted, self.settings.set_voice_muted)
        self._toggle("Sound effects", not self.settings.sounds_muted, lambda on: self.settings.set_sounds_muted(not on))

    def _toggle(self, text: str, checked: bool, setter: Callable[[bool], None], shortcut: QKeySequence | None = None) -> None:
        action = self.menu_.addAction(text)
        action.setCheckable(True)
        action.setChecked(checked)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.toggled.connect(setter)
