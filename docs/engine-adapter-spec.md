# Engine Adapter Spec

## Core Contract

All ASR engines must implement:

```text
TranscribeRequest -> TranscriptResult
```

Business logic and post processors must not consume engine-specific objects.

## TranscribeRequest

```json
{
  "media": {
    "source": "path-or-url",
    "kind": "file|url|text",
    "language": "auto|zh|en|mixed"
  },
  "mode": "transcript|knowledge|english-study|skill",
  "engine": "auto|sensevoice|faster-whisper|openai|mock",
  "need_diarization": false,
  "need_word_timestamps": false
}
```

## TranscriptResult

```json
{
  "meta": {
    "engine": "sensevoice",
    "model": "iic/SenseVoiceSmall",
    "language": "zh",
    "duration_sec": 31.2,
    "runtime_sec": 7.4,
    "cost_usd": 0,
    "extra": {
      "device": "cpu",
      "model_path": "cache/modelscope/..."
    }
  },
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "speaker": "SPEAKER_00",
      "text": "转录文本",
      "confidence": 0.91
    }
  ]
}
```

## Segment Rules

- `start` and `end` are seconds.
- `text` must be cleaned enough for reading, but raw engine output can be stored in `extra` if needed.
- `speaker` can be null when diarization is not available.
- `confidence` can be null when unavailable.
- Segments must be sorted by `start`.

## Engine Metadata Rules

`meta.engine` should be stable values:

```text
mock
sensevoice
faster-whisper
whisper-cpp
openai
```

`meta.model` should record the exact model:

```text
iic/SenseVoiceSmall
large-v3-turbo
whisper-large-v3
gpt-4o-mini-transcribe
```

## Error Rules

Use explicit errors:

```text
EngineNotInstalled
ModelDownloadFailed
MediaProbeFailed
TranscriptionFailed
UnsupportedLanguage
UnsupportedOption
```

Errors should include:

- engine
- model
- source
- user-actionable fix

## SenseVoice/FunASR Notes

Implementation target:

```text
engine: sensevoice
model: iic/SenseVoiceSmall
```

Expected responsibilities:

- lazy import FunASR
- set project-local cache paths before model loading
- accept local wav/mp3/m4a/mp4 after media resolver normalizes audio
- convert FunASR output into `TranscriptResult`

## faster-whisper Notes

Implementation target:

```text
engine: faster-whisper
model: large-v3-turbo
```

Expected responsibilities:

- lazy import faster-whisper
- support `compute_type` configuration
- support model path/cache directory
- convert segments into `TranscriptResult`

## TTS Adapter

TTS should follow a similar adapter style:

```text
SynthesizeRequest -> SynthesizeResult
```

Future shape:

```json
{
  "text": "hello",
  "voice": "zh-CN-XiaoxiaoNeural",
  "engine": "edge-tts",
  "format": "mp3",
  "output_path": "output/hello.mp3"
}
```
