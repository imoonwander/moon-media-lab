# Moon Media Lab

Local-first media lab: turn audio, video, and online media into
transcripts, subtitles, knowledge notes, study material — and voice.

```text
file / YouTube / Bilibili / Douyin / direct URL
        │
        ▼
  transcribe (SenseVoice · Paraformer+CAM++ · faster-whisper)
        │
        ▼
  transcript.md + segments.srt/vtt  (timestamps, speakers)
        │
        ▼
  process (any LLM CLI you already have)
        │
        ▼
  knowledge.md · english-study.md · skill-draft.md · transcript.clean.md
```

Speech recognition runs **entirely on your machine**. LLM post-processing
is opt-in and goes through whichever CLI you already use (`claude`,
`codex`, `gemini`); every output records which provider saw the data in
`postproc/provenance.json`.

## Features

- **Chinese ASR** — SenseVoice (fast) or Paraformer + CAM++ with
  `--diarization` for speaker-labeled interviews
- **English ASR** — faster-whisper `large-v3-turbo` with per-segment
  timestamps and confidence
- **Speaker naming** — `process --name-speakers` turns `SPEAKER_00`
  into inferred names/roles and re-renders transcript + subtitles
- **Online media** — `transcribe <url>` downloads via yt-dlp
  (YouTube/Bilibili need browser cookies); Douyin uses a built-in
  cookie-free direct downloader
- **Long media** — silence-aligned chunking, per-chunk checkpoints,
  `resume <job-dir>`, progress/ETA, `transcript.partial.md` while running
- **Playlists** — `--playlist [--playlist-items 1-5]`, one job per entry
- **Subtitles** — `segments.srt` / `segments.vtt` for every job
- **LLM post-processing** — summary/outline/knowledge cards, English
  study notes, SOP drafts, batched+concurrent transcript cleanup
- **TTS** — `moon-media tts` via Edge neural voices
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
.venv/bin/pip install -e '.[asr-sensevoice,asr-whisper,url,tts-edge]'
.venv/bin/moon-media doctor   # health report: what's ready, what's next
```

`moon-media doctor` prints a ✓/○/✗ checklist of ffmpeg, engines, LLM
CLIs, and downloaded models, ending with whether you can transcribe now
or the exact next step. Run it first.

Pick only the extras you need — the base CLI has zero dependencies.

**Global install** (use `moon-media` from anywhere):

```bash
pipx install 'moon-media-lab[asr-sensevoice,asr-whisper,url,tts-edge]'
# or, from a clone: ln -s "$(pwd)/.venv/bin/moon-media" ~/.local/bin/moon-media
```
For URL ingestion a standalone `yt-dlp` binary on PATH is preferred
(site extractors age quickly; the pip copy is pinned by your Python).

## Quickstart

```bash
# bundled 8-second sample (Chinese)
.venv/bin/moon-media transcribe examples/hello-zh.wav --language zh

# a Chinese interview with speaker labels (first run downloads ~1.2 GB of models)
.venv/bin/moon-media transcribe interview.m4a --language zh --diarization

# an English podcast from YouTube (first run downloads ~1.6 GB; use --mirror in CN)
.venv/bin/moon-media models download large-v3-turbo --mirror
MOON_MEDIA_LAB_COOKIES_BROWSER=chrome \
  .venv/bin/moon-media transcribe "https://youtu.be/..." --language en

# post-process a finished job with the LLM CLI you already have
.venv/bin/moon-media process jobs/transcribe-... --mode knowledge --clean --llm codex-cli

# or do all of the above from a browser
.venv/bin/pip install -e '.[web]'
.venv/bin/moon-media serve        # → http://127.0.0.1:8765
```

Every run creates `jobs/<job-id>/` with `transcript.md`,
`transcript.raw.json`, `segments.srt/vtt`, `run.log`, and any
post-processing outputs. The job folder is the API — nothing else to learn.

## Configuration

Everything lives in environment variables with project-local defaults;
see [.env.example](.env.example). Highlights:

```text
MOON_MEDIA_LAB_HOME              root for models/cache/jobs/downloads/output
MOON_MEDIA_LAB_DEVICE            cpu (default) or cuda
MOON_MEDIA_LAB_WHISPER_MODEL     large-v3-turbo (default) | small | medium | ...
MOON_MEDIA_LAB_LLM_PROVIDER      claude-cli | codex-cli | gemini-cli | mock
MOON_MEDIA_LAB_LLM_CONCURRENCY   parallel cleanup calls (default 3)
MOON_MEDIA_LAB_COOKIES_BROWSER   chrome | firefox | ... for bot-checked sites
MOON_MEDIA_LAB_HF_ENDPOINT       e.g. https://hf-mirror.com
```

## Versioning & branches

Each minor series is one product theme; small steps within a theme bump
the patch version.

| Series | Theme | Branch |
|--------|-------|--------|
| 0.1.x  | **CLI core** — excellent audio/video conversion, open-source ready, global install (current focus) | `main` |
| 0.2.x  | **Web experience** — UI/UX rebuilt to expectation; merges from the `web-ui` branch | `web-ui` |
| 0.3.x  | **Voice & beyond** — TTS as a product line, reader deepening, integrations | future |

`main` stays stable and cuts all releases; big themes incubate on their
own branch and land as a new series. See [Roadmap](docs/roadmap.md).

## Documentation

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
- Douyin direct-download technique from
  [vangie/douyin-transcriber](https://github.com/vangie/douyin-transcriber) (MIT)

## License

[MIT](LICENSE)
