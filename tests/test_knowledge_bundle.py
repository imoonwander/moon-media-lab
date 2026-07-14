from __future__ import annotations

import json

from moon_media_lab.jobs import write_json
from moon_media_lab.knowledge import build_knowledge_bundle, export_wiki_bundle


def _job(tmp_path):
    job = tmp_path / "jobs" / "transcribe-knowledge"
    job.mkdir(parents=True)
    write_json(
        job / "transcript.raw.json",
        {
            "meta": {"engine": "mock", "model": "mock", "language": "zh"},
            "segments": [{"start": 0, "end": 2, "text": "知识来自证据。"}],
        },
    )
    write_json(job / "input.json", {"source": "demo.mp4", "kind": "file", "language": "zh"})
    (job / "transcript.md").write_text("# Transcript\n", encoding="utf-8")
    (job / "transcript.clean.md").write_text("# 整理稿\n", encoding="utf-8")
    (job / "knowledge.md").write_text("# 知识来自证据\n", encoding="utf-8")
    write_json(
        job / "knowledge.structured.json",
        {
            "summary": "知识来自证据。",
            "concepts": [],
            "claims": [],
            "evidence": [],
            "entities": [],
            "relations": [],
            "openQuestions": [],
        },
    )
    return job


def test_manifest_has_four_layers_and_hashes(tmp_path):
    job = _job(tmp_path)
    output = build_knowledge_bundle(job)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["layers"] == ["source", "transcript", "knowledge", "derivative"]
    assert payload["sqlite"]["enabled"] is False
    assert {item["layer"] for item in payload["artifacts"]} >= {
        "source",
        "transcript",
        "knowledge",
    }
    assert all(len(item["sha256"]) == 64 for item in payload["artifacts"])


def test_wiki_export_is_portable_markdown_and_json(tmp_path):
    job = _job(tmp_path)
    output = export_wiki_bundle(job, tmp_path / "wiki")
    assert (output / "index.md").is_file()
    assert (output / "knowledge.json").is_file()
    assert (output / "transcript.clean.md").is_file()
    payload = json.loads((output / "knowledge.json").read_text(encoding="utf-8"))
    assert payload["knowledge"]["summary"] == "知识来自证据。"

