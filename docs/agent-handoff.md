# Agent Handoff

This document is the entry point for the next implementation agent.

## Current Task

Phase 1 (SenseVoice Chinese ASR) is done and validated as of 2026-07-03.
Implemented: media resolver (ffmpeg probe/extract), SenseVoice adapter with
lazy imports and project-local caches, language routing, CLI exit codes.

Next priority:

1. English ASR: faster-whisper `large-v3-turbo` (Phase 2)
2. Keep all models/cache/job outputs inside the project by default
3. Preserve adapter boundaries so a future Rust core and GUI can reuse the same concepts

Note: the local dev venv is Python 3.9 (funasr/torch preinstalled);
`requires-python` is set to `>=3.9` to match.

## Important Direction

This project is intended for open source.

Do not hard-code user-specific paths such as `/Users/one/...` in product code. The repo can include `.env.example`, but implementation should derive paths from:

- `MOON_MEDIA_LAB_HOME`
- `MOON_MEDIA_LAB_MODELS_DIR`
- `MOON_MEDIA_LAB_CACHE_DIR`
- `MOON_MEDIA_LAB_JOBS_DIR`
- `MOON_MEDIA_LAB_DOWNLOADS_DIR`
- `MOON_MEDIA_LAB_OUTPUT_DIR`

The current local checkout path is only a development workspace path.

## Do Not Do

- Do not import heavy ASR/TTS libraries during basic CLI startup.
- Do not let business logic depend directly on FunASR, faster-whisper, OpenAI, or any single engine.
- Do not write model files to global `~/.cache` by default.
- Do not design as a Python-only dead end.
- Do not make GUI assumptions in the CLI implementation.

## First Implementation Slice

Implement a SenseVoice engine behind the ASR adapter:

```text
source media
  -> ffmpeg extract 16k mono wav if needed
  -> SenseVoice/FunASR engine
  -> normalized TranscriptResult
  -> jobs/<job_id>/transcript.raw.json
  -> jobs/<job_id>/transcript.md
```

Recommended command:

```bash
moon-media transcribe <local-audio-or-video> --engine sensevoice --language zh
```

If package installation is needed, document it. Do not rely on undeclared global packages.

## Validation

Use a short Chinese audio/video sample first. Avoid 2-4 hour files until chunking and checkpointing exist.

Minimum validation:

- `moon-media doctor` does not import FunASR
- `moon-media transcribe ... --engine sensevoice --language zh` produces a job folder
- `transcript.raw.json` follows `docs/engine-adapter-spec.md`
- `transcript.md` is readable
- model/cache files land under project directories or configured paths

## Existing Docs to Read

Read in this order:

1. `docs/product-brief.md`
2. `docs/architecture.md`
3. `docs/runtime-and-models.md`
4. `docs/engine-adapter-spec.md`
5. `docs/cli-v1-spec.md`
6. `docs/roadmap.md`
