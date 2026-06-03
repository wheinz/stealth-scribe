import argparse
import sys
from pathlib import Path

from src.diarizer import diarize
from src.merger import merge
from src.recorder import record
from src.transcriber import transcribe


def _record_command(args: argparse.Namespace) -> None:
    record()


def _diarize_command(args: argparse.Namespace) -> None:
    audio_path = Path(args.audio)
    output = diarize(audio_path)
    print(f"Diarization saved to {output}")


def _transcribe_command(args: argparse.Namespace) -> None:
    audio_path = Path(args.audio)
    output = transcribe(audio_path)
    print(f"Transcription saved to {output}")


def _merge_command(args: argparse.Namespace) -> None:
    audio_path = Path(args.audio)
    json_path = merge(audio_path)
    txt_path = json_path.with_suffix(".txt")
    print(f"Merged JSON saved to {json_path}")
    print(f"Merged text saved to {txt_path}")


def _serve_command(args: argparse.Namespace) -> None:
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.web_ui.settings")
    from django.core.management import execute_from_command_line

    host = args.host
    port = args.port
    execute_from_command_line(["manage.py", "runserver", f"{host}:{port}"])


def main() -> None:
    parser = argparse.ArgumentParser(prog="stealth-scribe")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("record", help="Start recording from microphone")

    diarize_parser = subparsers.add_parser(
        "diarize", help="Run speaker diarization on a WAV file"
    )
    diarize_parser.add_argument(
        "audio", help="Path to the WAV file (e.g. data/raw/meeting_20260602_143000.wav)"
    )

    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe a WAV file via whisper.cpp server"
    )
    transcribe_parser.add_argument(
        "audio", help="Path to the WAV file (e.g. data/raw/meeting_20260602_143000.wav)"
    )

    merge_parser = subparsers.add_parser(
        "merge", help="Merge diarization and transcription into speaker-labeled output"
    )
    merge_parser.add_argument(
        "audio", help="Path to the WAV file (e.g. data/raw/meeting_20260602_143000.wav)"
    )

    serve_parser = subparsers.add_parser("serve", help="Start the web UI server")
    serve_parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "record": _record_command,
        "diarize": _diarize_command,
        "transcribe": _transcribe_command,
        "merge": _merge_command,
        "serve": _serve_command,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
