"""Tests for the local Phonon-2 process and JSON parser."""

import json
import subprocess
from pathlib import Path

import pytest

from video_transcriber import phonon
from video_transcriber.errors import TranscriberError
from video_transcriber.models import PHONON_2


def phonon_payload() -> dict[str, object]:
    return {
        "text": "Hello world.",
        "model": "FermionResearch/Phonon-2",
        "engine": "mlx",
        "duration_seconds": 1.2,
        "decode_seconds": 0.1,
        "wall_seconds": 2.0,
        "segments": [{"id": 0, "start": 0.0, "end": 1.2, "text": "Hello world."}],
        "words": [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "world.", "start": 0.5, "end": 1.2},
        ],
        "truncated": False,
    }


@pytest.fixture(autouse=True)
def use_default_test_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phonon, "get_configured_model", lambda: PHONON_2)


def test_transcribe_calls_fermion_and_parses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(phonon_payload()), "")

    monkeypatch.setattr(phonon, "_fermion_executable", lambda: "/venv/bin/fermion")
    monkeypatch.setattr(phonon.subprocess, "run", fake_run)
    result = phonon.transcribe(tmp_path / "audio.wav")

    assert result.text == "Hello world."
    assert result.engine == "mlx"
    assert result.segments[0].text == "Hello world."
    assert result.words[1].end == 1.2
    assert commands == [
        [
            "/venv/bin/fermion",
            "transcribe",
            "phonon-2",
            str(tmp_path / "audio.wav"),
            "--json",
        ]
    ]


def test_transcribe_reports_process_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "model missing")

    monkeypatch.setattr(phonon, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(phonon.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="model missing"):
        phonon.transcribe(tmp_path / "audio.wav")


def test_transcribe_rejects_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "not json", "")

    monkeypatch.setattr(phonon, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(phonon.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="invalid JSON"):
        phonon.transcribe(tmp_path / "audio.wav")


def test_download_model_uses_catalog_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(phonon, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(phonon.subprocess, "run", fake_run)
    phonon.download_model(PHONON_2)
    assert commands == [
        [
            "fermion",
            "transcribe",
            "phonon-2",
            "--download-only",
            "unused.wav",
        ]
    ]


def test_transcribe_rejects_missing_word_timestamps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = phonon_payload()
    payload["words"] = None

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(phonon, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(phonon.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="words is not a JSON array"):
        phonon.transcribe(tmp_path / "audio.wav")
