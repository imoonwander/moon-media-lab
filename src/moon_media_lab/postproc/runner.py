from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.jobs import append_log, write_json
from moon_media_lab.llm.base import LLMProvider
from moon_media_lab.postproc.prompts import CLEANUP, MODE_PROMPTS, SPEAKER_NAMING, SYSTEM
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
# Batches are independent; run several LLM calls at once.
DEFAULT_LLM_CONCURRENCY = 3


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


def name_speakers(
    result: TranscriptResult,
    provider: LLMProvider,
    job_dir: Path,
) -> Path:
    """Infer real names/roles for SPEAKER_NN labels and re-render artifacts."""
    speakers = sorted({s.speaker for s in result.segments if s.speaker})
    if len(speakers) < 2:
        raise InvalidArguments(
            "Transcript has fewer than two labeled speakers; nothing to name.",
            hint="Run the transcribe job with --diarization first.",
        )

    # A few early + middle turns per speaker are enough context to infer roles.
    samples: list[str] = []
    for speaker in speakers:
        turns = [s.text for s in result.segments if s.speaker == speaker]
        picked = turns[:8] + turns[len(turns) // 2 : len(turns) // 2 + 4]
        joined = "\n".join(f"- {t[:120]}" for t in picked)
        samples.append(f"{speaker}:\n{joined}")

    _progress(f"naming {len(speakers)} speakers with {provider.name}...")
    response = provider.complete(
        SPEAKER_NAMING.format(samples="\n\n".join(samples)), system=SYSTEM
    )
    raw = response.text.strip().strip("`")
    if raw.startswith("json"):
        raw = raw[4:]
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidArguments(
            f"Speaker naming returned non-JSON output: {response.text[:200]}"
        ) from exc
    mapping = {k: str(v).strip() for k, v in mapping.items() if k in speakers and str(v).strip()}
    if not mapping:
        raise InvalidArguments("Speaker naming produced no usable mapping.")

    names_path = job_dir / "postproc" / "speakers.json"
    names_path.parent.mkdir(exist_ok=True)
    write_json(names_path, mapping)
    _provenance(response.provider, response.cloud, job_dir, "speakers.json")

    named = TranscriptResult(
        meta=result.meta,
        segments=[
            TranscriptSegment(
                start=s.start,
                end=s.end,
                text=s.text,
                speaker=mapping.get(s.speaker, s.speaker) if s.speaker else None,
                confidence=s.confidence,
            )
            for s in result.segments
        ],
    )
    from moon_media_lab.pipelines.subtitles import render_srt, render_vtt
    from moon_media_lab.pipelines.transcribe import render_transcript_md

    (job_dir / "transcript.md").write_text(render_transcript_md(named), encoding="utf-8")
    (job_dir / "segments.srt").write_text(render_srt(named), encoding="utf-8")
    (job_dir / "segments.vtt").write_text(render_vtt(named), encoding="utf-8")
    append_log(job_dir, f"postproc speakers named: {mapping}")
    _progress(f"speakers: {mapping}")
    return names_path


def _build_batches(result: TranscriptResult) -> list[list[TranscriptSegment]]:
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
    return batches


def clean_transcript(
    result: TranscriptResult,
    provider: LLMProvider,
    job_dir: Path,
) -> Path:
    """Clean segments in concurrent batches with per-batch checkpoints."""
    postproc_dir = job_dir / "postproc"
    postproc_dir.mkdir(exist_ok=True)

    batches = _build_batches(result)
    total = len(batches)
    cleaned: dict[int, str] = {}
    pending: list[int] = []
    for index, batch in enumerate(batches):
        checkpoint = postproc_dir / f"clean-{index:04d}.json"
        if checkpoint.exists():
            cleaned[index] = json.loads(checkpoint.read_text(encoding="utf-8"))["text"]
        else:
            pending.append(index)
    if cleaned:
        _progress(f"[clean] {len(cleaned)}/{total} batches restored from checkpoints")

    lock = threading.Lock()
    done_count = 0
    run_started = time.perf_counter()

    def _clean_one(index: int) -> tuple[int, str, bool]:
        batch = batches[index]
        text = "\n".join(segment.text for segment in batch)
        response = provider.complete(CLEANUP.format(text=text), system=SYSTEM)
        checkpoint = postproc_dir / f"clean-{index:04d}.json"
        write_json(
            checkpoint,
            {"start": batch[0].start, "end": batch[-1].end, "text": response.text},
        )
        return index, response.text, response.cloud

    if pending:
        workers = int(os.environ.get("MOON_MEDIA_LAB_LLM_CONCURRENCY", DEFAULT_LLM_CONCURRENCY))
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(_clean_one, index) for index in pending]
            cloud_seen = False
            for future in as_completed(futures):
                index, text, cloud = future.result()
                cloud_seen = cloud_seen or cloud
                with lock:
                    cleaned[index] = text
                    done_count += 1
                    elapsed = time.perf_counter() - run_started
                    eta = elapsed / done_count * (len(pending) - done_count)
                    batch = batches[index]
                    _progress(
                        f"[clean {len(cleaned)}/{total}] "
                        f"{_format_ts(batch[0].start)}-{_format_ts(batch[-1].end)} done, "
                        f"eta {_format_ts(eta)}"
                    )
                    append_log(job_dir, f"clean batch {index + 1}/{total} done")
        _provenance(provider.name, cloud_seen, job_dir, "transcript.clean.md")

    lines = ["# Transcript (cleaned)", ""]
    for index, batch in enumerate(batches):
        lines.append(f"## {_format_ts(batch[0].start)} - {_format_ts(batch[-1].end)}")
        lines.append("")
        lines.append(cleaned[index])
        lines.append("")
    output = job_dir / "transcript.clean.md"
    output.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    append_log(job_dir, "postproc transcript.clean.md done")
    return output
