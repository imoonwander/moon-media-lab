# Roadmap

## Phase 0: Documentation and Skeleton

Status: done.

- Define product scope
- Define adapter contracts
- Define local model/cache strategy
- Keep code scaffold minimal

## Phase 1: Chinese ASR

Status: done (2026-07-03). Note: SenseVoiceSmall does not emit per-segment
timestamps, so v1 returns one segment per file; per-chunk segments arrive
with Phase 3 chunking.

Goal:

```text
short Chinese audio/video -> transcript job
```

Engine:

```text
SenseVoice / FunASR
```

Deliverables:

- SenseVoice engine adapter
- ffmpeg audio extraction
- project-local model/cache behavior
- readable `transcript.md`
- raw normalized JSON

## Phase 2: English ASR

Engine:

```text
faster-whisper large-v3-turbo
```

Deliverables:

- faster-whisper adapter
- language route config
- English sample test
- English study post-processor draft

## Phase 3: Long Media

Goal:

```text
1-4 hour audio/video with checkpointing
```

Status: done (2026-07-03). Audio longer than `chunk_sec * 1.5`
(default 10-minute chunks) is split with ffmpeg at silence-aligned cut
points (silencedetect midpoints near each boundary, falling back to
fixed times), transcribed chunk by chunk with per-chunk JSON
checkpoints and automatic retry (3 attempts per chunk), and merged into
offset segments. `moon-media resume <job-dir>` continues an interrupted
job. Progress and ETA print to stderr; `transcript.partial.md` is
updated after every chunk and removed on completion.

Deliverables:

- chunking (done, silence-aligned)
- resume support (done)
- partial output (done)
- failed chunk retry (done)
- progress reporting (done)

## Phase 4: Post-processing

Deliverables:

- transcript cleanup
- summary
- knowledge cards
- English study materials
- Skill/SOP draft output

LLM providers should be adapters too.

## Phase 5: TTS

Goal:

```text
text -> voice output
```

Engines:

- Edge TTS
- OpenAI TTS
- local TTS later

## Phase 6: Rust Core

Candidate Rust responsibilities:

- media probing
- job database
- file watching
- command orchestration
- GUI backend API
- packaging helpers

Python can remain an engine host for ML libraries.

## Phase 7: GUI

Targets:

- macOS
- Windows

Possible stack:

- Tauri + Rust backend
- Python sidecar for ML engines
- local job folder protocol

GUI should call a stable local API or CLI, not import engine internals directly.
