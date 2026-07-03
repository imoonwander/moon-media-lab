from __future__ import annotations

from abc import ABC, abstractmethod

from moon_media_lab.schema import TranscriptResult, TranscribeRequest


class ASREngine(ABC):
    name: str

    @abstractmethod
    def transcribe(self, request: TranscribeRequest) -> TranscriptResult:
        """Return a normalized transcript result."""
