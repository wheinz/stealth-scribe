import json
from pathlib import Path


def _load_diarization(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["exclusive_diarization"]


def _load_transcription(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def _overlap(t_start: float, t_end: float, s_start: float, s_end: float) -> float:
    return max(0.0, min(t_end, s_end) - max(t_start, s_start))


def _assign_speakers(
    transcription: list[dict], speaker_segments: list[dict]
) -> list[dict]:
    merged = []

    for tseg in transcription:
        best_speaker = None
        best_overlap = 0.0

        for sseg in speaker_segments:
            overlap = _overlap(tseg["start"], tseg["end"], sseg["start"], sseg["end"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = sseg["speaker"]

        merged.append(
            {
                "start": tseg["start"],
                "end": tseg["end"],
                "speaker": best_speaker,
                "text": tseg["text"],
            }
        )

    return merged


def _merge_adjacent(segments: list[dict]) -> list[dict]:
    if not segments:
        return []

    result = [segments[0].copy()]

    for seg in segments[1:]:
        prev = result[-1]
        if prev["speaker"] == seg["speaker"]:
            prev["end"] = seg["end"]
            prev["text"] += " " + seg["text"]
        else:
            result.append(seg.copy())

    return result


def merge(audio_path: Path) -> Path:
    stem = audio_path.stem
    diarization_path = audio_path.with_name(f"{stem}_diarization.json")
    transcription_path = audio_path.with_name(f"{stem}_transcription.json")

    if not diarization_path.exists():
        raise FileNotFoundError(f"Diarization file not found: {diarization_path}")
    if not transcription_path.exists():
        raise FileNotFoundError(f"Transcription file not found: {transcription_path}")

    speaker_segments = _load_diarization(diarization_path)
    transcription = _load_transcription(transcription_path)

    assigned = _assign_speakers(transcription, speaker_segments)
    merged = _merge_adjacent(assigned)

    json_path = audio_path.with_name(f"{stem}_merged.json")
    json_path.write_text(json.dumps(merged, indent=2))

    txt_path = audio_path.with_name(f"{stem}_merged.txt")
    lines = [f"{seg['speaker']}: {seg['text']}" for seg in merged if seg["speaker"]]
    txt_path.write_text("\n".join(lines) + "\n")

    return json_path
