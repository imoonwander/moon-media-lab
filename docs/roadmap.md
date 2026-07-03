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

Deliverables:

- chunking
- resume support
- partial output
- failed chunk retry
- progress reporting

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
