"""Tests for all transcript output formats."""

import json

from video_transcriber.formats import render_transcript
from video_transcriber.media import Media
from video_transcriber.transcript import Transcript


def test_txt_output(transcript: Transcript, media: Media) -> None:
    assert render_transcript(transcript, media, "txt") == (
        "Hello world. This is local.\n"
    )


def test_srt_output(transcript: Transcript, media: Media) -> None:
    assert render_transcript(transcript, media, "srt") == (
        "1\n00:00:00,000 --> 00:00:01,250\nHello world.\n\n"
        "2\n00:00:01,250 --> 00:00:02,000\nThis is local.\n"
    )


def test_vtt_output(transcript: Transcript, media: Media) -> None:
    assert render_transcript(transcript, media, "vtt") == (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:01.250\nHello world.\n\n"
        "00:00:01.250 --> 00:00:02.000\nThis is local.\n"
    )


def test_json_output_has_source_segments_and_words(
    transcript: Transcript, media: Media
) -> None:
    rendered: object = json.loads(render_transcript(transcript, media, "json"))
    assert isinstance(rendered, dict)
    assert rendered["text"] == transcript.text
    assert rendered["source"] == {
        "input": media.original_input,
        "type": "url",
        "url": media.source_url,
        "title": media.title,
        "id": media.media_id,
        "uploader": media.uploader,
        "upload_date": media.upload_date,
        "duration_seconds": media.duration_seconds,
    }
    assert rendered["segments"] == [
        {"id": 0, "start": 0.0, "end": 1.25, "text": "Hello world."},
        {"id": 1, "start": 1.25, "end": 2.0, "text": "This is local."},
    ]
    assert rendered["words"][0] == {"text": "Hello", "start": 0.0, "end": 0.4}
    assert rendered["truncated"] is False
