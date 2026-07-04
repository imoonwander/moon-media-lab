# Contributing

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/moon-media doctor
```

Optional engine groups: `asr-sensevoice`, `asr-whisper`, `url`, `tts-edge`.
`ffmpeg` must be on PATH (or set `MOON_MEDIA_LAB_FFMPEG`).

## Checks before a PR

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/pytest tests/ -q
```

Both must pass. Tests must stay fast: no network, no model downloads, no
heavy imports — use the `mock` ASR engine and `mock` LLM provider.

## Architecture rules

Read `docs/architecture.md` and `docs/engine-adapter-spec.md` first.
The load-bearing constraints:

- ASR engines implement `TranscribeRequest -> TranscriptResult`; nothing
  downstream may depend on engine-specific objects.
- LLM providers implement `complete(prompt, system) -> LLMResponse`;
  post-processors consume the normalized transcript only.
- Heavy ML imports happen inside engine methods, never at module import
  time. `moon-media doctor` must stay fast; CI asserts nothing heavy
  loads with the CLI.
- No user-specific absolute paths; all runtime directories come from
  `MOON_MEDIA_LAB_*` environment variables with project-local defaults.
- Cloud services are opt-in and recorded in `postproc/provenance.json`.

## Adding an engine

1. Create `src/moon_media_lab/asr/engines/<name>.py` implementing `ASREngine`.
2. Register it in `asr/registry.py` (lazy import inside the factory).
3. Add the dependency group to `pyproject.toml` optional-dependencies.
4. Map its package in `cli.py` `ENGINE_PACKAGES` so `doctor --engine` works.
5. Document model storage: files must land under the project `models/`
   or `cache/` directories.
