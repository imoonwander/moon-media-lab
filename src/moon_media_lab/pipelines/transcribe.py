from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.asr.registry import get_asr_engine, resolve_engine_name
from moon_media_lab.errors import InvalidArguments, TranscriptionFailed
from moon_media_lab.jobs import append_log, new_job_dir, write_json
from moon_media_lab.media.downloader import download_media, is_url
from moon_media_lab.media.resolver import AudioChunk, resolve_media, split_audio
from moon_media_lab.paths import get_paths
from moon_media_lab.schema import (
    MediaInput,
    TranscribeRequest,
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)

# Audio longer than chunk_sec * 1.5 is transcribed chunk by chunk with checkpoints.
DEFAULT_CHUNK_SEC = 600
CHUNK_MAX_ATTEMPTS = 3


def format_ts(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render_transcript_md(result) -> str:
    lines = ["# Transcript", ""]
    lines.append(
        f"- engine: `{result.meta.engine}`\n"
        f"- model: `{result.meta.model}`\n"
        f"- language: `{result.meta.language}`\n"
        f"- duration_sec: `{result.meta.duration_sec}`\n"
        f"- cost_usd: `{result.meta.cost_usd}`"
    )
    lines.append("")
    for segment in result.segments:
        speaker = f" {segment.speaker}" if segment.speaker else ""
        lines.append(f"## {format_ts(segment.start)} - {format_ts(segment.end)}{speaker}")
        lines.append("")
        lines.append(segment.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _chunk_request(chunk_path: str, base: TranscribeRequest) -> TranscribeRequest:
    return TranscribeRequest(
        media=MediaInput(source=chunk_path, kind="file", language=base.media.language),
        mode=base.mode,
        engine=base.engine,
        need_diarization=base.need_diarization,
        need_word_timestamps=base.need_word_timestamps,
    )


def _result_from_dict(data: dict) -> TranscriptResult:
    return TranscriptResult(
        meta=TranscriptMeta(**data["meta"]),
        segments=[TranscriptSegment(**segment) for segment in data["segments"]],
    )


def _transcribe_with_retry(
    engine: ASREngine,
    request: TranscribeRequest,
    job_dir: Path,
    label: str,
) -> TranscriptResult:
    last_error: Exception | None = None
    for attempt in range(1, CHUNK_MAX_ATTEMPTS + 1):
        try:
            return engine.transcribe(request)
        except TranscriptionFailed as exc:
            last_error = exc
            append_log(job_dir, f"{label} attempt {attempt}/{CHUNK_MAX_ATTEMPTS} failed: {exc}")
            if attempt < CHUNK_MAX_ATTEMPTS:
                _progress(f"{label} failed (attempt {attempt}), retrying...")
                time.sleep(2)
    raise TranscriptionFailed(
        f"{label} failed after {CHUNK_MAX_ATTEMPTS} attempts: {last_error}",
        hint="Fix the cause and rerun `moon-media resume <job-dir>`; finished chunks are kept.",
    ) from last_error


def _merge_results(
    chunks: list[AudioChunk],
    results: list[TranscriptResult],
    request: TranscribeRequest,
) -> TranscriptResult:
    segments: list[TranscriptSegment] = []
    for chunk, result in zip(chunks, results):
        for segment in result.segments:
            # Skip silent/degenerate chunks (e.g. a sub-second tail) in the merge.
            if not segment.text or segment.text == "(empty transcription)":
                continue
            segments.append(
                TranscriptSegment(
                    start=round(chunk.start_sec + segment.start, 2),
                    end=round(min(chunk.start_sec + segment.end, chunk.end_sec), 2),
                    text=segment.text,
                    speaker=segment.speaker,
                    confidence=segment.confidence,
                )
            )

    last_meta = results[-1].meta
    extra = dict(last_meta.extra)
    extra.pop("raw_text", None)
    extra.update({"chunked": True, "chunk_count": len(chunks), "chunks_done": len(results)})
    return TranscriptResult(
        meta=TranscriptMeta(
            engine=last_meta.engine,
            model=last_meta.model,
            language=request.media.language,
            duration_sec=chunks[len(results) - 1].end_sec,
            runtime_sec=round(sum(r.meta.runtime_sec or 0.0 for r in results), 2),
            cost_usd=round(sum(r.meta.cost_usd for r in results), 4),
            extra=extra,
        ),
        segments=segments,
    )


def _run_chunked(
    engine: ASREngine,
    request: TranscribeRequest,
    job_dir: Path,
    chunks: list[AudioChunk],
) -> TranscriptResult:
    """Transcribe chunks sequentially, checkpointing each one to survive restarts."""
    chunk_dir = job_dir / "chunks"
    partial_md = job_dir / "transcript.partial.md"
    results: list[TranscriptResult] = []
    total = len(chunks)
    run_started = time.perf_counter()
    fresh_runtimes: list[float] = []

    for chunk in chunks:
        checkpoint = chunk_dir / f"chunk-{chunk.index:04d}.json"
        window = f"{format_ts(chunk.start_sec)}-{format_ts(chunk.end_sec)}"
        if checkpoint.exists():
            results.append(_result_from_dict(json.loads(checkpoint.read_text(encoding="utf-8"))))
            _progress(f"[chunk {chunk.index + 1}/{total}] {window} restored from checkpoint")
            continue

        result = _transcribe_with_retry(
            engine,
            _chunk_request(chunk.path, request),
            job_dir,
            f"chunk {chunk.index + 1}/{total}",
        )
        write_json(checkpoint, result.to_dict())
        results.append(result)
        append_log(job_dir, f"chunk {chunk.index + 1}/{total} done runtime={result.meta.runtime_sec}s")

        partial_md.write_text(
            render_transcript_md(_merge_results(chunks, results, request)), encoding="utf-8"
        )

        fresh_runtimes.append(result.meta.runtime_sec or 0.0)
        remaining = total - len(results)
        eta = (sum(fresh_runtimes) / len(fresh_runtimes)) * remaining if fresh_runtimes else 0.0
        _progress(
            f"[chunk {chunk.index + 1}/{total}] {window} done in {result.meta.runtime_sec}s, "
            f"elapsed {format_ts(time.perf_counter() - run_started)}, eta {format_ts(eta)}"
        )

    if not results:
        raise TranscriptionFailed("Chunked transcription produced no results.")
    merged = _merge_results(chunks, results, request)
    partial_md.unlink(missing_ok=True)
    return merged


def _load_or_create_chunks(
    job_dir: Path, audio_path: str, chunk_sec: int
) -> list[AudioChunk]:
    manifest_path = job_dir / "chunks" / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [AudioChunk(**chunk) for chunk in data["chunks"]]
    chunks = split_audio(Path(audio_path), job_dir / "chunks", chunk_sec)
    write_json(
        manifest_path,
        {"chunk_sec": chunk_sec, "chunks": [asdict(chunk) for chunk in chunks]},
    )
    return chunks


def _execute(
    request: TranscribeRequest,
    job_dir: Path,
    *,
    chunk_sec: int,
    model_dir: str | None,
    llm: str = "auto",
) -> Path:
    engine_source = request.media.source
    resolved_engine = request.engine
    duration_sec: float | None = None

    if resolved_engine != "mock":
        if request.media.kind == "text":
            raise InvalidArguments(
                f"--kind text is only supported by the mock engine, not {resolved_engine}."
            )
        media_json = job_dir / "media.json"
        if media_json.exists():
            media_data = json.loads(media_json.read_text(encoding="utf-8"))
            engine_source = media_data["audio_path"]
            duration_sec = media_data.get("duration_sec")
        else:
            local_source = Path(request.media.source)
            if request.media.kind == "url":
                _progress(f"downloading {request.media.source} ...")
                local_source = download_media(request.media.source, get_paths().downloads)
                append_log(job_dir, f"downloaded to {local_source}")
                _progress(f"downloaded: {local_source.name}")
            media = resolve_media(local_source, job_dir)
            engine_source = media.audio_path
            duration_sec = media.duration_sec
            append_log(
                job_dir,
                f"media resolved: duration={media.duration_sec}s extracted={media.extracted}",
            )

    engine = get_asr_engine(resolved_engine, request.media.language, model_dir=model_dir)

    if resolved_engine != "mock" and duration_sec and duration_sec > chunk_sec * 1.5:
        chunks = _load_or_create_chunks(job_dir, engine_source, chunk_sec)
        append_log(job_dir, f"chunked run: {len(chunks)} chunks of {chunk_sec}s")
        _progress(f"long media ({format_ts(duration_sec)}): {len(chunks)} chunks of {chunk_sec}s")
        result = _run_chunked(engine, request, job_dir, chunks)
    else:
        result = engine.transcribe(_chunk_request(engine_source, request))

    write_json(job_dir / "transcript.raw.json", result.to_dict())
    (job_dir / "transcript.md").write_text(render_transcript_md(result), encoding="utf-8")
    if request.mode in {"knowledge", "skill", "english-study"}:
        # Transcript artifacts are already on disk: if the LLM step fails,
        # `moon-media process <job-dir>` can redo it without re-transcribing.
        from moon_media_lab.llm.registry import get_llm_provider
        from moon_media_lab.postproc.runner import generate_mode_doc

        generate_mode_doc(result, request.mode, get_llm_provider(llm), job_dir)
    append_log(
        job_dir,
        f"finished engine={result.meta.engine} model={result.meta.model} "
        f"runtime_sec={result.meta.runtime_sec}",
    )
    return job_dir


def run_transcription(
    source: str,
    *,
    mode: str = "transcript",
    language: str = "auto",
    engine_name: str = "auto",
    kind: str = "file",
    need_diarization: bool = False,
    need_word_timestamps: bool = False,
    job_base_dir: Path | None = None,
    model_dir: str | None = None,
    chunk_sec: int = DEFAULT_CHUNK_SEC,
    llm: str = "auto",
) -> Path:
    if kind == "file" and is_url(source):
        kind = "url"
    resolved_engine = resolve_engine_name(engine_name, language)
    request = TranscribeRequest(
        media=MediaInput(source=source, kind=kind, language=language),
        mode=mode,
        engine=resolved_engine,
        need_diarization=need_diarization,
        need_word_timestamps=need_word_timestamps,
    )
    job_dir = new_job_dir("transcribe", base_dir=job_base_dir)
    append_log(job_dir, f"created job for {source} engine={resolved_engine}")
    write_json(job_dir / "input.json", asdict(request))
    return _execute(request, job_dir, chunk_sec=chunk_sec, model_dir=model_dir, llm=llm)


def resume_transcription(
    job_dir: Path, *, model_dir: str | None = None, llm: str = "auto"
) -> Path:
    """Continue an interrupted job from its per-chunk checkpoints."""
    input_json = job_dir / "input.json"
    if not input_json.exists():
        raise InvalidArguments(
            f"Not a job directory (missing input.json): {job_dir}",
            hint="Pass the jobs/transcribe-... folder printed when the job started.",
        )
    if (job_dir / "transcript.raw.json").exists():
        _progress(f"job already finished: {job_dir}")
        return job_dir

    data = json.loads(input_json.read_text(encoding="utf-8"))
    request = TranscribeRequest(
        media=MediaInput(**data["media"]),
        mode=data["mode"],
        engine=data["engine"],
        need_diarization=data["need_diarization"],
        need_word_timestamps=data["need_word_timestamps"],
    )
    manifest_path = job_dir / "chunks" / "manifest.json"
    chunk_sec = DEFAULT_CHUNK_SEC
    if manifest_path.exists():
        chunk_sec = json.loads(manifest_path.read_text(encoding="utf-8"))["chunk_sec"]
    append_log(job_dir, "resuming job")
    return _execute(request, job_dir, chunk_sec=chunk_sec, model_dir=model_dir, llm=llm)
