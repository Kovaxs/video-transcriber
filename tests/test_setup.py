"""Tests for model setup through the speech port."""

from pathlib import Path

import pytest

from tests.fakes import FakeBackend
from video_transcriber import setup
from video_transcriber.errors import TranscriberError
from video_transcriber.models import PHONON_2, get_configured_model


def test_model_prompt_marks_phonon_2_recommended_and_english_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def select_default(prompt: str) -> str:
        return ""

    selected = setup.select_model(select_default)
    output = capsys.readouterr().out
    assert selected == PHONON_2
    assert "Phonon-2 (recommended)" in output
    assert "Languages: English" in output
    assert "Phonon-2 transcribes English only." in output


def test_model_prompt_rejects_unknown_choice(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(["99", "1"])

    def select_from_answers(prompt: str) -> str:
        return next(answers)

    assert setup.select_model(select_from_answers) == PHONON_2
    assert "Enter the number" in capsys.readouterr().out


def test_setup_downloads_and_saves_catalog_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: FakeBackend
) -> None:
    def fail_if_prompted(prompt: str) -> str:
        raise AssertionError("The model prompt must not run with --model.")

    monkeypatch.setattr(setup, "_ensure_tools", lambda: None)
    selected = setup.run_setup("phonon-2", tmp_path, fail_if_prompted)

    assert selected == PHONON_2
    assert backend.downloads == [PHONON_2]
    assert get_configured_model(tmp_path) == PHONON_2


def test_setup_installs_missing_python_tools_and_ffmpeg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    backend: FakeBackend,
) -> None:
    available = {"uv": "/usr/local/bin/uv", "brew": "/usr/local/bin/brew"}
    commands: list[list[str]] = []

    def fake_which(command: str) -> str | None:
        return available.get(command)

    def fake_installer(command: list[str], failure: str) -> None:
        commands.append(command)

    monkeypatch.setattr(setup.shutil, "which", fake_which)
    monkeypatch.setattr(setup, "_run_installer", fake_installer)
    setup.run_setup("phonon-2", tmp_path)

    assert commands[0][:4] == ["uv", "tool", "install", "--python"]
    assert commands[0][5].startswith("yt-dlp==")
    assert commands[1][-1] == "youtube-transcript-api==1.2.5"
    assert commands[2] == ["brew", "install", "ffmpeg"]
    assert backend.downloads == [PHONON_2]
    assert "Setup is complete." in capsys.readouterr().out


def test_setup_does_not_reinstall_available_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: FakeBackend
) -> None:
    def fail_install(command: list[str], failure: str) -> None:
        raise AssertionError(f"Unexpected installation: {command}")

    def fake_which(command: str) -> str:
        return f"/bin/{command}"

    monkeypatch.setattr(setup.shutil, "which", fake_which)
    monkeypatch.setattr(setup, "_run_installer", fail_install)
    assert setup.run_setup("phonon-2", tmp_path) == PHONON_2
    assert backend.downloads == [PHONON_2]


def test_failed_dependency_setup_does_not_save_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: FakeBackend
) -> None:
    def fail_tools() -> None:
        raise TranscriberError("dependency failed")

    monkeypatch.setattr(setup, "_ensure_tools", fail_tools)
    with pytest.raises(TranscriberError, match="dependency failed"):
        setup.run_setup("phonon-2", tmp_path)
    assert backend.downloads == []
    assert not tmp_path.joinpath("config.json").exists()


def test_failed_model_download_does_not_save_a_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: FakeBackend
) -> None:
    def fail_download(self: FakeBackend, model: object) -> None:
        raise TranscriberError("model download failed")

    monkeypatch.setattr(setup, "_ensure_tools", lambda: None)
    monkeypatch.setattr(FakeBackend, "download", fail_download)
    with pytest.raises(TranscriberError, match="model download failed"):
        setup.run_setup("phonon-2", tmp_path)
    assert not tmp_path.joinpath("config.json").exists()
