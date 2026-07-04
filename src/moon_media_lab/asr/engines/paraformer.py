from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

from moon_media_lab.asr.base import ASREngine
from moon_media_lab.errors import EngineNotInstalled, ModelDownloadFailed, TranscriptionFailed
from moon_media_lab.paths import redirect_model_caches
from moon_media_lab.schema import (
    TranscribeRequest,
    TranscriptMeta,
    TranscriptResult,
    TranscriptSegment,
)

# FunASR aliases; resolved and downloaded via ModelScope on first load.
ASR_MODEL = "paraformer-zh"
VAD_MODEL = "fsmn-vad"
PUNC_MODEL = "ct-punc"
SPK_MODEL = "cam++"


class ParaformerEngine(ASREngine):
    """Chinese ASR with speaker diarization (paraformer-zh + CAM++)."""

    name = "paraformer"

    def __init__(self, model_dir: str | None = None, device: str | None = None) -> None:
        self.model_dir = model_dir
        self.device = device or os.environ.get("MOON_MEDIA_LAB_DEVICE", "cpu")
        self._model = None
        self._modelscope_cache: str | None = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        self._modelscope_cache = redirect_model_caches()

        if importlib.util.find_spec("funasr") is None:
            raise EngineNotInstalled(
                "funasr is not installed for engine paraformer.",
                hint="Install the engine group: pip install 'moon-media-lab[asr-sensevoice]'",
            )
        from funasr import AutoModel

        try:
            # Keep FunASR's tqdm visible: diarization runs are long single
            # passes and this is the only live progress signal.
            self._model = AutoModel(
                model=self.model_dir or ASR_MODEL,
                vad_model=VAD_MODEL,
                punc_model=PUNC_MODEL,
                spk_model=SPK_MODEL,
                device=self.device,
                disable_update=True,
                disable_pbar=os.environ.get("MOON_MEDIA_LAB_QUIET") == "1",
                log_level="ERROR",
            )
        except Exception as exc:  # noqa: BLE001
            raise ModelDownloadFailed(
                f"Failed to load paraformer diarization stack: {exc}",
                hint=f"Check network access; models cache under {self._modelscope_cache}",
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
        try:
            outputs = model.generate(input=str(audio), batch_size_s=300)
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionFailed(
                f"Paraformer transcription failed for {audio}: {exc}"
            ) from exc
        if not outputs:
            raise TranscriptionFailed(f"Paraformer returned no output for {audio}")

        sentences = outputs[0].get("sentence_info", [])
        segments = [
            TranscriptSegment(
                start=round(sentence["start"] / 1000, 2),
                end=round(sentence["end"] / 1000, 2),
                speaker=f"SPEAKER_{sentence.get('spk', 0):02d}",
                text=sentence["text"].strip(),
                confidence=None,
            )
            for sentence in sentences
            if sentence.get("text", "").strip()
        ]
        if not segments:
            # No sentence_info (e.g. spk model unavailable): fall back to flat text.
            text = outputs[0].get("text", "").strip()
            duration = _audio_duration_sec(audio)
            segments = [
                TranscriptSegment(
                    start=0.0,
                    end=duration or 0.0,
                    speaker=None,
                    text=text or "(empty transcription)",
                    confidence=None,
                )
            ]

        return TranscriptResult(
            meta=TranscriptMeta(
                engine=self.name,
                model=f"{ASR_MODEL}+{SPK_MODEL}",
                language=request.media.language,
                duration_sec=_audio_duration_sec(audio),
                runtime_sec=round(time.perf_counter() - started, 2),
                cost_usd=0.0,
                extra={
                    "cloud": False,
                    "provider": "local",
                    "device": self.device,
                    "diarization": True,
                    "speakers": sorted({s.speaker for s in segments if s.speaker}),
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
