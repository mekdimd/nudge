from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QRectF, QSize, Qt
from PySide6.QtGui import QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPen
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QHBoxLayout, QMenu, QStyleFactory, QToolButton, QWidget

from .audio_settings import AudioSettings
from .icons import svg_pixmap

HEIGHT = 54
MUTE_W = 44
ARROW_W = 28


class MicButton(QWidget):
    """One rounded control: the mic mutes, the chevron opens the audio menu. Neither draws past the edge."""

    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.setObjectName("mic")
        self.setFixedSize(MUTE_W + ARROW_W, HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(1, 1, 1, 1)
        row.setSpacing(0)

        self.mute = self._half("micMute", MUTE_W - 1, "Mute the mic")
        self.mute.clicked.connect(lambda: settings.set_mic_muted(not settings.mic_muted))
        self.arrow = self._half("micArrow", ARROW_W - 1, "Choose a microphone")
        self.arrow.setIcon(QIcon(svg_pixmap("chevron", 14)))
        self.arrow.setIconSize(QSize(14, 14))
        self.arrow.clicked.connect(self._popup)
        row.addWidget(self.mute)
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
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawRoundedRect(box, 12, 12)
        painter.setPen(QPen(QColor(255, 255, 255, 32), 1))
        split = self.mute.geometry().right() + 1
        painter.drawLine(QPoint(split, 14), QPoint(split, self.height() - 14))

    def _refresh(self) -> None:
        muted = self.settings.mic_muted
        self.mute.setIcon(QIcon(svg_pixmap("mic-off" if muted else "mic", 20)))
        self.mute.setIconSize(QSize(20, 20))
        self.mute.setToolTip("Unmute the mic" if muted else "Mute the mic")

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
