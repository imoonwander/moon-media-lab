from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from moon_media_lab import __version__
from moon_media_lab.errors import InvalidArguments, MoonMediaError
from moon_media_lab.paths import get_paths
from moon_media_lab.pipelines.transcribe import (
    DEFAULT_CHUNK_SEC,
    resume_transcription,
    run_transcription,
)
from moon_media_lab.tts.registry import get_tts_engine

# Engine name -> importable package that proves the engine group is installed.
# Checked with find_spec so doctor never triggers heavy ML imports.
ENGINE_PACKAGES = {
    "sensevoice": "funasr",
    "paraformer": "funasr",
    "faster-whisper": "faster_whisper",
    "mock": None,
}


# Optional capabilities checked by doctor: label -> (import spec, extra, why).
_OPTIONAL_DEPS = [
    ("Chinese ASR (SenseVoice/Paraformer)", "funasr", "asr-sensevoice", "转写中文音视频"),
    ("English ASR (faster-whisper)", "faster_whisper", "asr-whisper", "转写英文音视频"),
    ("URL ingestion (yt-dlp)", "yt_dlp", "url", "直接转 YouTube/Bilibili/抖音 链接"),
    ("Text-to-speech (edge-tts)", "edge_tts", "tts-edge", "文字转语音"),
    (
        "Voice design/clone (Qwen3-TTS MLX)",
        "mlx_audio",
        "tts-qwen3-mlx",
        "Apple Silicon 本地音色设计与克隆",
    ),
    ("Web UI (fastapi)", "fastapi", "web", "浏览器界面 moon-media serve"),
]
_LLM_CLIS = [("claude", "claude-cli"), ("codex", "codex-cli"), ("gemini", "gemini-cli")]


def _doctor_payload(engine: str | None) -> dict:
    import shutil

    from moon_media_lab.media.resolver import find_tool

    paths = get_paths()
    paths.ensure()
    payload = {
        "version": __version__,
        "home": str(paths.home),
        "models": str(paths.models),
        "cache": str(paths.cache),
        "jobs": str(paths.jobs),
        "downloads": str(paths.downloads),
        "output": str(paths.output),
        "ffmpeg": find_tool("ffmpeg"),
        "ffprobe": find_tool("ffprobe"),
        "engines": {
            label: importlib.util.find_spec(spec) is not None
            for label, spec, _extra, _why in _OPTIONAL_DEPS
        },
        "llm_clis": {name: shutil.which(name) is not None for name, _p in _LLM_CLIS},
    }
    try:
        from moon_media_lab import models_cli

        payload["models"] = str(paths.models)
        payload["downloaded_models"] = models_cli.list_models()
    except Exception:  # noqa: BLE001 - model listing is best-effort
        payload["downloaded_models"] = []
    if engine:
        package = ENGINE_PACKAGES.get(engine)
        if engine not in ENGINE_PACKAGES:
            payload["engine"] = {"name": engine, "known": False}
        else:
            installed = package is None or importlib.util.find_spec(package) is not None
            payload["engine"] = {"name": engine, "installed": installed, "package": package}
    return payload


def command_doctor(args: argparse.Namespace) -> int:
    payload = _doctor_payload(args.engine)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    ok, warn, bad = "\033[32m✓\033[0m", "\033[33m○\033[0m", "\033[31m✗\033[0m"
    print(f"\n  moon-media-lab {payload['version']}")
    print(f"  home: {payload['home']}\n")

    ffmpeg_ok = bool(payload["ffmpeg"])
    ffmpeg_line = payload["ffmpeg"] or "NOT FOUND — brew install ffmpeg (必需)"
    print("  System")
    print(f"    {ok if ffmpeg_ok else bad} ffmpeg   {ffmpeg_line}")

    print("\n  Capabilities")
    for label, _spec, extra, why in _OPTIONAL_DEPS:
        installed = payload["engines"][label]
        mark = ok if installed else warn
        tail = f"{why}" if installed else f"缺失 · pip install 'moon-media-lab[{extra}]' — {why}"
        print(f"    {mark} {label}")
        if not installed:
            print(f"        └ {tail}")

    print("\n  LLM CLI (用于知识笔记/清理，任选其一)")
    any_llm = False
    for name, _p in _LLM_CLIS:
        present = payload["llm_clis"][name]
        any_llm = any_llm or present
        print(f"    {ok if present else warn} {name}")

    models = payload.get("downloaded_models", [])
    print(f"\n  Downloaded models ({len(models)})")
    if models:
        for name, size in models:
            print(f"    {ok} {size:>8}  {name}")
    else:
        print("    ○ 暂无 · moon-media models download sensevoice")

    # Verdict: can the user actually transcribe right now?
    print("\n  ─────────────────────────────────────")
    if not ffmpeg_ok:
        print("  ✗ 还不能用：先安装 ffmpeg（brew install ffmpeg）")
    elif not (payload["engines"]["Chinese ASR (SenseVoice/Paraformer)"]
              or payload["engines"]["English ASR (faster-whisper)"]):
        print("  ○ 差一步：装一个 ASR 引擎，例如")
        print("      pip install 'moon-media-lab[asr-sensevoice]'")
        print("      moon-media models download sensevoice")
    else:
        print("  ✓ 已就绪，可以开始：")
        print("      moon-media transcribe your-file.m4a --language zh")
        if not any_llm:
            print("    （知识笔记需要 claude/codex/gemini 任一 CLI）")
    print()
    return 0


