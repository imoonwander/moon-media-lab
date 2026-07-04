from moon_media_lab.pipelines.subtitles import render_srt, render_vtt
from moon_media_lab.schema import TranscriptMeta, TranscriptResult, TranscriptSegment


def _result():
    return TranscriptResult(
        meta=TranscriptMeta(engine="mock", model="m", language="zh"),
        segments=[
            TranscriptSegment(start=0.0, end=4.25, text="第一句"),
            TranscriptSegment(start=3661.5, end=3665.0, text="one hour later"),
        ],
    )


def test_srt_format():
    srt = render_srt(_result())
    assert srt.startswith("1\n00:00:00,000 --> 00:00:04,250\n第一句")
    assert "2\n01:01:01,500 --> 01:01:05,000\none hour later" in srt


def test_vtt_format():
    vtt = render_vtt(_result())
    assert vtt.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:04.250" in vtt
    assert "01:01:01.500 --> 01:01:05.000" in vtt
