from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from moon_media_lab.errors import InvalidArguments, ModelDownloadFailed
from moon_media_lab.paths import get_paths, redirect_model_caches

HF_ENDPOINT_DEFAULT = "https://huggingface.co"
HF_MIRROR = "https://hf-mirror.com"

# Whisper model name -> HF repo (CTranslate2 conversions used by faster-whisper).
WHISPER_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base": "Systran/faster-whisper-base",
    "base.en": "Systran/faster-whisper-base.en",
    "small": "Systran/faster-whisper-small",
    "small.en": "Systran/faster-whisper-small.en",
    "medium": "Systran/faster-whisper-medium",
    "medium.en": "Systran/faster-whisper-medium.en",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
}

SKIP_FILES = {".gitattributes", "README.md"}
CHUNK_SIZE = 1024 * 1024


class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib does not follow 308 by default; hf-mirror uses it."""

    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_301(req, fp, 301, msg, headers)


_OPENER = urllib.request.build_opener(_RedirectHandler)


def _endpoint(mirror: bool) -> str:
    configured = os.environ.get("MOON_MEDIA_LAB_HF_ENDPOINT")
    if configured:
        return configured.rstrip("/")
    return HF_MIRROR if mirror else HF_ENDPOINT_DEFAULT


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _list_repo_files(endpoint: str, repo: str) -> list[str]:
    url = f"{endpoint}/api/models/{repo}"
    try:
        with _OPENER.open(url, timeout=30) as response:
            data = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001
        raise ModelDownloadFailed(
            f"Failed to list files for {repo} via {endpoint}: {exc}",
            hint="Try --mirror (hf-mirror.com) or set MOON_MEDIA_LAB_HF_ENDPOINT.",
        ) from exc
    return [
        sibling["rfilename"]
        for sibling in data.get("siblings", [])
        if sibling["rfilename"] not in SKIP_FILES
    ]


def _download_with_resume(url: str, target: Path) -> None:
    """Stream a file with HTTP Range resume; survives flaky connections."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    offset = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": "moon-media-lab"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    try:
        with _OPENER.open(request, timeout=60) as response:
            mode = "ab" if offset and response.status == 206 else "wb"
            done = offset if mode == "ab" else 0
            next_report = done + 50 * CHUNK_SIZE
            with part.open(mode) as handle:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    if done >= next_report:
                        _progress(f"  {target.name}: {done // (1024 * 1024)} MB")
                        next_report = done + 50 * CHUNK_SIZE
    except Exception as exc:  # noqa: BLE001
        raise ModelDownloadFailed(
            f"Download failed for {url}: {exc}",
            hint="Rerun the command; downloads resume from where they stopped.",
        ) from exc
    part.replace(target)


def download_whisper_model(name: str, *, mirror: bool = False) -> Path:
    if name not in WHISPER_REPOS:
        raise InvalidArguments(
            f"Unknown whisper model: {name}",
            hint=f"Known models: {', '.join(sorted(WHISPER_REPOS))}",
        )
    repo = WHISPER_REPOS[name]
    endpoint = _endpoint(mirror)
    target_dir = get_paths().models / "asr" / "faster-whisper" / name
    files = _list_repo_files(endpoint, repo)
    _progress(f"downloading {repo} ({len(files)} files) from {endpoint}")
    for filename in files:
        target = target_dir / filename
        if target.exists():
            _progress(f"  {filename}: already present")
            continue
        _download_with_resume(f"{endpoint}/{repo}/resolve/main/{filename}", target)
        _progress(f"  {filename}: done")
    return target_dir


def download_sensevoice() -> Path:
    """SenseVoice downloads via ModelScope (CN-friendly CDN, resumable)."""
    modelscope_cache = redirect_model_caches()
    from modelscope import snapshot_download  # heavy import, explicit command only

    for model_id in ("iic/SenseVoiceSmall", "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"):
        _progress(f"downloading {model_id} via ModelScope")
        snapshot_download(model_id)
    return Path(modelscope_cache)


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def list_models() -> list[tuple[str, str]]:
    paths = get_paths()
    rows: list[tuple[str, str]] = []
    whisper_dir = paths.models / "asr" / "faster-whisper"
    if whisper_dir.exists():
        for entry in sorted(whisper_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                rows.append((f"faster-whisper/{entry.name}", _format_size(_dir_size(entry))))
    modelscope_models = paths.cache / "modelscope" / "models"
    if modelscope_models.exists():
        for owner in sorted(modelscope_models.iterdir()):
            if not owner.is_dir() or owner.name.startswith((".", "_")):
                continue
            for entry in sorted(owner.iterdir()):
                if entry.is_dir():
                    rows.append(
                        (f"modelscope/{owner.name}/{entry.name}", _format_size(_dir_size(entry)))
                    )
    return rows


def prune_models() -> list[str]:
    """Remove interrupted download leftovers (.part/.incomplete files)."""
    paths = get_paths()
    removed = []
    for root in (paths.models, paths.cache):
        if not root.exists():
            continue
        for pattern in ("*.part", "*.incomplete"):
            for stale in root.rglob(pattern):
                removed.append(str(stale.relative_to(root)))
                stale.unlink()
    return removed


def _format_size(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GB"
    return f"{size / 1024**2:.0f} MB"
