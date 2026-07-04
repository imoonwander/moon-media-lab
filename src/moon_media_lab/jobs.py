from __future__ import annotations

import json
import time
from pathlib import Path

from moon_media_lab.paths import get_paths


def new_job_dir(prefix: str = "job", base_dir: Path | None = None) -> Path:
    paths = get_paths()
    paths.ensure()
    jobs_root = base_dir if base_dir is not None else paths.jobs
    job_id = time.strftime(f"{prefix}-%Y%m%d-%H%M%S")
    job_dir = jobs_root / job_id
    suffix = 1
    while job_dir.exists():
        suffix += 1
        job_dir = jobs_root / f"{job_id}-{suffix}"
    job_dir.mkdir(parents=True)
    return job_dir


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(job_dir: Path, message: str) -> None:
    with (job_dir / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}\n")


def update_state(job_dir: Path, status: str, **fields) -> None:
    """Merge status/fields into state.json — the machine-readable job status
    any frontend (CLI, web, GUI) can poll. Job folders stay the API."""
    state_path = job_dir / "state.json"
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    state.update(fields)
    state["status"] = status
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_json(state_path, state)


def read_state(job_dir: Path) -> dict:
    state_path = job_dir / "state.json"
    if not state_path.exists():
        # Jobs created before state.json existed: infer from artifacts.
        if (job_dir / "transcript.raw.json").exists():
            return {"status": "done"}
        return {"status": "unknown"}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "unknown"}
