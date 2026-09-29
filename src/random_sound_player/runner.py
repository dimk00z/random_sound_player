"""The blocking random-playback loop."""

from __future__ import annotations

import random
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from .library import discover_mp3_files, select_next_file
from .player import build_player_command

if TYPE_CHECKING:
    from .cli import Settings


def play_random_forever(
    settings: Settings,
    *,
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    choice: Callable[[Sequence[Path]], Path] = random.choice,
    uniform: Callable[[float, float], float] = random.uniform,
    sleep: Callable[[float], None] = time.sleep,
    run_command: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    output: Callable[[str], None] = print,
) -> None:
    files = discover_mp3_files(settings.directory)
    if not files:
        raise ValueError(f"no MP3 files found in: {settings.directory}")

    previous: Path | None = None
    while True:
        selected = select_next_file(files, previous, choice)
        output(f"Playing: {selected}")
        run_command(
            build_player_command(selected, settings.volume, system=system, which=which),
            check=True,
        )
        previous = selected
        delay_seconds = uniform(settings.min_minutes, settings.max_minutes) * 60
        output(f"Waiting {delay_seconds / 60:g} minutes")
        sleep(delay_seconds)
