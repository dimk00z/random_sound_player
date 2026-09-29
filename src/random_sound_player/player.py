"""Platform-specific audio player commands."""

from __future__ import annotations

import platform
import shutil
from collections.abc import Callable
from pathlib import Path


class PlayerUnavailableError(RuntimeError):
    """Raised when the platform's supported audio player is unavailable."""


def build_player_command(
    file_path: Path,
    volume: int,
    *,
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    system_name = system or platform.system()
    if system_name == "Darwin":
        player = which("afplay")
        if player is None:
            raise PlayerUnavailableError(
                "afplay is required on macOS but was not found"
            )
        return [player, "-v", f"{volume / 100:g}", str(file_path)]
    if system_name == "Linux":
        player = which("ffplay")
        if player is None:
            raise PlayerUnavailableError(
                "ffplay is required on Linux but was not found"
            )
        return [
            player,
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            "-volume",
            str(volume),
            str(file_path),
        ]
    raise PlayerUnavailableError(f"unsupported operating system: {system_name}")
