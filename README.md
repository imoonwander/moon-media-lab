# Moon Media Lab

**English · [简体中文](README.zh-CN.md)**

Local-first media knowledge lab: turn local or online audio/video into
evidence-linked transcripts, speaker/English editions, structured knowledge,
recommendation reports, diagrams, and portable Wiki-ready bundles.

```text
file / YouTube / Bilibili / Douyin / direct URL
        │
        ▼
  transcribe (SenseVoice · Paraformer+CAM++ · faster-whisper)
        │
        ▼
  Source: raw segments + subtitles + media evidence
        │
        ▼
  Transcript: source / clean / speaker / polished English editions
        │
        ▼
  Knowledge: concepts / claims / evidence / entities / recommendations
        │
        ▼
  Derivatives: diagram / Wiki export / article and video inputs
```

Speech recognition runs **entirely on your machine**. LLM post-processing
is opt-in and goes through whichever CLI you already use (`claude`,
`codex`, `gemini`); every output records which provider saw the data in
`postproc/provenance.json`.

> Chinese task-oriented guide: [核心功能与操作手册](docs/core-workflows.zh-CN.md).
> For dated evidence and failure conditions, see
> [Platform support and verification](docs/platform-support.md).

## Features

- **Chinese ASR** — SenseVoice (fast) or Paraformer + CAM++ with
  `--diarization` for speaker-labeled interviews
- **English ASR** — faster-whisper `large-v3-turbo` with per-segment
  timestamps and confidence
- **Speaker naming** — `process --name-speakers` turns `SPEAKER_00`
  into inferred names/roles and re-renders transcript + subtitles
- **Online media** — `process <url>` routes acquisition by platform;
  YouTube uses yt-dlp plus a JS runtime, Bilibili commonly needs cookies,
  and public Douyin shares use the built-in downloader
- **Long media** — silence-aligned chunking, per-chunk checkpoints,
  `resume <job-dir>`, progress/ETA, `transcript.partial.md` while running
- **Playlists** — `--playlist [--playlist-items 1-5]`, one job per entry
- **Subtitles** — `segments.srt` / `segments.vtt` for every job
- **LLM post-processing** — summary/outline/knowledge cards, English
  study notes, SOP drafts, batched+concurrent transcript cleanup
- **Knowledge bundles** — four-layer manifests with artifact hashes and provenance
- **Structured knowledge** — concepts, claims, evidence, entities, relations, open questions
- **Recommendation reports** — evidence timestamps, conditions, risks, confidence, inference origin
- **Wiki export** — vendor-neutral Markdown + JSON; no database required
- **Knowledge visualization** — Codex built-in `imagegen` / gpt-image-2 turns a
  reviewed `knowledge.md` into a diagram with its prompt and provenance
- **Optional voice plugin** — compatibility commands remain while voice design,
  cloning, catalogs, and narration move to `moon-voice-lab`
- **Self-contained models** — `models list|download|prune`, resumable
  downloads, `--mirror` for hf-mirror.com; nothing writes to `~/.cache`
- **Web UI (beta preview)** — `moon-media serve` starts a local web app
  (submit files/URLs, live progress, click-a-timestamp audio playback,
  inline previews, one-click post-processing); every job also writes a
  machine-readable `state.json`, so the job folder stays the API.
  Active web development happens on the `web-ui` branch (0.2.x line)

## Install

