"""Provide a speech backend test double with no model or network access."""

from dataclasses import dataclass, field
from pathlib import Path

from video_transcriber.models import ModelSpec
from video_transcriber.transcript import Transcript


@dataclass
class FakeBackend:
    """Record port calls and return a preset transcript."""

    result: Transcript
    downloads: list[ModelSpec] = field(default_factory=list[ModelSpec])
    transcriptions: list[tuple[Path, ModelSpec]] = field(
        default_factory=list[tuple[Path, ModelSpec]]
    )

    def download(self, model: ModelSpec) -> None:
        """Record a model download without external work."""
        self.downloads.append(model)

    def transcribe(self, audio_path: Path, model: ModelSpec) -> Transcript:
        """Record a transcription and return the test result."""
        self.transcriptions.append((audio_path, model))
        return self.result
