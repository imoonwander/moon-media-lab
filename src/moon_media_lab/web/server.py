from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from pathlib import Path

from moon_media_lab.jobs import read_state
from moon_media_lab.paths import get_paths

# One worker: ASR is CPU/memory bound, serial execution keeps the machine usable.
_task_queue: "queue.Queue[dict]" = queue.Queue()
_pending: list[dict] = []
_pending_lock = threading.Lock()

ARTIFACT_WHITELIST = {
    "transcript.md",
    "transcript.clean.md",
    "transcript.raw.json",
    "transcript.partial.md",
    "knowledge.md",
    "english-study.md",
    "skill-draft.md",
    "segments.srt",
    "segments.vtt",
    "run.log",
    "input.json",
    "media.json",
    "state.json",
    "audio.wav",
}


def _worker() -> None:
    while True:
        task = _task_queue.get()
        with _pending_lock:
            task["status"] = "running"
        try:
            task["fn"]()
            task["status"] = "finished"
        except Exception as exc:  # noqa: BLE001 - job state carries the error
            task["status"] = "failed"
            task["error"] = str(exc)
        finally:
            with _pending_lock:
                if task in _pending:
                    _pending.remove(task)
            _task_queue.task_done()


def _submit(kind: str, label: str, fn) -> dict:
    task = {
        "id": uuid.uuid4().hex[:8],
        "kind": kind,
        "label": label,
        "status": "queued",
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fn": fn,
    }
    with _pending_lock:
        _pending.append(task)
    _task_queue.put(task)
    return {k: v for k, v in task.items() if k != "fn"}


def _job_summary(job_dir: Path) -> dict:
    state = read_state(job_dir)
    summary = {
        "id": job_dir.name,
        "status": state.get("status", "unknown"),
        "state": state,
        "artifacts": sorted(
            f.name for f in job_dir.iterdir() if f.is_file() and f.name in ARTIFACT_WHITELIST
        ),
    }
    input_json = job_dir / "input.json"
    if input_json.exists():
        try:
            summary["input"] = json.loads(input_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return summary


def create_app():
    from fastapi import FastAPI, HTTPException, UploadFile
    from fastapi.responses import FileResponse, JSONResponse

    from moon_media_lab import __version__

    app = FastAPI(title="Moon Media Lab", version=__version__)
    paths = get_paths()
    paths.ensure()
    threading.Thread(target=_worker, daemon=True, name="moon-media-worker").start()

    @app.get("/")
    def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/status")
    def status():
        with _pending_lock:
            pending = [{k: v for k, v in t.items() if k != "fn"} for t in _pending]
        return {"version": __version__, "home": str(paths.home), "queue": pending}

    @app.get("/api/jobs")
    def list_jobs():
        jobs = [
            _job_summary(job_dir)
            for job_dir in sorted(paths.jobs.iterdir(), reverse=True)
            if job_dir.is_dir()
        ]
        return {"jobs": jobs}

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        job_dir = _safe_job_dir(job_id)
        return _job_summary(job_dir)

    @app.get("/api/jobs/{job_id}/segments")
    def job_segments(job_id: str):
        job_dir = _safe_job_dir(job_id)
        raw = job_dir / "transcript.raw.json"
        if not raw.exists():
            raise HTTPException(404, "transcript not ready")
        data = json.loads(raw.read_text(encoding="utf-8"))
        names_path = job_dir / "postproc" / "speakers.json"
        if names_path.exists():
            names = json.loads(names_path.read_text(encoding="utf-8"))
            for segment in data.get("segments", []):
                if segment.get("speaker") in names:
                    segment["speaker"] = names[segment["speaker"]]
        return JSONResponse(data)

    @app.get("/api/jobs/{job_id}/file/{name}")
    def job_file(job_id: str, name: str):
        job_dir = _safe_job_dir(job_id)
        if name not in ARTIFACT_WHITELIST:
            raise HTTPException(403, "artifact not allowed")
        target = job_dir / name
        if not target.exists():
            raise HTTPException(404, "not found")
        return FileResponse(target)

    @app.post("/api/upload")
    async def upload(file: UploadFile):
        uploads = paths.downloads / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "upload.bin").name
        target = uploads / f"{int(time.time())}-{safe_name}"
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                handle.write(chunk)
        return {"path": str(target)}

    @app.post("/api/jobs")
    async def submit_job(payload: dict):
        source = (payload.get("source") or "").strip()
        if not source:
            raise HTTPException(422, "source is required")
        options = dict(
            mode=payload.get("mode", "transcript"),
            language=payload.get("language", "auto"),
            engine_name=payload.get("engine", "auto"),
            need_diarization=bool(payload.get("diarization")),
            llm=payload.get("llm", "auto"),
        )

        def run():
            from moon_media_lab.pipelines.transcribe import run_transcription

            run_transcription(source, **options)

        return _submit("transcribe", source, run)

    @app.post("/api/jobs/{job_id}/process")
    async def postprocess_job(job_id: str, payload: dict):
        job_dir = _safe_job_dir(job_id)
        mode = payload.get("mode")
        clean = bool(payload.get("clean"))
        name_speakers = bool(payload.get("name_speakers"))
        llm = payload.get("llm", "auto")
        if not (mode or clean or name_speakers):
            raise HTTPException(422, "nothing to do")

        def run():
            from moon_media_lab.jobs import update_state
            from moon_media_lab.llm.registry import get_llm_provider
            from moon_media_lab.postproc.runner import (
                clean_transcript,
                generate_mode_doc,
                load_result,
                name_speakers as run_naming,
            )

            result = load_result(job_dir)
            provider = get_llm_provider(llm)
            update_state(job_dir, "postprocessing")
            try:
                if name_speakers:
                    run_naming(result, provider, job_dir)
                if clean:
                    clean_transcript(result, provider, job_dir)
                if mode:
                    generate_mode_doc(result, mode, provider, job_dir)
                update_state(job_dir, "done")
            except Exception as exc:
                update_state(job_dir, "postprocess_failed", error=str(exc))
                raise

        return _submit("process", job_id, run)

    @app.post("/api/jobs/{job_id}/resume")
    async def resume_job(job_id: str):
        job_dir = _safe_job_dir(job_id)

        def run():
            from moon_media_lab.pipelines.transcribe import resume_transcription

            resume_transcription(job_dir)

        return _submit("resume", job_id, run)

    def _safe_job_dir(job_id: str) -> Path:
        if "/" in job_id or ".." in job_id:
            raise HTTPException(400, "bad job id")
        job_dir = paths.jobs / job_id
        if not job_dir.is_dir():
            raise HTTPException(404, "job not found")
        return job_dir

    return app


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
