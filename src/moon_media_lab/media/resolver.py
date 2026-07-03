from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from moon_media_lab.errors import MediaProbeFailed
from moon_media_lab.jobs import write_json

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1


def find_tool(name: str) -> str | None:
    """Locate ffmpeg/ffprobe from MOON_MEDIA_LAB_FFMPEG or PATH."""
    override = os.environ.get("MOON_MEDIA_LAB_FFMPEG")
    if override:
        override_path = Path(override)
        if name == "ffmpeg" and override_path.is_file():
            return str(override_path)
        sibling = override_path.parent / name
        if sibling.is_file():
            return str(sibling)
    return shutil.which(name)


@dataclass(frozen=True)
class ResolvedMedia:
    source: str
    audio_path: str
    duration_sec: float | None
    sample_rate: int | None
    channels: int | None
    codec: str | None
    extracted: bool


def probe(path: Path) -> dict:
    ffprobe = find_tool("ffprobe")
    if not ffprobe:
        raise MediaProbeFailed(
            "ffprobe not found.",
            hint="Install ffmpeg (e.g. `brew install ffmpeg`) or set MOON_MEDIA_LAB_FFMPEG.",
        )
    argv = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"ffprobe failed for {path}: {completed.stderr.strip()}",
            hint="Check that the file is a valid audio/video file.",
        )
    return json.loads(completed.stdout)


def resolve_media(source: Path, job_dir: Path) -> ResolvedMedia:
    """Probe media and produce a normalized 16 kHz mono wav for ASR engines."""
    if not source.exists() or not source.is_file():
        raise MediaProbeFailed(f"Media file not found: {source}")

    info = probe(source)
    audio_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None
    )
    if audio_stream is None:
        raise MediaProbeFailed(f"No audio stream found in {source}")

    duration_raw = info.get("format", {}).get("duration") or audio_stream.get("duration")
    duration_sec = round(float(duration_raw), 2) if duration_raw else None
    sample_rate = int(audio_stream["sample_rate"]) if audio_stream.get("sample_rate") else None
    channels = audio_stream.get("channels")
    codec = audio_stream.get("codec_name")

    already_normalized = (
        source.suffix.lower() == ".wav"
        and sample_rate == TARGET_SAMPLE_RATE
        and channels == TARGET_CHANNELS
        and codec == "pcm_s16le"
    )
    if already_normalized:
        audio_path = source
        extracted = False
    else:
        ffmpeg = find_tool("ffmpeg")
        if not ffmpeg:
            raise MediaProbeFailed(
                "ffmpeg not found.",
                hint="Install ffmpeg (e.g. `brew install ffmpeg`) or set MOON_MEDIA_LAB_FFMPEG.",
            )
        audio_path = job_dir / "audio.wav"
        argv = [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-vn",
            "-ac",
            str(TARGET_CHANNELS),
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-acodec",
            "pcm_s16le",
            str(audio_path),
        ]
        completed = subprocess.run(argv, capture_output=True, text=True)
        if completed.returncode != 0:
            raise MediaProbeFailed(
                f"ffmpeg audio extraction failed for {source}: {completed.stderr.strip()}"
            )
        extracted = True

    resolved = ResolvedMedia(
        source=str(source),
        audio_path=str(audio_path),
        duration_sec=duration_sec,
        sample_rate=sample_rate,
        channels=channels,
        codec=codec,
        extracted=extracted,
    )
    write_json(job_dir / "media.json", asdict(resolved))
    return resolved


@dataclass(frozen=True)
class AudioChunk:
    index: int
    path: str
    start_sec: float
    end_sec: float


def detect_silences(audio_path: Path) -> list[tuple[float, float]]:
    """Return (start, end) silence intervals via ffmpeg silencedetect."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        return []
    argv = [
        ffmpeg,
        "-i",
        str(audio_path),
        "-af",
        "silencedetect=noise=-35dB:d=0.4",
        "-f",
        "null",
        "-",
    ]
    completed = subprocess.run(argv, capture_output=True, text=True)
    silences: list[tuple[float, float]] = []
    start: float | None = None
    for line in completed.stderr.splitlines():
        if "silence_start:" in line:
            start = float(line.split("silence_start:")[1].strip().split()[0])
        elif "silence_end:" in line and start is not None:
            end = float(line.split("silence_end:")[1].strip().split()[0])
            silences.append((start, end))
            start = None
    return silences


def plan_cut_times(
    duration_sec: float, chunk_sec: int, silences: list[tuple[float, float]]
) -> list[float]:
    """Pick cut points near each chunk boundary, preferring silence midpoints."""
    window = max(5.0, min(60.0, chunk_sec * 0.1))
    midpoints = [(s + e) / 2 for s, e in silences]
    cuts: list[float] = []
    target = float(chunk_sec)
    while target < duration_sec - 1.0:
        candidates = [m for m in midpoints if abs(m - target) <= window]
        floor = cuts[-1] + 1.0 if cuts else 1.0
        candidates = [m for m in candidates if m > floor]
        cut = min(candidates, key=lambda m: abs(m - target)) if candidates else target
        cuts.append(round(cut, 3))
        target = cut + chunk_sec
    return cuts


def split_audio(audio_path: Path, chunk_dir: Path, chunk_sec: int) -> list[AudioChunk]:
    """Split a normalized wav into chunks aligned to silence for checkpointed ASR."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        raise MediaProbeFailed(
            "ffmpeg not found.",
            hint="Install ffmpeg (e.g. `brew install ffmpeg`) or set MOON_MEDIA_LAB_FFMPEG.",
        )
    chunk_dir.mkdir(parents=True, exist_ok=True)
    pattern = chunk_dir / "chunk-%04d.wav"

    info = probe(audio_path)
    duration_raw = info.get("format", {}).get("duration")
    duration_sec = float(duration_raw) if duration_raw else 0.0
    cut_times = plan_cut_times(duration_sec, chunk_sec, detect_silences(audio_path))

    if cut_times:
        segmenting = ["-segment_times", ",".join(str(t) for t in cut_times)]
    else:
        segmenting = ["-segment_time", str(chunk_sec)]
    argv = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        *segmenting,
        "-c",
        "copy",
        str(pattern),
    ]
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"ffmpeg chunking failed for {audio_path}: {completed.stderr.strip()}"
        )

    chunks: list[AudioChunk] = []
    cursor = 0.0
    for index, path in enumerate(sorted(chunk_dir.glob("chunk-*.wav"))):
        info = probe(path)
        duration_raw = info.get("format", {}).get("duration")
        duration = float(duration_raw) if duration_raw else float(chunk_sec)
        chunks.append(
            AudioChunk(
                index=index,
                path=str(path),
                start_sec=round(cursor, 2),
                end_sec=round(cursor + duration, 2),
            )
        )
        cursor += duration
    if not chunks:
        raise MediaProbeFailed(f"Chunking produced no output for {audio_path}")
    return chunks
