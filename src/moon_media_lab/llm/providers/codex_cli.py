from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from moon_media_lab.errors import EngineNotInstalled
from moon_media_lab.llm.base import LLMProvider, LLMResponse
from moon_media_lab.llm.cli_runner import complete_via_cli


class CodexCLIProvider(LLMProvider):
    """Runs the OpenAI Codex CLI non-interactively (`codex exec`)."""

    name = "codex-cli"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.environ.get("MOON_MEDIA_LAB_CODEX_BIN", "codex")

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        resolved = shutil.which(self.binary)
        if not resolved:
            raise EngineNotInstalled(
                f"codex CLI not found: {self.binary}",
                hint="Install Codex CLI or set MOON_MEDIA_LAB_CODEX_BIN.",
            )
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        # stdout mixes agent logs with the answer; --output-last-message gives
        # the clean final message.
        with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as handle:
            last_message = Path(handle.name)
        try:
            argv = [
                resolved,
                "exec",
                "-",
                "--skip-git-repo-check",
                "--output-last-message",
                str(last_message),
            ]
            text = complete_via_cli(
                argv,
                full_prompt,
                provider=self.name,
                extract=lambda _: last_message.read_text(encoding="utf-8"),
            )
        finally:
            last_message.unlink(missing_ok=True)
        return LLMResponse(text=text, provider=self.name, model=None, cloud=True)
