from __future__ import annotations

import numpy as np

import json

import pytest

from moon_media_lab.tts.video_case import VoiceProfile, assemble_segments, run_case, split_sentences


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


def test_run_case_rejects_missing_explicit_reference_before_model_load(tmp_path):
    text_file = tmp_path / "narration.txt"
    profile_file = tmp_path / "profile.json"
    text_file.write_text("测试。", encoding="utf-8")
    profile_file.write_text(
        json.dumps(
            {
                "id": "reader",
                "description": "calm",
                "referenceText": "你好。",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="Reference audio not found"):
        run_case(
            text_file=text_file,
            profile_file=profile_file,
            output_dir=tmp_path / "output",
            reference_audio=tmp_path / "missing.wav",
        )
