"""Central configuration.

Defaults come from environment variables; what the user picks on the setup / settings screen is
saved in data/settings.json and wins over them (see EDITABLE and apply())."""
import json
import os
from pathlib import Path

APP_NAME = "english-hub"
ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default=None):
    """ENGLISH_HUB_<name>, falling back to the old DEV_ENGLISH_<name>."""
    return os.getenv("ENGLISH_HUB_" + name) or os.getenv("DEV_ENGLISH_" + name) or default


DATA_DIR = Path(_env("DATA", ROOT / "data"))
MODELS_DIR = Path(_env("MODELS", ROOT / "models"))
DB_PATH = DATA_DIR / "english_hub.sqlite3"
_OLD_DB = DATA_DIR / "dev_english.sqlite3"
# Neutral working dir for the claude CLI, so it doesn't pick up this repo's CLAUDE.md / memory.
CLAUDE_WORKDIR = DATA_DIR / "claude-work"

# Speech-to-text (faster-whisper). Multilingual model so the "Como se diz?" helper understands Portuguese.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # auto | cuda | mps (macOS) | cpu
WHISPER_CPU_FALLBACK_MODEL = os.getenv("WHISPER_CPU_FALLBACK_MODEL", "small")
# auto: float16 on big GPUs, int8_float16 on <= 6 GB GPUs (e.g. GTX 1650). Or force one.
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "auto")
# CPU threads for Whisper on CPU: physical cores (e.g. 6 on an i5-11400H), leaving SMT siblings
# for Kokoro TTS and the browser.
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", str(max(1, (os.cpu_count() or 2) // 2))))

# Text-to-speech (Kokoro, ONNX, runs on CPU).
KOKORO_MODEL = MODELS_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS_DIR / "voices-v1.0.bin"

# LLM via a local CLI and the user's own plan: claude (Claude Code), gemini (Antigravity CLI) or codex (Codex CLI).
# Each role picks a provider and a model ("" = the provider's default model).
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "claude")
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "claude")
FEEDBACK_PROVIDER = os.getenv("FEEDBACK_PROVIDER", "claude")
HELPER_PROVIDER = os.getenv("HELPER_PROVIDER", "claude")
CHAT_MODEL = os.getenv("CHAT_MODEL", "haiku")          # fast, for conversation turns
FEEDBACK_MODEL = os.getenv("FEEDBACK_MODEL", "sonnet")  # stronger, for the end-of-session report
HELPER_MODEL = os.getenv("HELPER_MODEL", "haiku")       # "Como se diz?" and retell tips

# What the learner practises for: "dev" (international developer jobs) or "daily" (everyday English).
TRACK = os.getenv("TRACK", "dev")

# Speaking metrics thresholds.
LONG_PAUSE_S = float(os.getenv("LONG_PAUSE_S", "1.2"))
UNCLEAR_PROB = float(os.getenv("UNCLEAR_PROB", "0.45"))

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))

for d in (DATA_DIR, MODELS_DIR, CLAUDE_WORKDIR):
    d.mkdir(parents=True, exist_ok=True)
if _OLD_DB.exists() and not DB_PATH.exists():  # renamed from dev-english
    _OLD_DB.rename(DB_PATH)

# ---------------------------------------------------------------------------------------------
# Settings editable from the UI: name -> (module attribute, type). Saved in data/settings.json.
# ---------------------------------------------------------------------------------------------
SETTINGS_PATH = DATA_DIR / "settings.json"
EDITABLE = {
    "whisper_model": ("WHISPER_MODEL", str),
    "whisper_device": ("WHISPER_DEVICE", str),
    "whisper_compute": ("WHISPER_COMPUTE", str),
    "whisper_cpu_fallback_model": ("WHISPER_CPU_FALLBACK_MODEL", str),
    "whisper_cpu_threads": ("WHISPER_CPU_THREADS", int),
    "chat_provider": ("CHAT_PROVIDER", str),
    "feedback_provider": ("FEEDBACK_PROVIDER", str),
    "helper_provider": ("HELPER_PROVIDER", str),
    "track": ("TRACK", str),
    "chat_model": ("CHAT_MODEL", str),
    "feedback_model": ("FEEDBACK_MODEL", str),
    "helper_model": ("HELPER_MODEL", str),
}
FLAGS = ("setup_done", "onboarding_done")


def _read_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def current() -> dict:
    """Effective values of every editable setting plus the first-run flags."""
    saved = _read_settings()
    out = {k: globals()[attr] for k, (attr, _) in EDITABLE.items()}
    out.update({f: bool(saved.get(f)) for f in FLAGS})
    return out


def role(name: str) -> tuple[str, str]:
    """(provider, model) for a role: chat | feedback | helper."""
    return globals()[name.upper() + "_PROVIDER"], globals()[name.upper() + "_MODEL"]


VALID = {"track": {"dev", "daily"}, "chat_provider": {"claude", "gemini", "codex"},
         "feedback_provider": {"claude", "gemini", "codex"}, "helper_provider": {"claude", "gemini", "codex"}}


def apply(values: dict) -> dict:
    """Validate, apply to this module and persist. Unknown keys are ignored."""
    for k, allowed in VALID.items():
        if k in values and values[k] not in allowed:
            raise ValueError(f"{k}={values[k]!r}")
    saved = _read_settings()
    for k, v in values.items():
        if k in EDITABLE:
            attr, typ = EDITABLE[k]
            v = typ(v)
            globals()[attr] = v
            saved[k] = v
        elif k in FLAGS:
            saved[k] = bool(v)
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)
    return current()


for _k, _v in _read_settings().items():
    if _k in EDITABLE:
        try:
            globals()[EDITABLE[_k][0]] = EDITABLE[_k][1](_v)
        except (TypeError, ValueError):
            pass
