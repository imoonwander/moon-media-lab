from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import time

from moon_media_lab.errors import EngineNotInstalled, MediaProbeFailed

OUTPUT_TEMPLATE = "%(title).80s-%(id)s.%(ext)s"
MAX_ATTEMPTS = 3
RETRY_DELAY_SEC = 15


def is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def _external_ytdlp() -> str | None:
    """Prefer a standalone yt-dlp binary: extractors age fast and the binary
    can be newer than what this venv's Python version allows via pip."""
    override = os.environ.get("MOON_MEDIA_LAB_YTDLP_BIN")
    if override:
        return override
    found = shutil.which("yt-dlp")
    # Skip this venv's own pip copy; it is pinned by the venv's Python version.
    if found and not found.startswith(sys.prefix):
        return found
    return None


def _cookie_args() -> list[str]:
    args: list[str] = []
    browser = os.environ.get("MOON_MEDIA_LAB_COOKIES_BROWSER")
    if browser:
        args += ["--cookies-from-browser", browser]
    cookie_file = os.environ.get("MOON_MEDIA_LAB_COOKIES_FILE")
    if cookie_file:
        args += ["--cookies", cookie_file]
    return args


def _js_runtime_args() -> list[str]:
    # YouTube's n-challenge needs a JS runtime; yt-dlp only enables deno by
    # default, so surface node when it is the runtime actually installed.
    if shutil.which("deno"):
        return []
    if shutil.which("node"):
        return ["--js-runtimes", "node"]
    return []


def _download_via_binary(binary: str, url: str, downloads_dir: Path) -> Path:
    argv = [
        binary,
        "--no-playlist",
        "-f",
        "bestaudio/best",
        "-o",
        str(downloads_dir / OUTPUT_TEMPLATE),
        "--no-simulate",
        "--print",
        "after_move:filepath",
        "-q",
        "--no-warnings",
        *_cookie_args(),
        *_js_runtime_args(),
        url,
    ]
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"Download failed for {url}: {completed.stderr.strip()[:500]}",
            hint="Check the URL and network; some sites need cookies "
            "(MOON_MEDIA_LAB_COOKIES_BROWSER) or are region-locked.",
        )
    lines = [line for line in completed.stdout.strip().splitlines() if line.strip()]
    if not lines:
        raise MediaProbeFailed(f"yt-dlp produced no output path for {url}")
    return Path(lines[-1])


def _download_via_module(url: str, downloads_dir: Path) -> Path:
    if importlib.util.find_spec("yt_dlp") is None:
        raise EngineNotInstalled(
            "yt-dlp is not installed for URL ingestion.",
            hint="Install it: pip install 'moon-media-lab[url]' "
            "or put a yt-dlp binary on PATH.",
        )
    import yt_dlp

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(downloads_dir / OUTPUT_TEMPLATE),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    browser = os.environ.get("MOON_MEDIA_LAB_COOKIES_BROWSER")
    if browser:
        options["cookiesfrombrowser"] = (browser,)
    cookie_file = os.environ.get("MOON_MEDIA_LAB_COOKIES_FILE")
    if cookie_file:
        options["cookiefile"] = cookie_file
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:  # playlist despite noplaylist, take first
                info = info["entries"][0]
            return Path(ydl.prepare_filename(info))
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises many error types
        raise MediaProbeFailed(
            f"Download failed for {url}: {exc}",
            hint="Check the URL and network; some sites need cookies "
            "(MOON_MEDIA_LAB_COOKIES_BROWSER) or are region-locked.",
        ) from exc


def download_media(url: str, downloads_dir: Path) -> Path:
    """Download online media as audio via yt-dlp; return the local file path."""
    downloads_dir.mkdir(parents=True, exist_ok=True)
    binary = _external_ytdlp()
    # Sites rate-limit bursts (e.g. Bilibili HTTP 412); brief retries absorb them.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            path = (
                _download_via_binary(binary, url, downloads_dir)
                if binary
                else _download_via_module(url, downloads_dir)
            )
            break
        except MediaProbeFailed:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SEC)
    if not path.exists():
        raise MediaProbeFailed(f"yt-dlp reported success but file is missing: {path}")
    return path
