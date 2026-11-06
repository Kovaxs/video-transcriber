"""Tests for the command-line interface."""

import json
from pathlib import Path

import pytest

from video_transcriber import cli
from video_transcriber.errors import TranscriberError
from video_transcriber.media import Media
from video_transcriber.models import PHONON_2, ModelSpec
from video_transcriber.phonon import Transcript


def test_cli_writes_srt_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    media: Media,
    transcript: Transcript,
) -> None:
    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    def fake_transcribe(audio_path: Path) -> Transcript:
        return transcript

    monkeypatch.setattr(cli, "prepare_media", fake_prepare)
    monkeypatch.setattr(cli, "transcribe", fake_transcribe)

    exit_code = cli.main(["transcribe", "video.mp4", "--format", "srt"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("1\n00:00:00,000 --> 00:00:01,250")
    assert "Preparing audio" in captured.err
    assert "Transcribing with Phonon-2" in captured.err


def test_cli_writes_json_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    media: Media,
    transcript: Transcript,
) -> None:
    output = tmp_path / "nested" / "transcript.json"

    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    def fake_transcribe(audio_path: Path) -> Transcript:
        return transcript

    monkeypatch.setattr(cli, "prepare_media", fake_prepare)
    monkeypatch.setattr(cli, "transcribe", fake_transcribe)

    exit_code = cli.main(
        ["transcribe", "video.mp4", "--format", "json", "--output", str(output)]
    )

    assert exit_code == 0
    value: object = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert value["model"] == "FermionResearch/Phonon-2"


def test_cli_runs_setup_with_catalog_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected: list[str | None] = []

    def fake_setup(model_id: str | None) -> ModelSpec:
        selected.append(model_id)
        return PHONON_2

    monkeypatch.setattr(cli, "run_setup", fake_setup)
    assert cli.main(["setup", "--model", "phonon-2"]) == 0
    assert selected == ["phonon-2"]


def test_cli_reports_expected_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(source: str, cache_dir: Path | None) -> Media:
        raise TranscriberError("Input file does not exist")

    monkeypatch.setattr(cli, "prepare_media", fail)
    exit_code = cli.main(["transcribe", "missing.mp4"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "error: Input file does not exist" in captured.err
