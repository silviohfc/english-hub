"""Speech-to-text with faster-whisper, plus word-level timing/confidence for speaking metrics."""
from __future__ import annotations

import io
import logging
import os
import sys
import threading
from pathlib import Path

from . import config

log = logging.getLogger("stt")

# Encourage Whisper to transcribe hesitations instead of silently dropping them.
_EN_PROMPT = "Um, so, uh, I think... well, you know, I mean, like, I worked on the backend."


def _add_cuda_dll_dirs() -> None:
    """On Windows, ctranslate2 needs cuBLAS/cuDNN DLLs on the search path. The pip
    packages nvidia-cublas-cu12 / nvidia-cudnn-cu12 ship them under site-packages/nvidia."""
    if sys.platform != "win32":
        return
    for base in map(Path, sys.path):
        nvidia = base / "nvidia"
        if not nvidia.is_dir():
            continue
        for sub in ("cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"):
            bin_dir = nvidia / sub / "bin"
            if bin_dir.is_dir():
                os.add_dll_directory(str(bin_dir))
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")


def decode_audio(data: bytes, sr: int = 16000):
    """Decode any browser/container audio (webm/opus, wav, ...) to 16 kHz mono float32 with PyAV."""
    import av
    import numpy as np

    chunks = []
    with av.open(io.BytesIO(data), mode="r") as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=sr)
        for frame in container.decode(audio=0):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype="float32")
    return np.concatenate(chunks).astype("float32") / 32768.0


class STT:
    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self.device = None
        self.model_name = None

    def load(self) -> None:
        if self._model is not None:
            return
        _add_cuda_dll_dirs()
        from faster_whisper import WhisperModel

        attempts = []
        if config.WHISPER_DEVICE in ("auto", "cuda"):
            attempts.append(("cuda", "float16", config.WHISPER_MODEL))
        if config.WHISPER_DEVICE in ("auto", "cpu"):
            attempts.append(("cpu", "int8", config.WHISPER_CPU_FALLBACK_MODEL))

        last_err = None
        for device, compute, name in attempts:
            try:
                log.info("Loading Whisper %s on %s (%s)...", name, device, compute)
                model = WhisperModel(name, device=device, compute_type=compute,
                                     download_root=str(config.MODELS_DIR / "whisper"))
                # Warm-up forces CUDA libs to load now, so failures fall back to CPU here.
                import numpy as np
                list(model.transcribe(np.zeros(16000, dtype="float32"), language="en")[0])
                self._model, self.device, self.model_name = model, device, name
                log.info("Whisper ready on %s.", device)
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning("Whisper on %s failed: %s", device, e)
        raise RuntimeError(f"Could not load Whisper: {last_err}")

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        """Returns {text, words:[{w,start,end,p}], duration}."""
        self.load()
        audio = decode_audio(audio_bytes)
        if audio.size < 1600:  # < 0.1 s
            return {"text": "", "words": [], "duration": 0}
        with self._lock:
            segments, info = self._model.transcribe(
                audio,
                language=language,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 700},
                initial_prompt=_EN_PROMPT if language == "en" else None,
                condition_on_previous_text=False,
                beam_size=5,
            )
            words, texts = [], []
            for seg in segments:
                texts.append(seg.text.strip())
                for w in seg.words or []:
                    words.append({"w": w.word.strip(), "start": round(w.start, 2),
                                  "end": round(w.end, 2), "p": round(w.probability, 3)})
        return {"text": " ".join(t for t in texts if t), "words": words,
                "duration": round(info.duration, 2)}


stt = STT()
