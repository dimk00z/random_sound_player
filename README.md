# Random Sound Player

`random-sound-player` plays a random MP3 from a directory immediately, then waits a random interval before playing another file.

```sh
uv run random-sound-player "/Users/ds/Desktop/Обращения"
```

Unicode paths and filenames, including Cyrillic names, are supported. The command only scans MP3 files directly inside the supplied directory.

By default it waits from 5 to 30 minutes and plays at 100% volume. Override those settings when needed:

```sh
uv run random-sound-player "/Users/ds/Desktop/Обращения" \
  --min-minutes 10 --max-minutes 20 --volume 75
```

With at least three MP3 files available, it does not choose the previous file for the next playback. Press `Ctrl-C` to stop.

The player uses macOS `afplay`; on Linux it requires `ffplay`.
