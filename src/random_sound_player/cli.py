"""Command-line parsing and process-level error handling."""

from __future__ import annotations

import argparse
import logging
import math
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .player import PlayerUnavailableError
from .runner import play_random_forever

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    directory: Path
    min_minutes: float
    max_minutes: float
    volume: int
    noise: tuple[Path, ...] = ()
    noise_volume: int = 50


def _positive_number(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def _volume(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100") from error
    if not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return number


def _noise_paths(value: str) -> tuple[Path, ...]:
    paths = tuple(Path(part.strip()) for part in value.split(",") if part.strip())
    if not paths or len(paths) != len(value.split(",")):
        raise argparse.ArgumentTypeError("must be a comma-separated list of MP3 paths")
    return paths


def parse_args(argv: Sequence[str] | None = None) -> Settings:
    parser = argparse.ArgumentParser(
        description="Play random MP3 files at random intervals."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path(".play"),
        help="Directory containing MP3 files (default: .play)",
    )
    parser.add_argument(
        "--min-minutes",
        type=_positive_number,
        default=5,
        help="Minimum delay (default: 5)",
    )
    parser.add_argument(
        "--max-minutes",
        type=_positive_number,
        default=15,
        help="Maximum delay (default: 15)",
    )
    parser.add_argument(
        "--volume",
        type=_volume,
        default=100,
        help="Playback volume, 0-100 (default: 100)",
    )
    parser.add_argument(
        "--noise",
        type=_noise_paths,
        help="Comma-separated MP3 files to loop while waiting",
    )
    parser.add_argument(
        "--noise-volume",
        "--noise_volume",
        dest="noise_volume",
        type=_volume,
        default=50,
        help="Noise volume, 0-100 (default: 50)",
    )
    arguments = parser.parse_args(argv)
    if arguments.min_minutes > arguments.max_minutes:
        parser.error("--min-minutes cannot be greater than --max-minutes")
    settings = Settings(
        arguments.directory,
        arguments.min_minutes,
        arguments.max_minutes,
        arguments.volume,
        arguments.noise,
        arguments.noise_volume,
    )
    logger.info("Settings: %s", settings)
    return settings


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        play_random_forever(parse_args(argv))
    except KeyboardInterrupt:
        logger.info("Stopped.")
    except (
        OSError,
        PlayerUnavailableError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        logger.error("%s", error)
        raise SystemExit(1) from error
