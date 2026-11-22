"""Microphone capture that yields 16 kHz mono PCM.

Qt's resampler delivers 16 kHz too fast on macOS (measured around 1.2x to 1.4x on
the built-in mic), so the wake word and speech-to-text heard sped-up speech and
missed it. Record at the device's own rate and convert here.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource

TARGET_RATE = 16000

_KIND = {
    QAudioFormat.SampleFormat.UInt8: "uint8",
    QAudioFormat.SampleFormat.Int16: "int16",
    QAudioFormat.SampleFormat.Int32: "int32",
    QAudioFormat.SampleFormat.Float: "float32",
}
_WIDTH = {"uint8": 1, "int16": 2, "int32": 4, "float32": 4}


def input_format(device: QAudioDevice) -> QAudioFormat | None:
    """The format to open. Prefer the device's own rate over asking Qt to resample."""
    preferred = device.preferredFormat()
    candidates = []
    if preferred.sampleRate() >= 8000:
        candidates.append(preferred)
    rate = preferred.sampleRate() if preferred.sampleRate() >= 8000 else 48000
    for sample_rate, sample_format in (
        (rate, QAudioFormat.SampleFormat.Int16),
        (rate, QAudioFormat.SampleFormat.Float),
        (48000, QAudioFormat.SampleFormat.Int16),
        (TARGET_RATE, QAudioFormat.SampleFormat.Int16),
    ):
        fmt = QAudioFormat()
        fmt.setSampleRate(sample_rate)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(sample_format)
        candidates.append(fmt)
    for fmt in candidates:
        if _KIND.get(fmt.sampleFormat()) and device.isFormatSupported(fmt):
            return fmt
    return None


def open_mic(device: QAudioDevice, parent):
    """Open `device` and a converter to 16 kHz mono int16. None when the mic can't be opened."""
    if device.isNull():
        return None
    fmt = input_format(device)
    kind = None if fmt is None else _KIND.get(fmt.sampleFormat())
    if fmt is None or kind is None:
        return None
    source = QAudioSource(device, fmt, parent)
    frame = _WIDTH[kind] * max(1, fmt.channelCount())
    source.setBufferSize(fmt.sampleRate() * frame)  # a second of slack so a busy UI doesn't drop audio
    io = source.start()
    # PySide wraps this enum twice, so identity comparison against QAudio.Error is unreliable.
    if io is None or source.error().name != "NoError":
        source.stop()
        return None
    return source, io, PcmStream(fmt.sampleRate(), max(1, fmt.channelCount()), kind)


class PcmStream:
    """Converts device-format chunks into a continuous 16 kHz mono int16 stream."""

    def __init__(self, rate: int, channels: int, kind: str):
        self.rate = rate
        self.channels = channels
        self.kind = kind
        self._hold = np.zeros(0, dtype=np.float32)
        self._pos = 0.0

    def push(self, data: bytes) -> bytes:
        if not data:
            return b""
        if self.rate == TARGET_RATE and self.channels == 1 and self.kind == "int16":
            return data[: len(data) // 2 * 2]
        samples = _mono_float(data, self.channels, self.kind)
        if samples.size == 0:
            return b""
        if self.rate == TARGET_RATE:
            return _float_to_i16(samples)
        if self.rate % TARGET_RATE == 0:
            return self._decimate(samples, self.rate // TARGET_RATE)
        return self._resample(samples, self.rate / TARGET_RATE)

    def _decimate(self, samples: np.ndarray, factor: int) -> bytes:
        block = samples if self._hold.size == 0 else np.concatenate((self._hold, samples))
        usable = len(block) // factor * factor
        self._hold = block[usable:]
        if usable == 0:
            return b""
        return _float_to_i16(block[:usable].reshape(-1, factor).mean(axis=1))

    def _resample(self, samples: np.ndarray, step: float) -> bytes:
        block = samples if self._hold.size == 0 else np.concatenate((self._hold, samples))
        window = max(1, int(round(step)))
        limit = len(block) - window
        if limit < self._pos:
            self._hold = block
            return b""
        count = int(np.floor((limit - self._pos) / step)) + 1
        starts = self._pos + np.arange(count) * step
        index = starts.astype(np.int32)
        reduced = block[index[:, None] + np.arange(window)].mean(axis=1)
        end = float(starts[-1] + step)
        if end >= len(block):
            self._hold = np.zeros(0, dtype=np.float32)
            self._pos = end - len(block)
        else:
            consumed = int(end)
            self._hold = block[consumed:]
            self._pos = end - consumed
        return _float_to_i16(reduced)


def _mono_float(data: bytes, channels: int, kind: str) -> np.ndarray:
    if kind == "float32":
        samples = np.frombuffer(data[: len(data) // 4 * 4], dtype="<f4")
    elif kind == "int16":
        samples = np.frombuffer(data[: len(data) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
    elif kind == "int32":
        samples = np.frombuffer(data[: len(data) // 4 * 4], dtype="<i4").astype(np.float32) / 2147483648.0
    elif kind == "uint8":
        samples = (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        return np.zeros(0, dtype=np.float32)
    if channels > 1:
        usable = len(samples) // channels * channels
        samples = samples[:usable].reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(samples, dtype=np.float32)


def _float_to_i16(samples: np.ndarray) -> bytes:
    return np.clip(np.rint(samples * 32767.0), -32768, 32767).astype("<i2").tobytes()
