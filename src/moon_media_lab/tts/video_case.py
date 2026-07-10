from __future__ import annotations

import argparse
import gc
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from moon_media_lab.paths import redirect_model_caches

DEFAULT_DESIGN_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-6bit"
DEFAULT_CLONE_MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-6bit"
SENTENCE_PATTERN = re.compile(r"[^。！？!?….]+[。！？!?….]+|[^。！？!?….]+$")


@dataclass(frozen=True)
class VoiceProfile:
    profile_id: str
    description: str
    reference_text: str
    language: str = "Chinese"
    design_model: str = DEFAULT_DESIGN_MODEL
    clone_model: str = DEFAULT_CLONE_MODEL
    seed: int = 42
    temperature: float = 0.7
    pause_ms: int = 180

    @classmethod
    def from_json(cls, path: Path) -> "VoiceProfile":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            profile_id=payload["id"],
            description=payload["description"],
            reference_text=payload["referenceText"],
            language=payload.get("language", "Chinese"),
            design_model=os.environ.get(
                "MOON_MEDIA_LAB_QWEN3_DESIGN_MODEL",
                payload.get("designModel", DEFAULT_DESIGN_MODEL),
            ),
            clone_model=os.environ.get(
                "MOON_MEDIA_LAB_QWEN3_CLONE_MODEL",
                payload.get("cloneModel", DEFAULT_CLONE_MODEL),
            ),
            seed=int(payload.get("seed", 42)),
            temperature=float(payload.get("temperature", 0.7)),
            pause_ms=int(payload.get("pauseMs", 180)),
        )


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"[\r\n]+", " ", text.strip())
    compact = re.sub(r"[ \t]+", " ", compact)
    return [match.group(0).strip() for match in SENTENCE_PATTERN.finditer(compact)]


