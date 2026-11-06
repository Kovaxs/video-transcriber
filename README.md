# video-transcriber

`video-transcriber` changes a video URL or a local media file into a transcript. It runs Phonon-2 locally through MLX on Apple silicon. It does not send audio to an external transcription service.

The current version supports English transcription. It accepts HTTP and HTTPS URLs that yt-dlp supports. It also accepts local audio and video files that ffmpeg supports.

## Requirements

- macOS on Apple silicon.
- Python 3.12. `uv` can install this Python version.
- ffmpeg.
- The Phonon-2 model in the local Fermion cache.

Install ffmpeg with Homebrew:

```bash
brew install ffmpeg
```

## Install

Install the CLI from GitHub:

```bash
uv tool install --python 3.12 \
  git+https://github.com/Kovaxs/video-transcriber.git
```

Install the Pi skill separately:

```bash
pi install https://github.com/Kovaxs/video-transcriber
```

For development, use the local environment:

```bash
uv sync
uv run video-transcriber --help
```

## Use

Write plain text to standard output:

```bash
video-transcriber transcribe ./talk.mp4
```

Write subtitles to a file:

```bash
video-transcriber transcribe ./talk.mp4 --format srt --output talk.srt
```

Transcribe a HackerTube video:

```bash
video-transcriber transcribe \
  https://hackertube.org/watch/S4gU2Tsv6hY \
  --format json --output iroquois.json
```

The supported formats are `txt`, `srt`, `vtt`, and `json`. The JSON format includes source metadata, segments, and word timestamps. The default format is `txt`.

Use `--cache-dir` to select another audio cache:

```bash
video-transcriber transcribe ./talk.mp4 --cache-dir /tmp/media-cache
```

## Cache

The default audio cache is `~/.cache/video-transcriber/audio`. The `XDG_CACHE_HOME` variable changes the parent cache directory. The `VIDEO_TRANSCRIBER_CACHE_DIR` variable changes the full cache directory.

Each URL has a separate cache entry. Each local file has a cache entry based on its path, size, and modification time. A later run reuses unchanged audio.

Phonon-2 uses the separate Fermion model cache. The default path is `~/.cache/fermion`.

## Pi skill

Load the skill explicitly:

```text
/skill:youtube-captions <video-url>
```

The skill uses provider captions when they exist. It uses this CLI when captions do not exist. It reads the full transcript before it writes a researched summary.

## Development

Run the unit tests:

```bash
uv run pytest
```

Run the code checks:

```bash
uv run ruff check
uv run ruff format --check
uv run pyright
```

Unit tests do not use the network or the speech model. Integration tests use the `integration` marker and run only on request.
