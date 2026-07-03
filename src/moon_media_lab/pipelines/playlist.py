from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from moon_media_lab.errors import MediaProbeFailed, MoonMediaError
from moon_media_lab.media.downloader import _cookie_args, _external_ytdlp


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def list_playlist_entries(url: str, items: str | None = None) -> list[str]:
    """Enumerate entry URLs of a playlist/multi-part video via yt-dlp."""
    binary = _external_ytdlp() or "yt-dlp"
    argv = [
        binary,
        "--flat-playlist",
        "--print",
        "%(url)s",
        "-q",
        "--no-warnings",
        *_cookie_args(),
    ]
    if items:
        argv += ["--playlist-items", items]
    argv.append(url)
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"Playlist enumeration failed for {url}: {completed.stderr.strip()[:300]}",
            hint="Check the URL; sites with bot checks need MOON_MEDIA_LAB_COOKIES_BROWSER.",
        )
    entries = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not entries:
        raise MediaProbeFailed(f"No playlist entries found for {url}")
    return entries


def run_playlist(url: str, *, items: str | None = None, **transcribe_kwargs) -> list[Path]:
    """Transcribe every entry of a playlist; failures skip to the next entry."""
    from moon_media_lab.pipelines.transcribe import run_transcription

    entries = list_playlist_entries(url, items)
    total = len(entries)
    _progress(f"playlist: {total} entries")
    job_dirs: list[Path] = []
    failures: list[tuple[str, str]] = []
    for index, entry in enumerate(entries, start=1):
        _progress(f"[entry {index}/{total}] {entry}")
        try:
            job_dirs.append(run_transcription(entry, **transcribe_kwargs))
        except MoonMediaError as error:
            failures.append((entry, str(error)))
            _progress(f"[entry {index}/{total}] FAILED: {error}")
    _progress(f"playlist done: {len(job_dirs)} succeeded, {len(failures)} failed")
    for entry, message in failures:
        _progress(f"  failed: {entry} ({message})")
    return job_dirs
