"""Command-line parsing and process-level error handling."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import sys

from .player import PlayerUnavailableError
from .runner import play_random_forever


@dataclass(frozen=True)
class Settings:
    directory: Path
    min_minutes: float
    max_minutes: float
    volume: int


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


def parse_args(argv: Sequence[str] | None = None) -> Settings:
    parser = argparse.ArgumentParser(description="Play random MP3 files at random intervals.")
    parser.add_argument("directory", type=Path, help="Directory containing MP3 files")
    parser.add_argument("--min-minutes", type=_positive_number, default=5, help="Minimum delay (default: 5)")
    parser.add_argument("--max-minutes", type=_positive_number, default=30, help="Maximum delay (default: 30)")
    parser.add_argument("--volume", type=_volume, default=100, help="Playback volume, 0-100 (default: 100)")
    arguments = parser.parse_args(argv)
    if arguments.min_minutes > arguments.max_minutes:
        parser.error("--min-minutes cannot be greater than --max-minutes")
    return Settings(arguments.directory, arguments.min_minutes, arguments.max_minutes, arguments.volume)


def main(argv: Sequence[str] | None = None) -> None:
    try:
        play_random_forever(parse_args(argv))
    except KeyboardInterrupt:
        print("Stopped.")
    except (OSError, PlayerUnavailableError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
