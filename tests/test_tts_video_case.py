from __future__ import annotations

import numpy as np

import json

from moon_media_lab.tts.video_case import VoiceProfile, assemble_segments, split_sentences


def test_split_sentences_handles_chinese_paragraphs():
    text = "第一句。\n\n第二句！还有第三句？"
    assert split_sentences(text) == ["第一句。", "第二句！", "还有第三句？"]


def test_split_sentences_preserves_spaces_inside_english():
    assert split_sentences("Hello Moon. This is a test!") == [
        "Hello Moon.",
        "This is a test!",
    ]


def test_assemble_segments_emits_exact_timeline():
    sentences = ["第一句。", "第二句。"]
    segments = [np.ones(10, dtype=np.float32), np.ones(20, dtype=np.float32)]

    audio, timeline = assemble_segments(sentences, segments, sample_rate=10, pause_ms=200)

    assert len(audio) == 32
    assert timeline == [
        {"index": 1, "text": "第一句。", "start": 0.0, "end": 1.0},
        {"index": 2, "text": "第二句。", "start": 1.2, "end": 3.2},
    ]


def test_voice_profile_allows_local_model_overrides(tmp_path, monkeypatch):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "id": "reader",
                "description": "calm",
                "referenceText": "hello",
                "designModel": "remote-design",
                "cloneModel": "remote-clone",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MOON_MEDIA_LAB_QWEN3_DESIGN_MODEL", "/models/design")
    monkeypatch.setenv("MOON_MEDIA_LAB_QWEN3_CLONE_MODEL", "/models/clone")

    profile = VoiceProfile.from_json(profile_path)

    assert profile.design_model == "/models/design"
    assert profile.clone_model == "/models/clone"
