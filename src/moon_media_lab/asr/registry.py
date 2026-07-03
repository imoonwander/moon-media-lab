from __future__ import annotations

import os

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.asr.engines.mock import MockASREngine
from moon_media_lab.errors import EngineNotInstalled, InvalidArguments

# Default language routing per docs/architecture.md. faster-whisper lands in Phase 2.
LANGUAGE_ROUTES = {
    "zh": "sensevoice",
    "en": "faster-whisper",
    "mixed": "faster-whisper",
}

KNOWN_ENGINES = {"mock", "sensevoice", "paraformer", "faster-whisper", "openai"}

# Engines that can label speakers.
DIARIZATION_ENGINES = {"paraformer"}


def resolve_engine_name(engine: str, language: str = "auto") -> str:
    normalized = engine.lower().strip()
    if normalized != "auto":
        if normalized not in KNOWN_ENGINES:
            raise InvalidArguments(
                f"Unknown ASR engine: {engine}",
                hint=f"Known engines: {', '.join(sorted(KNOWN_ENGINES))}",
            )
        return normalized
    routed = LANGUAGE_ROUTES.get(language)
    if routed:
        return routed
    return os.environ.get("MOON_MEDIA_LAB_DEFAULT_ASR_ENGINE", "sensevoice")


def get_asr_engine(
    name: str,
    language: str = "auto",
    model_dir: str | None = None,
) -> ASREngine:
    resolved = resolve_engine_name(name, language)
    if resolved == "mock":
        return MockASREngine()
    if resolved == "sensevoice":
        from moon_media_lab.asr.engines.sensevoice import SenseVoiceEngine

        return SenseVoiceEngine(model_dir=model_dir)
    if resolved == "paraformer":
        from moon_media_lab.asr.engines.paraformer import ParaformerEngine

        return ParaformerEngine(model_dir=model_dir)
    if resolved == "faster-whisper":
        from moon_media_lab.asr.engines.faster_whisper import FasterWhisperEngine

        return FasterWhisperEngine(model_dir=model_dir)
    raise EngineNotInstalled(
        f"ASR engine is not implemented yet: {resolved}",
        hint="Available engines: sensevoice, faster-whisper, mock.",
    )
