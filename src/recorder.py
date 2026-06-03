import signal
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sounddevice as sd

from src.config import TIMEZONE

_tz = ZoneInfo(TIMEZONE) if TIMEZONE else None


def record(
    stop_event: threading.Event | None = None,
    output_path: Path | None = None,
) -> Path | None:
    if output_path is None:
        raw_dir = Path("data/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=_tz).strftime("%Y%m%d_%H%M%S")
        meeting_dir = raw_dir / f"meeting_{timestamp}"
        meeting_dir.mkdir(parents=True, exist_ok=True)
        output_path = meeting_dir / f"meeting_{timestamp}.wav"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    import wave

    wav_file = wave.open(str(output_path), "wb")
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(48000)

    if stop_event is None:
        stop_event = threading.Event()

        def handle_signal(signum, frame):
            print("\nStopping recording...")
            stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Audio input status: {status}", flush=True)
        wav_file.writeframes(indata.tobytes())

    print(f"Recording to {output_path}...")
    print("Sample rate: 48000 Hz | Channels: mono | Format: 16-bit PCM")
    if stop_event is not None:
        print("Press Ctrl+C to stop recording.\n")

    try:
        with sd.InputStream(
            samplerate=48000,
            channels=1,
            dtype="int16",
            callback=callback,
        ):
            stop_event.wait()
    except sd.PortAudioError as e:
        print(f"\nError: Could not access microphone — {e}", flush=True)
        output_path.unlink(missing_ok=True)
        return None
    finally:
        wav_file.close()

    duration = wav_file.getnframes() / 48000
    print(f"Recording saved: {output_path} ({duration:.1f}s)")
    return output_path
