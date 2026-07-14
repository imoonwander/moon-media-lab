from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.jobs import write_json


LAYER_FILES = {
    "source": [
        "input.json",
        "media.json",
        "audio.wav",
        "transcript.raw.json",
        "segments.srt",
        "segments.vtt",
    ],
    "transcript": [
        "transcript.md",
        "transcript.clean.md",
        "transcript.speakers.md",
        "transcript.en.clean.md",
        "transcript.bilingual.md",
    ],
    "knowledge": [
        "knowledge.md",
        "knowledge.structured.json",
        "recommendations.md",
        "english-study.md",
    ],
    "derivative": ["skill-draft.md"],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(job_dir: Path, path: Path, layer: str) -> dict[str, Any]:
    stat = path.stat()
    return {
        "id": f"{job_dir.name}:{path.relative_to(job_dir).as_posix()}",
        "layer": layer,
        "path": path.relative_to(job_dir).as_posix(),
        "mediaType": _media_type(path),
        "bytes": stat.st_size,
        "sha256": _sha256(path),
    }


def _media_type(path: Path) -> str:
    return {
        ".json": "application/json",
        ".md": "text/markdown",
        ".srt": "application/x-subrip",
        ".vtt": "text/vtt",
        ".wav": "audio/wav",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(path.suffix.lower(), "application/octet-stream")


def build_knowledge_bundle(job_dir: Path) -> Path:
    """Create the machine-readable four-layer contract for one media job."""
    job_dir = job_dir.expanduser().resolve()
    if not (job_dir / "transcript.raw.json").is_file():
        raise InvalidArguments(
            f"Not a completed media job: {job_dir}",
            hint="Expected transcript.raw.json. Finish or resume transcription first.",
        )

    artifacts: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for layer, names in LAYER_FILES.items():
        for name in names:
            path = job_dir / name
            if path.is_file():
                artifacts.append(_artifact(job_dir, path, layer))
                seen.add(path)

    visuals = job_dir / "visuals"
    if visuals.is_dir():
        for path in sorted(item for item in visuals.rglob("*") if item.is_file()):
            artifacts.append(_artifact(job_dir, path, "derivative"))
            seen.add(path)

    postproc_provenance = job_dir / "postproc" / "provenance.json"
    provenance = (
        json.loads(postproc_provenance.read_text(encoding="utf-8"))
        if postproc_provenance.is_file()
        else {}
    )
    input_payload = _read_json(job_dir / "input.json")
    media_payload = _read_json(job_dir / "media.json")
    media_input = input_payload.get("media", input_payload)
    manifest = {
        "schemaVersion": "0.1.0",
        "id": f"knowledge:{job_dir.name}",
        "kind": "media-knowledge-bundle",
        "status": "candidate",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "value": media_input.get("source"),
            "kind": media_input.get("kind"),
            "language": media_input.get("language"),
            "media": media_payload,
        },
        "layers": ["source", "transcript", "knowledge", "derivative"],
        "artifacts": artifacts,
        "rights": {
            "visibility": "private",
            "sourceRightsReviewed": False,
            "publicReleaseConfirmed": False,
        },
        "provenance": provenance,
        "sqlite": {"enabled": False, "reason": "Deferred by product decision"},
    }
    output = job_dir / "knowledge-bundle.manifest.json"
    write_json(output, manifest)
    return output


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
