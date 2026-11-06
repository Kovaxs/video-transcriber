"""Prepare cached audio and metadata from URLs and local files."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import parse_qs, urlparse

from video_transcriber.errors import TranscriberError


@dataclass(frozen=True)
class Media:
    """Describe a media source and its cached audio."""

    original_input: str
    source_type: Literal["url", "local"]
    audio_path: Path
    title: str
    source_url: str | None
    media_id: str | None
    uploader: str | None
    upload_date: str | None
    duration_seconds: float | None


def default_cache_dir() -> Path:
    """Return the user cache directory for audio and metadata."""
    configured = os.environ.get("VIDEO_TRANSCRIBER_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    root = Path(xdg_cache).expanduser() if xdg_cache else Path.home() / ".cache"
    return root / "video-transcriber"


def normalize_url(url: str) -> str:
    """Convert a HackerTube watch URL to its YouTube source URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise TranscriberError(f"Invalid HTTP URL: {url}")
    if parsed.hostname not in {"hackertube.org", "www.hackertube.org"}:
        return url

    parts = [part for part in parsed.path.split("/") if part]
    video_id = parts[1] if len(parts) == 2 and parts[0] == "watch" else None
    if video_id is None:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    if video_id is None or len(video_id) != 11:
        raise TranscriberError(
            "The HackerTube URL must contain an 11-character YouTube video ID."
        )
    return f"https://www.youtube.com/watch?v={video_id}"


def prepare_media(source: str, cache_dir: Path | None = None) -> Media:
    """Return cached 16 kHz mono WAV audio for a URL or local file."""
    path = Path(source).expanduser()
    if path.is_file():
        return _prepare_local(path.resolve(), source, cache_dir or default_cache_dir())

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return _prepare_url(source, cache_dir or default_cache_dir())
    if parsed.scheme:
        raise TranscriberError(f"Unsupported input scheme: {parsed.scheme}")
    raise TranscriberError(f"Input file does not exist: {path}")


def _prepare_local(path: Path, original_input: str, cache_root: Path) -> Media:
    stat = path.stat()
    identity = f"{path}\0{stat.st_size}\0{stat.st_mtime_ns}"
    audio_path = _cache_audio_path(cache_root, identity)
    if not audio_path.is_file():
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".partial-", dir=audio_path.parent
        ) as temporary_directory:
            partial_path = Path(temporary_directory) / "audio.wav"
            _run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(partial_path),
                ],
                "ffmpeg could not convert the input file",
            )
            if not partial_path.is_file():
                raise TranscriberError("ffmpeg did not create the expected WAV file.")
            partial_path.replace(audio_path)
    return Media(
        original_input=original_input,
        source_type="local",
        audio_path=audio_path,
        title=path.stem,
        source_url=None,
        media_id=None,
        uploader=None,
        upload_date=None,
        duration_seconds=None,
    )


def _prepare_url(source: str, cache_root: Path) -> Media:
    download_url = normalize_url(source)
    audio_path = _cache_audio_path(cache_root, download_url)
    metadata_path = audio_path.parent / "metadata.json"
    if audio_path.is_file() and metadata_path.is_file():
        return _read_cached_url_media(source, audio_path, metadata_path)

    metadata = _fetch_metadata(download_url)
    if not audio_path.is_file():
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".partial-", dir=audio_path.parent
        ) as temporary_directory:
            partial_path = Path(temporary_directory) / "audio.wav"
            _run(
                [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--no-playlist",
                    "--no-warnings",
                    "--no-progress",
                    "--extract-audio",
                    "--audio-format",
                    "wav",
                    "--postprocessor-args",
                    "ffmpeg:-ar 16000 -ac 1",
                    "--output",
                    str(partial_path.parent / "audio.%(ext)s"),
                    "--print",
                    "after_move:filepath",
                    download_url,
                ],
                "yt-dlp could not download the audio",
            )
            if not partial_path.is_file():
                raise TranscriberError("yt-dlp did not create the expected WAV file.")
            partial_path.replace(audio_path)

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return _media_from_metadata(source, "url", audio_path, metadata)


def _cache_audio_path(cache_root: Path, identity: str) -> Path:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return cache_root / "audio" / digest / "audio.wav"


def _fetch_metadata(url: str) -> dict[str, object]:
    process = _run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--no-warnings",
            "--skip-download",
            "--dump-single-json",
            url,
        ],
        "yt-dlp could not read the video metadata",
    )
    try:
        value: object = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise TranscriberError("yt-dlp returned invalid metadata JSON.") from error
    return _as_object(value, "yt-dlp metadata")


def _read_cached_url_media(source: str, audio_path: Path, metadata_path: Path) -> Media:
    try:
        value: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TranscriberError(
            f"Cached metadata is unreadable: {metadata_path}. "
            "Remove this cache directory and retry."
        ) from error
    metadata = _as_object(value, "cached metadata")
    return _media_from_metadata(source, "url", audio_path, metadata)


def _media_from_metadata(
    source: str,
    source_type: Literal["url", "local"],
    audio_path: Path,
    metadata: dict[str, object],
) -> Media:
    title = _optional_string(metadata.get("title"))
    media_id = _optional_string(metadata.get("id"))
    if title is None or media_id is None:
        raise TranscriberError("yt-dlp metadata does not contain a title and an ID.")
    duration = metadata.get("duration")
    return Media(
        original_input=source,
        source_type=source_type,
        audio_path=audio_path,
        title=title,
        source_url=_optional_string(metadata.get("webpage_url")) or source,
        media_id=media_id,
        uploader=_optional_string(metadata.get("uploader")),
        upload_date=_optional_string(metadata.get("upload_date")),
        duration_seconds=float(duration) if isinstance(duration, int | float) else None,
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TranscriberError(f"The {context} is not a JSON object.")
    if not all(isinstance(key, str) for key in cast(dict[object, object], value)):
        raise TranscriberError(f"The {context} has a non-string key.")
    return cast(dict[str, object], value)


def _run(command: list[str], failure: str) -> subprocess.CompletedProcess[str]:
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        message = f"Required executable is missing: {command[0]}"
        raise TranscriberError(message) from error
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "No error output."
        raise TranscriberError(f"{failure}.\n{detail}")
    return process
