"""Orpheus 3B text-to-speech worker.

Runs inside Orpheus's own Python environment (models/engines/orpheus/.venv, see app/voices.py), never inside the
app's: it only needs llama-cpp-python (GGUF on Metal or CUDA), onnxruntime (SNAC audio decoder) and numpy.

Protocol (JSON lines):
  -> {"id", "text", "voice"}             synthesize, streaming the audio back as it is generated
  -> {"cancel": id}                      stop that request early (the learner interrupted)
  <- {"ready": true, "gpu": bool}        once the model is loaded
  <- {"id", "pcm": base64}               16-bit mono PCM at 24 kHz, in order
  <- {"id", "done": true, "seconds", "took", "tps"} or {"id", "error"}
Library chatter goes to stderr so stdout stays clean for the protocol.

Speed: tokens are read as ids (no detokenizing), and SNAC decodes blocks of frames in a second thread while the
model keeps generating, instead of one 4-frame window per frame.
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import queue
import re
import sys
import threading
import time

SR = 24_000
FRAME = 2048            # samples per SNAC frame (7 audio tokens)
AUDIO_BASE = 128266     # id of <custom_token_10>, the first audio code
# Before the audio the model emits start_of_ai / start_of_speech. After it, it closes its turn and starts a new one
# (end_of_speech, end_of_ai, start_of_human, text...) that can speak the same line again: once audio has begun, any
# non-audio token ends the line.
EOS = {128009, 128001}
BLOCKS = (3, 6, 8)      # frames per decoded block (~85 ms each): small first so playback starts early, then steady


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
    SAMPLING = {"top_k": 40, "top_p": 0.9, "min_p": 0.05, "temp": 0.6, "repeat_penalty": 1.1}

    def __init__(self, model: str, snac: str, gpu_layers: int, penalty_window: int = 64) -> None:
        import llama_cpp
        import onnxruntime

        self.gpu = bool(llama_cpp.llama_supports_gpu_offload()) and gpu_layers != 0
        self.llm = llama_cpp.Llama(model_path=model, n_ctx=4096, n_gpu_layers=gpu_layers, verbose=False, n_batch=512,
                                   last_n_tokens_size=penalty_window)
        self.sampling = dict(self.SAMPLING)
        opts = onnxruntime.SessionOptions()
        opts.intra_op_num_threads = max(2, (os.cpu_count() or 4) // 2)
        self.snac = onnxruntime.InferenceSession(snac, sess_options=opts, providers=["CPUExecutionProvider"])
        self.snac_inputs = [i.name for i in self.snac.get_inputs()]

    def _decode(self, frames: list[list[int]]):
        import numpy as np

        c0, c1, c2 = [], [], []
        for f in frames:
            c0.append(f[0])
            c1 += [f[1], f[4]]
            c2 += [f[2], f[3], f[5], f[6]]
        codes = [np.array([c], dtype=np.int64) for c in (c0, c1, c2)]
        audio = self.snac.run(None, dict(zip(self.snac_inputs, codes)))[0][0, 0]
        return np.clip(audio * 32767, -32768, 32767).astype(np.int16)

    def stream(self, text: str, voice: str, cancelled):
        """Yield PCM chunks (int16 arrays) for `text` while it is being generated."""
        prompt = self.llm.tokenize(f"<|audio|>{voice}: {text}<|eot_id|><custom_token_4>".encode(),
                                   add_bos=True, special=True)
        # ~84 tokens per second of speech; allow about twice the expected length (laughs, slow speakers), never a rerun.
        spoken = len(re.sub(r"<[^>]+>", "", text))
        max_tokens = int(84 * (2.5 + 2 * spoken / 13))
        frames: list[list[int]] = []
        state = {"done": False, "error": None, "tokens": 0}
        lock = threading.Lock()

        def generate():
            cur: list[int] = []
            try:
                for n, tok in enumerate(self.llm.generate(prompt, reset=True, **self.sampling)):
                    state["tokens"] = n + 1
                    if n >= max_tokens or cancelled():
                        break
                    if tok < AUDIO_BASE:
                        if tok in EOS or frames or cur:
                            break
                        continue
                    code = tok - AUDIO_BASE - len(cur) * 4096
                    if not 0 <= code < 4096:
                        continue  # not an audio code (or out of place): skip it like the reference decoder
                    cur.append(code)
                    if len(cur) == 7:
                        with lock:
                            frames.append(cur)
                        cur = []
            except Exception as e:  # noqa: BLE001
                state["error"] = e
            state["done"] = True

        t = threading.Thread(target=generate, daemon=True)
        t.start()
        emitted, block = 0, 0
        while True:
            with lock:
                n = len(frames)
            finished = state["done"]
            size = BLOCKS[min(block, len(BLOCKS) - 1)]
            # A block of frames [emitted, end) needs 1 frame of context on the left and 2 on the right.
            end = n if finished else min(n - 2, emitted + size)
            if end - emitted >= (1 if finished else size):
                left = 1 if emitted else 0
                right = min(2, n - end)
                with lock:
                    window = frames[emitted - left:end + right]
                pcm = self._decode(window)
                yield pcm[left * FRAME:(left + end - emitted) * FRAME]
                emitted, block = end, block + 1
                continue
            if finished:
                break
            time.sleep(0.01)
        t.join()
        if state["error"]:
            raise state["error"]
        if not emitted and not cancelled():
            raise RuntimeError("o Orpheus não gerou áudio para esse texto")
        self.last_tokens = state["tokens"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--snac", required=True)
    ap.add_argument("--gpu-layers", type=int, default=-1)
    args = ap.parse_args()
    proto = _protocol_stream()
    out_lock = threading.Lock()

    def say(obj: dict) -> None:
        with out_lock:
            proto.write(json.dumps(obj) + "\n")
            proto.flush()

    try:
        _cuda_dlls()
        engine = Orpheus(args.model, args.snac, args.gpu_layers)
    except Exception as e:  # noqa: BLE001
        say({"ready": False, "error": f"{type(e).__name__}: {e}"})
        return
    say({"ready": True, "gpu": engine.gpu})

    # stdin is read in its own thread so a cancel can arrive while a request is being generated.
    jobs: queue.Queue = queue.Queue()
    cancels: set = set()

    def reader():
        for line in sys.stdin:
            if not line.strip():
                continue
            msg = json.loads(line)
            if "cancel" in msg:
                cancels.add(msg["cancel"])
            else:
                jobs.put(msg)
        jobs.put(None)

    threading.Thread(target=reader, daemon=True).start()
    while (req := jobs.get()) is not None:
        rid = req.get("id")
        if rid in cancels:
            say({"id": rid, "done": True, "seconds": 0, "took": 0, "tps": 0, "cancelled": True})
            continue
        t0, samples = time.time(), 0
        try:
            for pcm in engine.stream(req["text"], req["voice"], lambda: rid in cancels):
                samples += len(pcm)
                say({"id": rid, "pcm": base64.b64encode(pcm.tobytes()).decode()})
            took = time.time() - t0
            say({"id": rid, "done": True, "seconds": round(samples / SR, 2), "took": round(took, 2),
                 "tps": round(getattr(engine, "last_tokens", 0) / max(took, 0.01), 1), "cancelled": rid in cancels})
        except Exception as e:  # noqa: BLE001
            say({"id": rid, "error": f"{type(e).__name__}: {e}"})
        cancels.discard(rid)


if __name__ == "__main__":
    main()
