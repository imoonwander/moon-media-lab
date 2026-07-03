from __future__ import annotations

from moon_media_lab.llm.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Echoes input for plumbing tests without any network call."""

    name = "mock"

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        return LLMResponse(
            text=f"[mock-llm output]\n\n{prompt[-500:]}",
            provider=self.name,
            model="mock",
            cloud=False,
        )
