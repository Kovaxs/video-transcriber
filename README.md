# video-transcriber

`video-transcriber` changes a video URL or a local media file into a transcript. It runs speech recognition locally on Apple silicon. It does not send audio to an external transcription service.

The tool accepts HTTP and HTTPS URLs that yt-dlp supports. It also accepts local audio and video files that ffmpeg supports.

## Requirements

- macOS on Apple silicon.
- `uv` for Python commands and Python 3.12.
- Pi for the skill.
- Homebrew if ffmpeg is missing.

Install `uv` with the instructions at https://docs.astral.sh/uv/.

## Install with Pi

Install the Pi package:

```bash
pi install https://github.com/Kovaxs/video-transcriber
```

Run the setup command in Pi:

```text
/video-setup
```

The command installs the Python CLI from the same package that Pi loads. It does not fetch another repository version.

The command reads the Python model catalog and opens a Pi selection dialog. Each option shows the model, supported languages, download size, and recommendation.

Select a model with the arrow keys and press Enter. Press Escape to cancel before the model download.

The command then installs missing caption tools and ffmpeg. It downloads the selected model and saves the selection. The command shows progress and errors in Pi. It does not use a terminal prompt.

After a package update, run `/reload` in Pi to load the command. Run `/video-setup` again to change the model.

The setup uses `uv tool` for Python commands. It uses Homebrew for ffmpeg. The `fermion` command downloads and verifies the model weights.

## Manual installation

Install the CLI without Pi:

```bash
uv tool install --python 3.12 \
  git+https://github.com/Kovaxs/video-transcriber.git
```

Run the interactive setup:

```bash
video-transcriber setup
```

For a non-interactive setup, select a catalog model by ID:

```bash
video-transcriber setup --model phonon-2
```

## Supported models

| Model | Catalog ID | Languages | Download | Status |
|---|---|---|---:|---|
| Phonon-2 | `phonon-2` | English only | 158 MB | Recommended |

Phonon-2 runs locally through MLX. It provides punctuation, capitalization, segments, and word timestamps.

Print the catalog as JSON without a model download:

```bash
video-transcriber models
```

The CLI accepts only models from this catalog. It does not accept arbitrary model names. A maintainer must add each supported model and all its languages.

To request another model, open an issue:

https://github.com/Kovaxs/video-transcriber/issues

Include the model name, its languages, and a link to its documentation.

## Transcribe

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

## Pi skill

Transcribe and summarize a video:

```text
/skill:video-summary <video-url>
```

Use a local file path instead of a URL for a local audio or video file. The skill uses provider captions when they exist. It uses local transcription when captions do not exist. It reads the full transcript before it writes a researched summary.

## Configuration and cache

The setup saves the selected model in `~/.config/video-transcriber/config.json`. The `XDG_CONFIG_HOME` variable changes the parent configuration directory. The `VIDEO_TRANSCRIBER_CONFIG_DIR` variable changes the full configuration directory.

Without a configuration file, the CLI uses the recommended model.

The default audio cache is `~/.cache/video-transcriber/audio`. The `XDG_CACHE_HOME` variable changes the parent cache directory. The `VIDEO_TRANSCRIBER_CACHE_DIR` variable changes the full cache directory.

Each URL has a separate cache entry. Each local file has a cache entry based on its path, size, and modification time. A later run reuses unchanged audio. Failed downloads and conversions do not create a cached WAV file.

The model uses the separate Fermion cache. Its default path is `~/.cache/fermion`.

## Development

Create the local environment:

```bash
uv sync
```

Run the unit tests:

```bash
uv run pytest
```

Run the Pi extension tests with Node.js 22.18 or later:

```bash
node --test tests/test_video_setup.mjs
```

Test the Pi dialog from the local package:

```bash
pi -e .
```

Then enter `/video-setup` in Pi.

Run the code checks:

```bash
uv run ruff check
uv run ruff format --check
uv run pyright
```

Unit tests do not use the network or a speech model. Integration tests use the `integration` marker and run only on request.
