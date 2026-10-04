from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices


class AudioSettings(QObject):
    """Which microphone to use and what's muted. Remembered between launches."""

    changed = Signal()

    def __init__(self, store: QSettings | None = None):
        super().__init__()
        self._store = store if store is not None else QSettings("Nudge", "Nudge")
        self.missing_saved_input = False

    @property
    def mic_muted(self) -> bool:
        return self._flag("audio/mic_muted")

    @property
    def voice_muted(self) -> bool:
        return self._flag("audio/voice_muted")

    @property
    def sounds_muted(self) -> bool:
        return self._flag("audio/sounds_muted")

    def set_mic_muted(self, on: bool) -> None:
        self._set("audio/mic_muted", bool(on))

    def set_voice_muted(self, on: bool) -> None:
        self._set("audio/voice_muted", bool(on))

    def set_sounds_muted(self, on: bool) -> None:
        self._set("audio/sounds_muted", bool(on))

    def input_device(self) -> QAudioDevice:
        saved = self._store.value("audio/input", "", type=str)
        if saved:
            for device in QMediaDevices.audioInputs():
                if bytes(device.id()).hex() == saved:
                    self.missing_saved_input = False
                    return device
        self.missing_saved_input = bool(saved)
        return QMediaDevices.defaultAudioInput()

    def set_input(self, device: QAudioDevice | None) -> None:
        self._store.setValue("audio/input", bytes(device.id()).hex() if device is not None else "")
        self.changed.emit()

    def _flag(self, key: str) -> bool:
        return self._store.value(key, False, type=bool)

    def _set(self, key: str, value: bool) -> None:
        if self._flag(key) == value:
            return
        self._store.setValue(key, value)
        self.changed.emit()
