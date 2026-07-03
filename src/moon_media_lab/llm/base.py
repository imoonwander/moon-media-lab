from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str | None = None
    cloud: bool = True


class LLMProvider(ABC):
    """Adapter contract for text completion. Post processors must not
    depend on any provider-specific API."""

    name: str

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        """Return the completion for a single prompt."""
