"""Render transcripts as TXT, SRT, VTT, or JSON."""

from __future__ import annotations

import json
from typing import Literal

from video_transcriber.media import Media
from video_transcriber.transcript import Transcript

OutputFormat = Literal["txt", "srt", "vtt", "json"]


def render_transcript(
    transcript: Transcript, media: Media, output_format: OutputFormat
) -> str:
    """Render one transcript in the requested output format."""
    if output_format == "txt":
        return transcript.text + "\n"
    if output_format == "srt":
        return _render_srt(transcript)
    if output_format == "vtt":
        return _render_vtt(transcript)
    return _render_json(transcript, media)


def _render_srt(transcript: Transcript) -> str:
    cues = [
        f"{index}\n{_timestamp(segment.start, ',')} --> "
        f"{_timestamp(segment.end, ',')}\n{segment.text}"
        for index, segment in enumerate(transcript.segments, start=1)
    ]
    return "\n\n".join(cues) + ("\n" if cues else "")


def _render_vtt(transcript: Transcript) -> str:
    cues = [
        f"{_timestamp(segment.start, '.')} --> {_timestamp(segment.end, '.')}\n"
        f"{segment.text}"
        for segment in transcript.segments
    ]
    return "WEBVTT\n\n" + "\n\n".join(cues) + ("\n" if cues else "")


def _timestamp(seconds: float, separator: str) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _render_json(transcript: Transcript, media: Media) -> str:
    value = {
        "source": {
            "input": media.original_input,
            "type": media.source_type,
            "url": media.source_url,
            "title": media.title,
            "id": media.media_id,
            "uploader": media.uploader,
            "upload_date": media.upload_date,
            "duration_seconds": media.duration_seconds,
        },
        "model": transcript.model,
        "engine": transcript.engine,
        "text": transcript.text,
        "duration_seconds": transcript.duration_seconds,
        "decode_seconds": transcript.decode_seconds,
        "wall_seconds": transcript.wall_seconds,
        "truncated": transcript.truncated,
        "segments": [
            {
                "id": segment.segment_id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for segment in transcript.segments
        ],
        "words": [
            {"text": word.text, "start": word.start, "end": word.end}
            for word in transcript.words
        ],
    }
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
