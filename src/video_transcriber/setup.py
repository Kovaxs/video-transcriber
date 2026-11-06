"""Install dependencies and download a maintainer-approved speech model."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

from video_transcriber.backends import get_backend
from video_transcriber.errors import TranscriberError
from video_transcriber.models import (
    SUPPORTED_MODELS,
    ModelSpec,
    default_model,
    get_model,
    save_selected_model,
)


def select_model(input_fn: Callable[[str], str]) -> ModelSpec:
    """Ask the user to select a model from the supported catalog."""
    print("Supported speech recognition models:")
    for index, model in enumerate(SUPPORTED_MODELS, start=1):
        languages = ", ".join(language.name for language in model.languages)
        recommendation = " (recommended)" if model.recommended else ""
        print(
            f"{index}. {model.display_name}{recommendation}\n"
            f"   Languages: {languages}\n"
            f"   Download: {model.download_size_mb} MB"
        )
    if len(SUPPORTED_MODELS) == 1 and len(SUPPORTED_MODELS[0].languages) == 1:
        model = SUPPORTED_MODELS[0]
        print(f"{model.display_name} transcribes {model.languages[0].name} only.")

    default_index = SUPPORTED_MODELS.index(default_model()) + 1
    while True:
        try:
            answer = input_fn(f"Select a model [{default_index}]: ").strip()
        except EOFError as error:
            model_id = default_model().model_id
            raise TranscriberError(
                f"Model selection needs a terminal. Use setup --model {model_id}."
            ) from error
        if not answer:
            return default_model()
        try:
            index = int(answer)
        except ValueError:
            index = 0
        if 1 <= index <= len(SUPPORTED_MODELS):
            return SUPPORTED_MODELS[index - 1]
        print("Enter the number of a supported model.")


def run_setup(
    model_id: str | None = None,
    config_dir: Path | None = None,
    input_fn: Callable[[str], str] = input,
) -> ModelSpec:
    """Install setup requirements, download a model, and save the selection."""
    model = get_model(model_id) if model_id is not None else select_model(input_fn)
    backend = get_backend(model.backend)
    print(f"Selected model: {model.display_name}")
    _ensure_tools()
    print(f"Downloading {model.display_name}. A cached model needs no download.")
    backend.download(model)
    config_path = save_selected_model(model, config_dir)
    print(f"Saved the model selection to {config_path}")
    print("Setup is complete.")
    return model


def _ensure_tools() -> None:
    if shutil.which("uv") is None:
        raise TranscriberError(
            "uv is missing. Install it from https://docs.astral.sh/uv/."
        )

    python_tools = (
        ("yt-dlp", f"yt-dlp=={metadata.version('yt-dlp')}"),
        ("youtube_transcript_api", "youtube-transcript-api==1.2.5"),
    )
    for command, package in python_tools:
        if shutil.which(command) is not None:
            print(f"{command} is available.")
            continue
        print(f"Installing {package} with uv tool.")
        _run_installer(
            ["uv", "tool", "install", "--python", "3.12", package],
            f"Could not install {package}",
        )

    if shutil.which("ffmpeg") is not None:
        print("ffmpeg is available.")
        return
    if shutil.which("brew") is None:
        raise TranscriberError(
            "ffmpeg is missing. Install it with your package manager. "
            "Then run setup again."
        )
    print("Installing ffmpeg with Homebrew.")
    _run_installer(["brew", "install", "ffmpeg"], "Could not install ffmpeg")


def _run_installer(command: list[str], failure: str) -> None:
    try:
        process = subprocess.run(command, check=False)
    except FileNotFoundError as error:
        message = f"Required executable is missing: {command[0]}"
        raise TranscriberError(message) from error
    if process.returncode != 0:
        raise TranscriberError(f"{failure}. Review the command output and retry.")
