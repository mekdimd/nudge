from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QActionGroup, QIcon, QKeySequence
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QMenu, QToolButton

from .audio_settings import AudioSettings
from .icons import svg_pixmap


class MicButton(QToolButton):
    """Click to mute or unmute the mic; the arrow picks a microphone and the other audio toggles."""

    def __init__(self, settings: AudioSettings):
        super().__init__()
        self.settings = settings
        self.setObjectName("mic")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.setFixedHeight(54)
        self.setMinimumWidth(72)
        self.setIconSize(QSize(22, 22))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to mute the mic. Use the arrow to pick a microphone.")
        self.menu_ = QMenu(self)
        self.setMenu(self.menu_)
        self.menu_.aboutToShow.connect(self._rebuild)
        self.clicked.connect(lambda: settings.set_mic_muted(not settings.mic_muted))
        settings.changed.connect(self._refresh)
        self._refresh()
        self._rebuild()

    def _refresh(self) -> None:
        self.setIcon(QIcon(svg_pixmap("mic-off" if self.settings.mic_muted else "mic", 22)))

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
