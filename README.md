# Random Sound Player

`random-sound-player` plays a random MP3 from a directory immediately, then waits a random interval before playing another file. Without a directory argument, it uses `.play` in the current directory.

```sh
uv run random-sound-player
```

```sh
uv run random-sound-player "/Users/ds/Desktop/Обращения"
```

Unicode paths and filenames, including Cyrillic names, are supported. The command only scans MP3 files directly inside the supplied directory.

By default it waits from 5 to 30 minutes and plays at 100% volume. Override those settings when needed:

```sh
uv run random-sound-player "/Users/ds/Desktop/Обращения" \
  --min-minutes 10 --max-minutes 20 --volume 75
```

Optionally play a separate MP3 continuously during each waiting interval. It loops until the same `Waiting … minutes` interval ends; its default volume is 50.

```sh
uv run random-sound-player --noise "/Users/ds/Desktop/Обращения/пауза.mp3" \
  --noise_volume 50
```

With at least three MP3 files available, it does not choose the previous file for the next playback. Press `Ctrl-C` to stop.

The player uses macOS `afplay`; on Linux it requires `ffplay`.