def command_transcribe(args: argparse.Namespace) -> int:
    transcribe_kwargs = dict(
        mode=args.mode,
        language=args.language,
        engine_name=args.engine,
        kind=args.kind,
        need_diarization=args.diarization,
        need_word_timestamps=args.word_timestamps,
        job_base_dir=Path(args.job_dir) if args.job_dir else None,
        model_dir=args.model_dir,
        chunk_sec=args.chunk_sec,
        llm=args.llm,
    )
    if args.playlist:
        from moon_media_lab.pipelines.playlist import run_playlist

        job_dirs = run_playlist(args.source, items=args.playlist_items, **transcribe_kwargs)
        for job_dir in job_dirs:
            print(job_dir)
        return 0 if job_dirs else 1
    job_dir = run_transcription(args.source, **transcribe_kwargs)
    print(job_dir)
    return 0


def command_resume(args: argparse.Namespace) -> int:
    job_dir = resume_transcription(Path(args.job_dir), model_dir=args.model_dir, llm=args.llm)
    print(job_dir)
    return 0


def command_process(args: argparse.Namespace) -> int:
    from moon_media_lab.llm.registry import get_llm_provider
    from moon_media_lab.postproc.runner import (
        clean_transcript,
        generate_mode_doc,
        load_result,
        name_speakers,
    )

    from moon_media_lab.jobs import update_state

    job_dir = Path(args.job_dir)
    result = load_result(job_dir)
    provider = get_llm_provider(args.llm)
    if not (args.name_speakers or args.clean or args.mode):
        raise InvalidArguments(
            "Nothing to do.",
            hint="Pass --mode knowledge|english-study|skill, --clean, and/or --name-speakers.",
        )
    import time as _time

    update_state(
        job_dir,
        "postprocessing",
        percent=None,
        eta_sec=None,
        stage_started_at=int(_time.time()),
    )
    outputs = []
    try:
        if args.name_speakers:
            outputs.append(name_speakers(result, provider, job_dir))
        if args.clean:
            outputs.append(clean_transcript(result, provider, job_dir))
        if args.mode:
            outputs.append(generate_mode_doc(result, args.mode, provider, job_dir))
    except Exception as exc:
        update_state(job_dir, "postprocess_failed", error=str(exc))
        raise
    update_state(job_dir, "done")
    for output in outputs:
        print(output)
    return 0


def command_models(args: argparse.Namespace) -> int:
    from moon_media_lab import models_cli

    if args.models_command == "list":
        rows = models_cli.list_models()
        if not rows:
            print("no models downloaded yet")
        for name, size in rows:
            print(f"{size:>8}  {name}")
        return 0
    if args.models_command == "download":
        if args.name == "sensevoice":
            path = models_cli.download_sensevoice()
        elif args.name == "paraformer":
            path = models_cli.download_paraformer()
        else:
            path = models_cli.download_whisper_model(args.name, mirror=args.mirror)
        print(path)
        return 0
    if args.models_command == "prune":
        removed = models_cli.prune_models()
        for entry in removed:
            print(f"removed {entry}")
        print(f"{len(removed)} stale download file(s) removed")
        return 0
    raise InvalidArguments("Unknown models subcommand")


def command_serve(args: argparse.Namespace) -> int:
    if importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None:
        raise MoonMediaError(
            "web dependencies are not installed.",
            hint="Install them: pip install 'moon-media-lab[web]'",
        )
    from moon_media_lab.web.server import serve

    print(f"Moon Media Lab web UI: http://{args.host}:{args.port}")
    serve(host=args.host, port=args.port)
    return 0


