"""Terminal progress displays and audio-duration discovery."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO


class ProgressBar:
    """A small single-line progress bar for an interactive terminal."""

    def __init__(
        self,
        duration_seconds: float,
        label: str,
        *,
        stream: TextIO | None = None,
        width: int = 24,
    ) -> None:
        self.duration_seconds = duration_seconds
        self.label = label
        self.stream = stream or sys.stderr
        self.width = width
        isatty = getattr(self.stream, "isatty", None)
        self.enabled = stream is not None or (not callable(isatty) or isatty())

    def update(self, elapsed_seconds: float) -> None:
        if not self.enabled:
            return
        ratio = min(max(elapsed_seconds / self.duration_seconds, 0), 1)
        completed = round(ratio * self.width)
        percent = round(ratio * 100)
        bar = "#" * completed + "-" * (self.width - completed)
        self.stream.write(
            f"\r{self.label} [{bar}] {percent:3d}% "
            f"{min(elapsed_seconds, self.duration_seconds):.0f}/{self.duration_seconds:.0f}s"
        )
        self.stream.flush()

    def finish(self) -> None:
        if not self.enabled:
            return
        self.update(self.duration_seconds)
        self.stream.write("\n")
        self.stream.flush()


def get_audio_duration(
    file_path: Path,
    *,
    system: str,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> float | None:
    if system == "Darwin":
        tool = which("afinfo")
        command = [tool, "--real", str(file_path)] if tool else None
        pattern = r"estimated duration:\s*([0-9.]+) sec"
    elif system == "Linux":
        tool = which("ffprobe")
        command = (
            [
                tool,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ]
            if tool
            else None
        )
        pattern = r"^([0-9.]+)$"
    else:
        return None

    if command is None:
        return None
    try:
        result = run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    match = re.search(pattern, result.stdout, re.MULTILINE)
    if match is None:
        return None
    duration = float(match.group(1))
    return duration if duration > 0 else None


@contextmanager
def show_progress(
    duration_seconds: float | None,
    label: str,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> Iterator[ProgressBar | None]:
    if duration_seconds is None:
        yield None
        return

    progress = ProgressBar(duration_seconds, label)
    if not progress.enabled:
        yield progress
        return

    stop = threading.Event()
    started_at = monotonic()

    def update_progress() -> None:
        while not stop.wait(0.1):
            progress.update(monotonic() - started_at)

    thread = threading.Thread(target=update_progress, daemon=True)
    thread.start()
    try:
        yield progress
    finally:
        stop.set()
        thread.join()
        progress.finish()
