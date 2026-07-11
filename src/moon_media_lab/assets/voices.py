from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from moon_media_lab.errors import InvalidArguments, MediaProbeFailed
from moon_media_lab.media.resolver import find_tool
from moon_media_lab.paths import get_paths

VOICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*-v[1-9][0-9]*$")
DEFAULT_CLONE_MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-6bit"
DEFAULT_DESIGN_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-6bit"


@dataclass(frozen=True)
class VoiceAsset:
    voice_id: str
    directory: Path
    manifest: dict[str, Any]
    profile: Path
    reference: Path


def voice_assets_root() -> Path:
    return get_paths().home / "assets" / "voices"


def validate_voice_id(voice_id: str) -> str:
    if not VOICE_ID_PATTERN.fullmatch(voice_id):
        raise InvalidArguments(
            f"Invalid voice id: {voice_id}",
            hint="Use a versioned lowercase id such as moon-reader-v1.",
        )
    return voice_id


def list_voice_assets(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or voice_assets_root()
    if not base.exists():
        return []
    assets = []
    for manifest_path in sorted(base.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        assets.append(manifest)
    return assets


def load_voice_asset(voice_id: str, root: Path | None = None) -> VoiceAsset:
    validate_voice_id(voice_id)
    directory = (root or voice_assets_root()) / voice_id
    manifest_path = directory / "manifest.json"
    profile_path = directory / "profile.json"
    reference_path = directory / "reference.wav"
    missing = [
        path.name
        for path in (manifest_path, profile_path, reference_path)
        if not path.is_file()
    ]
    if missing:
        raise InvalidArguments(
            f"Voice asset '{voice_id}' is incomplete: missing {', '.join(missing)}",
            hint=f"Inspect {directory} or import it again with 'moon-media learn voice'.",
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return VoiceAsset(voice_id, directory, manifest, profile_path, reference_path)


def import_voice_asset(
    *,
    source: Path,
    transcript: str,
    voice_id: str,
    authorization_confirmed: bool,
    root: Path | None = None,
) -> VoiceAsset:
    validate_voice_id(voice_id)
    if not authorization_confirmed:
        raise InvalidArguments(
            "Voice authorization is required.",
            hint="Only import your own voice or an explicitly authorized voice; pass "
            "--authorization-confirmed after verification.",
        )
    if not source.is_file():
        raise InvalidArguments(f"Reference media not found: {source}")
    transcript = transcript.strip()
    if not transcript:
        raise InvalidArguments("Reference transcript cannot be empty.")

    directory = (root or voice_assets_root()) / voice_id
    if directory.exists():
        raise InvalidArguments(
            f"Voice asset already exists: {voice_id}",
            hint="Create a new version instead of overwriting a frozen voice asset.",
        )
    samples_dir = directory / "samples"
    samples_dir.mkdir(parents=True)
    reference_path = directory / "reference.wav"

    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        raise MediaProbeFailed("ffmpeg not found", hint="Install ffmpeg or set PATH.")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "pcm_s16le",
        str(reference_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"Failed to extract voice reference from {source}",
            hint=completed.stderr.strip()[-800:] or "Check the input media with ffprobe.",
        )

    profile = {
        "id": voice_id,
        "description": "",
        "referenceText": transcript,
        "language": "Chinese",
        "cloneModel": DEFAULT_CLONE_MODEL,
        "seed": 42,
        "temperature": 0.65,
        "pauseMs": 180,
    }
    profile_path = directory / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "id": voice_id,
        "version": int(voice_id.rsplit("-v", 1)[1]),
        "sourceType": "authorized-clone-reference",
        "authorization": "confirmed-by-operator",
        "referenceSha256": _sha256(reference_path),
        "referenceDuration": _wav_duration(reference_path),
        "status": "candidate",
        "createdAt": date.today().isoformat(),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return VoiceAsset(voice_id, directory, manifest, profile_path, reference_path)


def design_voice_asset(
    *,
    voice_id: str,
    description: str,
    reference_text: str,
    root: Path | None = None,
) -> VoiceAsset:
    from moon_media_lab.tts.video_case import run_case

    validate_voice_id(voice_id)
    description = description.strip()
    reference_text = reference_text.strip()
    if not description:
        raise InvalidArguments("Voice description cannot be empty.")
    if not reference_text:
        raise InvalidArguments("Reference text cannot be empty.")

    directory = (root or voice_assets_root()) / voice_id
    if directory.exists():
        raise InvalidArguments(
            f"Voice asset already exists: {voice_id}",
            hint="Create a new version instead of overwriting a frozen voice asset.",
        )

    profile = {
        "id": voice_id,
        "description": description,
        "referenceText": reference_text,
        "language": "Chinese",
        "designModel": DEFAULT_DESIGN_MODEL,
        "cloneModel": DEFAULT_CLONE_MODEL,
        "seed": 42,
        "temperature": 0.7,
        "pauseMs": 180,
    }
    runs_root = get_paths().output / "voice-runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"design-{voice_id}-", dir=runs_root) as temp:
        temp_dir = Path(temp)
        profile_path = temp_dir / "profile.json"
        text_path = temp_dir / "reference.txt"
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        text_path.write_text(reference_text, encoding="utf-8")
        result = run_case(
            text_file=text_path,
            profile_file=profile_path,
            output_dir=temp_dir,
            reference_only=True,
        )
        generated_reference = Path(result["referenceAudio"])
        (directory / "samples").mkdir(parents=True)
        reference_path = directory / "reference.wav"
        shutil.copy2(generated_reference, reference_path)

    stored_profile = directory / "profile.json"
    stored_profile.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "id": voice_id,
        "version": int(voice_id.rsplit("-v", 1)[1]),
        "sourceType": "voice-design",
        "authorization": "not-applicable-synthetic",
        "referenceSha256": _sha256(reference_path),
        "referenceDuration": _wav_duration(reference_path),
        "status": "candidate",
        "createdAt": date.today().isoformat(),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return VoiceAsset(voice_id, directory, manifest, stored_profile, reference_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return round(handle.getnframes() / handle.getframerate(), 6)
