"""Local text-to-speech with Kokoro (ONNX)."""
from __future__ import annotations

import io
import logging
import re
import threading

from . import config

log = logging.getLogger("tts")
SR = 24_000


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
        # The first synthesis is about twice as slow (graph and phonemizer warm-up): pay it now, not on the first line.
        self._k.create("Hi.", voice="af_heart", speed=1.0, lang="en-us")
        log.info("Kokoro ready.")

    def _create(self, text: str, voice: str, speed: float):
        self.load()
        text = re.sub(r"[*_#`]", "", text).strip() or "..."
        lang = "en-gb" if voice.startswith("b") else "en-us"
        with self._lock:
            return self._k.create(text, voice=voice, speed=speed, lang=lang)

    def synth_pcm(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        """16-bit mono PCM at 24 kHz (Kokoro's native rate), for the streaming player."""
        import numpy as np

        samples, sr = self._create(text, voice, speed)
        if sr != SR:  # never expected; keep the wire format fixed anyway
            idx = np.linspace(0, len(samples) - 1, int(len(samples) * SR / sr))
            samples = np.interp(idx, np.arange(len(samples)), samples)
        return (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()

    def synth(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        import soundfile as sf

        samples, sr = self._create(text, voice, speed)
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV")
        return buf.getvalue()


tts = TTS()
