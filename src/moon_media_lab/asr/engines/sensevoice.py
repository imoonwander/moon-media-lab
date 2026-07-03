from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.errors import EngineNotInstalled, ModelDownloadFailed, TranscriptionFailed
from moon_media_lab.paths import get_paths
from moon_media_lab.schema import (
    TranscribeRequest,
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)

MODEL_ID = "iic/SenseVoiceSmall"
VAD_MODEL_ID = "fsmn-vad"

# SenseVoice language hints; anything else falls back to auto detection.
LANGUAGE_HINTS = {"zh": "zh", "en": "en"}


def _redirect_model_caches() -> str:
    """Point ModelScope/HF caches at the project cache before any heavy import."""
    cache = get_paths().cache
    modelscope_cache = os.environ.setdefault("MODELSCOPE_CACHE", str(cache / "modelscope"))
    os.environ.setdefault("HF_HOME", str(cache / "huggingface"))
    os.environ.setdefault("TORCH_HOME", str(cache / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache / "xdg"))
    return modelscope_cache


class SenseVoiceEngine(ASREngine):
    name = "sensevoice"

    def __init__(self, model_dir: str | None = None, device: str | None = None) -> None:
        self.model_dir = model_dir or os.environ.get("MOON_MEDIA_LAB_SENSEVOICE_MODEL_DIR")
        self.device = device or os.environ.get("MOON_MEDIA_LAB_DEVICE", "cpu")

    def transcribe(self, request: TranscribeRequest) -> TranscriptResult:
        started = time.perf_counter()
        audio = Path(request.media.source)
        if not audio.exists() or not audio.is_file():
            raise TranscriptionFailed(
                f"Audio file not found for engine {self.name}: {audio}",
                hint="Pass a local audio/video file; the media resolver should run first.",
            )

        modelscope_cache = _redirect_model_caches()

        if importlib.util.find_spec("funasr") is None:
            raise EngineNotInstalled(
                "funasr is not installed for engine sensevoice.",
                hint="Install the engine group: pip install 'moon-media-lab[asr-sensevoice]'",
            )
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        model_source = self.model_dir or MODEL_ID
        try:
            model = AutoModel(
                model=model_source,
                vad_model=VAD_MODEL_ID,
                vad_kwargs={"max_single_segment_time": 30000},
                device=self.device,
                disable_update=True,
                disable_pbar=True,
                log_level="ERROR",
            )
        except Exception as exc:  # noqa: BLE001 - funasr raises plain Exception subclasses
            raise ModelDownloadFailed(
                f"Failed to load SenseVoice model '{model_source}': {exc}",
                hint=f"Check network access; models cache under {modelscope_cache}",
            ) from exc

        language = LANGUAGE_HINTS.get(request.media.language, "auto")
        try:
            outputs = model.generate(
                input=str(audio),
                cache={},
                language=language,
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionFailed(
                f"SenseVoice transcription failed for {audio}: {exc}"
            ) from exc

        if not outputs:
            raise TranscriptionFailed(f"SenseVoice returned no output for {audio}")

        raw_text = outputs[0].get("text", "")
        text = rich_transcription_postprocess(raw_text).strip()

        duration_sec = _audio_duration_sec(audio)

        # SenseVoiceSmall does not emit per-segment timestamps; v1 returns one
        # segment spanning the file. Per-chunk segments arrive with Phase 3.
        segments = [
            TranscriptSegment(
                start=0.0,
                end=duration_sec or 0.0,
                speaker=None,
                text=text or "(empty transcription)",
                confidence=None,
            )
        ]

        return TranscriptResult(
            meta=TranscriptMeta(
                engine=self.name,
                model=model_source if self.model_dir else MODEL_ID,
                language=request.media.language,
                duration_sec=duration_sec,
                runtime_sec=round(time.perf_counter() - started, 2),
                cost_usd=0.0,
                extra={
                    "cloud": False,
                    "provider": "local",
                    "device": self.device,
                    "modelscope_cache": modelscope_cache,
                    "raw_text": raw_text,
                },
            ),
            segments=segments,
        )


def _audio_duration_sec(audio: Path) -> float | None:
    try:
        import soundfile

        info = soundfile.info(str(audio))
        return round(info.frames / info.samplerate, 2)
    except Exception:  # noqa: BLE001 - duration is best-effort metadata
        return None
