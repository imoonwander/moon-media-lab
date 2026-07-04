from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path

from moon_media_lab.errors import EngineNotInstalled, TranscriptionFailed
from moon_media_lab.tts.base import TTSEngine

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge neural TTS (cloud service, no API key required)."""

    name = "edge-tts"

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        if importlib.util.find_spec("edge_tts") is None:
            raise EngineNotInstalled(
                "edge-tts is not installed.",
                hint="Install the engine group: pip install 'moon-media-lab[tts-edge]'",
            )
        import edge_tts

        resolved_voice = voice or os.environ.get("MOON_MEDIA_LAB_TTS_VOICE", DEFAULT_VOICE)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, resolved_voice)
            await communicate.save(str(output_path))

        try:
            asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001 - edge-tts raises aiohttp/service errors
            raise TranscriptionFailed(
                f"edge-tts synthesis failed: {exc}",
                hint="Check network access and the voice name "
                "(list voices: python -m edge_tts --list-voices).",
            ) from exc
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise TranscriptionFailed("edge-tts produced no audio output.")
        return output_path
