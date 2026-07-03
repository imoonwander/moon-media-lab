from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from moon_media_lab.errors import MediaProbeFailed

# Technique ported from vangie/douyin-transcriber (MIT):
# Douyin's mobile share page needs no cookies/login and embeds CDN URLs
# in window._ROUTER_DATA, unlike the desktop API that yt-dlp uses.
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

VIDEO_ID_PATTERN = re.compile(r"(?:/share)?/video/(\d+)")
ROUTER_DATA_PATTERN = re.compile(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", re.DOTALL)


def is_douyin_url(source: str) -> bool:
    return "douyin.com/" in source.lower()


def _get(url: str, timeout: int = 30) -> tuple[str, bytes]:
    """GET with mobile UA; returns (final_url, body)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": MOBILE_UA, "Referer": "https://www.douyin.com/"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.geturl(), response.read()


def resolve_video_id(url: str) -> str:
    match = VIDEO_ID_PATTERN.search(url)
    if not match:
        # Short link (v.douyin.com): follow redirects to the canonical URL.
        final_url, _ = _get(url)
        match = VIDEO_ID_PATTERN.search(final_url)
    if not match:
        raise MediaProbeFailed(f"Could not extract Douyin video id from {url}")
    return match.group(1)


def fetch_video_info(video_id: str) -> tuple[str, str]:
    """Return (title, cdn_video_url) from the mobile share page."""
    share_url = f"https://www.iesdouyin.com/share/video/{video_id}"
    _, body = _get(share_url)
    html = body.decode("utf-8", errors="replace")

    match = ROUTER_DATA_PATTERN.search(html)
    if not match:
        raise MediaProbeFailed(
            f"_ROUTER_DATA not found in Douyin share page for video {video_id}",
            hint="Douyin may have changed its mobile page; try again or report.",
        )
    router_data = json.loads(match.group(1).strip())

    loader_data = router_data.get("loaderData", {})
    page = loader_data.get("video_(id)/page", {})
    items = page.get("videoInfoRes", {}).get("item_list", [])
    if not items:
        raise MediaProbeFailed(f"No video items in Douyin share data for {video_id}")

    item = items[0]
    title = (item.get("desc") or f"douyin-{video_id}").strip()
    url_list = item.get("video", {}).get("play_addr", {}).get("url_list", [])
    if not url_list:
        raise MediaProbeFailed(f"No playable URL in Douyin share data for {video_id}")
    # "playwm" is the watermarked variant; "play" is clean.
    video_url = url_list[0].replace("playwm", "play")
    return title, video_url


def download_douyin(url: str, downloads_dir: Path) -> Path:
    """Download a Douyin video directly from its CDN; returns the local path."""
    video_id = resolve_video_id(url)
    title, video_url = fetch_video_info(video_id)
    safe_title = re.sub(r'[\\/:*?"<>|\s]+', "-", title)[:60].strip("-")
    target = downloads_dir / f"{safe_title}-{video_id}.mp4"
    try:
        _, body = _get(video_url, timeout=300)
    except Exception as exc:  # noqa: BLE001
        raise MediaProbeFailed(f"Douyin CDN download failed for {url}: {exc}") from exc
    if not body:
        raise MediaProbeFailed(f"Douyin CDN returned empty body for {url}")
    target.write_bytes(body)
    return target
