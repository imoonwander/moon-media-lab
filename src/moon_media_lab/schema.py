from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Language = Literal["auto", "zh", "en", "mixed"]
MediaKind = Literal["file", "url", "text"]
RunMode = Literal[
    "transcript",
    "knowledge",
    "english-study",
    "skill",
    "speaker-notes",
    "english-transcript",
    "structured-knowledge",
    "recommendations",
]


@dataclass(frozen=True)
class MediaInput:
    source: str
    kind: MediaKind = "file"
    language: Language = "auto"


@dataclass(frozen=True)
class TranscribeRequest:
    media: MediaInput
    mode: RunMode = "transcript"
    engine: str = "auto"
    need_diarization: bool = False
    need_word_timestamps: bool = False


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class TranscriptMeta:
    engine: str
    model: str
    language: str
    duration_sec: float | None = None
    runtime_sec: float | None = None
    cost_usd: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TranscriptResult:
    meta: TranscriptMeta
    segments: list[TranscriptSegment]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
