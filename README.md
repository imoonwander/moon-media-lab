# moon_media_lab

`moon_media_lab` is an open-source-oriented media processing lab.

The product goal is not only transcription. It should become a cross-platform system that turns local or online media into text, knowledge, learning materials, reusable workflows, and eventually voice output.

## Scope

- Local audio/video to text
- Online media URL to text
- Chinese and English ASR routing
- Text to speech
- Transcript cleanup and normalization
- Knowledge notes, English study notes, and Skill/SOP drafts
- CLI first, with room for later Rust core and macOS/Windows GUI packaging

## Documentation

Start here:

- [Agent Handoff](docs/agent-handoff.md)
- [Product Brief](docs/product-brief.md)
- [Architecture](docs/architecture.md)
- [Runtime and Models](docs/runtime-and-models.md)
- [Engine Adapter Spec](docs/engine-adapter-spec.md)
- [CLI v1 Spec](docs/cli-v1-spec.md)
- [Open Source Engineering Notes](docs/open-source-engineering.md)
- [Roadmap](docs/roadmap.md)

## Runtime Principle

All runtime assets should be configurable and local to the project by default:

```text
products/moon_media_lab/
  models/      ASR/TTS model files
  cache/       Hugging Face / ModelScope / torch / tool cache
  jobs/        per-run job folders
  downloads/   downloaded online media
  output/      exported artifacts
```

Use `.env.example` as the default local configuration template.

## Current State

Phase 1 (Chinese ASR) is implemented and validated:

- SenseVoice/FunASR engine behind the ASR adapter (`--engine sensevoice`)
- ffmpeg media probe and 16 kHz mono wav extraction
- language routing (`zh` -> sensevoice, `en`/`mixed` -> faster-whisper pending)
- project-local ModelScope/HF caches, no writes to global `~/.cache`
- CLI exit codes and actionable error hints per `docs/cli-v1-spec.md`
- long media: automatic chunking with checkpoints, progress/ETA, and
  `moon-media resume <job-dir>` to continue interrupted jobs
- LLM post-processing via provider adapters (`claude-cli` today, `mock`
  for tests): `moon-media process <job-dir> --mode knowledge --clean`
  turns a finished transcript into knowledge notes and a cleaned
  readable transcript; `postproc/provenance.json` records which
  provider saw the data

Quick start:

```bash
python -m venv .venv && .venv/bin/pip install -e '.[asr-sensevoice]'
.venv/bin/moon-media doctor --engine sensevoice
.venv/bin/moon-media transcribe path/to/audio.m4a --language zh
```

Phase 2 (faster-whisper for English) is the next milestone. TTS engines are still mock.
