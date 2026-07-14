# Product Brief

## Product Name

`moon_media_lab`

## One-line Positioning

A local-first, open-source media knowledge system: ingest audio/video sources and turn them into evidence-linked transcripts, structured knowledge, reports and portable Wiki assets.

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
- role-oriented and polished English transcript editions
- claims, evidence, concepts, entities and relations
- evidence-bound recommendation reports
- portable Markdown + JSON Wiki exports

## Product Boundaries

`moon_media_lab` is not just an ASR wrapper. Its product lifecycle is:

```text
process source -> transcribe -> organize -> understand -> package -> export
```

It should own:

- media ingestion
- ASR routing
- transcript normalization
- post-processing hooks
- reusable media knowledge manifests
- structured knowledge and recommendation post-processors
- vendor-neutral Wiki and derivative export adapters
- job storage
- export formats

It should not own:

- permanent knowledge base UI or database in v1
- full desktop GUI in v1
- cloud account management in v1
- TTS/voice implementation as a core responsibility (`moon-voice-lab` owns it)
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
