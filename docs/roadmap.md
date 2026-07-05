# Roadmap

## Version lines

Each minor series is one product theme. `main` is the CLI core line;
big themes incubate on feature branches and merge as their own series.

### 0.1.x — CLI core (current focus, branch: `main`)

Goal: **the CLI converts video/audio excellently, is open-source ready,
and works globally on your machine.**

- [x] Chinese ASR (SenseVoice), English ASR (faster-whisper), diarization (paraformer+CAM++)
- [x] URL ingestion (YouTube / Bilibili / Douyin / direct), playlists
- [x] Long-media chunking, checkpoints, resume, progress
- [x] LLM post-processing (knowledge / clean / speakers) via provider adapters
- [x] Subtitles (srt/vtt), models management with mirror + resume
- [ ] Global install story (pipx / uv tool), first-run experience polish
- [ ] CLI stability hardening: clearer errors, edge cases from daily use
- [ ] Public release: flip the repo public, announce
- Note: the built-in web UI (`moon-media serve`) ships in 0.1.x as a
  **beta preview**; its active development moved to the `web-ui` branch.

### 0.2.x — Web experience (branch: `web-ui`)

Goal: a web UI whose interaction quality matches the CLI's capability.

- UI/UX redesign to expectation (current beta does not meet the bar)
- Transcript reader experience (markdown reading, search, navigation)
- Job management refinements, richer progress, mobile-friendly layout
- Merges back to `main` and releases as the 0.2.x series when ready

### 0.3.x — Voice and beyond

- TTS as a real product line (edge-tts shipped early and idles in 0.1.x;
  it graduates here: voices, batch narration, transcript-to-speech)
- Reader/knowledge deepening, integrations (e.g. Lark), API providers
- Later themes each get their own minor series (0.4.x, ...)

## Branching

- `main` — CLI core; stable; all tags/releases cut here
- `web-ui` — web experience line; merges to main at series boundaries
- short-lived feature branches as needed

---

# Phase history (original plan)


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

Status: done (2026-07-03). faster-whisper adapter with per-segment
timestamps and confidence, project-local model storage under
`models/asr/faster-whisper`, `en`/`mixed` routing. Model/compute
configurable via `MOON_MEDIA_LAB_WHISPER_MODEL` / `_COMPUTE`
(default `large-v3-turbo` / `int8`). URL ingestion via yt-dlp landed
in the same release: `moon-media transcribe <url>` auto-detects
http(s), downloads audio to `downloads/`, cookies configurable for
bot-checked sites.

Engine:

```text
faster-whisper large-v3-turbo
```

Deliverables:

- faster-whisper adapter (done)
- language route config (done)
- English sample test (done)
- English study post-processor draft (done in Phase 4)

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

Status: core done (2026-07-03). LLM providers are adapters
(`claude-cli` shells out to the local Claude Code CLI with retry;
`mock` for tests; select via `--llm` or `MOON_MEDIA_LAB_LLM_PROVIDER`).
`moon-media process <job-dir>` post-processes finished jobs without
re-transcribing: `--mode knowledge|english-study|skill` generates the
mode document in one call; `--clean` produces `transcript.clean.md`
in checkpointed batches. `postproc/provenance.json` records which
provider saw the data and whether it left the machine.

Deliverables:

- transcript cleanup (done, batched + checkpointed)
- summary (done, part of knowledge.md)
- knowledge cards (done, part of knowledge.md)
- English study materials (done, english-study.md)
- Skill/SOP draft output (done, skill-draft.md)

Remaining:

- API-based providers (anthropic/openai SDK) as alternative adapters
- diff-aware re-processing when a transcript is re-run

## Phase 5: TTS

Status: core done (2026-07-04). `moon-media tts` synthesizes via
edge-tts (default voice zh-CN-XiaoxiaoNeural, override with --voice or
MOON_MEDIA_LAB_TTS_VOICE). The mock engine remains for tests.

Goal:

```text
text -> voice output
```

Engines:

- Edge TTS (done)
- OpenAI TTS (planned)
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
