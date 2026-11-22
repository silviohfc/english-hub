"""Central configuration. Everything can be overridden with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DEV_ENGLISH_DATA", ROOT / "data"))
MODELS_DIR = Path(os.getenv("DEV_ENGLISH_MODELS", ROOT / "models"))
DB_PATH = DATA_DIR / "dev_english.sqlite3"
# Neutral working dir for the claude CLI, so it doesn't pick up this repo's CLAUDE.md / memory.
CLAUDE_WORKDIR = DATA_DIR / "claude-work"

# Speech-to-text (faster-whisper). Multilingual model so the "Como se diz?" helper understands Portuguese.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # auto | cuda | cpu
WHISPER_CPU_FALLBACK_MODEL = os.getenv("WHISPER_CPU_FALLBACK_MODEL", "small")

# Text-to-speech (Kokoro, ONNX, runs on CPU).
KOKORO_MODEL = MODELS_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS_DIR / "voices-v1.0.bin"

# LLM via the local Claude Code CLI (uses your Claude subscription, no API key).
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "claude")
CHAT_MODEL = os.getenv("CHAT_MODEL", "haiku")          # fast, for conversation turns
FEEDBACK_MODEL = os.getenv("FEEDBACK_MODEL", "sonnet")  # stronger, for the end-of-session report
HELPER_MODEL = os.getenv("HELPER_MODEL", "haiku")       # "Como se diz?" and retell tips

# Speaking metrics thresholds.
LONG_PAUSE_S = float(os.getenv("LONG_PAUSE_S", "1.2"))
UNCLEAR_PROB = float(os.getenv("UNCLEAR_PROB", "0.45"))

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))

for d in (DATA_DIR, MODELS_DIR, CLAUDE_WORKDIR):
    d.mkdir(parents=True, exist_ok=True)
