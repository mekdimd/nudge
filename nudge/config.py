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


def _wake_word(value: str, base: Path = ROOT) -> str:
    """Resolve model paths relative to the configuration folder."""
    if value.lower().endswith(".onnx") and not Path(value).is_absolute():
        return str(base / value)
    return value


def load_environment() -> Path:
    env_file = Path.cwd() / ".env"
    if not env_file.is_file() and (ROOT / ".env").is_file():
        env_file = ROOT / ".env"
    load_dotenv(env_file)
    return env_file


def load_config() -> Config:
    env_file = load_environment()
    return Config(
        typesafe_api_key=os.environ.get("TYPESAFE_API_KEY", "").strip(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", "").strip(),
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb").strip(),
        wake_word=_wake_word(os.environ.get("WAKE_WORD", "hey_jarvis").strip(), env_file.parent),
        wake_threshold=float(os.environ.get("WAKE_THRESHOLD", "0.5")),
    )
