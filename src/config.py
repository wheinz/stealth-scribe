import os

from dotenv import load_dotenv

load_dotenv()

PYANNOTE_AUTH_TOKEN = os.environ.get("PYANNOTE_AUTH_TOKEN", "")
PYANNOTE_DIARIZATION_MODEL = os.environ.get(
    "PYANNOTE_DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1"
)
WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "")
WHISPER_SERVER_URL = os.environ.get("WHISPER_SERVER_URL", "http://localhost:8080")
TIMEZONE = os.environ.get("TIMEZONE", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
