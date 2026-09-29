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
from .player import build_noise_command, build_player_command

if TYPE_CHECKING:
    from .cli import Settings


def play_noise_for_duration(
    noise_path: Path,
    volume: int,
    duration_seconds: float,
    *,
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    popen: Callable[[list[str]], subprocess.Popen[bytes]] = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if not noise_path.is_file() or noise_path.suffix.lower() != ".mp3":
        raise ValueError(f"noise must be an MP3 file: {noise_path}")

    deadline = monotonic() + duration_seconds
    process: subprocess.Popen[bytes] | None = None
    try:
        while (remaining := deadline - monotonic()) > 0:
            if process is None or process.poll() is not None:
                process = popen(
                    build_noise_command(
                        noise_path,
                        volume,
                        duration_seconds=remaining,
                        system=system,
                        which=which,
                    )
                )
            sleep(min(0.1, remaining))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def play_random_forever(
    settings: Settings,
    *,
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    choice: Callable[[Sequence[Path]], Path] = random.choice,
    uniform: Callable[[float, float], float] = random.uniform,
    sleep: Callable[[float], None] = time.sleep,
    run_command: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    noise_popen: Callable[[list[str]], subprocess.Popen[bytes]] = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
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
        if settings.noise is None:
            sleep(delay_seconds)
        else:
            play_noise_for_duration(
                settings.noise,
                settings.noise_volume,
                delay_seconds,
                system=system,
                which=which,
                popen=noise_popen,
                monotonic=monotonic,
                sleep=sleep,
            )
