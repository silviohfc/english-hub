"""Speech-to-text with faster-whisper, plus word-level timing/confidence for speaking metrics."""
from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from . import config

log = logging.getLogger("stt")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

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


def _gpu_vram_mb() -> int | None:
    """Total VRAM of the first NVIDIA GPU, via nvidia-smi (ships with the driver)."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10, check=False,
                             creationflags=_NO_WINDOW)
        name, mem = out.stdout.splitlines()[0].rsplit(",", 1)
        log.info("GPU: %s (%s MB)", name.strip(), mem.strip())
        return int(mem)
    except Exception:  # noqa: BLE001
        return None


def _cuda_computes() -> list[str]:
    """Entry-level/laptop GPUs (<= 6 GB, e.g. GTX 1650 4 GB) use int8 weights: ~half the VRAM of
    float16 with near-identical accuracy. Bigger GPUs use float16 and fall back to int8."""
    vram = _gpu_vram_mb()
    if vram is not None and vram <= 6144:
        return ["int8_float16", "int8"]
    return ["float16", "int8_float16"]


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
        self.compute = None

    def reset(self) -> None:
        """Forget the loaded model so the next load() picks up changed settings."""
        with self._lock:
            self._model, self.device, self.model_name, self.compute = None, None, None, None

    def _attempts(self) -> list[tuple[str, str, str]]:
        """(device, compute_type, model) to try in order: GPU first, then CPU."""
        gpu = "mps" if sys.platform == "darwin" else "cuda"
        attempts: list[tuple[str, str, str]] = []
        if config.WHISPER_DEVICE in ("auto", gpu):
            if config.WHISPER_COMPUTE != "auto":
                computes = [config.WHISPER_COMPUTE]
            elif gpu == "cuda":
                computes = _cuda_computes()
            else:
                computes = ["float16"]
            attempts += [(gpu, c, config.WHISPER_MODEL) for c in computes]
        if config.WHISPER_DEVICE in ("auto", "cpu"):
            attempts.append(("cpu", "int8", config.WHISPER_CPU_FALLBACK_MODEL))
        return attempts

    def load(self, skip_gpu: bool = False) -> None:
        if self._model is not None:
            return
        _add_cuda_dll_dirs()
        import numpy as np
        from faster_whisper import WhisperModel

        last_err = None
        for device, compute, name in self._attempts():
            if skip_gpu and device != "cpu":
                continue
            try:
                log.info("Loading Whisper %s on %s (%s)...", name, device, compute)
                model = WhisperModel(name, device=device, compute_type=compute,
                                     cpu_threads=config.WHISPER_CPU_THREADS,
                                     download_root=str(config.MODELS_DIR / "whisper"))
                # Warm-up forces GPU libs to load now, so failures fall back here.
                list(model.transcribe(np.zeros(16000, dtype="float32"), language="en")[0])
                self._model, self.device, self.model_name, self.compute = model, device, name, compute
                log.info("Whisper ready on %s (%s).", device, compute)
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning("Whisper on %s (%s) failed: %s", device, compute, e)
        raise RuntimeError(f"Could not load Whisper: {last_err}")

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        """Returns {text, words:[{w,start,end,p}], duration}."""
        self.load()
        audio = decode_audio(audio_bytes)
        if audio.size < 1600:  # < 0.1 s
            return {"text": "", "words": [], "duration": 0}
        with self._lock:
            try:
                return self._transcribe(audio, language)
            except RuntimeError as e:
                # e.g. CUDA out of memory on a 4 GB laptop GPU: move to CPU and keep going.
                if self.device == "cpu":
                    raise
                log.warning("Whisper on %s failed mid-session (%s); switching to CPU.", self.device, e)
                self._model = None
                self.load(skip_gpu=True)
                return self._transcribe(audio, language)

    def _transcribe(self, audio, language: str) -> dict:
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
