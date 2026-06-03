import json
import os
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""

from pyannote.audio import Pipeline  # noqa: E402

from src.config import PYANNOTE_AUTH_TOKEN, PYANNOTE_DIARIZATION_MODEL

_pipeline: Pipeline | None = None


def _load_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    if not PYANNOTE_AUTH_TOKEN:
        raise RuntimeError(
            "PYANNOTE_AUTH_TOKEN environment variable is not set. "
            "This token is required to download and use pyannote diarization models."
        )

    _pipeline = Pipeline.from_pretrained(
        PYANNOTE_DIARIZATION_MODEL,
        token=PYANNOTE_AUTH_TOKEN,
    )
    return _pipeline


def _output_path(audio_path: Path) -> Path:
    stem = audio_path.stem
    return audio_path.with_name(f"{stem}_diarization.json")


def diarize(audio_path: Path) -> Path:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    pipeline = _load_pipeline()
    result = pipeline(str(audio_path))

    output = _output_path(audio_path)
    output.write_text(json.dumps(result.serialize(), indent=2))
    return output
