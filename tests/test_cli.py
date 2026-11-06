"""Tests for the command-line interface through the speech port."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tests.fakes import FakeBackend
from video_transcriber import cli
from video_transcriber.errors import TranscriberError
from video_transcriber.media import Media
from video_transcriber.models import PHONON_2, SUPPORTED_MODELS, ModelSpec


def test_cli_writes_srt_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    media: Media,
    backend: FakeBackend,
) -> None:
    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    monkeypatch.setattr(cli, "prepare_media", fake_prepare)

    exit_code = cli.main(["transcribe", "video.mp4", "--format", "srt"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("1\n00:00:00,000 --> 00:00:01,250")
    assert "Preparing audio" in captured.err
    assert "Transcribing with Phonon-2" in captured.err
    assert backend.transcriptions == [(media.audio_path, PHONON_2)]


def test_cli_writes_json_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    media: Media,
    backend: FakeBackend,
) -> None:
    output = tmp_path / "nested" / "transcript.json"

    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    monkeypatch.setattr(cli, "prepare_media", fake_prepare)

    exit_code = cli.main(
        ["transcribe", "video.mp4", "--format", "json", "--output", str(output)]
    )

    assert exit_code == 0
    value: object = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert value["model"] == backend.result.model


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


def test_cli_prints_model_catalog_without_setup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_setup(model_id: str | None) -> ModelSpec:
        raise AssertionError("The catalog command must not run setup.")

    def fail_backend(backend_id: object) -> None:
        raise AssertionError("The catalog command must not resolve a backend.")

    monkeypatch.setattr(cli, "run_setup", fail_setup)
    monkeypatch.setattr(cli, "get_backend", fail_backend)
    assert cli.main(["models"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == [
        {
            "model_id": model.model_id,
            "display_name": model.display_name,
            "backend": model.backend.value,
            "backend_name": model.backend_name,
            "languages": [
                {"code": language.code, "name": language.name}
                for language in model.languages
            ],
            "download_size_mb": model.download_size_mb,
            "recommended": model.recommended,
        }
        for model in SUPPORTED_MODELS
    ]


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


def test_cli_warns_when_backend_truncates_audio(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    media: Media,
    backend: FakeBackend,
) -> None:
    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    backend.result = replace(backend.result, truncated=True)
    monkeypatch.setattr(cli, "prepare_media", fake_prepare)
    assert cli.main(["transcribe", "video.mp4"]) == 0
    assert "Phonon-2 truncated" in capsys.readouterr().err


def test_cli_rejects_model_outside_catalog() -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(["setup", "--model", "arbitrary-model"])
    assert error.value.code == 2
