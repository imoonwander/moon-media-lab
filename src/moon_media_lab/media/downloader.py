from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import time

from moon_media_lab.errors import EngineNotInstalled, MediaProbeFailed
from moon_media_lab.media.douyin import is_douyin_url

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


def _ua_args(url: str) -> list[str]:
    ua = os.environ.get("MOON_MEDIA_LAB_HTTP_UA")
    if ua:
        return ["--user-agent", ua]
    # Bilibili's WAF intermittently 412s Chrome-family UAs; Safari passes.
    if "bilibili.com" in url:
        return [
            "--user-agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        ]
    return []


def _format_selector(media_format: str) -> str:
    if media_format == "audio":
        return "bestaudio/best"
    if media_format == "video":
        return "bestvideo*+bestaudio/best"
    raise ValueError(f"Unknown download format: {media_format}")


def _download_via_binary(
    binary: str, url: str, downloads_dir: Path, media_format: str
) -> Path:
    argv = [
        binary,
        "--no-playlist",
        "-f",
        _format_selector(media_format),
        "-o",
        str(downloads_dir / OUTPUT_TEMPLATE),
        "--no-simulate",
        "--print",
        "after_move:filepath",
        "-q",
        "--no-warnings",
        *_cookie_args(),
        *_js_runtime_args(),
        *_ua_args(url),
    ]
    if media_format == "video":
        argv += ["--merge-output-format", "mp4"]
    argv.append(url)
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


def _download_via_module(url: str, downloads_dir: Path, media_format: str) -> Path:
    if importlib.util.find_spec("yt_dlp") is None:
        raise EngineNotInstalled(
            "yt-dlp is not installed for URL ingestion.",
            hint="Install it: pip install 'moon-media-lab[url]' "
            "or put a yt-dlp binary on PATH.",
        )
    import yt_dlp

    options = {
        "format": _format_selector(media_format),
        "outtmpl": str(downloads_dir / OUTPUT_TEMPLATE),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if media_format == "video":
        options["merge_output_format"] = "mp4"
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
            prepared = Path(ydl.prepare_filename(info))
            # prepare_filename describes the extractor's pre-merge container.
            # yt-dlp may move the final merged video to an mp4 sibling.
            if media_format == "video":
                merged = prepared.with_suffix(".mp4")
                if merged.is_file():
                    return merged
            return prepared
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises many error types
        raise MediaProbeFailed(
            f"Download failed for {url}: {exc}",
            hint="Check the URL and network; some sites need cookies "
            "(MOON_MEDIA_LAB_COOKIES_BROWSER) or are region-locked.",
        ) from exc


def download_media(url: str, downloads_dir: Path, *, media_format: str = "audio") -> Path:
    """Download online media via yt-dlp; return the local file path.

    Transcription uses the audio default. The public `download` command requests
    video by default so acquisition remains independent from knowledge processing.
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)
    binary = _external_ytdlp()
    # Sites rate-limit bursts (e.g. Bilibili HTTP 412); brief retries absorb them.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if is_douyin_url(url):
                # yt-dlp's Douyin extractor is broken upstream (desktop API
                # requires fresh cookies); the mobile share page path works.
                from moon_media_lab.media.douyin import download_douyin

                path = download_douyin(url, downloads_dir)
            else:
                path = (
                    _download_via_binary(binary, url, downloads_dir, media_format)
                    if binary
                    else _download_via_module(url, downloads_dir, media_format)
                )
            break
        except MediaProbeFailed:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SEC)
    if not path.exists():
        raise MediaProbeFailed(f"yt-dlp reported success but file is missing: {path}")
    return path