def command_tts(args: argparse.Namespace) -> int:
    paths = get_paths()
    paths.ensure()
    text = args.text
    source = Path(args.text)
    if source.exists() and source.is_file():
        text = source.read_text(encoding="utf-8")
    output_path = Path(args.output) if args.output else paths.output / "mock-tts.txt"
    engine = get_tts_engine(args.engine)
    result_path = engine.synthesize(text, output_path, voice=args.voice)
    print(result_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moon-media", description="Moon Media Lab CLI")
    parser.add_argument("--version", action="version", version=f"moon-media-lab {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Health check: tooling, engines, models")
    doctor.add_argument("--engine", help="Check install status of one engine (no heavy import)")
    doctor.add_argument("--json", action="store_true", help="Machine-readable output")
    doctor.set_defaults(func=command_doctor)

    transcribe = subparsers.add_parser("transcribe", help="Create a transcript job")
    transcribe.add_argument("source", help="Local file path, URL, or text for the mock engine")
    transcribe.add_argument("--kind", choices=["file", "url", "text"], default="file")
    transcribe.add_argument("--language", choices=["auto", "zh", "en", "mixed"], default="auto")
    transcribe.add_argument("--engine", default="auto")
    transcribe.add_argument(
        "--mode",
        choices=["transcript", "knowledge", "english-study", "skill"],
        default="transcript",
    )
    transcribe.add_argument("--diarization", action="store_true")
    transcribe.add_argument("--word-timestamps", action="store_true")
    transcribe.add_argument("--job-dir", help="Override the jobs root directory")
    transcribe.add_argument("--model-dir", help="Override the engine model path")
    transcribe.add_argument(
        "--chunk-sec",
        type=int,
        default=DEFAULT_CHUNK_SEC,
        help="Chunk length in seconds for long media (default: %(default)s)",
    )
    transcribe.add_argument("--llm", default="auto", help="LLM provider for post-processing")
    transcribe.add_argument(
        "--playlist", action="store_true", help="Transcribe every entry of a playlist URL"
    )
    transcribe.add_argument(
        "--playlist-items", help="Entry selection like 1-5 or 1,3,7 (yt-dlp syntax)"
    )
    transcribe.set_defaults(func=command_transcribe)

    resume = subparsers.add_parser("resume", help="Continue an interrupted transcribe job")
    resume.add_argument("job_dir", help="Path to the jobs/transcribe-... folder")
    resume.add_argument("--model-dir", help="Override the engine model path")
    resume.add_argument("--llm", default="auto", help="LLM provider for post-processing")
    resume.set_defaults(func=command_resume)

    process = subparsers.add_parser(
        "process", help="Run LLM post-processing on a finished transcribe job"
    )
    process.add_argument("job_dir", help="Path to the jobs/transcribe-... folder")
    process.add_argument(
        "--mode",
        choices=["knowledge", "english-study", "skill"],
        help="Generate this document from the transcript",
    )
    process.add_argument(
        "--clean", action="store_true", help="Produce transcript.clean.md (batched cleanup)"
    )
    process.add_argument(
        "--name-speakers",
        action="store_true",
        help="Infer names/roles for SPEAKER_NN labels and re-render transcript/subtitles",
    )
    process.add_argument("--llm", default="auto", help="LLM provider (claude-cli|mock)")
    process.set_defaults(func=command_process)

    serve_cmd = subparsers.add_parser("serve", help="Start the local web UI")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.set_defaults(func=command_serve)

    models = subparsers.add_parser("models", help="Manage local ASR models")
    models_sub = models.add_subparsers(dest="models_command", required=True)
    models_sub.add_parser("list", help="List downloaded models and sizes")
    models_download = models_sub.add_parser("download", help="Download a model")
    models_download.add_argument(
        "name", help="Model name: sensevoice, tiny.en, small, large-v3-turbo, ..."
    )
    models_download.add_argument(
        "--mirror", action="store_true", help="Use hf-mirror.com instead of huggingface.co"
    )
    models_sub.add_parser("prune", help="Remove interrupted download leftovers")
    models.set_defaults(func=command_models)

    tts = subparsers.add_parser("tts", help="Create speech from text using a TTS engine")
    tts.add_argument("text", help="Text or local text file path")
    tts.add_argument("--engine", default="auto")
    tts.add_argument("--voice")
    tts.add_argument("--output")
    tts.set_defaults(func=command_tts)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MoonMediaError as error:
        print(f"error: {error}", file=sys.stderr)
        if error.hint:
            print(f"hint: {error.hint}", file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
