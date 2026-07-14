# CLI v1 Spec

The first public interface should be CLI-only.

## Command Model

The media knowledge lifecycle is:

```text
moon-media process <source-or-job> --preset ...
moon-media package ...
moon-media export wiki ...
```

`process` is the primary media entry. `download` stops after acquisition. Low-level commands
(`transcribe`, `package`, `export`, `models`) remain stable for scripts and advanced use.
`learn media` is retained as a compatibility entry, while voice commands load `moon-voice-lab`
when installed; new voice-only workflows should use `moon-voice` directly.

### process

```bash
moon-media process interview.mp4 --preset interview --language zh
moon-media process "https://example.com/video" --preset wiki
moon-media process jobs/transcribe-... --add recommendations
```

Presets express the target bundle: `transcript`, `knowledge`, `interview`, `english`,
`research`, or `wiki`. `--add` augments a preset or an existing job and may be repeated.
Existing output is reused unless `--force` is set.

### download

```bash
moon-media download "https://example.com/video" --format video
moon-media download "https://example.com/video" --format audio
```

This command does not transcribe or call an LLM. It writes a source sidecar containing the
source URL, selected format, output file name, and SHA-256.

### learn (compatibility)

```bash
moon-media learn media <source> --language zh --mode knowledge

moon-media learn voice design \
  --id moon-reader-v1 \
  --description "warm, calm Chinese narrator" \
  --reference-text "你好，愿每一次阅读都让你更靠近自己。"

moon-media learn voice clone reference.mp4 \
  --id authorized-reader-v1 \
  --transcript "准确逐字稿" \
  --authorization-confirmed
```

`learn media` uses the legacy transcribe pipeline. `learn voice` creates a candidate asset under
`assets/voices/<voice-id>/`; it never silently overwrites an existing version.

### assets

```bash
moon-media assets voices list
moon-media assets voices list --json
moon-media assets voices show <voice-id>
```

### create

```bash
moon-media create narration narration.txt \
  --voice moon-reader-v1 \
  --output-dir output/voice-runs/episode-001
```

The command is retained during migration; creation ownership moves to `moon-voice-lab`.

## Compatibility Commands

### doctor

```bash
moon-media doctor
```

A health report — the first command a new user should run. It shows,
with ✓/○/✗ status:

- ffmpeg availability (required)
- each capability's install state (ASR engines, URL ingestion, TTS, web)
  with the exact `pip install` line to fix a missing one
- which LLM CLIs (claude/codex/gemini) are on PATH for post-processing
- downloaded models and their sizes
- a verdict: whether you can transcribe now, or the next step to get there

Never imports heavy ML packages (uses `find_spec` only).

Optional:

```bash
moon-media doctor --json              # machine-readable (CI/scripts)
moon-media doctor --engine sensevoice # check one engine's install state
```

### transcribe

```bash
moon-media transcribe <source> \
  --engine sensevoice \
  --language zh \
  --mode transcript
```

Arguments:

```text
source: local file, URL, or text depending on --kind
```

Flags:

```text
--kind file|url|text
--language auto|zh|en|mixed
--engine auto|sensevoice|faster-whisper|openai|mock
--mode transcript|knowledge|english-study|skill
--diarization
--word-timestamps
--job-dir <path>
--model-dir <path>
```

### tts

```bash
moon-media tts <text-or-file> \
  --engine edge-tts \
  --voice zh-CN-XiaoxiaoNeural \
  --output output/demo.mp3
```

### resume

```bash
moon-media resume jobs/transcribe-20260703-221149
```

Continues an interrupted transcribe job from its per-chunk checkpoints.

### legacy process flags

```bash
moon-media process jobs/transcribe-20260703-221149 \
  --mode knowledge \
  --clean \
  --llm claude-cli
```

These flags remain aliases for existing scripts that post-process a finished job:

```text
--mode knowledge|english-study|skill        generate the mode document
--clean                                     produce transcript.clean.md (batched, checkpointed,
                                            concurrent; MOON_MEDIA_LAB_LLM_CONCURRENCY, default 3)
--name-speakers                             infer names/roles for SPEAKER_NN labels and
                                            re-render transcript.md + subtitles
--llm auto|claude-cli|codex-cli|gemini-cli|mock   LLM provider adapter
```

`postproc/provenance.json` records which provider saw the data and
whether it left the machine.

### serve

```bash
moon-media serve [--host 127.0.0.1] [--port 8765]
```

Local web UI: submit files/URLs, watch queue and per-chunk progress,
read speaker-labeled segments with click-to-seek audio playback, and
trigger post-processing. Requires the `web` extra. Every job writes a
`state.json` (status/percent/eta) that any frontend can poll — the job
folder remains the API.

### models

```bash
moon-media models list
moon-media models download sensevoice
moon-media models download large-v3-turbo --mirror
moon-media models prune
```

`download` fetches whisper models file-by-file with HTTP-Range resume;
`--mirror` (or `MOON_MEDIA_LAB_HF_ENDPOINT`) switches to hf-mirror.com.
`sensevoice` and `paraformer` (diarization stack) download via
ModelScope. `prune` removes interrupted download leftovers
(`*.part`, `*.incomplete`).

### Diarization

```bash
moon-media transcribe interview.m4a --language zh --diarization
```

Routes to the `paraformer` engine (paraformer-zh + fsmn-vad + ct-punc
+ CAM++); segments carry `SPEAKER_NN` labels. Diarization runs skip
chunking so speaker ids stay globally consistent. English diarization
is not supported yet; the flag is ignored with a warning.

## Job Folder

Each `transcribe` call creates:

```text
jobs/<job_id>/
  input.json
  media.json
  run.log
  transcript.raw.json
  transcript.md
```

Optional:

```text
audio.wav
knowledge.md
english-study.md
skill-draft.md
transcript.clean.md
```

`segments.srt` and `segments.vtt` are generated automatically for real
(non-mock) engine runs.

Playlist mode creates one job per entry:

```bash
moon-media transcribe <playlist-url> --playlist --playlist-items 1-5
```

## Exit Codes

Recommended:

```text
0 success
1 generic failure
2 invalid arguments
3 engine not installed
4 media probe/extract failure
5 model download/load failure
6 transcription failure
7 post-processing failure
```

## Output

CLI should print the job directory on success:

```text
/path/to/jobs/transcribe-20260703-203159
```

Machine-readable option later:

```bash
moon-media transcribe ... --json
```

## Cross-platform Notes

The CLI must avoid shell-specific assumptions.

Path handling:

- use `pathlib`
- do not assume `/`
- do not hard-code macOS paths

ffmpeg:

- detect from `PATH`
- allow `MOON_MEDIA_LAB_FFMPEG`
- later bundle or ask GUI installer to configure it
