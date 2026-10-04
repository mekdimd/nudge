from __future__ import annotations

import numpy as np

GAIN = 4.0  # speech RMS sits around 0.05 to 0.2 of full scale


def rms_level(pcm: bytes) -> float:
    """Loudness of 16-bit mono PCM, scaled to 0..1 for the orb."""
    samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32)
    if samples.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(samples * samples))) / 32768.0
    return min(1.0, rms * GAIN)


def envelope(pcm: bytes, rate: int, window_ms: int = 30) -> list[float]:
    size = max(1, rate * window_ms // 1000) * 2
    return [rms_level(pcm[i : i + size]) for i in range(0, len(pcm), size)]
