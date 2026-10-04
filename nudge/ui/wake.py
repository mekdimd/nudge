from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

FRAME = 1280  # 80 ms at 16 kHz, what openWakeWord expects


class WakeWord(QObject):
    """Local wake-word detection with openWakeWord. Audio is analysed on this machine and never sent anywhere."""

    detected = Signal()
    failed = Signal(str)

    def __init__(self, model: str, threshold: float = 0.5, settings=None):
        super().__init__()
        self.settings = settings
        from openwakeword.model import Model
        from openwakeword.utils import download_models

        if not Path(model).suffix:  # a bundled name like "hey_jarvis"; fetch it on first run
            download_models([model])
        self._model = Model(wakeword_models=[model], inference_framework="onnx")
        self.threshold = threshold
        self._pending = b""
        self._source: QAudioSource | None = None
        self._io = None

    def start(self) -> None:
        if self._source is not None:
            return
        if self.settings is not None and self.settings.mic_muted:
            return
        device = self.settings.input_device() if self.settings is not None else QMediaDevices.defaultAudioInput()
        fmt = QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if device.isNull() or not device.isFormatSupported(fmt):
            self.failed.emit("no usable microphone")
            return
        self._pending = b""
        self._model.reset()
        self._source = QAudioSource(device, fmt, self)
        self._io = self._source.start()
        self._io.readyRead.connect(self._read)

    def pause(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source = None
            self._io = None

    def close(self) -> None:
        self.pause()

    def _read(self) -> None:
        self._pending += bytes(self._io.readAll())
        size = FRAME * 2
        while len(self._pending) >= size:
            chunk, self._pending = self._pending[:size], self._pending[size:]
            scores = self._model.predict(np.frombuffer(chunk, dtype=np.int16))
            if max(scores.values(), default=0.0) >= self.threshold:
                self._pending = b""
                self.detected.emit()
                return
