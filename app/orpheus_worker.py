"""Orpheus 3B text-to-speech worker.

Runs inside Orpheus's own Python environment (models/engines/orpheus/.venv, see app/voices.py), never inside the
app's: it only needs llama-cpp-python (GGUF on Metal or CUDA), onnxruntime (SNAC audio decoder) and numpy.

Protocol: JSON lines. The worker prints {"ready": true} once the model is loaded, then for each request
{"id", "text", "voice", "out"} writes a 24 kHz mono WAV to `out` and answers {"id", "ok", "seconds", "took"} or
{"id", "ok": false, "error"}. Library chatter goes to stderr so stdout stays clean for the protocol.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import wave

SR = 24_000
# Orpheus speaks these sounds when they appear in the text.
TAGS = ("laugh", "chuckle", "sigh", "gasp", "groan", "yawn", "cough", "sniffle")


def _protocol_stream():
    """Keep the real stdout for the protocol and send everything else (llama.cpp logs, prints) to stderr."""
    out = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return out


def _cuda_dlls() -> None:
    """On Windows the CUDA runtime comes from the nvidia-* wheels; make their DLLs findable."""
    if sys.platform != "win32":
        return
    for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


class Orpheus:
    def __init__(self, model: str, snac: str, gpu_layers: int) -> None:
        import onnxruntime
        from llama_cpp import Llama

        self.llm = Llama(model_path=model, n_ctx=4096, n_gpu_layers=gpu_layers, verbose=False, n_batch=512)
        self.snac = onnxruntime.InferenceSession(snac, providers=["CPUExecutionProvider"])
        self.snac_inputs = [i.name for i in self.snac.get_inputs()]

    # -- audio tokens --
    @staticmethod
    def _token_id(piece: str, index: int) -> int | None:
        start = piece.rfind("<custom_token_")
        if start < 0 or not piece.endswith(">"):
            return None
        try:
            return int(piece[start + 14:-1]) - 10 - ((index % 7) * 4096)
        except ValueError:
            return None

    def _decode(self, frames: list[int]):
        """SNAC decode of 4 frames (28 codes); returns the samples of the second-to-last frame (sliding window)."""
        import numpy as np

        n = len(frames) // 7
        c0, c1, c2 = [], [], []
        for j in range(n):
            f = frames[7 * j: 7 * j + 7]
            c0.append(f[0])
            c1 += [f[1], f[4]]
            c2 += [f[2], f[3], f[5], f[6]]
        codes = [np.array([c], dtype=np.int64) for c in (c0, c1, c2)]
        if any(((c < 0) | (c > 4096)).any() for c in codes):
            return None
        audio = self.snac.run(None, dict(zip(self.snac_inputs, codes)))[0]
        return audio[0, 0, 2048:4096]

    def synth(self, text: str, voice: str) -> "list":
        import numpy as np

        prompt = f"<|audio|>{voice}: {text}<|eot_id|><custom_token_4>"
        max_tokens = min(3000, 400 + 14 * len(text))  # ~1 s of audio per 84 tokens
        codes: list[int] = []
        chunks = []
        for part in self.llm(prompt, max_tokens=max_tokens, stream=True, temperature=0.6, top_p=0.9, top_k=40,
                             min_p=0.05, repeat_penalty=1.1):
            tok = self._token_id(part["choices"][0]["text"].strip(), len(codes))
            if tok is None or tok <= 0:
                continue
            codes.append(tok)
            if len(codes) % 7 == 0 and len(codes) > 27:
                a = self._decode(codes[-28:])
                if a is not None:
                    chunks.append(a)
        if not chunks:
            raise RuntimeError("o Orpheus não gerou áudio para esse texto")
        audio = np.concatenate(chunks)
        return np.clip(audio * 32767, -32768, 32767).astype(np.int16)


def _write_wav(path: str, samples) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(samples.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--snac", required=True)
    ap.add_argument("--gpu-layers", type=int, default=-1)
    args = ap.parse_args()
    proto = _protocol_stream()

    def say(obj: dict) -> None:
        proto.write(json.dumps(obj) + "\n")
        proto.flush()

    try:
        _cuda_dlls()
        engine = Orpheus(args.model, args.snac, args.gpu_layers)
    except Exception as e:  # noqa: BLE001
        say({"ready": False, "error": f"{type(e).__name__}: {e}"})
        return
    say({"ready": True})
    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        t0 = time.time()
        try:
            samples = engine.synth(req["text"], req["voice"])
            _write_wav(req["out"], samples)
            say({"id": req["id"], "ok": True, "seconds": round(len(samples) / SR, 2), "took": round(time.time() - t0, 2)})
        except Exception as e:  # noqa: BLE001
            say({"id": req.get("id"), "ok": False, "error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    main()
