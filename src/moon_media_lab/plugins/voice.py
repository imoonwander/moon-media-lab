from __future__ import annotations

import importlib
import os
from argparse import Namespace
from pathlib import Path
from typing import Any

from moon_media_lab.paths import get_paths


def backend_name() -> str:
    requested = os.environ.get("MOON_MEDIA_LAB_VOICE_BACKEND", "auto")
    if requested == "legacy":
        return "legacy"
    try:
        importlib.import_module("moon_voice_lab.plugin")
        return "moon-voice-lab"
    except ImportError:
        return "legacy"


def _external() -> Any | None:
    if backend_name() != "moon-voice-lab":
        return None
    # Compatibility commands keep using the existing media-lab home so approved
    # assets do not move merely because the optional plugin was installed.
    os.environ.setdefault("MOON_VOICE_LAB_HOME", str(get_paths().home))
    module = importlib.import_module("moon_voice_lab.plugin")
    return module.MediaLabVoicePlugin()


def synthesize(args: Namespace) -> Path:
    plugin = _external()
    if plugin:
        return plugin.synthesize(args)
    from moon_media_lab.tts.registry import get_tts_engine

    paths = get_paths()
    paths.ensure()
    source = Path(args.text)
    text = source.read_text(encoding="utf-8") if source.is_file() else args.text
    output = Path(args.output) if args.output else paths.output / "speech.mp3"
    return get_tts_engine(args.engine).synthesize(text, output, voice=args.voice)


def learn(args: Namespace) -> Path:
    plugin = _external()
    if plugin:
        return plugin.learn(args)
    from moon_media_lab.assets.voices import design_voice_asset, import_voice_asset

    if args.voice_learn_command == "clone":
        transcript = (
            Path(args.transcript_file).read_text(encoding="utf-8")
            if args.transcript_file
            else args.transcript
        )
        return import_voice_asset(
            source=Path(args.source),
            transcript=transcript,
            voice_id=args.voice_id,
            authorization_confirmed=args.authorization_confirmed,
        ).directory
    return design_voice_asset(
        voice_id=args.voice_id,
        description=args.description,
        reference_text=args.reference_text,
    ).directory


def assets(args: Namespace) -> Any:
    plugin = _external()
    if plugin:
        return plugin.assets(args)
    from moon_media_lab.assets.voices import (
        approve_voice_asset,
        generate_voice_catalog,
        list_voice_assets,
        load_voice_asset,
    )

    if args.voices_command == "list":
        return list_voice_assets()
    if args.voices_command == "show":
        asset = load_voice_asset(args.voice_id)
        payload = dict(asset.manifest)
        payload.update(directory=str(asset.directory), profile=str(asset.profile), reference=str(asset.reference))
        return payload
    if args.voices_command == "approve":
        return approve_voice_asset(
            voice_id=args.voice_id,
            display_name=args.name,
            summary=args.summary,
            sample=args.sample,
            usage_note=args.usage_note,
            license_name=args.license,
            attribution=args.attribution,
            public_release_confirmed=args.public_release_confirmed,
        ).directory
    output = Path(args.output_dir) if args.output_dir else get_paths().output / "voice-catalog"
    index, catalog, count = generate_voice_catalog(output_dir=output)
    return {"index": str(index), "catalog": str(catalog), "voices": count}


def narration(args: Namespace) -> dict[str, Any]:
    plugin = _external()
    if plugin:
        return plugin.narration(args)
    from datetime import datetime

    from moon_media_lab.assets.voices import load_voice_asset
    from moon_media_lab.tts.video_case import run_case

    asset = load_voice_asset(args.voice)
    output = Path(args.output_dir) if args.output_dir else (
        get_paths().output / "voice-runs" / f"narration-{datetime.now():%Y%m%d-%H%M%S}"
    )
    return run_case(
        text_file=Path(args.text_file),
        profile_file=asset.profile,
        output_dir=output,
        reference_audio=asset.reference,
    )

