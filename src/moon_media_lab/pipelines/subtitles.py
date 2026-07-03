from __future__ import annotations

from moon_media_lab.schema import TranscriptResult


def _timestamp(seconds: float, *, comma: bool) -> str:
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    sep = "," if comma else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def render_srt(result: TranscriptResult) -> str:
    blocks = []
    for index, segment in enumerate(result.segments, start=1):
        start = _timestamp(segment.start, comma=True)
        end = _timestamp(segment.end, comma=True)
        blocks.append(f"{index}\n{start} --> {end}\n{segment.text}")
    return "\n\n".join(blocks) + "\n"


def render_vtt(result: TranscriptResult) -> str:
    blocks = ["WEBVTT"]
    for segment in result.segments:
        start = _timestamp(segment.start, comma=False)
        end = _timestamp(segment.end, comma=False)
        blocks.append(f"{start} --> {end}\n{segment.text}")
    return "\n\n".join(blocks) + "\n"
