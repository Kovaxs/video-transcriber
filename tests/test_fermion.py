"""Tests for the Fermion speech adapter and its JSON conversion."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from video_transcriber.adapters import fermion
from video_transcriber.adapters.fermion import FermionAdapter
from video_transcriber.errors import TranscriberError
from video_transcriber.models import PHONON_2, ModelSpec


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


@pytest.mark.parametrize(
    "model",
    [
        PHONON_2,
        replace(PHONON_2, model_id="test-model", backend_name="test-profile"),
    ],
)
def test_transcribe_calls_fermion_and_parses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: ModelSpec
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(phonon_payload()), "")

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "/venv/bin/fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)
    result = FermionAdapter().transcribe(tmp_path / "audio.wav", model)

    assert result.text == "Hello world."
    assert result.engine == "mlx"
    assert result.segments[0].text == "Hello world."
    assert result.words[1].end == 1.2
    assert commands == [
        [
            "/venv/bin/fermion",
            "transcribe",
            model.backend_name,
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

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="model missing"):
        FermionAdapter().transcribe(tmp_path / "audio.wav", PHONON_2)


def test_transcribe_rejects_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "not json", "")

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="invalid JSON"):
        FermionAdapter().transcribe(tmp_path / "audio.wav", PHONON_2)


@pytest.mark.parametrize(
    "model",
    [
        PHONON_2,
        replace(PHONON_2, model_id="test-model", backend_name="test-profile"),
    ],
)
def test_download_model_uses_catalog_backend(
    monkeypatch: pytest.MonkeyPatch, model: ModelSpec
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)
    FermionAdapter().download(model)
    assert commands == [
        [
            "fermion",
            "transcribe",
            model.backend_name,
            "--download-only",
            "unused.wav",
        ]
    ]


def test_download_reports_process_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)
    with pytest.raises(TranscriberError, match="Could not download Phonon-2"):
        FermionAdapter().download(PHONON_2)


@pytest.mark.parametrize("operation", ["download", "transcribe"])
def test_missing_executable_reports_expected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    def missing(
        command: list[str],
        check: bool,
        capture_output: bool = False,
        text: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("fermion")

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", missing)
    with pytest.raises(TranscriberError, match="executable is not available"):
        if operation == "download":
            FermionAdapter().download(PHONON_2)
        else:
            FermionAdapter().transcribe(tmp_path / "audio.wav", PHONON_2)


def test_transcribe_rejects_missing_word_timestamps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = phonon_payload()
    payload["words"] = None

    def fake_run(
        command: list[str], capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(fermion, "_fermion_executable", lambda: "fermion")
    monkeypatch.setattr(fermion.subprocess, "run", fake_run)

    with pytest.raises(TranscriberError, match="words is not a JSON array"):
        FermionAdapter().transcribe(tmp_path / "audio.wav", PHONON_2)
