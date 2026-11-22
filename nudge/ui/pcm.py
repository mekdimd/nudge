"""Microphone capture that yields 16 kHz mono PCM.

On macOS, Qt's 16 kHz conversion can return too many samples. Capture at the
device's native rate and convert here. Other platforms keep 16 kHz capture.
"""

from __future__ import annotations

import sys

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
    """Use native capture on macOS and keep 16 kHz mono int16 elsewhere."""
    if sys.platform != "darwin":
        fmt = QAudioFormat()
        fmt.setSampleRate(TARGET_RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        return fmt if device.isFormatSupported(fmt) else None
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
    if sys.platform == "darwin":
        source.setBufferSize(fmt.sampleRate() * frame)
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
        self._pos = 0  # input position in units of 1/16000 of a sample
        self._raw = b""
        self._filter = None
        if rate > TARGET_RATE:
            cutoff = 7200.0 / rate
            offsets = np.arange(63) - 31
            kernel = 2 * cutoff * np.sinc(2 * cutoff * offsets) * np.hamming(63)
            self._filter = kernel / kernel.sum()
            self._history = np.zeros(62, dtype=np.float32)

    def push(self, data: bytes) -> bytes:
        frame = _WIDTH[self.kind] * max(1, self.channels)
        blob = self._raw + data
        usable = len(blob) // frame * frame
        self._raw = blob[usable:]
        data = blob[:usable]
        if not data:
            return b""
        if self.rate == TARGET_RATE and self.channels == 1 and self.kind == "int16":
            return data
        samples = _mono_float(data, self.channels, self.kind)
        if samples.size == 0:
            return b""
        if self.rate == TARGET_RATE:
            return _float_to_i16(samples)
        if self._filter is not None:
            block = np.concatenate((self._history, samples))
            self._history = block[-62:].copy()
            samples = np.convolve(block, self._filter, mode="valid")
        return self._resample(samples)

    def _resample(self, samples: np.ndarray) -> bytes:
        block = samples if self._hold.size == 0 else np.concatenate((self._hold, samples))
        limit = (len(block) - 1) * TARGET_RATE
        if limit < self._pos:
            self._hold = block
            return b""
        count = (limit - self._pos) // self.rate + 1
        positions = self._pos + np.arange(count, dtype=np.int64) * self.rate
        index, remainder = np.divmod(positions, TARGET_RATE)
        fraction = remainder / TARGET_RATE
        reduced = block[index] * (1 - fraction) + block[np.minimum(index + 1, len(block) - 1)] * fraction
        end = int(positions[-1]) + self.rate
        consumed = min(end // TARGET_RATE, len(block))
        self._hold = block[consumed:].copy()
        self._pos = end - consumed * TARGET_RATE
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
