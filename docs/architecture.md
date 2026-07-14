# Architecture

## Product Lifecycle

```text
Process
  local file / URL / existing job
  preset -> transcript / knowledge / report / Wiki bundle
    |
    v
Assets
  source / transcript / knowledge / derivative layers
    |
    v
Create
  narration / timings / export bundle
    |
    v
Remix / Export
  downstream adapters such as moon-video-cast
```

Low-level engines remain replaceable implementation details under this lifecycle.

## Media Learning Flow

```text
Input
  local file | URL | text
    |
    v
Media Resolver
  probe, download, extract audio
    |
    v
Job Manager
  creates jobs/<job_id>
    |
    v
ASR Router
  chooses engine by language, user option, cost, quality
    |
    v
ASR Engine Adapter
  SenseVoice / FunASR
  faster-whisper
  whisper.cpp
  OpenAI
    |
    v
Transcript Normalizer
  common segment schema
    |
    v
Post Processors
  transcript.md
  knowledge.md
  english-study.md
  skill-draft.md
    |
    v
Optional Knowledge Visualization
  Codex built-in image_gen / gpt-image-2
  diagram brief -> visuals/*.png + provenance
    |
    v
Asset Registry / Creation
  optional moon-voice-lab plugin -> narration + timings + safe manifest
```

## Layer Responsibilities

### CLI

Expose `process` as the primary media command and `download` as acquisition-only. Keep
`transcribe`, `package`, `export`, and `models` as composable expert commands. Voice compatibility
commands load the optional voice plugin and should not leak model-specific details into the core.

### Knowledge Asset Registry

Own portable four-layer knowledge bundles separately from one-off execution state. The bundle
manifest records source, transcript, knowledge and derivative artifacts with SHA-256 and
provenance. Files remain authoritative; SQLite and embeddings are deferred.

### Optional Voice Adapter

Voice design, cloning, catalogs and narration are moving to `moon-voice-lab`. Compatibility
commands remain and load the plugin lazily; the knowledge core must never import heavy TTS/ML
libraries at startup. Video rendering remains downstream in `moon-video-cast`.

### Media Resolver

Responsible for:

- local path validation
- URL download placeholder
- ffmpeg probing
- audio extraction to normalized wav
- duration detection

Recommended normalized audio:

```text
16 kHz
mono
wav
```

### Job Manager

Creates a job folder and writes:

```text
input.json
run.log
transcript.raw.json
transcript.md
```

Future files:

```text
media.json
segments.vtt
segments.srt
knowledge.md
english-study.md
skill-draft.md
tts-output.*
```

### ASR Router

Recommended default routing:

```text
zh      -> sensevoice
en      -> faster-whisper
mixed   -> faster-whisper
auto    -> detect or use configured default
fallback -> openai
```

The router should be replaceable. Avoid mixing route policy inside engine code.

### Engine Adapter

Each ASR engine implements one contract:

```text
TranscribeRequest -> TranscriptResult
```

No downstream code should depend on model-specific return objects.

### Transcript Normalizer

Normalizes:

- segment start/end
- text
- speaker label
- confidence
- language
- engine metadata
- cost and runtime metadata

### Post Processors

Post processors consume normalized transcript only.

They should not call model-specific ASR APIs.

### Knowledge Visualization Adapter

Consumes a reviewed `knowledge.md`, not raw model-specific ASR output. Codex's built-in
`image_gen` (gpt-image-2) may generate a diagram from an exact-text brief. The job folder owns
the selected bitmap, prompt, and provenance. This is an agent-level optional adapter rather than
a fake local CLI command; environments without built-in image generation stop after producing
the brief.

## Future Rust/GUI Direction

Keep stable boundaries that can be moved to Rust:

- media probe/extract
- job management
- schema validation
- engine process orchestration
- desktop app backend

Python can remain the first engine-host layer for ML libraries. A future Rust core can call Python engines as subprocesses or sidecar services.

GUI should talk to a stable local API or job folder protocol, not import Python internals directly.
