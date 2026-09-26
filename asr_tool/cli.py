"""
Command-line interface for the ASR tool.

Usage:
    python -m asr_tool.cli transcribe path/to/audio.wav
    python -m asr_tool.cli transcribe path/to/audio.mp3 --backend whisper
    python -m asr_tool.cli mic --duration 5
    python -m asr_tool.cli transcribe audio.wav --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from asr_tool.engine import ASRError, transcribe_file
from asr_tool.audio_utils import AudioUtilsError, convert_to_wav, record_from_microphone


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asr-tool",
        description="Transcribe speech to text from audio files or the microphone.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- transcribe ---
    t = subparsers.add_parser("transcribe", help="Transcribe an audio file")
    t.add_argument("audio_path", help="Path to an audio file (wav/mp3/flac/m4a/...)")
    t.add_argument(
        "--backend", default="sphinx", choices=["sphinx", "google", "whisper"],
        help="Recognition engine to use (default: sphinx, fully offline)",
    )
    t.add_argument("--language", default="en-US", help="Language code, e.g. en-US, fr-FR")
    t.add_argument(
        "--model-size", default="base",
        help="Model size for the whisper backend (tiny/base/small/medium/large)",
    )
    t.add_argument("--json", action="store_true", help="Print result as JSON")
    t.add_argument(
        "--no-convert", action="store_true",
        help="Skip automatic conversion to 16kHz mono WAV (assumes input is already WAV)",
    )

    # --- mic ---
    m = subparsers.add_parser("mic", help="Record from microphone and transcribe")
    m.add_argument("--duration", type=int, default=None, help="Max recording seconds")
    m.add_argument(
        "--backend", default="sphinx", choices=["sphinx", "google", "whisper"],
        help="Recognition engine to use (default: sphinx, fully offline)",
    )
    m.add_argument("--language", default="en-US", help="Language code, e.g. en-US")
    m.add_argument("--save", default=None, help="Optional path to save the captured WAV")

    return parser


def _resolve_audio_path(audio_path: str, no_convert: bool) -> str:
    path = Path(audio_path)
    if no_convert or path.suffix.lower() == ".wav":
        return str(path)
    return convert_to_wav(str(path))


def cmd_transcribe(args: argparse.Namespace) -> int:
    try:
        wav_path = _resolve_audio_path(args.audio_path, args.no_convert)
        backend_kwargs = {"model_size": args.model_size} if args.backend == "whisper" else None
        result = transcribe_file(
            wav_path,
            backend=args.backend,
            language=args.language,
            backend_kwargs=backend_kwargs,
        )
    except (ASRError, AudioUtilsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.text)
    return 0


def cmd_mic(args: argparse.Namespace) -> int:
    try:
        wav_path = record_from_microphone(
            duration=args.duration,
            output_path=args.save or "mic_capture.wav",
        )
        result = transcribe_file(wav_path, backend=args.backend, language=args.language)
    except (ASRError, AudioUtilsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if not args.save:
            Path("mic_capture.wav").unlink(missing_ok=True)

    print(result.text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "transcribe":
        return cmd_transcribe(args)
    if args.command == "mic":
        return cmd_mic(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
