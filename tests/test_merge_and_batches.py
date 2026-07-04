from moon_media_lab.media.resolver import AudioChunk
from moon_media_lab.pipelines.transcribe import _merge_results, format_ts
from moon_media_lab.postproc.runner import _build_batches
from moon_media_lab.schema import (
    MediaInput,
    TranscribeRequest,
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)


def _chunk_result(text: str) -> TranscriptResult:
    return TranscriptResult(
        meta=TranscriptMeta(engine="mock", model="m", language="zh", runtime_sec=1.0),
        segments=[TranscriptSegment(start=0.0, end=10.0, text=text)],
    )


def test_merge_offsets_segments_by_chunk_start():
    chunks = [
        AudioChunk(index=0, path="a", start_sec=0.0, end_sec=10.0),
        AudioChunk(index=1, path="b", start_sec=10.0, end_sec=20.0),
    ]
    results = [_chunk_result("一"), _chunk_result("二")]
    request = TranscribeRequest(media=MediaInput(source="x", kind="file", language="zh"))
    merged = _merge_results(chunks, results, request)
    assert [s.start for s in merged.segments] == [0.0, 10.0]
    assert merged.meta.duration_sec == 20.0
    assert merged.meta.extra["chunk_count"] == 2


def test_merge_skips_empty_tail_chunks():
    chunks = [
        AudioChunk(index=0, path="a", start_sec=0.0, end_sec=10.0),
        AudioChunk(index=1, path="b", start_sec=10.0, end_sec=10.4),
    ]
    results = [_chunk_result("正文"), _chunk_result("(empty transcription)")]
    request = TranscribeRequest(media=MediaInput(source="x", kind="file", language="zh"))
    merged = _merge_results(chunks, results, request)
    assert len(merged.segments) == 1


def test_batches_respect_char_budget():
    segments = [
        TranscriptSegment(start=i, end=i + 1, text="字" * 1200) for i in range(6)
    ]
    result = TranscriptResult(
        meta=TranscriptMeta(engine="mock", model="m", language="zh"), segments=segments
    )
    batches = _build_batches(result)
    assert sum(len(b) for b in batches) == 6
    assert all(sum(len(s.text) for s in b) >= 3000 for b in batches[:-1])


def test_format_ts():
    assert format_ts(0) == "00:00:00"
    assert format_ts(3661.9) == "01:01:01"
