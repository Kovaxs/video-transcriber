"""Provide the video-transcriber command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import cast

from video_transcriber.backends import get_backend
from video_transcriber.errors import TranscriberError
from video_transcriber.formats import OutputFormat, render_transcript
from video_transcriber.media import prepare_media
from video_transcriber.models import SUPPORTED_MODELS, get_configured_model
from video_transcriber.setup import run_setup


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="video-transcriber",
        description="Transcribe a video URL or a local media file with a local model.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup_parser = subparsers.add_parser(
        "setup", help="Install dependencies and download a supported model."
    )
    setup_parser.add_argument(
        "--model",
        choices=[model.model_id for model in SUPPORTED_MODELS],
        help="Select a supported model without an interactive prompt.",
    )
    subparsers.add_parser("models", help="Print the supported model catalog as JSON.")
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe a URL or local media file."
    )
    transcribe_parser.add_argument("input", help="An HTTP URL or a local file path.")
    transcribe_parser.add_argument(
        "--format",
        choices=["txt", "srt", "vtt", "json"],
        default="txt",
        help="The output format. The default is txt.",
    )
    transcribe_parser.add_argument(
        "--output",
        type=Path,
        help="Write to this file instead of standard output.",
    )
    transcribe_parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Override the audio cache directory.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return its exit code."""
    args = build_parser().parse_args(argv)
    if args.command not in {"setup", "transcribe", "models"}:
        return 2
    try:
        if args.command == "models":
            print(json.dumps([asdict(model) for model in SUPPORTED_MODELS]))
            return 0
        if args.command == "setup":
            run_setup(args.model)
            return 0
        model = get_configured_model()
        backend = get_backend(model.backend)
        print("Preparing audio...", file=sys.stderr)
        media = prepare_media(args.input, args.cache_dir)
        print(f"Transcribing with {model.display_name}...", file=sys.stderr)
        transcript = backend.transcribe(media.audio_path, model)
        rendered = render_transcript(transcript, media, cast(OutputFormat, args.format))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Wrote {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(rendered)
        if transcript.truncated:
            print(
                f"Warning: {model.display_name} truncated at least one audio window.",
                file=sys.stderr,
            )
    except (TranscriberError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
