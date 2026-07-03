from __future__ import annotations


class MoonMediaError(Exception):
    """Base error carrying a CLI exit code and a user-actionable hint."""

    exit_code = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class InvalidArguments(MoonMediaError):
    exit_code = 2


class EngineNotInstalled(MoonMediaError):
    exit_code = 3


class MediaProbeFailed(MoonMediaError):
    exit_code = 4


class ModelDownloadFailed(MoonMediaError):
    exit_code = 5


class TranscriptionFailed(MoonMediaError):
    exit_code = 6
