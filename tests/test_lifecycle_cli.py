from __future__ import annotations

import json
import wave

import pytest

from moon_media_lab.assets.voices import (
    approve_voice_asset,
    design_voice_asset,
    generate_voice_catalog,
    import_voice_asset,
    validate_voice_id,
)
from moon_media_lab.cli import main
from moon_media_lab.errors import InvalidArguments


def _write_voice_asset(lab_home, voice_id="reader-v1"):
    directory = lab_home / "assets" / "voices" / voice_id
    directory.mkdir(parents=True)
    manifest = {
        "id": voice_id,
        "version": 1,
        "sourceType": "voice-design",
        "status": "approved",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "profile.json").write_text(
        json.dumps(
            {
                "id": voice_id,
                "description": "calm",
                "referenceText": "你好。",
            }
        ),
        encoding="utf-8",
    )
    with wave.open(str(directory / "reference.wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\0\0" * 240)
    samples = directory / "samples"
    samples.mkdir()
    with wave.open(str(samples / "preview.wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\0\0" * 240)
    return directory


def test_learn_media_is_high_level_transcribe_alias(lab_home):
    source = lab_home / "input.txt"
    source.write_text("第一行。\n第二行。\n", encoding="utf-8")

    assert main(["learn", "media", str(source), "--engine", "mock", "--language", "zh"]) == 0

    jobs = list((lab_home / "jobs").glob("transcribe-*"))
    assert len(jobs) == 1
    assert (jobs[0] / "transcript.md").is_file()


def test_assets_voices_list_and_show(lab_home, capsys):
    directory = _write_voice_asset(lab_home)

    assert main(["assets", "voices", "list"]) == 0
    assert "reader-v1" in capsys.readouterr().out

    assert main(["assets", "voices", "show", "reader-v1"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "reader-v1"
    assert payload["directory"] == str(directory)


def test_voice_id_requires_versioned_slug():
    assert validate_voice_id("reader-v2") == "reader-v2"
    with pytest.raises(InvalidArguments, match="Invalid voice id"):
        validate_voice_id("Reader")


def test_public_approval_is_separate_from_import_authorization(lab_home):
    _write_voice_asset(lab_home)

    with pytest.raises(InvalidArguments, match="Public release confirmation"):
        approve_voice_asset(
            voice_id="reader-v1",
            display_name="Reader",
            summary="Warm narration voice",
            sample="preview.wav",
            usage_note="Public demo only",
            public_release_confirmed=False,
        )


def test_public_catalog_excludes_private_data_and_candidates(lab_home):
    _write_voice_asset(lab_home)
    candidate = _write_voice_asset(lab_home, "candidate-v1")
    candidate_manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    candidate_manifest["status"] = "candidate"
    (candidate / "manifest.json").write_text(json.dumps(candidate_manifest), encoding="utf-8")

    approve_voice_asset(
        voice_id="reader-v1",
        display_name="Moon Reader",
        summary="Warm narration voice",
        sample="preview.wav",
        usage_note="Public demo only",
        license_name="All rights reserved",
        public_release_confirmed=True,
    )
    output_dir = lab_home / "output" / "voice-catalog"
    index_path, catalog_path, count = generate_voice_catalog(output_dir=output_dir)

    assert count == 1
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["voices"][0]["id"] == "reader-v1"
    assert "candidate-v1" not in catalog_path.read_text(encoding="utf-8")
    assert "referenceText" not in catalog_path.read_text(encoding="utf-8")
    assert "referenceSha256" not in catalog_path.read_text(encoding="utf-8")
    assert (output_dir / "audio" / "reader-v1.wav").is_file()
    assert "Moon Reader" in index_path.read_text(encoding="utf-8")


def test_learn_voice_requires_explicit_authorization(lab_home):
    source = lab_home / "reference.wav"
    source.write_bytes(b"not used before authorization check")

    with pytest.raises(InvalidArguments, match="authorization"):
        import_voice_asset(
            source=source,
            transcript="你好。",
            voice_id="reader-v1",
            authorization_confirmed=False,
        )


def test_design_voice_persists_generated_reference(lab_home, monkeypatch):
    def fake_run_case(**kwargs):
        output_dir = kwargs["output_dir"]
        generated = output_dir / "synthetic-v1.reference.wav"
        with wave.open(str(generated), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(b"\0\0" * 240)
        return {"referenceAudio": str(generated)}

    monkeypatch.setattr("moon_media_lab.tts.video_case.run_case", fake_run_case)

    asset = design_voice_asset(
        voice_id="synthetic-v1",
        description="warm and calm",
        reference_text="你好。",
    )

    assert asset.reference.is_file()
    assert asset.manifest["sourceType"] == "voice-design"
    assert asset.manifest["status"] == "candidate"
