"""Public API for the random sound player."""

from .cli import Settings, main, parse_args
from .library import discover_mp3_files, select_next_file
from .player import PlayerUnavailableError, build_noise_command, build_player_command
from .runner import play_noise_for_duration, play_random_forever

__all__ = [
    "PlayerUnavailableError",
    "Settings",
    "build_noise_command",
    "build_player_command",
    "discover_mp3_files",
    "main",
    "parse_args",
    "play_noise_for_duration",
    "play_random_forever",
    "select_next_file",
]
