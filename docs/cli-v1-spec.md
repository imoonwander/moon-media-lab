# CLI v1 Spec

The first public interface should be CLI-only.

## Commands

### doctor

```bash
moon-media doctor
```

Purpose:

- print project paths
- check ffmpeg availability
- check optional engine install status
- avoid importing heavy ML packages unless explicitly requested

Optional:

```bash
moon-media doctor --engine sensevoice
moon-media doctor --engine faster-whisper
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

### process

```bash
moon-media process jobs/transcribe-20260703-221149 \
  --mode knowledge \
  --clean \
  --llm claude-cli
```

Runs LLM post-processing on a finished transcribe job:

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
