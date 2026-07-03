from __future__ import annotations

import os

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.llm.base import LLMProvider

KNOWN_PROVIDERS = {"claude-cli", "codex-cli", "gemini-cli", "mock"}


def resolve_provider_name(name: str) -> str:
    normalized = name.lower().strip()
    if normalized == "auto":
        normalized = os.environ.get("MOON_MEDIA_LAB_LLM_PROVIDER", "claude-cli")
    if normalized not in KNOWN_PROVIDERS:
        raise InvalidArguments(
            f"Unknown LLM provider: {name}",
            hint=f"Known providers: {', '.join(sorted(KNOWN_PROVIDERS))}",
        )
    return normalized


def get_llm_provider(name: str = "auto") -> LLMProvider:
    resolved = resolve_provider_name(name)
    if resolved == "mock":
        from moon_media_lab.llm.providers.mock import MockLLMProvider

        return MockLLMProvider()
    if resolved == "codex-cli":
        from moon_media_lab.llm.providers.codex_cli import CodexCLIProvider

        return CodexCLIProvider()
    if resolved == "gemini-cli":
        from moon_media_lab.llm.providers.gemini_cli import GeminiCLIProvider

        return GeminiCLIProvider()
    from moon_media_lab.llm.providers.claude_cli import ClaudeCLIProvider

    return ClaudeCLIProvider()