Requires Python 3.9+ (3.10+ recommended) and [ffmpeg](https://ffmpeg.org).

```bash
git clone <repo-url> && cd moon_media_lab
python3 -m venv .venv
.venv/bin/pip install -e '.[asr-sensevoice,asr-whisper,url]'
.venv/bin/moon-media doctor   # health report: what's ready, what's next
```

`moon-media doctor` prints a ✓/○/✗ checklist of ffmpeg, engines, LLM
CLIs, and downloaded models, ending with whether you can transcribe now
or the exact next step. Run it first.

Pick only the extras you need — the base CLI has zero dependencies.

**Global install** (use `moon-media` from anywhere):

```bash
pipx install 'moon-media-lab[asr-sensevoice,asr-whisper,url]'
# or, from a clone: ln -s "$(pwd)/.venv/bin/moon-media" ~/.local/bin/moon-media
```
For URL ingestion a standalone `yt-dlp` binary on PATH is preferred
(site extractors age quickly; the pip copy is pinned by your Python).

## Quickstart

```bash
# Unified entry; local files are referenced, not copied
.venv/bin/moon-media process examples/hello-zh.wav --preset transcript --language zh

# a Chinese interview with speaker labels (first run downloads ~1.2 GB of models)
.venv/bin/moon-media process interview.m4a --preset interview --language zh

# an English podcast from YouTube (first run downloads ~1.6 GB; use --mirror in CN)
.venv/bin/moon-media models download large-v3-turbo --mirror
MOON_MEDIA_LAB_COOKIES_BROWSER=chrome \
  .venv/bin/moon-media process "https://youtu.be/..." --preset english --language en

# post-process a finished job with the LLM CLI you already have
.venv/bin/moon-media process jobs/transcribe-... --mode knowledge --clean --llm codex-cli
.venv/bin/moon-media process jobs/transcribe-... --mode structured-knowledge --llm codex-cli
.venv/bin/moon-media process jobs/transcribe-... --mode recommendations --llm codex-cli
.venv/bin/moon-media package jobs/transcribe-...
.venv/bin/moon-media export wiki jobs/transcribe-...

# or do all of the above from a browser
.venv/bin/pip install -e '.[web]'
.venv/bin/moon-media serve        # → http://127.0.0.1:8765
```

Every run creates `jobs/<job-id>/` with `transcript.md`,
`transcript.raw.json`, `segments.srt/vtt`, `run.log`, and any
post-processing outputs. The job folder is the API — nothing else to learn.

## Commands

| Command | Purpose |
|---------|---------|
| `doctor` | Health report: ffmpeg, engines, LLM CLIs, models, verdict |
| `process <source-or-job>` | Unified local file, URL, or existing-job workflow with presets |
| `download <url>` | Download online video/audio without transcription |
| `learn media\|voice` | Compatibility entry; prefer `process` for new media workflows |
| `assets voices list\|show\|approve\|preview` | Inspect, approve, and preview voice assets |
| `package <job-dir>` | Build the four-layer knowledge asset manifest |
| `export wiki <job-dir>` | Export portable Markdown + JSON knowledge assets |
| `create narration` | Create narration and sentence timings from a voice asset |
| `transcribe <source>` | Low-level transcript and subtitle job |
| `resume <job-dir>` | Continue an interrupted transcribe job |
| `models list\|download\|prune` | Manage local ASR models |
| `tts <text>` | Text to speech (edge-tts) |
| `moon-media-voice-case` | Low-level compatibility entry; prefer lifecycle commands above |
| `serve` | Local web UI (beta) |

### process: unified entry

```bash
moon-media process <local-file|URL|job-dir> --preset <goal>
```

Presets: `transcript`, `knowledge`, `interview`, `english`, `research`, and `wiki`.
Local files are referenced directly, URLs are downloaded when needed, and existing jobs are not
re-transcribed.

```bash
moon-media process video.mp4 --preset wiki
moon-media process jobs/transcribe-... --add recommendations
moon-media process jobs/transcribe-... --add structured-knowledge

moon-media download <URL>
moon-media download <URL> --format audio
```

### transcribe: low-level entry

```bash
moon-media transcribe <source> [options]
```

| Flag | Values / default | Meaning |
|------|------------------|---------|
| `--language` | `auto` `zh` `en` `mixed` | Language; drives engine routing |
| `--engine` | `auto` `sensevoice` `paraformer` `faster-whisper` `mock` | Force an engine (usually leave `auto`) |
| `--mode` | `transcript` (default) `knowledge` `english-study` `skill` | Also generate this document after transcribing |
| `--diarization` | flag | Label speakers (Chinese; routes to paraformer+CAM++) |
| `--kind` | `file` `url` `text` | Source type (auto-detected for http(s)) |
| `--chunk-sec` | `600` | Chunk length for long media |
| `--llm` | `auto` `claude-cli` `codex-cli` `gemini-cli` | Provider for `--mode` post-processing |
| `--playlist` | flag | Transcribe every entry of a playlist/multi-part URL |
| `--playlist-items` | `1-5` or `1,3,7` | Which playlist entries |
| `--word-timestamps` | flag | Per-word timestamps (faster-whisper) |
| `--job-dir` / `--model-dir` | path | Override jobs root / model path |

Language routing when `--engine auto`: `zh → sensevoice`
(or `paraformer` with `--diarization`), `en`/`mixed → faster-whisper`.

### existing-job compatibility flags

The original job post-processing flags remain compatible and map to the new `--add` actions.
Existing transcript artifacts are never re-transcribed.

```bash
moon-media process <job-dir> [--mode ...] [--clean] [--name-speakers] [--llm ...]
```

| Flag | Output | What it does |
|------|--------|--------------|
| `--mode knowledge` | `knowledge.md` | Summary, timestamped outline, knowledge cards, quotes |
| `--mode english-study` | `english-study.md` | Vocabulary, expressions, grammar notes, exercises |
| `--mode skill` | `skill-draft.md` | Reusable SOP / how-to distilled from the content |
| `--clean` | `transcript.clean.md` | Fix homophones, drop fillers, add punctuation (batched, concurrent, checkpointed) |
| `--name-speakers` | rewrites `transcript.md` + subtitles | Infer real names/roles for `SPEAKER_NN` from context |

LLM providers are the CLIs you already have — `claude`, `codex`,
`gemini` — used as swappable adapters (no extra API keys). Each output
records which provider saw the data in `postproc/provenance.json`.

### models

```bash
moon-media models list                          # downloaded models + sizes
moon-media models download sensevoice           # Chinese ASR (via ModelScope)
moon-media models download paraformer           # diarization stack (~1.2 GB)
moon-media models download large-v3-turbo        # English ASR (~1.6 GB)
moon-media models download large-v3-turbo --mirror   # via hf-mirror.com (faster in CN)
moon-media models prune                         # remove interrupted .part/.incomplete files
```

Models download file-by-file with HTTP-Range resume — interrupt and
rerun, it continues. Everything lands under the project `models/` and
`cache/`; nothing is written to `~/.cache`.

### Local voice design + video narration (Apple Silicon)

The optional Qwen3-TTS MLX workflow first designs a reusable reference
voice, then clones it sentence by sentence. It writes a WAV plus exact
sentence timings derived from the generated sample counts, so a video
renderer can use the same artifact for narration, captions, and scene cuts.

```bash
pip install -e '.[tts-qwen3-mlx]'

moon-media learn voice design \
  --id moon-reader-v1 \
  --description "warm, calm Chinese narrator" \
  --reference-text "Hello. May every reading bring you closer to yourself."

moon-media create narration /path/to/narration.txt \
  --voice moon-reader-v1 \
  --output-dir output/voice-runs/episode-001
```

Use `moon-media learn voice clone` for your own or explicitly authorized
reference audio. `learn` retains a versioned candidate under `assets/voices/`;
`create` consumes that asset without exposing profile/reference paths.

Approved voices remain in the local ignored `assets/voices/<voice-id>/`
library. See [`docs/voice-assets-workflow.md`](docs/voice-assets-workflow.md).
`moon-media-voice-case` remains a low-level compatibility entry.

For a pre-downloaded ModelScope/Hugging Face snapshot, override the two model
IDs with `MOON_MEDIA_LAB_QWEN3_DESIGN_MODEL` and
`MOON_MEDIA_LAB_QWEN3_CLONE_MODEL`.

## Verified sources

| Source | Status | Primary entry | Current evidence |
|--------|--------|---------------|------------------|
| <img src="docs/assets/platforms/local-file.svg" width="22" alt="Local file"> Local file | ✅ End to end | `process video.mp4 --preset knowledge` | Audio/video readable by ffmpeg |
| <img src="docs/assets/platforms/direct-url.svg" width="22" alt="Direct URL"> HTTP(S) media URL | ✅ Download | `download "https://…/a.mp3"` | Public direct media URL |
| <img src="docs/assets/platforms/youtube.svg" width="22" alt="YouTube"> YouTube | 🧪 Stream probe | `process "https://youtu.be/…" --preset english` | Node runtime; restricted videos may need cookies |
| <img src="docs/assets/platforms/bilibili.svg" width="22" alt="Bilibili"> Bilibili | 🟡 Conditional | `process "https://www.bilibili.com/video/BV…" --preset knowledge` | Historical E2E success; current no-cookie probe returned 412 |
| <img src="docs/assets/platforms/douyin.svg" width="22" alt="Douyin"> Douyin | ✅ End to end | `process "https://v.douyin.com/…" --preset knowledge` | Public share download and transcription verified |

Statuses are not permanent promises. See the dated commands, first failure gates,
and icon attribution in [Platform support and verification](docs/platform-support.md).
Playlists currently use the compatibility entry:
`transcribe "<url>" --playlist --playlist-items 1-10`.

Online media downloads to `downloads/` first (usually via `yt-dlp`; Douyin has
a dedicated downloader). For bot-checked sites, knowingly set
`MOON_MEDIA_LAB_COOKIES_BROWSER` (chrome/firefox/edge/…) or
`MOON_MEDIA_LAB_COOKIES_FILE`.

## The job folder

```text
jobs/transcribe-YYYYMMDD-HHMMSS/
  input.json            the request
  state.json            status / percent / eta (machine-readable)
  media.json            probed duration, codec, sample rate
  audio.wav             normalized 16 kHz mono (for real engines)
  transcript.raw.json   normalized segments (the canonical output)
  transcript.md         readable transcript with timestamps + speakers
  segments.srt/.vtt     subtitles
  run.log               human-readable event log
  chunks/               per-chunk checkpoints (long media)
  postproc/             clean checkpoints, speakers.json, provenance.json
  knowledge.md · english-study.md · skill-draft.md · transcript.clean.md
```

The folder **is** the API — any tool (or the web UI) can poll
`state.json` and read the artifacts; there is no database.

## Configuration

Everything lives in environment variables with project-local defaults;
see [.env.example](.env.example). Highlights:

```text
MOON_MEDIA_LAB_HOME              root for models/cache/jobs/downloads/output
MOON_MEDIA_LAB_DEVICE            cpu (default) or cuda
MOON_MEDIA_LAB_WHISPER_MODEL     large-v3-turbo (default) | small | medium | ...
MOON_MEDIA_LAB_WHISPER_COMPUTE   int8 (default) | float16 | ...
MOON_MEDIA_LAB_LLM_PROVIDER      claude-cli | codex-cli | gemini-cli | mock
MOON_MEDIA_LAB_LLM_CONCURRENCY   parallel cleanup calls (default 3)
MOON_MEDIA_LAB_COOKIES_BROWSER   chrome | firefox | ... for bot-checked sites
MOON_MEDIA_LAB_COOKIES_FILE      path to a cookies.txt (alternative to browser)
MOON_MEDIA_LAB_HF_ENDPOINT       e.g. https://hf-mirror.com
MOON_MEDIA_LAB_FFMPEG            explicit ffmpeg path if not on PATH
MOON_MEDIA_LAB_TTS_VOICE         default edge-tts voice
```

Defaults are project-local, so a fresh clone is self-contained. Copy
`.env.example` and `source` it, or export only what you need.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ffmpeg not found` | `brew install ffmpeg` (or set `MOON_MEDIA_LAB_FFMPEG`) |
| Model download stalls / very slow | add `--mirror`, or set `MOON_MEDIA_LAB_HF_ENDPOINT=https://hf-mirror.com`; rerun to resume |
| Interrupted download leftovers | `moon-media models prune` |
| YouTube: "Requested format is not available" | install a JS runtime (`node`) for the n-challenge; ensure a recent standalone `yt-dlp` is on PATH |
| Bilibili `HTTP 412` | pass `MOON_MEDIA_LAB_COOKIES_BROWSER=chrome`; transient 412s auto-retry |
| Any site "needs cookies" | `MOON_MEDIA_LAB_COOKIES_BROWSER=<browser>` (must be logged in there) |
| Post-processing hangs | check the chosen `--llm` CLI works standalone; calls time out at 300s ×2 |
| Long job interrupted | `moon-media resume <job-dir>` — finished chunks are kept |

Run `moon-media doctor` any time for a full status readout.

## Exit codes

```text
0 success        3 engine not installed   6 transcription failure
1 generic        4 media probe/extract     7 post-processing failure
2 bad arguments  5 model download/load
```

## Versioning & branches

Each minor series is one product theme; small steps within a theme bump
the patch version.

| Series | Theme | Branch |
|--------|-------|--------|
| 0.1.x  | **CLI core** — audio/video conversion and local ASR | `main` |
| 0.2.x  | **Knowledge assets** — unified process presets, structured evidence, reports and Wiki export (current) | `main` |
| 0.3.x  | **Experience & adapters** — stronger UI and downstream integrations | future |

`main` stays stable and cuts all releases; big themes incubate on their
own branch and land as a new series. See [Roadmap](docs/roadmap.md).

## Documentation

- [Platform support and verification](docs/platform-support.md)
- [CLI reference](docs/cli-v1-spec.md)
- [Architecture](docs/architecture.md)
- [Engine adapter spec](docs/engine-adapter-spec.md) — add your own engine
- [Runtime & models](docs/runtime-and-models.md)
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)

## Acknowledgements

- [FunASR](https://github.com/modelscope/FunASR) — SenseVoice, Paraformer, CAM++
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Platform identification icons from [Simple Icons](https://simpleicons.org/) (CC0-1.0)
- Douyin direct-download technique from
  [vangie/douyin-transcriber](https://github.com/vangie/douyin-transcriber) (MIT)

## License

[MIT](LICENSE)