def assemble_segments(
    sentences: Sequence[str],
    audio_segments: Sequence[np.ndarray],
    sample_rate: int,
    pause_ms: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    if len(sentences) != len(audio_segments):
        raise ValueError("sentences and audio_segments must have the same length")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    pause_samples = round(sample_rate * pause_ms / 1000)
    silence = np.zeros(pause_samples, dtype=np.float32)
    timeline: list[dict[str, Any]] = []
    parts: list[np.ndarray] = []
    cursor = 0

    for index, (sentence, segment) in enumerate(zip(sentences, audio_segments, strict=True)):
        mono = np.asarray(segment, dtype=np.float32).reshape(-1)
        start = cursor / sample_rate
        parts.append(mono)
        cursor += len(mono)
        end = cursor / sample_rate
        timeline.append(
            {
                "index": index + 1,
                "text": sentence,
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
        if index < len(audio_segments) - 1 and pause_samples:
            parts.append(silence)
            cursor += pause_samples

    audio = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
    return audio, timeline


def _generated_audio(model: Any, **kwargs: Any) -> tuple[np.ndarray, int, list[dict[str, Any]]]:
    results = list(model.generate(**kwargs))
    if not results:
        raise RuntimeError("Qwen3-TTS returned no audio")

    sample_rates = {int(result.sample_rate) for result in results}
    if len(sample_rates) != 1:
        raise RuntimeError(f"Qwen3-TTS returned mixed sample rates: {sorted(sample_rates)}")

    audio = np.concatenate(
        [np.asarray(result.audio, dtype=np.float32).reshape(-1) for result in results]
    )
    metrics = [
        {
            "audioDuration": result.audio_duration,
            "processingSeconds": round(float(result.processing_time_seconds), 3),
            "peakMemoryGB": round(float(result.peak_memory_usage), 3),
            "tokens": int(result.token_count),
        }
        for result in results
    ]
    return audio, sample_rates.pop(), metrics


def _clear_mlx() -> None:
    gc.collect()
    try:
        import mlx.core as mx

        mx.clear_cache()
    except ImportError:
        pass


def run_case(
    *,
    text_file: Path,
    profile_file: Path,
    output_dir: Path,
    reuse_reference: bool = False,
    reference_only: bool = False,
) -> dict[str, Any]:
    redirect_model_caches()
    try:
        import mlx.core as mx
        import soundfile as sf
        from mlx_audio.tts.utils import load_model
    except ImportError as exc:
        raise RuntimeError(
            "Qwen3-TTS MLX dependencies are missing. Install "
            "'moon-media-lab[tts-qwen3-mlx]' on an Apple Silicon Mac."
        ) from exc

    profile = VoiceProfile.from_json(profile_file)
    text = text_file.read_text(encoding="utf-8").strip()
    sentences = split_sentences(text)
    if not sentences:
        raise ValueError(f"No narration sentences found in {text_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    reference_path = output_dir / f"{profile.profile_id}.reference.wav"
    narration_path = output_dir / f"{profile.profile_id}.narration.wav"
    timings_path = output_dir / f"{profile.profile_id}.timings.json"
    run_path = output_dir / f"{profile.profile_id}.run.json"
    started_at = time.time()
    run_metrics: dict[str, Any] = {"reference": [], "sentences": []}

    if not reuse_reference or not reference_path.exists():
        mx.random.seed(profile.seed)
        design_model = load_model(profile.design_model)
        reference_audio, reference_rate, metrics = _generated_audio(
            design_model,
            text=profile.reference_text,
            instruct=profile.description,
            lang_code=profile.language,
            temperature=profile.temperature,
            verbose=False,
        )
        sf.write(reference_path, reference_audio, reference_rate, subtype="PCM_16")
        run_metrics["reference"] = metrics
        del design_model
        _clear_mlx()

    if reference_only:
        result = {
            "profile": profile.profile_id,
            "referenceAudio": str(reference_path),
            "designModel": profile.design_model,
            "elapsedSeconds": round(time.time() - started_at, 3),
            "metrics": run_metrics,
        }
        run_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    clone_model = load_model(profile.clone_model)
    segments: list[np.ndarray] = []
    sample_rate: int | None = None
    for index, sentence in enumerate(sentences):
        mx.random.seed(profile.seed + index + 1)
        segment, current_rate, metrics = _generated_audio(
            clone_model,
            text=sentence,
            ref_audio=str(reference_path),
            ref_text=profile.reference_text,
            lang_code=profile.language,
            temperature=profile.temperature,
            verbose=False,
        )
        if sample_rate is None:
            sample_rate = current_rate
        elif sample_rate != current_rate:
            raise RuntimeError(
                f"Sentence {index + 1} used {current_rate} Hz; expected {sample_rate} Hz"
            )
        segments.append(segment)
        run_metrics["sentences"].append({"index": index + 1, "metrics": metrics})

    del clone_model
    _clear_mlx()
    assert sample_rate is not None
    narration_audio, timeline = assemble_segments(
        sentences, segments, sample_rate, profile.pause_ms
    )
    sf.write(narration_path, narration_audio, sample_rate, subtype="PCM_16")
    duration = len(narration_audio) / sample_rate

    timings = {
        "audio": str(narration_path),
        "voice": {
            "engine": "qwen3-tts-mlx",
            "profile": profile.profile_id,
            "description": profile.description,
            "designModel": profile.design_model,
            "cloneModel": profile.clone_model,
            "referenceAudio": str(reference_path),
            "referenceText": profile.reference_text,
            "seed": profile.seed,
            "temperature": profile.temperature,
            "pauseMs": profile.pause_ms,
        },
        "sampleRate": sample_rate,
        "duration": round(duration, 3),
        "sentences": timeline,
    }
    timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "profile": profile.profile_id,
        "textFile": str(text_file),
        "profileFile": str(profile_file),
        "referenceAudio": str(reference_path),
        "narrationAudio": str(narration_path),
        "timings": str(timings_path),
        "duration": round(duration, 3),
        "sentences": len(sentences),
        "elapsedSeconds": round(time.time() - started_at, 3),
        "metrics": run_metrics,
    }
    run_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moon-media-voice-case",
        description="Design a Qwen3-TTS voice, clone it sentence by sentence, and emit video timings.",
    )
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--reuse-reference", action="store_true")
    parser.add_argument("--reference-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_case(
        text_file=args.text_file,
        profile_file=args.profile,
        output_dir=args.output_dir,
        reuse_reference=args.reuse_reference,
        reference_only=args.reference_only,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
