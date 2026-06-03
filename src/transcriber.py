import json
from pathlib import Path

import httpx

from src.config import WHISPER_SERVER_URL


def _output_path(audio_path: Path) -> Path:
    stem = audio_path.stem
    return audio_path.with_name(f"{stem}_transcription.json")


def transcribe(audio_path: Path) -> Path:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio_bytes = audio_path.read_bytes()

    with httpx.Client(timeout=None) as client:
        response = client.post(
            f"{WHISPER_SERVER_URL}/inference",
            files={"file": (audio_path.name, audio_bytes, "audio/wav")},
            data={"response_format": "verbose_json"},
        )
        response.raise_for_status()

    result = response.json()

    segments = []
    for seg in result.get("segments", []):
        segments.append(
            {
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
            }
        )

    output = _output_path(audio_path)
    output.write_text(json.dumps(segments, indent=2))
    return output
