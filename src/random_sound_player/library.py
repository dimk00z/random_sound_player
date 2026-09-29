"""MP3 discovery and random selection."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from pathlib import Path


def discover_mp3_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"not a directory: {directory}")
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".mp3"
    )


def select_next_file(
    files: Sequence[Path],
    previous: Path | None = None,
    choice: Callable[[Sequence[Path]], Path] = random.choice,
) -> Path:
    if not files:
        raise ValueError("no MP3 files found")
    candidates = (
        [path for path in files if path != previous] if len(files) >= 3 else list(files)
    )
    return choice(candidates)
