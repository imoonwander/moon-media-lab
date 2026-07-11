# Product Brief

## Product Name

`moon_media_lab`

## One-line Positioning

A local-first, open-source media learning and creation system: ingest sources, learn from them, retain reusable assets, and create derivative media outputs.

## Why This Exists

The target user has many media inputs:

- Chinese interviews
- Chinese courses and public talks
- English learning videos and podcasts
- YouTube / Bilibili / local video files
- Audio notes and downloaded media

The user does not only want raw transcription. The useful output is:

- clean transcript
- speaker-aware transcript when possible
- summary
- knowledge cards
- English study notes
- reusable Skill/SOP drafts
- optional voice output from text

## Product Boundaries

`moon_media_lab` is not just an ASR wrapper. Its product lifecycle is:

```text
learn -> assets -> create/remix -> export
```

It should own:

- media ingestion
- ASR routing
- transcript normalization
- post-processing hooks
- TTS routing
- reusable voice and media asset registries
- creation/export adapters for downstream projects
- job storage
- export formats

It should not own:

- permanent knowledge base UI in v1
- full desktop GUI in v1
- cloud account management in v1
- model fine-tuning/training in v1 (zero-shot voice conditioning is supported)
- final video rendering in core (delegate through a future adapter)

## Users

Primary:

- individual knowledge worker
- creator / researcher
- English learner
- operator building media-to-knowledge workflows

Future:

- small content team
- education workflow
- internal knowledge management

## Success Criteria for v1

- Runs from CLI on macOS.
- Can transcribe a short Chinese audio/video file using SenseVoice/FunASR.
- Can transcribe English with faster-whisper later without changing downstream output schema.
- Keeps models, cache, jobs, downloads, and outputs under configurable directories.
- Produces stable JSON and Markdown artifacts.
- Has architecture that can later support Rust and GUI packaging.
