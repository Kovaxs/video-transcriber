"""Define supported speech models and persist the user's selection."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from video_transcriber.errors import TranscriberError


class BackendId(StrEnum):
    """Identify each maintainer-approved local speech backend."""

    FERMION = "fermion"


@dataclass(frozen=True)
class Language:
    """Describe one language that a speech model supports."""

    code: str
    name: str


@dataclass(frozen=True)
class ModelSpec:
    """Describe one maintainer-approved speech recognition model."""

    model_id: str
    display_name: str
    backend: BackendId
    backend_name: str
    languages: tuple[Language, ...]
    download_size_mb: int
    recommended: bool = False


PHONON_2 = ModelSpec(
    model_id="phonon-2",
    display_name="Phonon-2",
    backend=BackendId.FERMION,
    backend_name="phonon-2",
    languages=(Language(code="en", name="English"),),
    download_size_mb=158,
    recommended=True,
)
SUPPORTED_MODELS = (PHONON_2,)


def get_model(model_id: str) -> ModelSpec:
    """Return a supported model by its catalog ID."""
    for model in SUPPORTED_MODELS:
        if model.model_id == model_id:
            return model
    raise TranscriberError(
        f"Unsupported model: {model_id}. Run video-transcriber setup to select a model."
    )


def default_model() -> ModelSpec:
    """Return the recommended model for a new installation."""
    return next(model for model in SUPPORTED_MODELS if model.recommended)


def default_config_dir() -> Path:
    """Return the user configuration directory."""
    configured = os.environ.get("VIDEO_TRANSCRIBER_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser()
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg_config).expanduser() if xdg_config else Path.home() / ".config"
    return root / "video-transcriber"


def get_configured_model(config_dir: Path | None = None) -> ModelSpec:
    """Return the saved model, or the recommended model before setup."""
    config_path = (config_dir or default_config_dir()) / "config.json"
    if not config_path.is_file():
        return default_model()
    try:
        value: object = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TranscriberError(
            f"The model configuration is unreadable: {config_path}"
        ) from error
    if not isinstance(value, dict):
        raise TranscriberError("The model configuration is not a JSON object.")
    model_id = cast(dict[object, object], value).get("model")
    if not isinstance(model_id, str):
        raise TranscriberError("The model configuration does not contain a model ID.")
    return get_model(model_id)


def save_selected_model(model: ModelSpec, config_dir: Path | None = None) -> Path:
    """Save a supported model selection and return the configuration path."""
    get_model(model.model_id)
    directory = config_dir or default_config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    config_path = directory / "config.json"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".config-",
            suffix=".json",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump({"model": model.model_id}, temporary_file, indent=2)
            temporary_file.write("\n")
        temporary_path.replace(config_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return config_path
