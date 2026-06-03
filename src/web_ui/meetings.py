import json
import re
from pathlib import Path

DATA_DIR = Path("data/raw")

STEM_RE = re.compile(r"^meeting_(\d{8}_\d{6})$")


def _meeting_dir(stem: str) -> Path:
    return DATA_DIR / f"meeting_{stem}"


def scan_meetings() -> list[dict]:
    if not DATA_DIR.exists():
        return []

    stems: list[dict] = []
    for f in sorted(DATA_DIR.iterdir(), reverse=True):
        if not f.is_dir():
            continue
        m = STEM_RE.match(f.name)
        if not m:
            continue

        stem = m.group(1)
        meeting_dir = f
        info = {
            "stem": stem,
            "has_wav": (meeting_dir / f"meeting_{stem}.wav").exists(),
            "has_diarization": (
                meeting_dir / f"meeting_{stem}_diarization.json"
            ).exists(),
            "has_transcription": (
                meeting_dir / f"meeting_{stem}_transcription.json"
            ).exists(),
            "has_merged": (meeting_dir / f"meeting_{stem}_merged.json").exists(),
        }
        stems.append(info)

    return stems


def load_merged(stem: str) -> list[dict]:
    path = _meeting_dir(stem) / f"meeting_{stem}_merged.json"
    if not path.exists():
        raise FileNotFoundError(f"Merged file not found: {path}")
    return json.loads(path.read_text())


def load_merged_text(stem: str) -> str:
    path = _meeting_dir(stem) / f"meeting_{stem}_merged.txt"
    if not path.exists():
        raise FileNotFoundError(f"Merged text file not found: {path}")
    return path.read_text()


def load_diarization(stem: str) -> dict:
    path = _meeting_dir(stem) / f"meeting_{stem}_diarization.json"
    if not path.exists():
        raise FileNotFoundError(f"Diarization file not found: {path}")
    return json.loads(path.read_text())


def wav_path(stem: str) -> Path:
    return _meeting_dir(stem) / f"meeting_{stem}.wav"
