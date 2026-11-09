# video-transcriber

`video-transcriber` changes a video URL or a local media file into a transcript. It runs speech recognition locally on Apple silicon. It does not send audio to an external transcription service.

The tool accepts HTTP and HTTPS URLs that yt-dlp supports. It also accepts local audio and video files that ffmpeg supports.

## Requirements

- macOS on Apple silicon.
- `uv` for Python commands and Python 3.12.
- Pi with `codemode` for the summary skill. The setup command needs no `codemode`.
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

The skill has 2 summary templates:

| Template | Use for | Sections |
|---|---|---|
| `news` | Announcements, releases, events, commentary | What's new, how it works, background, why it matters, opinion |
| `guide` | Tutorials, how-to videos, walkthroughs | Goal, prerequisites, steps, result check, problems and fixes, reference, opinion |

Give the template name as the first argument to choose a template:

```text
/skill:video-summary guide <video-url>
/skill:video-summary news <video-url>
```

Without a template name, the skill chooses from the request and the transcript. A video that mainly teaches a task gets the `guide` template. To add a template, add a file in `skills/video-summary/templates/` and a row to the table in `SKILL.md`.

## How the tool works

The project has 3 parts:

| Part | Job | Uses a language model? |
|---|---|---|
| Pi setup extension | Install the CLI, show the model dialog, and run setup. | No |
| Python CLI | Prepare audio, run Phonon-2 locally, and write transcript files. | No |
| Pi summary skill | Choose the transcript path, read the transcript, research the topic, and write the summary. | Yes, the configured Pi language model |

### Setup

Enter `/video-setup` in Pi. The extension runs commands directly through `pi.exec()` and shows the model dialog through `ctx.ui.select()`.

```mermaid
flowchart TD
    Start["/video-setup"] --> UV{"uv available?"}
    UV -->|No| Missing["Show the uv installation link and stop"]
    UV -->|Yes| Install["Install the Python CLI from the loaded Pi package"]
    Install --> Catalog["Read the Python model catalog"]
    Catalog --> Dialog["Pi dialog: model, languages, size, recommendation"]
    Dialog -->|Escape| Cancel["Stop before the model download"]
    Dialog -->|Select| Setup["Run setup with the selected model ID"]
    Setup --> Tools["Install missing caption tools and ffmpeg"]
    Tools --> Model["Download and verify the model, or reuse its cache"]
    Model --> Config["Save the selected model in config.json"]
```

Only Phonon-2 appears in the current catalog. It supports English only. A maintainer must add each new model and its supported languages.

The extension installs the CLI before the model dialog. Escape leaves the CLI installed, but it starts no model download.

### Transcript paths

Enter `/skill:video-summary <URL-or-local-path>`. The agent follows the skill and chooses the transcript path.

```mermaid
flowchart TD
    Input["URL or local media file"] --> Kind{"Input type?"}
    Kind -->|YouTube URL| Captions["Try youtube_transcript_api"]
    Captions --> Available{"Captions available?"}
    Available -->|Yes| CaptionText["Provider captions and video metadata"]
    Available -->|No| CLI["Python CLI"]
    Kind -->|HackerTube or another URL| CLI
    Kind -->|Local audio or video file| CLI

    subgraph Local["Python CLI - local transcription"]
        CLI --> Source{"URL or file?"}
        Source -->|URL| Normalize["Convert HackerTube URLs to YouTube URLs"]
        Normalize --> Download["Get metadata and audio with yt-dlp"]
        Source -->|File| File["Read the local media file"]
        Download --> WAV["Use ffmpeg to produce 16 kHz mono WAV audio"]
        File --> WAV
        WAV --> AudioCache["Cache the WAV audio"]
        AudioCache --> Phonon["Run Phonon-2 locally through fermion and MLX"]
        Phonon --> Formats["Write TXT, SRT, VTT, or JSON"]
    end

    CaptionText --> Read["Agent reads the full transcript through codemode"]
    Formats --> Read
    Read --> Research["Agent uses codemode for web research"]
    Research --> Summary["Agent writes the researched summary"]
```

For YouTube URLs, the skill first tries provider captions. That path needs no audio download or speech recognition.

