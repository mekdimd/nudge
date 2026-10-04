from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Config:
    typesafe_api_key: str
    gemini_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    wake_word: str
    wake_threshold: float


def load_config() -> Config:
    load_dotenv(ROOT / ".env")
    return Config(
        typesafe_api_key=os.environ.get("TYPESAFE_API_KEY", "").strip(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", "").strip(),
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb").strip(),
        wake_word=os.environ.get("WAKE_WORD", "hey_jarvis").strip(),
        wake_threshold=float(os.environ.get("WAKE_THRESHOLD", "0.5")),
    )
