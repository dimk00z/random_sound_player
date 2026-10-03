"""The blocking random-playback loop."""

from __future__ import annotations

import logging
import platform
import random
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from .library import discover_mp3_files, select_next_file
from .player import build_noise_command, build_player_command
from .progress import ProgressBar, get_audio_duration, show_progress

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .cli import Settings


def play_noise_for_duration(
    noise_paths: Sequence[Path] | Path,
    volume: int,
    duration_seconds: float,
    *,
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    popen: Callable[[list[str]], subprocess.Popen[bytes]] = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    normalized_noise_paths = (noise_paths,) if isinstance(noise_paths, Path) else noise_paths
    for noise_path in normalized_noise_paths:
        if not noise_path.is_file() or noise_path.suffix.lower() != ".mp3":
            raise ValueError(f"noise must be an MP3 file: {noise_path}")

    deadline = monotonic() + duration_seconds
    processes: list[subprocess.Popen[bytes] | None] = [None] * len(normalized_noise_paths)
    progress = ProgressBar(duration_seconds, "Noise")
    try:
        while (remaining := deadline - monotonic()) > 0:
            for index, noise_path in enumerate(normalized_noise_paths):
                process = processes[index]
                if process is None or process.poll() is not None:
                    logger.info("Playing noise: %s", noise_path)
                    processes[index] = popen(
                        build_noise_command(
                            noise_path,
                            volume,
                            duration_seconds=remaining,
                            system=system,
                            which=which,
                        )
                    )
            sleep(min(0.1, remaining))
            progress.update(duration_seconds - max(deadline - monotonic(), 0))
    finally:
        for process in processes:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        progress.finish()


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
) -> None:
    files = discover_mp3_files(settings.directory)
    if not files:
        raise ValueError(f"no MP3 files found in: {settings.directory}")

    previous: Path | None = None
    unreadable_files: set[Path] = set()
    remaining_files: list[Path] = []
    system_name = system or platform.system()
    while True:
        playable_files = [path for path in files if path not in unreadable_files]
        if not playable_files:
            raise ValueError(f"no playable MP3 files found in: {settings.directory}")

        remaining_files[:] = [
            path for path in remaining_files if path in playable_files
        ]
        selected = select_next_file(
            playable_files,
            previous,
            choice,
            remaining=remaining_files,
        )
        logger.info("Playing: %s", selected)
        try:
            duration = (
                get_audio_duration(selected, system=system_name, which=which)
                if run_command is subprocess.run
                else None
            )
            with show_progress(duration, "Playing"):
                run_command(
                    build_player_command(
                        selected, settings.volume, system=system, which=which
                    ),
                    check=True,
                )
        except subprocess.CalledProcessError:
            logger.warning("Skipping unreadable MP3: %s", selected)
            unreadable_files.add(selected)
            continue
        previous = selected
        delay_seconds = uniform(settings.min_minutes, settings.max_minutes) * 60
        logger.info("Waiting %g minutes", delay_seconds / 60)
        if not settings.noise:
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
