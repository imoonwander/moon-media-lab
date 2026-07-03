# Runtime and Models

## Open-source Runtime Principle

The project must run on different machines without hard-coded local paths.

Defaults should be project-local, but every path must be configurable.

## Environment Variables

`.env.example` defines:

```bash
MOON_MEDIA_LAB_HOME
MOON_MEDIA_LAB_MODELS_DIR
MOON_MEDIA_LAB_CACHE_DIR
MOON_MEDIA_LAB_JOBS_DIR
MOON_MEDIA_LAB_DOWNLOADS_DIR
MOON_MEDIA_LAB_OUTPUT_DIR
```

Model libraries should be redirected:

```bash
HF_HOME
HUGGINGFACE_HUB_CACHE
TRANSFORMERS_CACHE
MODELSCOPE_CACHE
TORCH_HOME
XDG_CACHE_HOME
```

Add `MODELSCOPE_CACHE` to `.env.example` if SenseVoice/FunASR is implemented.

## Directory Layout

```text
moon_media_lab/
  models/
    asr/
      sensevoice/
      faster-whisper/
      whisper-cpp/
    tts/
  cache/
    huggingface/
    modelscope/
    torch/
    xdg/
  downloads/
  jobs/
  output/
```

## Dependency Strategy

v1 can use Python for speed of implementation.

Recommended dependency groups:

```text
base:
  CLI, schema, job manager

asr-sensevoice:
  funasr
  modelscope
  torch
  torchaudio
  soundfile

asr-whisper:
  faster-whisper
  ctranslate2

tts:
  edge-tts or openai

dev:
  ruff, pytest
```

Do not require all ASR/TTS engines for basic CLI startup.

## Heavy Import Rule

Heavy ML imports should happen inside engine execution only.

Allowed:

```python
class SenseVoiceEngine:
    def transcribe(...):
        from funasr import AutoModel
```

Avoid:

```python
from funasr import AutoModel  # at module import time
```

Reason:

- `moon-media doctor` should be fast
- GUI startup should be fast
- users may install only one engine
- packaging should not force all engines

## Model Storage

The implementation must verify where downloaded model files land.

For SenseVoice/FunASR:

- set `MODELSCOPE_CACHE` to project cache
- optionally allow an explicit `model_dir`
- log resolved model path in `run.log`

For faster-whisper:

- prefer project-local model cache
- expose `--model-dir` or config option later

## Test Media

Use short files first:

- 5-30 seconds for first integration
- 1-5 minutes after basic success
- long files only after chunking/checkpointing exists

Do not use a 4-hour file as the first integration test.
