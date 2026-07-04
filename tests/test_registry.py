import pytest

from moon_media_lab.asr.registry import resolve_engine_name
from moon_media_lab.errors import InvalidArguments
from moon_media_lab.llm.registry import resolve_provider_name


def test_language_routing():
    assert resolve_engine_name("auto", "zh") == "sensevoice"
    assert resolve_engine_name("auto", "en") == "faster-whisper"
    assert resolve_engine_name("auto", "mixed") == "faster-whisper"


def test_explicit_engine_wins():
    assert resolve_engine_name("mock", "zh") == "mock"
    assert resolve_engine_name("paraformer", "en") == "paraformer"


def test_unknown_engine_rejected():
    with pytest.raises(InvalidArguments):
        resolve_engine_name("nosuch", "zh")


def test_auto_language_uses_env_default(monkeypatch):
    monkeypatch.setenv("MOON_MEDIA_LAB_DEFAULT_ASR_ENGINE", "mock")
    assert resolve_engine_name("auto", "auto") == "mock"


def test_llm_provider_resolution(monkeypatch):
    assert resolve_provider_name("codex-cli") == "codex-cli"
    monkeypatch.setenv("MOON_MEDIA_LAB_LLM_PROVIDER", "mock")
    assert resolve_provider_name("auto") == "mock"
    with pytest.raises(InvalidArguments):
        resolve_provider_name("nosuch")
