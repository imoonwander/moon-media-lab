# Open Source Engineering Notes

## Project Expectations

This project should be designed as if it may be published publicly.

That means:

- no user-specific absolute paths in source code
- no credentials in repository
- no checked-in local virtual environments
- no checked-in model weights
- no checked-in downloaded media
- no checked-in job outputs except tiny fixtures intentionally placed under `examples/`

## Configuration

Use environment variables and config files.

Good:

```text
MOON_MEDIA_LAB_HOME
MOON_MEDIA_LAB_MODELS_DIR
MOON_MEDIA_LAB_CACHE_DIR
MOON_MEDIA_LAB_JOBS_DIR
```

Bad:

```text
/Users/one/...
C:\Users\...
```

## Dependency Management

The first implementation can use Python, but dependencies should be grouped so users do not install every engine by default.

Recommended future layout:

```toml
[project.optional-dependencies]
asr-sensevoice = ["funasr", "modelscope", "torch", "torchaudio", "soundfile"]
asr-whisper = ["faster-whisper"]
tts-edge = ["edge-tts"]
dev = ["pytest", "ruff"]
```

## Cross-platform Rules

Use:

- `pathlib`
- UTF-8 files
- explicit subprocess argv arrays
- config/env for binary paths

Avoid:

- shell-only command strings
- macOS-only paths
- implicit global cache directories
- assuming ffmpeg is installed in `/opt/homebrew/bin`

## Packaging Direction

CLI v1 should be simple and scriptable.

Later GUI packaging can use:

```text
Tauri or native shell
Rust core
Python ASR/TTS sidecar
local job folder protocol
```

The GUI should not depend on direct Python imports. It should talk to:

- CLI commands
- local API
- or a stable job folder protocol

## Privacy and Safety

Media files may contain private voice or video.

Default behavior:

- local processing first
- cloud engines opt-in
- job folder clearly records engine and whether data left the machine

Every cloud engine should write:

```json
{
  "cloud": true,
  "provider": "openai",
  "model": "gpt-4o-mini-transcribe"
}
```

Local engines should write:

```json
{
  "cloud": false,
  "provider": "local"
}
```
