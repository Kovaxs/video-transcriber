"""Adapt the local Fermion command to the speech backend port."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

from video_transcriber.errors import TranscriberError
from video_transcriber.models import ModelSpec
from video_transcriber.transcript import Segment, Transcript, Word


class FermionAdapter:
    """Run approved Fermion models and convert their JSON to shared data."""

    def download(self, model: ModelSpec) -> None:
        """Download and verify a model through Fermion."""
        command = [
            _fermion_executable(),
            "transcribe",
            model.backend_name,
            "--download-only",
            "unused.wav",
        ]
        try:
            process = subprocess.run(command, check=False)
        except FileNotFoundError as error:
            raise TranscriberError(
                "The fermion executable is not available."
            ) from error
        if process.returncode != 0:
            raise TranscriberError(f"Could not download {model.display_name}.")

    def transcribe(self, audio_path: Path, model: ModelSpec) -> Transcript:
        """Transcribe a WAV file and return backend-independent data."""
        command = [
            _fermion_executable(),
            "transcribe",
            model.backend_name,
            str(audio_path),
            "--json",
        ]
        try:
            process = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
        except FileNotFoundError as error:
            raise TranscriberError(
                "The fermion executable is not available."
            ) from error
        if process.returncode != 0:
            detail = (
                process.stderr.strip() or process.stdout.strip() or "No error output."
            )
            message = f"{model.display_name} transcription failed.\n{detail}"
            raise TranscriberError(message)
        try:
            value: object = json.loads(process.stdout)
        except json.JSONDecodeError as error:
            raise TranscriberError("The model returned invalid JSON.") from error
        return _parse_transcript(value)


def _fermion_executable() -> str:
    sibling = Path(sys.executable).with_name("fermion")
    if sibling.is_file():
        return str(sibling)
    executable = shutil.which("fermion")
    if executable is None:
        raise TranscriberError(
            "The fermion executable is missing. Install the Python dependencies."
        )
    return executable


def _parse_transcript(value: object) -> Transcript:
    data = _as_object(value, "output")
    segments = tuple(
        _parse_segment(item) for item in _as_array(data.get("segments"), "segments")
    )
    words = tuple(_parse_word(item) for item in _as_array(data.get("words"), "words"))
    truncated = data.get("truncated")
    if not isinstance(truncated, bool):
        raise TranscriberError("The model output has an invalid truncated flag.")
    return Transcript(
        text=_as_string(data.get("text"), "text"),
        model=_as_string(data.get("model"), "model"),
        engine=_as_string(data.get("engine"), "engine"),
        duration_seconds=_as_number(data.get("duration_seconds"), "duration_seconds"),
        decode_seconds=_as_number(data.get("decode_seconds"), "decode_seconds"),
        wall_seconds=_as_number(data.get("wall_seconds"), "wall_seconds"),
        segments=segments,
        words=words,
        truncated=truncated,
    )


def _parse_segment(value: object) -> Segment:
    data = _as_object(value, "segment")
    segment_id = _as_number(data.get("id"), "segment id")
    if not segment_id.is_integer():
        raise TranscriberError("The model output has an invalid segment ID.")
    return Segment(
        segment_id=int(segment_id),
        start=_as_number(data.get("start"), "segment start"),
        end=_as_number(data.get("end"), "segment end"),
        text=_as_string(data.get("text"), "segment text"),
    )


def _parse_word(value: object) -> Word:
    data = _as_object(value, "word")
    return Word(
        text=_as_string(data.get("text"), "word text"),
        start=_as_number(data.get("start"), "word start"),
        end=_as_number(data.get("end"), "word end"),
    )


def _as_object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TranscriberError(f"The model {context} is not a JSON object.")
    if not all(isinstance(key, str) for key in cast(dict[object, object], value)):
        raise TranscriberError(f"The model {context} has a non-string key.")
    return cast(dict[str, object], value)


def _as_array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise TranscriberError(f"The model {context} is not a JSON array.")
    return cast(list[object], value)


def _as_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise TranscriberError(f"The model {context} is not a string.")
    return value


def _as_number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TranscriberError(f"The model {context} is not a number.")
    return float(value)
