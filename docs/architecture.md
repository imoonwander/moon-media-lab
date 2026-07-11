# Architecture

## Product Lifecycle

```text
Learn
  media -> transcript / subtitles / notes
  voice -> designed or authorized cloned reference
    |
    v
Assets
  jobs / knowledge artifacts / voice registry
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
Asset Registry / Creation
  approved voices -> narration + timings + manifest
```

## Layer Responsibilities

### CLI

Expose lifecycle commands (`learn`, `assets`, `create`) and compatibility expert commands
(`transcribe`, `process`, `tts`, `models`). It should not know model-specific details.

### Asset Registry

Own reusable, versioned assets separately from one-off job output. Voice assets contain a
manifest, profile, reference, and approved samples. Private asset contents stay ignored by Git.

### Creation Adapters

Consume approved assets and produce derivative artifacts. Core currently creates narration and
sentence timings. Future video creation should delegate to a downstream adapter rather than
embedding a video renderer in the media engine layer.

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

## Future Rust/GUI Direction

Keep stable boundaries that can be moved to Rust:

- media probe/extract
- job management
- schema validation
- engine process orchestration
- desktop app backend

Python can remain the first engine-host layer for ML libraries. A future Rust core can call Python engines as subprocesses or sidecar services.

GUI should talk to a stable local API or job folder protocol, not import Python internals directly.
