from __future__ import annotations

import time
from pathlib import Path

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.schema import TranscriptMeta, TranscriptResult, TranscriptSegment, TranscribeRequest


class MockASREngine(ASREngine):
    name = "mock"

    def transcribe(self, request: TranscribeRequest) -> TranscriptResult:
        started = time.perf_counter()
        source = Path(request.media.source)
        if source.exists() and source.is_file():
            text = source.read_text(encoding="utf-8").strip()
        else:
            text = request.media.source.strip()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            lines = ["Mock transcript is empty because the input had no readable text."]

        segments: list[TranscriptSegment] = []
        cursor = 0.0
        for line in lines:
            duration = max(2.0, min(12.0, len(line) / 12))
            segments.append(
                TranscriptSegment(
                    start=round(cursor, 2),
                    end=round(cursor + duration, 2),
                    speaker="SPEAKER_00" if request.need_diarization else None,
                    text=line,
                    confidence=1.0,
                )
            )
            cursor += duration

        return TranscriptResult(
            meta=TranscriptMeta(
                engine=self.name,
                model="mock-text-as-transcript",
                language=request.media.language,
                duration_sec=round(cursor, 2),
                runtime_sec=round(time.perf_counter() - started, 4),
                cost_usd=0.0,
            ),
            segments=segments,
        )
