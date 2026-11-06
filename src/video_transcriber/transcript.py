"""Define transcript data shared by speech backends and output formats."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """Store the text and time range of one word."""

    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Segment:
    """Store one subtitle-ready transcript segment."""

    segment_id: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    """Store a speech transcript and its timing data."""

    text: str
    model: str
    engine: str
    duration_seconds: float
    decode_seconds: float
    wall_seconds: float
    segments: tuple[Segment, ...]
    words: tuple[Word, ...]
    truncated: bool
