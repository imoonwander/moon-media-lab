from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LabPaths:
    home: Path
    models: Path
    cache: Path
    jobs: Path
    downloads: Path
    output: Path

    def ensure(self) -> None:
        for path in (self.models, self.cache, self.jobs, self.downloads, self.output):
            path.mkdir(parents=True, exist_ok=True)


def get_paths() -> LabPaths:
    root = project_root()
    home = Path(os.environ.get("MOON_MEDIA_LAB_HOME", root)).expanduser().resolve()
    return LabPaths(
        home=home,
        models=Path(os.environ.get("MOON_MEDIA_LAB_MODELS_DIR", home / "models")).resolve(),
        cache=Path(os.environ.get("MOON_MEDIA_LAB_CACHE_DIR", home / "cache")).resolve(),
        jobs=Path(os.environ.get("MOON_MEDIA_LAB_JOBS_DIR", home / "jobs")).resolve(),
        downloads=Path(
            os.environ.get("MOON_MEDIA_LAB_DOWNLOADS_DIR", home / "downloads")
        ).resolve(),
        output=Path(os.environ.get("MOON_MEDIA_LAB_OUTPUT_DIR", home / "output")).resolve(),
    )
