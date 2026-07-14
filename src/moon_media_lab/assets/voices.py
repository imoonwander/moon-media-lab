from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from moon_media_lab.errors import InvalidArguments, MediaProbeFailed
from moon_media_lab.media.resolver import find_tool
from moon_media_lab.paths import get_paths

VOICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*-v[1-9][0-9]*$")
DEFAULT_CLONE_MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-6bit"
DEFAULT_DESIGN_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-6bit"


@dataclass(frozen=True)
class VoiceAsset:
    voice_id: str
    directory: Path
    manifest: dict[str, Any]
    profile: Path
    reference: Path


def voice_assets_root() -> Path:
    return get_paths().home / "assets" / "voices"


def validate_voice_id(voice_id: str) -> str:
    if not VOICE_ID_PATTERN.fullmatch(voice_id):
        raise InvalidArguments(
            f"Invalid voice id: {voice_id}",
            hint="Use a versioned lowercase id such as moon-reader-v1.",
        )
    return voice_id


def list_voice_assets(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or voice_assets_root()
    if not base.exists():
        return []
    assets = []
    for manifest_path in sorted(base.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        assets.append(manifest)
    return assets


def load_voice_asset(voice_id: str, root: Path | None = None) -> VoiceAsset:
    validate_voice_id(voice_id)
    directory = (root or voice_assets_root()) / voice_id
    manifest_path = directory / "manifest.json"
    profile_path = directory / "profile.json"
    reference_path = directory / "reference.wav"
    missing = [
        path.name
        for path in (manifest_path, profile_path, reference_path)
        if not path.is_file()
    ]
    if missing:
        raise InvalidArguments(
            f"Voice asset '{voice_id}' is incomplete: missing {', '.join(missing)}",
            hint=f"Inspect {directory} or import it again with 'moon-media learn voice'.",
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return VoiceAsset(voice_id, directory, manifest, profile_path, reference_path)


def approve_voice_asset(
    *,
    voice_id: str,
    display_name: str,
    summary: str,
    sample: str,
    usage_note: str,
    public_release_confirmed: bool,
    license_name: str = "All rights reserved",
    attribution: str = "",
    root: Path | None = None,
) -> VoiceAsset:
    """Approve a curated voice sample for public catalog display.

    Import authorization only covers learning the voice locally. Public release is
    deliberately confirmed separately so a collected reference cannot become public
    by accident.
    """
    if not public_release_confirmed:
        raise InvalidArguments(
            "Public release confirmation is required.",
            hint="Verify public display and reuse rights, then pass "
            "--public-release-confirmed.",
        )
    asset = load_voice_asset(voice_id, root=root)
    display_name = display_name.strip()
    summary = summary.strip()
    usage_note = usage_note.strip()
    license_name = license_name.strip()
    if not all((display_name, summary, usage_note, license_name)):
        raise InvalidArguments(
            "Public name, summary, usage note, and license cannot be empty."
        )

    sample_path = Path(sample)
    if sample_path.is_absolute():
        try:
            sample_path = sample_path.relative_to(asset.directory)
        except ValueError as exc:
            raise InvalidArguments("Public sample must be inside the voice asset directory.") from exc
    elif sample_path.parts[:1] != ("samples",):
        sample_path = Path("samples") / sample_path
    resolved_sample = (asset.directory / sample_path).resolve()
    samples_root = (asset.directory / "samples").resolve()
    if samples_root not in resolved_sample.parents or not resolved_sample.is_file():
        raise InvalidArguments(
            f"Public sample not found inside samples/: {sample}",
            hint="Generate and curate a WAV under the asset's samples/ directory first.",
        )
    if resolved_sample.suffix.lower() != ".wav":
        raise InvalidArguments("Public preview sample must be a WAV file.")

    manifest = dict(asset.manifest)
    manifest.update(
        {
            "status": "approved",
            "visibility": "public",
            "approvedAt": date.today().isoformat(),
            "publicRelease": "confirmed-by-operator",
            "public": {
                "displayName": display_name,
                "summary": summary,
                "language": "zh-CN",
                "sample": sample_path.as_posix(),
                "usageNote": usage_note,
                "license": license_name,
                "attribution": attribution.strip(),
            },
        }
    )
    (asset.directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return VoiceAsset(asset.voice_id, asset.directory, manifest, asset.profile, asset.reference)


def generate_voice_catalog(
    *, output_dir: Path, root: Path | None = None
) -> tuple[Path, Path, int]:
    """Build a de-identified static catalog from explicitly public voice assets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    public_assets: list[dict[str, Any]] = []

    for manifest in list_voice_assets(root=root):
        if manifest.get("status") != "approved" or manifest.get("visibility") != "public":
            continue
        public = manifest.get("public")
        if not isinstance(public, dict):
            continue
        voice_id = str(manifest.get("id", ""))
        try:
            asset = load_voice_asset(voice_id, root=root)
        except InvalidArguments:
            continue
        sample_relative = Path(str(public.get("sample", "")))
        sample_path = (asset.directory / sample_relative).resolve()
        samples_root = (asset.directory / "samples").resolve()
        if samples_root not in sample_path.parents or not sample_path.is_file():
            continue
        public_audio_name = f"{voice_id}{sample_path.suffix.lower()}"
        shutil.copy2(sample_path, audio_dir / public_audio_name)
        public_assets.append(
            {
                "id": voice_id,
                "version": manifest.get("version"),
                "sourceType": manifest.get("sourceType"),
                "displayName": public.get("displayName", voice_id),
                "summary": public.get("summary", ""),
                "language": public.get("language", ""),
                "usageNote": public.get("usageNote", ""),
                "license": public.get("license", ""),
                "attribution": public.get("attribution", ""),
                "audio": f"audio/{public_audio_name}",
            }
        )

    catalog_path = output_dir / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {"generatedAt": date.today().isoformat(), "voices": public_assets},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    index_path = output_dir / "index.html"
    index_path.write_text(_render_voice_catalog(public_assets), encoding="utf-8")
    return index_path, catalog_path, len(public_assets)


def _render_voice_catalog(voices: list[dict[str, Any]]) -> str:
    cards = []
    for voice in voices:
        source_label = (
            "合成设计音色" if voice["sourceType"] == "voice-design" else "授权克隆音色"
        )
        attribution = voice.get("attribution")
        attribution_html = (
            f'<p class="meta"><span>署名</span>{html.escape(str(attribution))}</p>'
            if attribution
            else ""
        )
        cards.append(
            f"""
            <article class="voice-card">
              <div class="card-top">
                <div>
                  <p class="eyebrow">{html.escape(source_label)} · {html.escape(str(voice['language']))}</p>
                  <h2>{html.escape(str(voice['displayName']))}</h2>
                </div>
                <span class="version">{html.escape(str(voice['id']))}</span>
              </div>
              <p class="summary">{html.escape(str(voice['summary']))}</p>
              <audio controls preload="metadata" src="{html.escape(str(voice['audio']))}"></audio>
              <div class="details">
                <p class="meta"><span>使用说明</span>{html.escape(str(voice['usageNote']))}</p>
                <p class="meta"><span>授权标记</span>{html.escape(str(voice['license']))}</p>
                {attribution_html}
              </div>
            </article>
            """
        )
    cards_html = "\n".join(cards) or (
        '<div class="empty">还没有通过公开审核的音色。先完成试听样本和公开权利确认。</div>'
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Moon Voice Library</title>
  <style>
    :root {{ color-scheme: dark; --bg:#080b0f; --panel:#11161d; --line:#27313d;
      --text:#f2f5f7; --muted:#97a3af; --accent:#b8ff5a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; background:radial-gradient(circle at 80% 0,#18221c 0,transparent 34%),var(--bg); color:var(--text); font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ width:min(980px,calc(100% - 32px)); margin:0 auto; padding:72px 0 80px; }}
    header {{ margin-bottom:40px; }}
    .brand {{ color:var(--accent); font:700 12px/1.2 ui-monospace,SFMono-Regular,monospace; letter-spacing:.18em; text-transform:uppercase; }}
    h1 {{ max-width:700px; margin:16px 0 14px; font-size:clamp(38px,7vw,72px); line-height:.96; letter-spacing:-.055em; }}
    .intro {{ max-width:620px; color:var(--muted); font-size:17px; line-height:1.7; }}
    .catalog {{ display:grid; gap:18px; }}
    .voice-card {{ padding:26px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(145deg,rgba(20,27,34,.96),rgba(12,16,21,.96)); box-shadow:0 18px 50px rgba(0,0,0,.2); }}
    .card-top {{ display:flex; justify-content:space-between; align-items:flex-start; gap:20px; }}
    .eyebrow,.version {{ margin:0; color:var(--accent); font:600 11px/1.4 ui-monospace,SFMono-Regular,monospace; letter-spacing:.08em; text-transform:uppercase; }}
    h2 {{ margin:8px 0 0; font-size:27px; letter-spacing:-.025em; }}
    .version {{ color:var(--muted); padding:5px 9px; border:1px solid var(--line); border-radius:99px; text-transform:none; white-space:nowrap; }}
    .summary {{ color:#c8d0d7; line-height:1.7; margin:22px 0 18px; }}
    audio {{ width:100%; height:42px; }}
    .details {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:20px; }}
    .meta {{ margin:0; color:var(--muted); font-size:13px; line-height:1.55; }}
    .meta span {{ display:block; margin-bottom:4px; color:#d8dee4; font-weight:650; }}
    .empty {{ padding:36px; border:1px dashed var(--line); border-radius:18px; color:var(--muted); text-align:center; }}
    footer {{ margin-top:28px; color:#66717c; font:12px/1.5 ui-monospace,SFMono-Regular,monospace; }}
    @media (max-width:640px) {{ main {{ padding-top:48px; }} .card-top {{ display:block; }} .version {{ display:inline-block; margin-top:14px; }} .details {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="brand">Moon · Voice Assets</div>
      <h1>让声音成为可复用的创作资产。</h1>
      <p class="intro">这里仅展示已经完成试听、权利确认与公开审核的版本。原始参考音、参考逐字稿和内部生成参数不会出现在公开目录中。</p>
    </header>
    <section class="catalog">{cards_html}</section>
    <footer>Generated by moon-media-lab · {date.today().isoformat()} · {len(voices)} public voice(s)</footer>
  </main>
</body>
</html>
"""


def import_voice_asset(
    *,
    source: Path,
    transcript: str,
    voice_id: str,
    authorization_confirmed: bool,
    root: Path | None = None,
) -> VoiceAsset:
    validate_voice_id(voice_id)
    if not authorization_confirmed:
        raise InvalidArguments(
            "Voice authorization is required.",
            hint="Only import your own voice or an explicitly authorized voice; pass "
            "--authorization-confirmed after verification.",
        )
    if not source.is_file():
        raise InvalidArguments(f"Reference media not found: {source}")
    transcript = transcript.strip()
    if not transcript:
        raise InvalidArguments("Reference transcript cannot be empty.")

    directory = (root or voice_assets_root()) / voice_id
    if directory.exists():
        raise InvalidArguments(
            f"Voice asset already exists: {voice_id}",
            hint="Create a new version instead of overwriting a frozen voice asset.",
        )
    samples_dir = directory / "samples"
    samples_dir.mkdir(parents=True)
    reference_path = directory / "reference.wav"

    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        raise MediaProbeFailed("ffmpeg not found", hint="Install ffmpeg or set PATH.")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "pcm_s16le",
        str(reference_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise MediaProbeFailed(
            f"Failed to extract voice reference from {source}",
            hint=completed.stderr.strip()[-800:] or "Check the input media with ffprobe.",
        )

    profile = {
        "id": voice_id,
        "description": "",
        "referenceText": transcript,
        "language": "Chinese",
        "cloneModel": DEFAULT_CLONE_MODEL,
        "seed": 42,
        "temperature": 0.65,
        "pauseMs": 180,
    }
    profile_path = directory / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "id": voice_id,
        "version": int(voice_id.rsplit("-v", 1)[1]),
        "sourceType": "authorized-clone-reference",
        "authorization": "confirmed-by-operator",
        "referenceSha256": _sha256(reference_path),
        "referenceDuration": _wav_duration(reference_path),
        "status": "candidate",
        "createdAt": date.today().isoformat(),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return VoiceAsset(voice_id, directory, manifest, profile_path, reference_path)


def design_voice_asset(
    *,
    voice_id: str,
    description: str,
    reference_text: str,
    root: Path | None = None,
) -> VoiceAsset:
    from moon_media_lab.tts.video_case import run_case

    validate_voice_id(voice_id)
    description = description.strip()
    reference_text = reference_text.strip()
    if not description:
        raise InvalidArguments("Voice description cannot be empty.")
    if not reference_text:
        raise InvalidArguments("Reference text cannot be empty.")

    directory = (root or voice_assets_root()) / voice_id
    if directory.exists():
        raise InvalidArguments(
            f"Voice asset already exists: {voice_id}",
            hint="Create a new version instead of overwriting a frozen voice asset.",
        )

    profile = {
        "id": voice_id,
        "description": description,
        "referenceText": reference_text,
        "language": "Chinese",
        "designModel": DEFAULT_DESIGN_MODEL,
        "cloneModel": DEFAULT_CLONE_MODEL,
        "seed": 42,
        "temperature": 0.7,
        "pauseMs": 180,
    }
    runs_root = get_paths().output / "voice-runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"design-{voice_id}-", dir=runs_root) as temp:
        temp_dir = Path(temp)
        profile_path = temp_dir / "profile.json"
        text_path = temp_dir / "reference.txt"
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        text_path.write_text(reference_text, encoding="utf-8")
        result = run_case(
            text_file=text_path,
            profile_file=profile_path,
            output_dir=temp_dir,
            reference_only=True,
        )
        generated_reference = Path(result["referenceAudio"])
        (directory / "samples").mkdir(parents=True)
        reference_path = directory / "reference.wav"
        shutil.copy2(generated_reference, reference_path)

    stored_profile = directory / "profile.json"
    stored_profile.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "id": voice_id,
        "version": int(voice_id.rsplit("-v", 1)[1]),
        "sourceType": "voice-design",
        "authorization": "not-applicable-synthetic",
        "referenceSha256": _sha256(reference_path),
        "referenceDuration": _wav_duration(reference_path),
        "status": "candidate",
        "createdAt": date.today().isoformat(),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return VoiceAsset(voice_id, directory, manifest, stored_profile, reference_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return round(handle.getnframes() / handle.getframerate(), 6)
