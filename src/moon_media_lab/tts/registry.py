from __future__ import annotations

import os

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.tts.base import TTSEngine
from moon_media_lab.tts.engines.mock import MockTTSEngine

KNOWN_ENGINES = {"edge-tts", "mock"}


def get_tts_engine(name: str) -> TTSEngine:
    normalized = name.lower().strip()
    if normalized == "auto":
        normalized = os.environ.get("MOON_MEDIA_LAB_DEFAULT_TTS_ENGINE", "edge-tts")
    if normalized == "mock":
        return MockTTSEngine()
    if normalized == "edge-tts":
        from moon_media_lab.tts.engines.edge import EdgeTTSEngine

        return EdgeTTSEngine()
    raise InvalidArguments(
        f"Unknown TTS engine: {name}",
        hint=f"Known engines: {', '.join(sorted(KNOWN_ENGINES))}",
    )
