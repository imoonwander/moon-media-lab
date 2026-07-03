from __future__ import annotations

from pathlib import Path

from moon_media_lab.tts.base import TTSEngine


class MockTTSEngine(TTSEngine):
    name = "mock"

    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"MOCK TTS\nvoice={voice or 'default'}\n\n{text}\n",
            encoding="utf-8",
        )
        return output_path
