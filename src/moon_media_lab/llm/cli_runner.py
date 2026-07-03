from __future__ import annotations

import subprocess
import time
from typing import Callable, Optional

from moon_media_lab.errors import PostProcessFailed

DEFAULT_TIMEOUT_SEC = 900
MAX_ATTEMPTS = 3
RETRY_DELAY_SEC = 20


def complete_via_cli(
    argv: list[str],
    prompt: str,
    *,
    provider: str,
    extract: Optional[Callable[[subprocess.CompletedProcess], str]] = None,
    env: Optional[dict] = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """Run a headless LLM CLI with retries; return the extracted completion text."""
    failure = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completed = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise PostProcessFailed(f"{provider} timed out after {timeout}s") from exc
        text = (extract(completed) if extract else completed.stdout).strip()
        if completed.returncode == 0 and text:
            return text
        failure = (
            f"exit {completed.returncode}: "
            f"{(completed.stderr.strip() or completed.stdout.strip())[:500]}"
        )
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY_SEC)
    raise PostProcessFailed(
        f"{provider} failed after {MAX_ATTEMPTS} attempts ({failure})",
        hint="API errors are often transient; rerun `moon-media process <job-dir>` "
        "later or switch providers with --llm. Cleanup batches resume from checkpoints.",
    )
