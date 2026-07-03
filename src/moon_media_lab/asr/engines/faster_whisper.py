from __future__ import annotations

import importlib.util
import math
import os
import time
from pathlib import Path

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.errors import EngineNotInstalled, ModelDownloadFailed, TranscriptionFailed
from moon_media_lab.paths import get_paths, redirect_model_caches
from moon_media_lab.schema import (
    TranscribeRequest,
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)

DEFAULT_MODEL = "large-v3-turbo"

# Whisper language hints; auto/mixed use built-in detection.
LANGUAGE_HINTS = {"zh": "zh", "en": "en"}


class FasterWhisperEngine(ASREngine):
    name = "faster-whisper"

    def __init__(self, model_dir: str | None = None, device: str | None = None) -> None:
        self.model_name = os.environ.get("MOON_MEDIA_LAB_WHISPER_MODEL", DEFAULT_MODEL)
        self.model_dir = model_dir or os.environ.get("MOON_MEDIA_LAB_WHISPER_MODEL_DIR")
        self.device = device or os.environ.get("MOON_MEDIA_LAB_DEVICE", "cpu")
        self.compute_type = os.environ.get("MOON_MEDIA_LAB_WHISPER_COMPUTE", "int8")
        self._model = None

    def _load_model(self):
        """Load the model once per engine instance so chunked runs reuse it."""
        if self._model is not None:
            return self._model

        redirect_model_caches()

        if importlib.util.find_spec("faster_whisper") is None:
            raise EngineNotInstalled(
                "faster-whisper is not installed.",
                hint="Install the engine group: pip install 'moon-media-lab[asr-whisper]'",
            )
        from faster_whisper import WhisperModel

        download_root = str(get_paths().models / "asr" / "faster-whisper")
        source = self.model_dir or self.model_name
        try:
            self._model = WhisperModel(
                source,
                device=self.device,
                compute_type=self.compute_type,
                download_root=download_root,
            )
        except Exception as exc:  # noqa: BLE001
            raise ModelDownloadFailed(
                f"Failed to load faster-whisper model '{source}': {exc}",
                hint=f"Check network access; models download under {download_root}",
            ) from exc
        return self._model

    def transcribe(self, request: TranscribeRequest) -> TranscriptResult:
        started = time.perf_counter()
        audio = Path(request.media.source)
        if not audio.exists() or not audio.is_file():
            raise TranscriptionFailed(
                f"Audio file not found for engine {self.name}: {audio}",
                hint="Pass a local audio/video file; the media resolver should run first.",
            )

        model = self._load_model()
        language = LANGUAGE_HINTS.get(request.media.language)
        try:
            raw_segments, info = model.transcribe(
                str(audio),
                language=language,
                vad_filter=True,
                word_timestamps=request.need_word_timestamps,
            )
            segments = [
                TranscriptSegment(
                    start=round(segment.start, 2),
                    end=round(segment.end, 2),
                    speaker=None,
                    text=segment.text.strip(),
                    confidence=round(math.exp(segment.avg_logprob), 3),
                )
                for segment in raw_segments
                if segment.text.strip()
            ]
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionFailed(
                f"faster-whisper transcription failed for {audio}: {exc}"
            ) from exc

        return TranscriptResult(
            meta=TranscriptMeta(
                engine=self.name,
                model=self.model_dir or self.model_name,
                language=info.language or request.media.language,
                duration_sec=round(info.duration, 2) if info.duration else None,
                runtime_sec=round(time.perf_counter() - started, 2),
                cost_usd=0.0,
                extra={
                    "cloud": False,
                    "provider": "local",
                    "device": self.device,
                    "compute_type": self.compute_type,
                    "language_probability": round(info.language_probability, 3)
                    if info.language_probability
                    else None,
                },
            ),
            segments=segments,
        )
