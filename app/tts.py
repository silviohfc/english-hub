"""Local text-to-speech with Kokoro (ONNX)."""
from __future__ import annotations

import io
import logging
import re
import threading

from . import config

log = logging.getLogger("tts")


class TTS:
    def __init__(self) -> None:
        self._k = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self._k is not None:
            return
        if not config.KOKORO_MODEL.exists() or not config.KOKORO_VOICES.exists():
            raise RuntimeError("Kokoro model files missing. Run: uv run python scripts/download_models.py")
        from kokoro_onnx import Kokoro

        log.info("Loading Kokoro TTS...")
        self._k = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))
        log.info("Kokoro ready.")

    def synth(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        import soundfile as sf

        self.load()
        text = re.sub(r"[*_#`]", "", text).strip() or "..."
        lang = "en-gb" if voice.startswith("b") else "en-us"
        with self._lock:
            samples, sr = self._k.create(text, voice=voice, speed=speed, lang=lang)
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV")
        return buf.getvalue()


tts = TTS()
