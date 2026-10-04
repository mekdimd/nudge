from __future__ import annotations

import io
import sys
import wave
from pathlib import Path

import numpy as np
from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtMultimedia import QSoundEffect

RATE = 44100
VOLUME = 0.35
VERSION = "v1"  # bump to regenerate cached files after changing TONES
TONES = {
    "start": [(1046.5, 0.06), (1318.5, 0.06)],
    "tick": [(2000.0, 0.015)],
    "attention": [(880.0, 0.08), (880.0, 0.08)],
    "success": [(1046.5, 0.07), (1318.5, 0.07), (1568.0, 0.12)],
    "failure": [(329.6, 0.09), (261.6, 0.14)],
}


def synth(notes: list[tuple[float, float]]) -> bytes:
    """Soft sine notes with a quick attack and exponential decay, as a 16-bit mono WAV."""
    parts = []
    for frequency, seconds in notes:
        t = np.arange(int(RATE * seconds)) / RATE
        shape = np.minimum(1.0, t / 0.003) * np.exp(-t / (seconds / 3))
        parts.append(np.sin(2 * np.pi * frequency * t) * shape)
        parts.append(np.zeros(int(RATE * 0.015)))
    samples = (np.concatenate(parts) * 0.6 * 32767).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(samples)
    return buffer.getvalue()


class Sounds:
    """Short UI sounds for run start, each press, needing you, success, and failure."""

    def __init__(self, settings, folder: Path | None = None):
        self.settings = settings
        self.effects: dict[str, QSoundEffect] = {}
        try:
            folder = folder or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / "sounds"
            folder.mkdir(parents=True, exist_ok=True)
            for name, notes in TONES.items():
                path = folder / f"{name}-{VERSION}.wav"
                if not path.exists():
                    path.write_bytes(synth(notes))
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(VOLUME)
                self.effects[name] = effect
        except Exception as exc:  # sounds are a nicety; never block startup
            print(f"Sound effects are off: {exc}", file=sys.stderr)
            self.effects = {}

    def play(self, name: str) -> None:
        if self.settings.sounds_muted:
            return
        effect = self.effects.get(name)
        if effect is not None:
            effect.play()
