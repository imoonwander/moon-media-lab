from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from moon_media_lab.jobs import read_state
from moon_media_lab.paths import get_paths

# One worker: ASR is CPU/memory bound, serial execution keeps the machine
# usable. Jobs run as subprocesses so they can be cancelled safely —
# checkpoints make interruption recoverable via resume.
_task_queue: "queue.Queue[dict]" = queue.Queue()
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()
MAX_TASK_HISTORY = 30

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


def _public(task: dict) -> dict:
    return {
        k: v
        for k, v in task.items()
        if k in {"id", "kind", "label", "status", "submitted_at", "started_at", "error", "job_id"}
    }


def _prune_history() -> None:
    finished = [
        t for t in _tasks.values() if t["status"] in {"finished", "failed", "cancelled"}
    ]
    finished.sort(key=lambda t: t.get("submitted_at", ""))
    while len(finished) > MAX_TASK_HISTORY:
        stale = finished.pop(0)
        _tasks.pop(stale["id"], None)


def _worker() -> None:
    while True:
        task = _task_queue.get()
        try:
            with _tasks_lock:
                if task["status"] == "cancelled":
                    continue
                task["status"] = "running"
                task["started_at"] = time.strftime("%H:%M:%S")
            process = subprocess.Popen(
                task["argv"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            with _tasks_lock:
                task["process"] = process
            output, _ = process.communicate()
            with _tasks_lock:
                if task["status"] == "cancelled":
                    pass  # terminated by cancel endpoint
                elif process.returncode == 0:
                    task["status"] = "finished"
                else:
                    task["status"] = "failed"
                    tail = (output or "").strip().splitlines()[-3:]
                    task["error"] = " / ".join(tail)[-300:]
                _prune_history()
        except Exception as exc:  # noqa: BLE001
            with _tasks_lock:
                task["status"] = "failed"
                task["error"] = str(exc)
        finally:
            _task_queue.task_done()


def _submit(kind: str, label: str, argv: list[str], job_id: str | None = None) -> dict:
    task = {
        "id": uuid.uuid4().hex[:8],
        "kind": kind,
        "label": label,
        "status": "queued",
        "submitted_at": time.strftime("%H:%M:%S"),
        "argv": argv,
        "job_id": job_id,
    }
    with _tasks_lock:
        _tasks[task["id"]] = task
    _task_queue.put(task)
    return _public(task)


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


def _cli(*args: str) -> list[str]:
    return [sys.executable, "-m", "moon_media_lab.cli", *args]


def create_app():
    from fastapi import FastAPI, HTTPException, UploadFile
    from fastapi.responses import FileResponse, JSONResponse

    from moon_media_lab import __version__

    app = FastAPI(title="Moon Media Lab", version=__version__)
    paths = get_paths()
    paths.ensure()
    threading.Thread(target=_worker, daemon=True, name="moon-media-worker").start()

    def _safe_job_dir(job_id: str) -> Path:
        if "/" in job_id or ".." in job_id:
            raise HTTPException(400, "bad job id")
        job_dir = paths.jobs / job_id
        if not job_dir.is_dir():
            raise HTTPException(404, "job not found")
        return job_dir

    @app.get("/")
    def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/status")
    def status():
        with _tasks_lock:
            tasks = sorted(
                (_public(t) for t in _tasks.values()),
                key=lambda t: t["submitted_at"],
                reverse=True,
            )
        return {"version": __version__, "home": str(paths.home), "tasks": tasks}

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
        return _job_summary(_safe_job_dir(job_id))

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
        argv = _cli(
            "transcribe",
            source,
            "--language",
            payload.get("language", "auto"),
            "--mode",
            payload.get("mode", "transcript"),
            "--llm",
            payload.get("llm", "auto"),
        )
        if payload.get("diarization"):
            argv.append("--diarization")
        return _submit("转写", source.split("/")[-1][:60], argv)

    @app.post("/api/jobs/{job_id}/process")
    async def postprocess_job(job_id: str, payload: dict):
        job_dir = _safe_job_dir(job_id)
        mode = payload.get("mode")
        clean = bool(payload.get("clean"))
        naming = bool(payload.get("name_speakers"))
        force = bool(payload.get("force"))
        if not (mode or clean or naming):
            raise HTTPException(422, "nothing to do")
        if clean and force:
            for checkpoint in (job_dir / "postproc").glob("clean-*.json"):
                checkpoint.unlink()
            (job_dir / "transcript.clean.md").unlink(missing_ok=True)
        argv = _cli("process", str(job_dir), "--llm", payload.get("llm", "auto"))
        labels = []
        if mode:
            argv += ["--mode", mode]
            labels.append(mode)
        if clean:
            argv.append("--clean")
            labels.append("清理全文")
        if naming:
            argv.append("--name-speakers")
            labels.append("说话人命名")
        return _submit("后处理", f"{'+'.join(labels)} · {job_id[-6:]}", argv, job_id=job_id)

    @app.post("/api/jobs/{job_id}/resume")
    async def resume_job(job_id: str):
        job_dir = _safe_job_dir(job_id)
        return _submit("续跑", job_id[-6:], _cli("resume", str(job_dir)), job_id=job_id)

    @app.post("/api/queue/{task_id}/cancel")
    async def cancel_task(task_id: str):
        with _tasks_lock:
            task = _tasks.get(task_id)
            if task is None:
                raise HTTPException(404, "task not found")
            if task["status"] == "queued":
                task["status"] = "cancelled"
                return {"cancelled": True, "was": "queued"}
            if task["status"] == "running":
                task["status"] = "cancelled"
                process = task.get("process")
                if process and process.poll() is None:
                    process.terminate()
                return {"cancelled": True, "was": "running"}
        return {"cancelled": False, "reason": f"task already {task['status']}"}

    return app


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
