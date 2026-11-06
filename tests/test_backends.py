"""Test backend registration and application behavior through the speech port."""

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from tests.fakes import FakeBackend
from video_transcriber import backends, cli, models, setup
from video_transcriber.adapters.fermion import FermionAdapter
from video_transcriber.errors import TranscriberError
from video_transcriber.media import Media
from video_transcriber.models import (
    PHONON_2,
    SUPPORTED_MODELS,
    BackendId,
    ModelSpec,
    get_configured_model,
)
from video_transcriber.ports import SpeechBackend
from video_transcriber.transcript import Transcript


def test_fermion_adapter_implements_the_port() -> None:
    backend: SpeechBackend = backends.get_backend(BackendId.FERMION)
    assert isinstance(backend, FermionAdapter)


def test_every_declared_backend_has_an_adapter() -> None:
    for backend_id in BackendId:
        backends.get_backend(backend_id)


def test_every_catalog_model_has_a_registered_backend() -> None:
    for model in SUPPORTED_MODELS:
        backends.get_backend(model.backend)


def test_unregistered_backend_has_a_clear_error() -> None:
    unknown = cast(BackendId, "unregistered")
    with pytest.raises(TranscriberError, match="Unsupported speech backend"):
        backends.get_backend(unknown)


def test_setup_and_cli_use_a_different_adapter_without_vendor_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    media: Media,
    transcript: Transcript,
) -> None:
    # This test-only identifier simulates a future approved backend.
    backend_id = cast(BackendId, "test-backend")
    model = replace(
        PHONON_2,
        model_id="test-model",
        display_name="Test Model",
        backend=backend_id,
        backend_name="vendor-specific-name",
        recommended=False,
    )
    result = replace(transcript, model="test-vendor/model", engine="test-engine")
    fake: SpeechBackend = FakeBackend(result)
    monkeypatch.setattr(
        backends,
        "_BACKENDS",
        {BackendId.FERMION: FermionAdapter(), backend_id: fake},
    )
    catalog = (*SUPPORTED_MODELS, model)
    monkeypatch.setattr(models, "SUPPORTED_MODELS", catalog)
    monkeypatch.setattr(cli, "SUPPORTED_MODELS", catalog)
    monkeypatch.setattr(setup, "_ensure_tools", lambda: None)

    def fake_prepare(source: str, cache_dir: Path | None) -> Media:
        return media

    def fail_fermion(self: FermionAdapter, model: ModelSpec) -> None:
        raise AssertionError("The application must select the test backend.")

    def fail_fermion_transcribe(
        self: FermionAdapter, audio_path: Path, model: ModelSpec
    ) -> Transcript:
        raise AssertionError("The application must select the test backend.")

    monkeypatch.setattr(cli, "prepare_media", fake_prepare)
    monkeypatch.setattr(FermionAdapter, "download", fail_fermion)
    monkeypatch.setattr(FermionAdapter, "transcribe", fail_fermion_transcribe)

    assert cli.main(["setup", "--model", model.model_id]) == 0
    assert get_configured_model() == model
    assert isinstance(fake, FakeBackend)
    assert fake.downloads == [model]
    output = tmp_path / "transcript.json"
    assert (
        cli.main(
            ["transcribe", "video.mp4", "--format", "json", "--output", str(output)]
        )
        == 0
    )
    assert fake.transcriptions == [(media.audio_path, model)]
    value: object = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert value["model"] == result.model
    assert value["engine"] == result.engine
    assert value["words"][0]["text"] == result.words[0].text
    captured = capsys.readouterr()
    assert "Transcribing with Test Model" in captured.err
    assert "Phonon-2" not in captured.err


def test_unregistered_backend_fails_before_dependency_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = replace(PHONON_2, backend=cast(BackendId, "unregistered"))
    monkeypatch.setattr(models, "SUPPORTED_MODELS", (model,))

    def fail_tools() -> None:
        raise AssertionError("No dependencies can install for an unknown backend.")

    monkeypatch.setattr(setup, "_ensure_tools", fail_tools)
    with pytest.raises(TranscriberError, match="Unsupported speech backend"):
        setup.run_setup(model.model_id, tmp_path)
    assert not (tmp_path / "config.json").exists()


def test_unregistered_backend_fails_before_audio_download(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    model = replace(PHONON_2, backend=cast(BackendId, "unregistered"))
    monkeypatch.setattr(cli, "get_configured_model", lambda: model)

    def fail_prepare(source: str, cache_dir: Path | None) -> Media:
        raise AssertionError("No audio can download for an unknown backend.")

    monkeypatch.setattr(cli, "prepare_media", fail_prepare)
    assert cli.main(["transcribe", "video.mp4"]) == 1
    assert "Unsupported speech backend" in capsys.readouterr().err
