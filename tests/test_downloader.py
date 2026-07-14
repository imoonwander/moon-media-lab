import pytest

from moon_media_lab.media.douyin import is_douyin_url, resolve_video_id
from moon_media_lab.media.downloader import _format_selector, is_url


def test_is_url():
    assert is_url("https://example.com/a.mp3")
    assert is_url("http://example.com")
    assert not is_url("/local/path.mp3")
    assert not is_url("file.mp4")


def test_download_format_selectors():
    assert _format_selector("audio") == "bestaudio/best"
    assert _format_selector("video") == "bestvideo*+bestaudio/best"
    with pytest.raises(ValueError):
        _format_selector("document")


def test_is_douyin_url():
    assert is_douyin_url("https://v.douyin.com/abc/")
    assert is_douyin_url("https://www.douyin.com/video/123")
    assert not is_douyin_url("https://youtube.com/watch?v=x")


def test_douyin_video_id_from_canonical_url():
    assert resolve_video_id("https://www.douyin.com/video/7656311673985358267") == (
        "7656311673985358267"
    )
    assert resolve_video_id("https://www.iesdouyin.com/share/video/123456") == "123456"
