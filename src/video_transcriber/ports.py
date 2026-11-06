"""Define the interface that local speech backends must implement."""

from pathlib import Path
from typing import Protocol

from video_transcriber.models import ModelSpec
from video_transcriber.transcript import Transcript


class SpeechBackend(Protocol):
    """Separate model operations from backend commands and packages.

    Adapters report expected model failures with TranscriberError.
    """

    def download(self, model: ModelSpec) -> None:
        """Download and verify model files, or reuse their local cache."""
        ...

    def transcribe(self, audio_path: Path, model: ModelSpec) -> Transcript:
        """Transcribe 16 kHz mono WAV audio locally with word timestamps."""
        ...
