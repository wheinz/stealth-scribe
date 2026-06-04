import os

from dotenv import load_dotenv

load_dotenv()

SHERPA_SEGMENTATION_MODEL = os.environ.get(
    "SHERPA_SEGMENTATION_MODEL",
    "models/sherpa-onnx-pyannote-segmentation-3-0/model.int8.onnx",
)
SHERPA_EMBEDDING_MODEL = os.environ.get(
    "SHERPA_EMBEDDING_MODEL",
    "models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
)
WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "")
WHISPER_SERVER_URL = os.environ.get("WHISPER_SERVER_URL", "http://localhost:8080")
TIMEZONE = os.environ.get("TIMEZONE", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
