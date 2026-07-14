# Voice plugin migration

Voice generation is being separated into [`moon-voice-lab`](https://github.com/imoonwander/moon-voice-lab). Media knowledge extraction remains the primary responsibility of this repository.

## Non-breaking phase

These compatibility commands remain available:

```bash
moon-media tts
moon-media learn voice
moon-media assets voices
moon-media create narration
```

They now call a lazy voice adapter. If `moon-voice-lab` is importable, it is selected and receives the existing media-lab home so current `assets/voices/` continue to work. Otherwise the bundled legacy implementation is used.

To force the old implementation while diagnosing migration:

```bash
MOON_MEDIA_LAB_VOICE_BACKEND=legacy moon-media assets voices list
```

## Standalone path

New voice-only workflows should install and call `moon-voice-lab` directly:

```bash
moon-voice learn clone ...
moon-voice assets list
moon-voice narration ...
```

Removal from this repository is a later major-version decision. It requires migrated assets, more than one proven downstream consumer, stable export compatibility and an explicit deprecation window.

