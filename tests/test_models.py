"""Tests for the supported model catalog and saved selection."""

import json
from pathlib import Path

import pytest

from video_transcriber.errors import TranscriberError
from video_transcriber.models import (
    PHONON_2,
    SUPPORTED_MODELS,
    BackendId,
    default_model,
    get_configured_model,
    get_model,
    save_selected_model,
)


def test_default_model_is_recommended_and_english_only() -> None:
    model = default_model()
    assert model == PHONON_2
    assert model.recommended is True
    assert model.backend is BackendId.FERMION
    assert [(language.code, language.name) for language in model.languages] == [
        ("en", "English")
    ]


def test_get_model_accepts_only_catalog_ids() -> None:
    assert get_model("phonon-2") == PHONON_2
    with pytest.raises(TranscriberError, match="Unsupported model"):
        get_model("arbitrary-model")


def test_save_and_load_selected_model(tmp_path: Path) -> None:
    config_path = save_selected_model(PHONON_2, tmp_path)
    assert get_configured_model(tmp_path) == PHONON_2
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"model": "phonon-2"}
    assert list(tmp_path.glob(".config-*")) == []


def test_missing_configuration_uses_recommended_model(tmp_path: Path) -> None:
    assert get_configured_model(tmp_path) == default_model()


def test_configuration_rejects_model_outside_catalog(tmp_path: Path) -> None:
    tmp_path.joinpath("config.json").write_text(
        json.dumps({"model": "arbitrary-model"}), encoding="utf-8"
    )
    with pytest.raises(TranscriberError, match="Unsupported model"):
        get_configured_model(tmp_path)


def test_catalog_has_one_recommended_model() -> None:
    assert sum(model.recommended for model in SUPPORTED_MODELS) == 1


def test_catalog_has_unique_ids_and_complete_metadata() -> None:
    assert len({model.model_id for model in SUPPORTED_MODELS}) == len(SUPPORTED_MODELS)
    for model in SUPPORTED_MODELS:
        assert model.model_id
        assert model.display_name
        assert isinstance(model.backend, BackendId)
        assert model.backend_name
        assert model.download_size_mb > 0
        assert model.languages
        assert len({language.code for language in model.languages}) == len(
            model.languages
        )
        assert all(language.code and language.name for language in model.languages)
