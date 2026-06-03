import io
import wave
from pathlib import Path

CLIP_DURATION = 5.0


def extract_speaker_clip(
    wav_path: Path, speaker_id: str, segments: list[dict]
) -> bytes | None:
    if not wav_path.exists():
        return None

    speaker_segments = [
        seg for seg in segments if seg.get("speaker") == speaker_id and seg.get("text")
    ]

    if not speaker_segments:
        return None

    seg = speaker_segments[0]
    seg_start = seg["start"]
    seg_end = seg["end"]
    seg_duration = seg_end - seg_start

    if seg_duration <= 0:
        return None

    clip_start = max(seg_start, seg_start + (seg_duration - CLIP_DURATION) / 2)

    with wave.open(str(wav_path), "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()

        total_frames = wf.getnframes()
        frame_start = int(clip_start * sample_rate)
        frame_count = int(CLIP_DURATION * sample_rate)

        frame_start = max(0, min(frame_start, total_frames - 1))
        frame_end = min(frame_start + frame_count, total_frames)
        frame_count = frame_end - frame_start

        wf.setpos(frame_start)
        audio_data = wf.readframes(frame_count)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sampwidth)
        out.setframerate(sample_rate)
        out.writeframes(audio_data)

    return buf.getvalue()
