from __future__ import annotations

import subprocess
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from random_sound_player import (
    PlayerUnavailableError,
    Settings,
    build_noise_command,
    build_player_command,
    discover_mp3_files,
    main,
    parse_args,
    play_noise_for_duration,
    play_random_forever,
    select_next_file,
)
from random_sound_player.progress import ProgressBar


class ProgressBarTests(unittest.TestCase):
    def test_renders_percentage_and_completes_the_line(self) -> None:
        stream = StringIO()
        progress = ProgressBar(10, "Playing", stream=stream, width=10)

        progress.update(5)
        progress.finish()

        self.assertIn("Playing [#####-----]  50%", stream.getvalue())
        self.assertTrue(stream.getvalue().endswith("\n"))


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
                [
                    directory / "first.mp3",
                    directory / "second.MP3",
                    directory / "Обращение.mp3",
                ],
            )


class SelectionTests(unittest.TestCase):
    def test_plays_every_file_before_refilling_the_random_pool(self) -> None:
        files = [Path("one.mp3"), Path("two.mp3"), Path("three.mp3")]
        remaining: list[Path] = []

        selected: list[Path] = []
        for _ in range(6):
            selected.append(
                select_next_file(
                files,
                previous=selected[-1] if selected else None,
                choice=lambda candidates: candidates[-1],
                remaining=remaining,
            )
            )

        self.assertEqual(selected, [files[2], files[1], files[0], files[2], files[1], files[0]])
        self.assertEqual(set(selected[:3]), set(files))
        self.assertEqual(set(selected[3:]), set(files))
        self.assertNotEqual(selected[2], selected[3])


class PlayerCommandTests(unittest.TestCase):
    def test_builds_mac_noise_command_capped_to_the_remaining_wait(self) -> None:
        self.assertEqual(
            build_noise_command(
                Path("/Users/ds/Desktop/Обращения/шум.mp3"),
                50,
                duration_seconds=750,
                system="Darwin",
                which=lambda _: "/usr/bin/afplay",
            ),
            [
                "/usr/bin/afplay",
                "-v",
                "0.5",
                "-t",
                "750",
                "/Users/ds/Desktop/Обращения/шум.mp3",
            ],
        )

    def test_builds_linux_noise_command_with_an_infinite_loop(self) -> None:
        self.assertEqual(
            build_noise_command(
                Path("noise.mp3"),
                50,
                duration_seconds=60,
                system="Linux",
                which=lambda _: "/usr/bin/ffplay",
            ),
            [
                "/usr/bin/ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "error",
                "-loop",
                "0",
                "-volume",
                "50",
                "noise.mp3",
            ],
        )

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
            build_player_command(
                Path("sound.mp3"), 100, system="Linux", which=lambda _: None
            )


class PlaybackLoopTests(unittest.TestCase):
    def test_skips_a_file_that_the_player_cannot_read(self) -> None:
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            broken_file = directory / "broken.mp3"
            playable_file = directory / "playable.mp3"
            broken_file.touch()
            playable_file.touch()
            commands: list[list[str]] = []

            def run_command(command: list[str], **_kwargs: object) -> None:
                commands.append(command)
                if len(commands) == 1:
                    raise subprocess.CalledProcessError(1, command)

            with (
                self.assertLogs("random_sound_player.runner", level="WARNING") as logs,
                self.assertRaises(KeyboardInterrupt),
            ):
                play_random_forever(
                    Settings(directory, 5, 30, 100),
                    system="Darwin",
                    which=lambda _: "/usr/bin/afplay",
                    choice=lambda candidates: candidates[0],
                    uniform=lambda _minimum, _maximum: 5,
                    sleep=lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt),
                    run_command=run_command,
                )

        self.assertEqual(
            [command[-1] for command in commands],
            [str(broken_file), str(playable_file)],
        )
        self.assertIn("Skipping unreadable MP3", logs.output[0])

    def test_noise_runs_until_the_wait_deadline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            noise_path = Path(temp_dir) / "шум.mp3"
            noise_path.touch()
            clock = [0.0]
            commands: list[list[str]] = []

            class Process:
                terminated = False

                def poll(self) -> None:
                    return None

                def terminate(self) -> None:
                    self.terminated = True

                def wait(self, timeout: float | None = None) -> None:
                    return None

            process = Process()

            with self.assertLogs("random_sound_player.runner", level="INFO") as logs:
                play_noise_for_duration(
                    noise_path,
                    50,
                    60,
                    system="Darwin",
                    which=lambda _: "/usr/bin/afplay",
                    popen=lambda command: commands.append(command) or process,
                    monotonic=lambda: clock[0],
                    sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
                )

        self.assertEqual(
            commands, [["/usr/bin/afplay", "-v", "0.5", "-t", "60", str(noise_path)]]
        )
        self.assertAlmostEqual(clock[0], 60)
        self.assertTrue(process.terminated)
        self.assertEqual(
            logs.output,
            [f"INFO:random_sound_player.runner:Playing noise: {noise_path}"],
        )

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
                )

        self.assertEqual(commands, [["/usr/bin/afplay", "-v", "1", str(file_path)]])
        self.assertEqual(delays, [750])


class ArgumentTests(unittest.TestCase):
    def test_noise_uses_default_volume_of_fifty(self) -> None:
        settings = parse_args(["--noise", "pause.mp3"])

        self.assertEqual(settings.noise, Path("pause.mp3"))
        self.assertEqual(settings.noise_volume, 50)

    def test_defaults_directory_to_dot_play(self) -> None:
        self.assertEqual(parse_args([]).directory, Path(".play"))

    def test_rejects_an_inverted_delay_range(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["music", "--min-minutes", "30", "--max-minutes", "5"])

    def test_rejects_a_nonfinite_delay(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["music", "--max-minutes", "inf"])

    def test_reports_filesystem_errors_without_a_traceback(self) -> None:
        with (
            patch(
                "random_sound_player.cli.play_random_forever",
                side_effect=PermissionError("permission denied"),
            ),
            self.assertRaises(SystemExit) as error,
        ):
            main(["music"])

        self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
