"""Tests for URL parsing, media preparation, and caching."""

import json
import subprocess
from pathlib import Path

import pytest

from video_transcriber import media
from video_transcriber.errors import TranscriberError


def test_normalize_hackertube_url() -> None:
    assert media.normalize_url("https://hackertube.org/watch/S4gU2Tsv6hY") == (
        "https://www.youtube.com/watch?v=S4gU2Tsv6hY"
    )


def test_normalize_other_url_does_not_change_it() -> None:
    url = "https://example.com/video/123?quality=high"
    assert media.normalize_url(url) == url


def test_normalize_hackertube_url_requires_video_id() -> None:
    with pytest.raises(TranscriberError, match="11-character"):
        media.normalize_url("https://hackertube.org/watch/short")


def test_prepare_media_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(TranscriberError, match="does not exist"):
        media.prepare_media(str(tmp_path / "missing.mp4"), tmp_path / "cache")


def test_prepare_media_rejects_non_http_url(tmp_path: Path) -> None:
    with pytest.raises(TranscriberError, match="Unsupported input scheme"):
        media.prepare_media("ftp://example.com/video.mp4", tmp_path / "cache")


def test_local_file_uses_ffmpeg_and_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "talk.mp4"
    source.write_bytes(b"video")
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        Path(command[-1]).write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    cache = tmp_path / "cache"
    first = media.prepare_media(str(source), cache)
    second = media.prepare_media(str(source), cache)

    assert first.title == "talk"
    assert first.source_type == "local"
    assert first.audio_path == second.audio_path
    assert first.audio_path.is_file()
    assert len(commands) == 1
    assert commands[0][0] == "ffmpeg"
    assert commands[0][-3:-1] == ["-c:a", "pcm_s16le"]
    assert commands[0][-1].endswith("/audio.wav")


def test_local_file_name_can_contain_a_colon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "talk:1.mp4"
    source.write_bytes(b"video")

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        Path(command[-1]).write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    prepared = media.prepare_media(str(source), tmp_path / "cache")
    assert prepared.title == "talk:1"


def test_failed_conversion_does_not_leave_cached_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "talk.mp4"
    source.write_bytes(b"video")

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        Path(command[-1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, "", "invalid input")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    cache = tmp_path / "cache"
    with pytest.raises(TranscriberError, match="invalid input"):
        media.prepare_media(str(source), cache)
    assert list(cache.rglob("audio.wav")) == []


def test_url_downloads_once_and_reads_cached_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "https://hackertube.org/watch/S4gU2Tsv6hY"
    fetch_count = 0
    download_count = 0

    def fake_fetch(url: str) -> dict[str, object]:
        nonlocal fetch_count
        fetch_count += 1
        assert url == "https://www.youtube.com/watch?v=S4gU2Tsv6hY"
        return {
            "id": "S4gU2Tsv6hY",
            "title": "The Iroquois Confederacy",
            "webpage_url": url,
            "uploader": "Historia Civilis",
            "upload_date": "20200101",
            "duration": 120,
        }

    def fake_download(
        command: list[str], failure: str
    ) -> subprocess.CompletedProcess[str]:
        nonlocal download_count
        download_count += 1
        output = Path(command[command.index("--output") + 1])
        output.with_suffix(".wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, str(output), "")

    monkeypatch.setattr(media, "_fetch_metadata", fake_fetch)
    monkeypatch.setattr(media, "_run", fake_download)
    cache = tmp_path / "cache"
    first = media.prepare_media(source, cache)
    second = media.prepare_media(source, cache)

    assert first.title == "The Iroquois Confederacy"
    assert first.uploader == "Historia Civilis"
    assert first.duration_seconds == 120.0
    assert second == first
    assert fetch_count == 1
    assert download_count == 1


def test_prepare_url_rejects_invalid_metadata_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "not json", "")

    monkeypatch.setattr(media.subprocess, "run", fake_run)
    with pytest.raises(TranscriberError, match="invalid metadata JSON"):
        media.prepare_media("https://example.com", tmp_path / "cache")


def test_cached_metadata_contains_original_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "https://example.com/video"
    cache = tmp_path / "cache"

    def fake_fetch(url: str) -> dict[str, object]:
        return {"id": "123", "title": "Video", "webpage_url": url}

    def fake_download(
        command: list[str], failure: str
    ) -> subprocess.CompletedProcess[str]:
        output = Path(command[command.index("--output") + 1])
        output.with_suffix(".wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(media, "_fetch_metadata", fake_fetch)
    monkeypatch.setattr(media, "_run", fake_download)
    prepared = media.prepare_media(source, cache)
    cached_value: object = json.loads(
        prepared.audio_path.parent.joinpath("metadata.json").read_text(encoding="utf-8")
    )
    assert isinstance(cached_value, dict)
    assert cached_value["title"] == "Video"
    assert media.prepare_media(source, cache) == prepared
