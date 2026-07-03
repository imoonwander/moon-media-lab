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