For HackerTube URLs and other URLs, the skill uses the Python CLI directly. HackerTube URLs contain a YouTube video ID. The CLI uses that ID to construct the YouTube source URL.

For local files, ffmpeg extracts the audio without a download. The CLI uses the file name without its extension as the title.

The CLI reuses cached audio when possible. It still runs transcription on each request. It does not cache transcripts or summaries.

TXT contains the transcript text. SRT and VTT contain subtitle segments. JSON also contains source metadata, word timestamps, model details, and timing measurements.

**The CLI does not check for captions or choose between the transcript paths.** A direct `video-transcriber transcribe` command always uses local speech recognition.

### Agent tool calls through codemode

`codemode` runs short JavaScript scripts that call Pi tools. The skill requires it for all agent shell commands, file reads, and web research.

The agent batches independent calls in one script. For example, it can get provider captions and video metadata at the same time.

The agent keeps dependent steps in order. It must finish transcription before it reads the transcript. It must read the full transcript before it writes the summary.

```mermaid
sequenceDiagram
    participant User
    participant Agent as Pi agent
    participant Code as codemode
    participant Tools as Shell, file, and web tools

    User->>Agent: /skill:video-summary with a source
    Agent->>Code: Script for transcript and metadata
    Code->>Tools: Batch independent calls and order dependent calls
    Tools-->>Code: Tool results
    Code-->>Agent: Full transcript text and source metadata
    Agent->>Code: Scripts for web research
    Code->>Tools: Search, then fetch selected sources
    Tools-->>Code: Source content
    Code-->>Agent: Relevant evidence and source URLs
    Agent-->>User: Researched summary
```

Only script output reaches the agent. Scripts omit duplicate word arrays, segment arrays, and web page content when the summary does not need them.

Scripts must not omit transcript text. The agent must read every transcript chunk. For a transcript-only request, the skill returns the transcript without a researched summary.

This approach can reduce agent turns and duplicate tool output. It does not reduce the local transcription work or guarantee a specific time or cost reduction.

### Enable codemode

Start Pi with `codemode`:

```bash
pi --tools +codemode
```

For persistent access, merge this setting into `~/.pi/agent/settings.json`:

```json
{
  "defaultTools": ["+codemode"]
}
```

This setting enables `codemode`, but it still exposes direct tools. The skill instructs the agent to use `codemode` for every tool action.

For stricter tool access, also set `codemode.mode` to `only`:

```json
{
  "defaultTools": ["+codemode"],
  "codemode": {
    "mode": "only"
  }
}
```

This mode hides direct tools that scripts can call. The agent reaches those tools through `codemode`. Merge these fields with existing settings; do not replace unrelated fields.

Reload Pi after a settings change. The package does not change your global Pi settings. If `codemode` is unavailable, the skill stops and gives the enable command.

The setup extension and Python CLI do not use `codemode`. They execute fixed code without agent model calls.

### Privacy and network use

The Python CLI runs speech recognition locally. It sends no audio or transcript to an external transcription service.

Setup needs network access for missing packages and model files. URL inputs need network access for metadata, captions, and audio. A cached model and a local file need no network access for transcription.

The summary has a different privacy boundary. Pi sends transcript text to its configured language model. Web research also sends queries to external services. Local transcription does not make the summary workflow fully local.

## Model architecture

The Python code uses a port-and-adapter design. A **port** defines the operations that the application needs. An **adapter** implements those operations for a specific backend.

The application uses the `SpeechBackend` port. It does not construct Fermion commands or parse vendor output.

```mermaid
flowchart LR
    Catalog["Model catalog: backend ID and model name"] --> Registry["Explicit backend registry"]
    Registry -->|selects| Fermion["FermionAdapter"]
    CLI["Transcription CLI"] -->|uses| Port["SpeechBackend port"]
    Setup["Model setup"] -->|uses| Port
    Fermion -->|implements| Port
    Fake["Fake backend in unit tests"] -->|implements| Port
    Port --> Shared["Shared Transcript, Segment, and Word types"]
    Formats["TXT, SRT, VTT, JSON"] -->|reads| Shared
```

