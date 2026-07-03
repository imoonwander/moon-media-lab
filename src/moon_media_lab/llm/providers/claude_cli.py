from __future__ import annotations

import os
import shutil

from moon_media_lab.errors import EngineNotInstalled
from moon_media_lab.llm.base import LLMProvider, LLMResponse
from moon_media_lab.llm.cli_runner import complete_via_cli

# When this tool itself runs inside a Claude Code session, the session injects
# scoped credentials that the nested CLI must not inherit; scrub them so the
# CLI falls back to the user's own configuration.
SESSION_ENV_VARS = (
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_KEY",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
)


class ClaudeCLIProvider(LLMProvider):
    """Runs the locally installed `claude` CLI in non-interactive mode.

    No API key handling here: the CLI uses the user's own login. Output
    quality/model follows the user's CLI configuration.
    """

    name = "claude-cli"

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.environ.get("MOON_MEDIA_LAB_CLAUDE_BIN", "claude")

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        resolved = shutil.which(self.binary)
        if not resolved:
            raise EngineNotInstalled(
                f"claude CLI not found: {self.binary}",
                hint="Install Claude Code (https://claude.com/claude-code) "
                "or set MOON_MEDIA_LAB_CLAUDE_BIN.",
            )
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        env = {k: v for k, v in os.environ.items() if k not in SESSION_ENV_VARS}
        text = complete_via_cli(
            [resolved, "-p", "--output-format", "text"],
            full_prompt,
            provider=self.name,
            env=env,
        )
        return LLMResponse(text=text, provider=self.name, model=None, cloud=True)
