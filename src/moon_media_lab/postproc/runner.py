from __future__ import annotations

import json
import sys
from pathlib import Path

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.jobs import append_log, write_json
from moon_media_lab.llm.base import LLMProvider
from moon_media_lab.postproc.prompts import CLEANUP, MODE_PROMPTS, SYSTEM
from moon_media_lab.schema import (
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)

MODE_FILES = {
    "knowledge": "knowledge.md",
    "english-study": "english-study.md",
    "skill": "skill-draft.md",
}

# Cleanup batches keep each LLM call small enough to stay accurate.
CLEAN_BATCH_CHARS = 3000


def _format_ts(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def load_result(job_dir: Path) -> TranscriptResult:
    raw = job_dir / "transcript.raw.json"
    if not raw.exists():
        raise InvalidArguments(
            f"No transcript.raw.json in {job_dir}",
            hint="Run or resume the transcribe job first.",
        )
    data = json.loads(raw.read_text(encoding="utf-8"))
    return TranscriptResult(
        meta=TranscriptMeta(**data["meta"]),
        segments=[TranscriptSegment(**segment) for segment in data["segments"]],
    )


def transcript_as_text(result: TranscriptResult) -> str:
    lines = []
    for segment in result.segments:
        lines.append(f"[{_format_ts(segment.start)}] {segment.text}")
    return "\n".join(lines)


def _provenance(provider_name: str, cloud: bool, job_dir: Path, filename: str) -> None:
    """Record which LLM saw the data, per open-source-engineering privacy rules."""
    manifest_path = job_dir / "postproc" / "provenance.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[filename] = {"provider": provider_name, "cloud": cloud}
    manifest_path.parent.mkdir(exist_ok=True)
    write_json(manifest_path, manifest)


def generate_mode_doc(
    result: TranscriptResult,
    mode: str,
    provider: LLMProvider,
    job_dir: Path,
) -> Path:
    """One LLM call: full transcript in, mode document out."""
    if mode not in MODE_PROMPTS:
        raise InvalidArguments(f"Unknown post-processing mode: {mode}")
    filename = MODE_FILES[mode]
    _progress(f"generating {filename} with {provider.name}...")
    prompt = MODE_PROMPTS[mode].format(transcript=transcript_as_text(result))
    response = provider.complete(prompt, system=SYSTEM)
    output = job_dir / filename
    output.write_text(response.text + "\n", encoding="utf-8")
    _provenance(response.provider, response.cloud, job_dir, filename)
    append_log(job_dir, f"postproc {filename} done provider={response.provider}")
    return output


def clean_transcript(
    result: TranscriptResult,
    provider: LLMProvider,
    job_dir: Path,
) -> Path:
    """Clean segments in batches with per-batch checkpoints, keep timestamps."""
    postproc_dir = job_dir / "postproc"
    postproc_dir.mkdir(exist_ok=True)

    batches: list[list[TranscriptSegment]] = []
    current: list[TranscriptSegment] = []
    size = 0
    for segment in result.segments:
        current.append(segment)
        size += len(segment.text)
        if size >= CLEAN_BATCH_CHARS:
            batches.append(current)
            current, size = [], 0
    if current:
        batches.append(current)

    cleaned_parts: list[tuple[float, float, str]] = []
    total = len(batches)
    for index, batch in enumerate(batches):
        checkpoint = postproc_dir / f"clean-{index:04d}.json"
        start, end = batch[0].start, batch[-1].end
        if checkpoint.exists():
            data = json.loads(checkpoint.read_text(encoding="utf-8"))
            cleaned_parts.append((start, end, data["text"]))
            _progress(f"[clean {index + 1}/{total}] restored from checkpoint")
            continue
        text = "\n".join(segment.text for segment in batch)
        response = provider.complete(CLEANUP.format(text=text), system=SYSTEM)
        write_json(checkpoint, {"start": start, "end": end, "text": response.text})
        cleaned_parts.append((start, end, response.text))
        _provenance(response.provider, response.cloud, job_dir, "transcript.clean.md")
        append_log(job_dir, f"clean batch {index + 1}/{total} done")
        _progress(f"[clean {index + 1}/{total}] {_format_ts(start)}-{_format_ts(end)} done")

    lines = ["# Transcript (cleaned)", ""]
    for start, end, text in cleaned_parts:
        lines.append(f"## {_format_ts(start)} - {_format_ts(end)}")
        lines.append("")
        lines.append(text)
        lines.append("")
    output = job_dir / "transcript.clean.md"
    output.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    append_log(job_dir, "postproc transcript.clean.md done")
    return output
