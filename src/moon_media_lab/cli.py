from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from moon_media_lab import __version__
from moon_media_lab.errors import MoonMediaError
from moon_media_lab.paths import get_paths
from moon_media_lab.pipelines.transcribe import run_transcription
from moon_media_lab.tts.registry import get_tts_engine

# Engine name -> importable package that proves the engine group is installed.
# Checked with find_spec so doctor never triggers heavy ML imports.
ENGINE_PACKAGES = {
    "sensevoice": "funasr",
    "faster-whisper": "faster_whisper",
    "mock": None,
}


def command_doctor(args: argparse.Namespace) -> int:
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
    }
    if args.engine:
        package = ENGINE_PACKAGES.get(args.engine)
        if args.engine not in ENGINE_PACKAGES:
            payload["engine"] = {"name": args.engine, "known": False}
        else:
            installed = package is None or importlib.util.find_spec(package) is not None
            payload["engine"] = {
                "name": args.engine,
                "installed": installed,
                "package": package,
            }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_transcribe(args: argparse.Namespace) -> int:
    job_dir = run_transcription(
        args.source,
        mode=args.mode,
        language=args.language,
        engine_name=args.engine,
        kind=args.kind,
        need_diarization=args.diarization,
        need_word_timestamps=args.word_timestamps,
        job_base_dir=Path(args.job_dir) if args.job_dir else None,
        model_dir=args.model_dir,
    )
    print(job_dir)
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Print project paths and check tooling")
    doctor.add_argument("--engine", help="Check install status of one engine (no heavy import)")
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
    transcribe.set_defaults(func=command_transcribe)

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
