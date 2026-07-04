import json

from moon_media_lab.jobs import write_json
from moon_media_lab.llm.providers.mock import MockLLMProvider
from moon_media_lab.postproc.runner import clean_transcript, load_result
from moon_media_lab.schema import TranscriptMeta, TranscriptResult, TranscriptSegment


def _write_job(job_dir, segments):
    job_dir.mkdir(parents=True)
    result = TranscriptResult(
        meta=TranscriptMeta(engine="mock", model="m", language="zh"),
        segments=segments,
    )
    write_json(job_dir / "transcript.raw.json", result.to_dict())
    return result


def test_clean_writes_checkpoints_and_output(lab_home):
    job = lab_home / "jobs" / "transcribe-x"
    result = _write_job(
        job, [TranscriptSegment(start=0.0, end=5.0, text="这是需要清理的口语文本。")]
    )
    output = clean_transcript(result, MockLLMProvider(), job)
    assert output.exists()
    assert (job / "postproc" / "clean-0000.json").exists()
    provenance = json.loads((job / "postproc" / "provenance.json").read_text("utf-8"))
    assert provenance["transcript.clean.md"]["cloud"] is False


def test_clean_restores_from_checkpoints(lab_home):
    job = lab_home / "jobs" / "transcribe-y"
    result = _write_job(job, [TranscriptSegment(start=0.0, end=5.0, text="文本")])
    (job / "postproc").mkdir()
    write_json(
        job / "postproc" / "clean-0000.json",
        {"start": 0.0, "end": 5.0, "text": "已清理的文本"},
    )

    class ExplodingProvider(MockLLMProvider):
        def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("checkpointed batch must not re-run")

    output = clean_transcript(result, ExplodingProvider(), job)
    assert "已清理的文本" in output.read_text(encoding="utf-8")


def test_load_result_roundtrip(lab_home):
    job = lab_home / "jobs" / "transcribe-z"
    _write_job(
        job,
        [TranscriptSegment(start=1.0, end=2.0, text="你好", speaker="SPEAKER_00")],
    )
    result = load_result(job)
    assert result.segments[0].speaker == "SPEAKER_00"
    assert result.meta.engine == "mock"
