from __future__ import annotations

from moon_media_lab.tts.base import TTSEngine
from moon_media_lab.tts.engines.mock import MockTTSEngine


def get_tts_engine(name: str) -> TTSEngine:
    normalized = name.lower().strip()
    if normalized in {"auto", "mock"}:
        return MockTTSEngine()
    raise ValueError(f"TTS engine is not implemented yet: {name}")
