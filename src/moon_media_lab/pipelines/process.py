from __future__ import annotations

from pathlib import Path

from moon_media_lab.errors import InvalidArguments
from moon_media_lab.jobs import append_log, update_state
from moon_media_lab.knowledge import build_knowledge_bundle, export_wiki_bundle
from moon_media_lab.postproc.runner import (
    MODE_FILES,
    clean_transcript,
    generate_mode_doc,
    load_result,
    name_speakers,
)


PRESETS: dict[str, tuple[str, ...]] = {
    "transcript": (),
    "knowledge": ("clean", "knowledge", "structured-knowledge"),
    "interview": ("clean", "name-speakers", "speaker-notes", "structured-knowledge"),
    "english": ("english-transcript", "english-study", "structured-knowledge"),
    "research": ("clean", "knowledge", "structured-knowledge", "recommendations"),
    "wiki": (
        "clean",
        "knowledge",
        "structured-knowledge",
        "recommendations",
        "package",
        "wiki",
    ),
}

ADD_ACTIONS = tuple(
    sorted(
        {
            "clean",
            "name-speakers",
            "package",
            "wiki",
            *MODE_FILES.keys(),
        }
    )
)


def is_job_dir(target: str | Path) -> bool:
    path = Path(target).expanduser()
    return path.is_dir() and (path / "transcript.raw.json").is_file()


def actions_for(preset: str | None, additions: list[str] | None = None) -> list[str]:
    if preset is not None and preset not in PRESETS:
        raise InvalidArguments(
            f"Unknown process preset: {preset}",
            hint=f"Available presets: {', '.join(PRESETS)}",
        )
    ordered = list(PRESETS.get(preset or "transcript", ()))
    for action in additions or []:
        if action not in ADD_ACTIONS:
            raise InvalidArguments(f"Unknown process addition: {action}")
        if action not in ordered:
            ordered.append(action)
    return ordered


def process_job(
    job_dir: Path,
    *,
    actions: list[str],
    llm: str = "auto",
    force: bool = False,
) -> list[Path]:
    """Derive requested artifacts from an existing transcript job."""
    job_dir = job_dir.expanduser().resolve()
    result = load_result(job_dir)
    outputs: list[Path] = []
    provider = None

    def get_provider():
        nonlocal provider
        if provider is None:
            from moon_media_lab.llm.registry import get_llm_provider

            provider = get_llm_provider(llm)
        return provider

    update_state(job_dir, "postprocessing", percent=None, eta_sec=None)
    try:
        for action in actions:
            if action == "clean":
                output = job_dir / "transcript.clean.md"
                if force or not output.is_file():
                    output = clean_transcript(result, get_provider(), job_dir)
                outputs.append(output)
            elif action == "name-speakers":
                output = job_dir / "postproc" / "speakers.json"
                if force or not output.is_file():
                    output = name_speakers(result, get_provider(), job_dir)
                    result = load_result(job_dir)
                outputs.append(output)
            elif action in MODE_FILES:
                output = job_dir / MODE_FILES[action]
                if force or not output.is_file():
                    output = generate_mode_doc(result, action, get_provider(), job_dir)
                outputs.append(output)
            elif action == "package":
                outputs.append(build_knowledge_bundle(job_dir))
            elif action == "wiki":
                outputs.append(export_wiki_bundle(job_dir, job_dir / "exports" / "wiki"))
        append_log(job_dir, f"process actions done: {actions}")
        update_state(job_dir, "done", percent=100)
        return outputs
    except Exception as exc:
        update_state(job_dir, "postprocess_failed", error=str(exc))
        raise
