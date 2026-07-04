from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture()
def lab_home(tmp_path, monkeypatch):
    """Point all lab paths at a temp directory."""
    monkeypatch.setenv("MOON_MEDIA_LAB_HOME", str(tmp_path))
    for name in ("MODELS", "CACHE", "JOBS", "DOWNLOADS", "OUTPUT"):
        monkeypatch.delenv(f"MOON_MEDIA_LAB_{name}_DIR", raising=False)
    return tmp_path
