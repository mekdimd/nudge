from __future__ import annotations

import threading

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QMediaDevices

from .levels import envelope

SAMPLE_RATE = 24000
URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_24000"
MODEL = "eleven_flash_v2_5"  # lowest latency


class Speaker(QObject):
    """Reads a question aloud with ElevenLabs text-to-speech. `finished` fires when the audio ends or can't play."""

    finished = Signal()
    level = Signal(float)  # loudness of what's playing, 0..1

    _audio = Signal(bytes, int)  # pcm, generation (crosses from the request thread)
    _failed = Signal(int)

    def __init__(self, api_key: str, voice_id: str):
        super().__init__()
        self.api_key, self.voice_id = api_key, voice_id
        self.speaking = False
        self._generation = 0
        self._sink: QAudioSink | None = None
        self._buffer: QBuffer | None = None
        self._data: QByteArray | None = None  # QBuffer doesn't own its bytes; keep them alive while playing
        self._envelope: list[float] = []
        self._meter = QTimer(self)
        self._meter.setInterval(30)
        self._meter.timeout.connect(self._emit_level)
        self._audio.connect(self._play)
        self._failed.connect(self._on_failed)

    def say(self, text: str) -> None:
        self.stop()
        if not text.strip() or QMediaDevices.defaultAudioOutput().isNull():
            self.finished.emit()
            return
        self.speaking = True
        generation = self._generation
        threading.Thread(target=self._fetch, args=(text, generation), name="tts", daemon=True).start()

    def stop(self) -> None:
        self._generation += 1  # late audio from an older request is dropped
        self.speaking = False
        self._release()

    def _release(self) -> None:
        self._meter.stop()
        self.level.emit(0.0)
        sink, buffer = self._sink, self._buffer
        self._sink = self._buffer = self._data = None
        if sink is not None:
            sink.stateChanged.disconnect()
            sink.stop()
            sink.deleteLater()  # may be called from the sink's own signal
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()

    # request thread

    def _fetch(self, text: str, generation: int) -> None:
        import httpx

        try:
            response = httpx.post(
                URL.format(voice=self.voice_id),
                headers={"xi-api-key": self.api_key},
                json={"text": text, "model_id": MODEL},
                timeout=15,
            )
            response.raise_for_status()
            self._audio.emit(response.content, generation)
        except Exception:
            self._failed.emit(generation)

    # main thread

    def _play(self, pcm: bytes, generation: int) -> None:
        if generation != self._generation:
            return
        fmt = QAudioFormat()
        fmt.setSampleRate(SAMPLE_RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._data = QByteArray(pcm)
        self._buffer = QBuffer(self)
        self._buffer.setData(self._data)
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), fmt, self)
        self._sink.stateChanged.connect(lambda state: self._on_state(state))
        self._sink.start(self._buffer)
        self._envelope = envelope(pcm, SAMPLE_RATE, 30)
        self._meter.start()

    def _emit_level(self) -> None:
        if self._sink is None:
            return
        index = int(self._sink.processedUSecs() / 30000)
        self.level.emit(self._envelope[index] if index < len(self._envelope) else 0.0)

    def _on_state(self, state) -> None:
        if state == QAudio.State.IdleState and self._sink is not None:  # the buffer is drained
            self.speaking = False
            self._release()
            self.finished.emit()

    def _on_failed(self, generation: int) -> None:
        if generation == self._generation:
            self.speaking = False
            self.finished.emit()