### Files and responsibilities

| File | Responsibility |
|---|---|
| `src/video_transcriber/models.py` | Define approved models, backend IDs, languages, and the saved selection. |
| `src/video_transcriber/ports.py` | Define the `SpeechBackend` interface with Python `Protocol`. |
| `src/video_transcriber/transcript.py` | Define backend-independent transcript data. |
| `src/video_transcriber/backends.py` | Connect each approved backend ID to its adapter. |
| `src/video_transcriber/adapters/fermion.py` | Run Fermion commands and convert their output to shared transcript data. |
| `src/video_transcriber/setup.py` | Select a catalog model, install common tools, and ask its adapter to download the model. |
| `src/video_transcriber/cli.py` | Select the adapter, prepare audio, and request transcription. |
| `src/video_transcriber/formats.py` | Write shared transcript data to the requested format. |

The port has 2 operations:

```python
from pathlib import Path
from typing import Protocol

from video_transcriber.models import ModelSpec
from video_transcriber.transcript import Transcript


class SpeechBackend(Protocol):
    def download(self, model: ModelSpec) -> None: ...

    def transcribe(self, audio_path: Path, model: ModelSpec) -> Transcript: ...
```

An adapter needs no base class. Its method signatures must match the protocol. The type checker checks each registered adapter against the port.

The `download` operation downloads and verifies model files, or reuses their cache. The `transcribe` operation accepts 16 kHz mono WAV audio and runs speech recognition locally.

Each adapter converts its own output to `Transcript`. That type contains text, subtitle segments, word timestamps, model details, timing measurements, and a truncation flag.

Adapters must report expected failures with `TranscriberError`. Setup saves the model selection only after the download succeeds. Unknown backend IDs fail before dependency installation or audio preparation.

### Model ID versus backend ID

A catalog entry contains 3 separate identifiers:

| Field | Example | Meaning |
|---|---|---|
| `model_id` | `phonon-2` | The public ID for CLI arguments and saved configuration. |
| `backend` | `BackendId.FERMION` | The approved backend that selects the adapter. |
| `backend_name` | `phonon-2` | The model name that this backend accepts. |

The configuration stores only `model_id`. The application resolves the backend from the catalog on each request. Users cannot select arbitrary model names or import adapter code through configuration.

The registry is explicit. The project does not scan plugins or load user-supplied Python module names.

### Add a model to an existing backend

Use this path when an existing adapter already supports the model and its transcript data.

1. Verify the backend model name, input requirements, download size, license, and supported languages.
2. Add a `ModelSpec` entry in `src/video_transcriber/models.py`.
3. Set its `backend` to an existing `BackendId`.
4. Set its `backend_name` to the verified backend model name.
5. Record every supported language and the verified download size.
6. Add the entry to `SUPPORTED_MODELS`. Keep exactly 1 recommended model.
7. Add tests for selection, backend model names, downloads, and transcript output.
8. Update the supported model table in this README.

The catalog command, CLI model choices, Pi dialog, and saved selection use the new entry automatically. The CLI and setup need no model-specific branch.

Phonon-2 remains the only supported model in this version. A new model still requires a maintainer review and an explicit scope change.

### Add a new backend

Use this path when the model needs another runtime, command, or output conversion.

1. Add an adapter under `src/video_transcriber/adapters/`.
2. Implement both `SpeechBackend` methods with the exact port signatures.
3. Convert vendor output to the shared transcript types inside the adapter.
4. Keep backend commands, model caches, and vendor imports inside the adapter.
5. Add an approved identifier to `BackendId` in `models.py`.
6. Import and register the adapter in `backends.py`.
7. Add the model catalog entry as described above.
8. Pin any new Python dependency to an exact version with `uv`.
9. Test the adapter with mocked commands or a fake vendor API.
10. Test setup and transcription through the port. Network and model tests require the `integration` marker.

Output formats and media preparation stay unchanged. Backend-specific JSON parsing belongs in the adapter, not in the CLI or shared transcript types.

The unit tests include a fake second backend. They check setup, saved selection, adapter selection, progress messages, and JSON output without real models or network access.

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
