"""Shared test objects."""

from pathlib import Path

import pytest

from video_transcriber.media import Media
from video_transcriber.phonon import Segment, Transcript, Word


@pytest.fixture
def media(tmp_path: Path) -> Media:
    return Media(
        original_input="https://example.com/watch?v=abc",
        source_type="url",
        audio_path=tmp_path / "audio.wav",
        title="A test video",
        source_url="https://example.com/watch?v=abc",
        media_id="abc",
        uploader="A channel",
        upload_date="20260102",
        duration_seconds=2.0,
    )


@pytest.fixture
def transcript() -> Transcript:
    return Transcript(
        text="Hello world. This is local.",
        model="FermionResearch/Phonon-2",
        engine="mlx",
        duration_seconds=2.0,
        decode_seconds=0.2,
        wall_seconds=1.0,
        segments=(
            Segment(segment_id=0, start=0.0, end=1.25, text="Hello world."),
            Segment(segment_id=1, start=1.25, end=2.0, text="This is local."),
        ),
        words=(
            Word(text="Hello", start=0.0, end=0.4),
            Word(text="world.", start=0.4, end=1.0),
            Word(text="This", start=1.25, end=1.4),
            Word(text="is", start=1.4, end=1.5),
            Word(text="local.", start=1.5, end=2.0),
        ),
        truncated=False,
    )
