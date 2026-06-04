import json
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

from src.config import SHERPA_SEGMENTATION_MODEL, SHERPA_EMBEDDING_MODEL

_diarizer: sherpa_onnx.OfflineSpeakerDiarization | None = None


def _load_diarizer() -> sherpa_onnx.OfflineSpeakerDiarization:
    global _diarizer
    if _diarizer is not None:
        return _diarizer

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=SHERPA_SEGMENTATION_MODEL,
            ),
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=SHERPA_EMBEDDING_MODEL,
        ),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=-1,
            threshold=0.5,
        ),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    _diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
    return _diarizer


def _output_path(audio_path: Path) -> Path:
    stem = audio_path.stem
    return audio_path.with_name(f"{stem}_diarization.json")


def diarize(audio_path: Path) -> Path:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
    audio = audio[:, 0]

    if int(sample_rate) == 48000:
        audio = audio[::3]

    diarizer = _load_diarizer()
    result = diarizer.process(audio.tolist())

    exclusive = []
    for seg in result.sort_by_start_time():
        exclusive.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "speaker": f"SPEAKER_{seg.speaker:02d}",
        })

    output_json = {"exclusive_diarization": exclusive}

    output = _output_path(audio_path)
    output.write_text(json.dumps(output_json, indent=2))
    return output
