from __future__ import annotations

import os
import shutil

from moon_media_lab.errors import EngineNotInstalled
from moon_media_lab.llm.base import LLMProvider, LLMResponse
from moon_media_lab.llm.cli_runner import complete_via_cli


class GeminiCLIProvider(LLMProvider):
    """Runs the Google Gemini CLI in headless mode (stdin prompt)."""

    name = "gemini-cli"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.environ.get("MOON_MEDIA_LAB_GEMINI_BIN", "gemini")

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        resolved = shutil.which(self.binary)
        if not resolved:
            raise EngineNotInstalled(
                f"gemini CLI not found: {self.binary}",
                hint="Install Gemini CLI or set MOON_MEDIA_LAB_GEMINI_BIN.",
            )
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        text = complete_via_cli(
            [resolved, "-o", "text"],
            full_prompt,
            provider=self.name,
        )
        return LLMResponse(text=text, provider=self.name, model=None, cloud=True)
