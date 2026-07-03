from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from moon_media_lab.asr.registry import get_asr_engine, resolve_engine_name
from moon_media_lab.errors import InvalidArguments
from moon_media_lab.jobs import append_log, new_job_dir, write_json
from moon_media_lab.media.resolver import resolve_media
from moon_media_lab.schema import MediaInput, TranscribeRequest


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
        lines.append(f"## {segment.start:.2f} - {segment.end:.2f}{speaker}")
        lines.append("")
        lines.append(segment.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_knowledge_md(result) -> str:
    full_text = "\n".join(segment.text for segment in result.segments)
    words = full_text.split()
    preview = " ".join(words[:80])
    return (
        "# Knowledge Notes\n\n"
        "## Source Summary\n\n"
        f"{preview or 'No transcript text available.'}\n\n"
        "## Reusable Assets\n\n"
        "- Topic map: pending LLM processor\n"
        "- Knowledge cards: pending LLM processor\n"
        "- Skill/SOP candidates: pending LLM processor\n"
    )


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
) -> Path:
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

    engine_source = source
    if resolved_engine != "mock":
        if kind == "url":
            raise InvalidArguments(
                "URL ingestion is not implemented yet.",
                hint="Download the media locally first, then pass the file path.",
            )
        if kind == "text":
            raise InvalidArguments(
                f"--kind text is only supported by the mock engine, not {resolved_engine}."
            )
        media = resolve_media(Path(source), job_dir)
        engine_source = media.audio_path
        append_log(
            job_dir,
            f"media resolved: duration={media.duration_sec}s extracted={media.extracted}",
        )
        request = TranscribeRequest(
            media=MediaInput(source=engine_source, kind="file", language=language),
            mode=mode,
            engine=resolved_engine,
            need_diarization=need_diarization,
            need_word_timestamps=need_word_timestamps,
        )

    engine = get_asr_engine(resolved_engine, language, model_dir=model_dir)
    result = engine.transcribe(request)
    write_json(job_dir / "transcript.raw.json", result.to_dict())
    (job_dir / "transcript.md").write_text(render_transcript_md(result), encoding="utf-8")
    if mode in {"knowledge", "skill", "english-study"}:
        (job_dir / "knowledge.md").write_text(render_knowledge_md(result), encoding="utf-8")
    append_log(
        job_dir,
        f"finished engine={result.meta.engine} model={result.meta.model} "
        f"runtime_sec={result.meta.runtime_sec}",
    )
    return job_dir
