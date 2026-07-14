import json

from moon_media_lab.cli import main
from moon_media_lab.pipelines.process import actions_for


def test_mock_transcribe_end_to_end(lab_home, capsys):
    source = lab_home / "input.txt"
    source.write_text("第一行。\n第二行内容更长一些。\n", encoding="utf-8")

    exit_code = main(["transcribe", str(source), "--engine", "mock", "--language", "zh"])
    assert exit_code == 0

    job_dir = lab_home / "jobs"
    jobs = list(job_dir.glob("transcribe-*"))
    assert len(jobs) == 1
    job = jobs[0]

    raw = json.loads((job / "transcript.raw.json").read_text(encoding="utf-8"))
    assert raw["meta"]["engine"] == "mock"
    assert len(raw["segments"]) == 2
    starts = [segment["start"] for segment in raw["segments"]]
    assert starts == sorted(starts)
    assert (job / "transcript.md").exists()
    assert (job / "input.json").exists()
    assert (job / "run.log").exists()


def test_unknown_engine_exit_code(lab_home):
    assert main(["transcribe", "x.wav", "--engine", "nosuch"]) == 2


def test_doctor_json_reports_paths(lab_home, capsys):
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["home"] == str(lab_home)
    assert "ffmpeg" in payload
    assert "engines" in payload
    assert "llm_clis" in payload


def test_doctor_human_readable(lab_home, capsys):
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "moon-media-lab" in out
    assert "Capabilities" in out


def test_version_flag(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "moon-media-lab" in capsys.readouterr().out


def test_process_source_with_transcript_preset(lab_home):
    source = lab_home / "source.txt"
    source.write_text("第一段。\n第二段。\n", encoding="utf-8")

    assert (
        main(
            [
                "process",
                str(source),
                "--preset",
                "transcript",
                "--engine",
                "mock",
                "--kind",
                "text",
                "--language",
                "zh",
            ]
        )
        == 0
    )
    jobs = list((lab_home / "jobs").glob("transcribe-*"))
    assert len(jobs) == 1
    assert (jobs[0] / "transcript.raw.json").is_file()
    assert not (jobs[0] / "knowledge.md").exists()


def test_process_existing_job_adds_output_without_retranscribing(lab_home):
    source = lab_home / "source.txt"
    source.write_text("知识应该连接行动。\n", encoding="utf-8")
    assert main(["transcribe", str(source), "--engine", "mock", "--kind", "text"]) == 0
    job = next((lab_home / "jobs").glob("transcribe-*"))
    original = (job / "transcript.raw.json").read_bytes()

    assert main(["process", str(job), "--add", "recommendations", "--llm", "mock"]) == 0
    assert (job / "recommendations.md").is_file()
    assert (job / "transcript.raw.json").read_bytes() == original


def test_download_rejects_local_path(lab_home):
    assert main(["download", str(lab_home / "video.mp4")]) == 2


def test_process_preset_actions_are_ordered_and_deduplicated():
    assert actions_for("wiki", ["knowledge", "speaker-notes"])[-2:] == [
        "wiki",
        "speaker-notes",
    ]
