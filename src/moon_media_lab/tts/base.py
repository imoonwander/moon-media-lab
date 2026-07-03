from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    name: str

    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str | None = None) -> Path:
        """Write speech audio to output_path and return it."""
