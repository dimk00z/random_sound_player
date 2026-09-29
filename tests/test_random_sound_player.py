from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from random_sound_player import (
    PlayerUnavailableError,
    build_player_command,
    discover_mp3_files,
    main,
    parse_args,
    play_random_forever,
    select_next_file,
    Settings,
)


class DiscoverMp3FilesTests(unittest.TestCase):
    def test_returns_direct_mp3_files_case_insensitively(self) -> None:
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "first.mp3").touch()
            (directory / "second.MP3").touch()
            (directory / "Обращение.mp3").touch()
            (directory / "notes.txt").touch()
            (directory / "nested").mkdir()
            (directory / "nested" / "third.mp3").touch()

            self.assertEqual(
                discover_mp3_files(directory),
                [directory / "first.mp3", directory / "second.MP3", directory / "Обращение.mp3"],
            )


class SelectionTests(unittest.TestCase):
    def test_excludes_previous_file_when_three_or_more_candidates_exist(self) -> None:
        files = [Path("one.mp3"), Path("two.mp3"), Path("three.mp3")]

        selected = select_next_file(files, previous=files[0])

        self.assertIn(selected, files[1:])


class PlayerCommandTests(unittest.TestCase):
    def test_builds_afplay_command_with_normalized_volume(self) -> None:
        self.assertEqual(
            build_player_command(
                Path("/Users/ds/Desktop/Обращения/звонок.mp3"),
                75,
                system="Darwin",
                which=lambda _: "/usr/bin/afplay",
            ),
            ["/usr/bin/afplay", "-v", "0.75", "/Users/ds/Desktop/Обращения/звонок.mp3"],
        )

    def test_requires_ffplay_on_linux(self) -> None:
        with self.assertRaises(PlayerUnavailableError):
            build_player_command(Path("sound.mp3"), 100, system="Linux", which=lambda _: None)


class PlaybackLoopTests(unittest.TestCase):
    def test_plays_immediately_then_sleeps_for_the_selected_delay(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "Обращение.mp3"
            file_path.touch()
            commands: list[list[str]] = []
            delays: list[float] = []

            def stop_after_first_sleep(delay: float) -> None:
                delays.append(delay)
                raise KeyboardInterrupt

            with self.assertRaises(KeyboardInterrupt):
                play_random_forever(
                    Settings(Path(temp_dir), 5, 30, 100),
                    system="Darwin",
                    which=lambda _: "/usr/bin/afplay",
                    choice=lambda candidates: candidates[0],
                    uniform=lambda _minimum, _maximum: 12.5,
                    sleep=stop_after_first_sleep,
                    run_command=lambda command, **_kwargs: commands.append(command),
                    output=lambda _message: None,
                )

        self.assertEqual(commands, [["/usr/bin/afplay", "-v", "1", str(file_path)]])
        self.assertEqual(delays, [750])


class ArgumentTests(unittest.TestCase):
    def test_defaults_directory_to_dot_play(self) -> None:
        self.assertEqual(parse_args([]).directory, Path(".play"))

    def test_rejects_an_inverted_delay_range(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["music", "--min-minutes", "30", "--max-minutes", "5"])

    def test_rejects_a_nonfinite_delay(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["music", "--max-minutes", "inf"])

    def test_reports_filesystem_errors_without_a_traceback(self) -> None:
        with patch("random_sound_player.cli.play_random_forever", side_effect=PermissionError("permission denied")):
            with self.assertRaises(SystemExit) as error:
                main(["music"])

        self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
