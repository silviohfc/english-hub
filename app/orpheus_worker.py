"""Orpheus 3B text-to-speech worker.

Runs inside Orpheus's own Python environment (models/engines/orpheus/.venv, see app/voices.py), never inside the
app's: it needs onnxruntime (SNAC audio decoder) and numpy, plus one way to run the GGUF model:
  - llama.cpp's own `llama-server` (--server): current CUDA kernels, and two lines generated at once in one batch,
    so the next sentence is ready while this one plays (each runs at almost full speed: decoding is bound by
    memory bandwidth, not by the batch size).
  - llama-cpp-python in this process (fallback, and on the Mac): one line at a time.

Protocol (JSON lines):
  -> {"id", "text", "voice"}             synthesize, streaming the audio back as it is generated
  -> {"cancel": id}                      stop that request early (the learner interrupted)
  <- {"ready": true, "gpu": bool, "slots": n}   once the model is loaded
  <- {"id", "pcm": base64}               16-bit mono PCM at 24 kHz, in order
  <- {"id", "done": true, "seconds", "took", "tps", "events"} or {"id", "error", "events"}
"events" is the request's timeline for the app's telemetry (app/telemetry.py): [{"ts": epoch ms, "name", ...}]
(received, queue wait, first token, each decoded block, voice onset, llama-server timings). The ready message
carries the load timeline the same way.
Requests are served `slots` at a time, in arrival order. Library chatter goes to stderr so stdout stays clean.

Speed: tokens are read as ids (no detokenizing), and SNAC decodes blocks of frames in a second thread while the
model keeps generating. Blocks stay small until the voice starts (the model opens every line with ~0.5 s of
silence, which is trimmed later), so the first syllable is sent as soon as it exists.
"""
from __future__ import annotations

import argparse
import base64
import glob
import http.client
import json
import os
import queue
import re
import socket
import subprocess
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
# Frames per decoded block (~85 ms each): small first so playback starts early, then growing gently (each block
# must arrive before the audio already queued runs out), then steady.
BLOCKS = (3, 4, 6, 8)
VOICED = 0.012 * 32768  # |sample| above which a block has voice (same threshold as the app's silence trimmer)
SAMPLING = {"top_k": 40, "top_p": 0.9, "min_p": 0.05, "temperature": 0.6, "repeat_penalty": 1.1, "repeat_last_n": 64}
SLOT_CTX = 3072         # tokens per line: prompt + ~36 s of speech


def now_ms() -> float:
    return round(time.time() * 1000, 2)


BOOT: list[dict] = []  # load timeline, sent with the ready message


def _boot(name: str, t0: float, **kw) -> None:
    BOOT.append({"ts": t0, "dur": round(now_ms() - t0, 2), "name": name, **kw})


def _protocol_stream():
    """Keep the real stdout for the protocol and send everything else (llama.cpp logs, prints) to stderr."""
    out = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return out


def _cuda_dlls() -> None:
    """On Windows the CUDA runtime comes from the nvidia-* wheels; make their DLLs findable (also for llama-server,
    which inherits PATH)."""
    if sys.platform != "win32":
        return
    for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


def _die_with_me(proc: subprocess.Popen):
    """Windows: put `proc` in a job that is closed (and the process killed) when this process ends, however it
    ends. Returns the job handle, which must stay open."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = k32.CreateJobObjectW(None, None)
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))  # JobObjectExtendedLimitInformation
    k32.AssignProcessToJobObject(job, wintypes.HANDLE(int(proc._handle)))
    return job


# ---------------------------------------------------------------------------------------------
# backends: turn a prompt into a stream of token ids
# ---------------------------------------------------------------------------------------------
class LocalLlama:
    """llama-cpp-python in this process: one line at a time."""
    slots = 1

    def __init__(self, model: str, gpu_layers: int) -> None:
        t0 = now_ms()
        import llama_cpp

        self.gpu = bool(llama_cpp.llama_supports_gpu_offload()) and gpu_layers != 0
        self.llm = llama_cpp.Llama(model_path=model, n_ctx=4096, n_gpu_layers=gpu_layers, verbose=False, n_batch=512,
                                   last_n_tokens_size=SAMPLING["repeat_last_n"], flash_attn=True)
        self.sampling = {"top_k": SAMPLING["top_k"], "top_p": SAMPLING["top_p"], "min_p": SAMPLING["min_p"],
                         "temp": SAMPLING["temperature"], "repeat_penalty": SAMPLING["repeat_penalty"]}
        _boot("load.llama_cpp", t0, gpu=self.gpu)

    def tokens(self, prompt: str, max_tokens: int, cancelled, info: dict | None = None):
        ids = self.llm.tokenize(prompt.encode(), add_bos=True, special=True)
        for n, tok in enumerate(self.llm.generate(ids, reset=True, **self.sampling)):
            if n >= max_tokens or cancelled():
                return
            yield tok


class LlamaServer:
    """llama.cpp's llama-server, private to this worker (localhost, a free port, killed with the worker)."""
    slots = 2

    def __init__(self, exe: str, model: str, gpu_layers: int) -> None:
        t0 = now_ms()
        devices = subprocess.run([exe, "--list-devices"], capture_output=True, text=True, timeout=60,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        self.gpu = gpu_layers != 0 and bool(re.search(r"^\s+(CUDA|Metal|MTL|Vulkan)\d*:", devices, re.M))
        _boot("load.list_devices", t0, gpu=self.gpu, devices=devices.strip()[-300:])
        t0 = now_ms()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        log_path = os.path.join(os.path.dirname(exe), "llama-server.log")
        self.log = open(log_path, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(
            [exe, "-m", model, "-ngl", "99" if gpu_layers != 0 else "0", "-fa", "on" if gpu_layers != 0 else "off",
             "-c", str(SLOT_CTX * self.slots), "-np", str(self.slots), "--host", "127.0.0.1",
             "--port", str(self.port), "--no-webui"],
            stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.job = _die_with_me(self.proc)
        deadline = time.time() + 180
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError("o llama-server fechou ao carregar: " + self._tail())
            try:
                status, _ = self._get("/health")
                if status == 200:
                    break
            except OSError:
                pass
            if time.time() > deadline:
                self.close()
                raise RuntimeError("o llama-server não carregou o modelo a tempo")
            time.sleep(0.2)
        _boot("load.llama_server", t0, port=self.port, slots=self.slots)

    def _tail(self) -> str:
        try:
            self.log.flush()
            with open(self.log.name, encoding="utf-8", errors="replace") as f:
                return " | ".join(f.read().strip().splitlines()[-3:])[-300:]
        except OSError:
            return ""

    def _get(self, path: str):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            c.request("GET", path)
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def tokens(self, prompt: str, max_tokens: int, cancelled, info: dict | None = None):
        """Token ids as they are generated. `info` receives llama-server's own timings at the end."""
        body = {"prompt": prompt, "n_predict": max_tokens, "stream": True, "return_tokens": True, **SAMPLING}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request("POST", "/completion", json.dumps(body), {"Content-Type": "application/json"})
            r = c.getresponse()
            if r.status != 200:
                raise RuntimeError(f"llama-server {r.status}: {r.read()[:200].decode(errors='replace')}")
            for line in r:
                if cancelled():
                    return  # closing the connection makes the server drop the request
                if not line.startswith(b"data: "):
                    continue
                d = json.loads(line[6:])
                if "error" in d:
                    raise RuntimeError(f"llama-server: {d['error']}")
                yield from d.get("tokens") or ()
                if d.get("stop"):
                    if info is not None and isinstance(d.get("timings"), dict):
                        info.update({f"server_{k}": v for k, v in d["timings"].items()
                                     if isinstance(v, (int, float))})
                        info["stop_type"] = d.get("stop_type")
                    return
        finally:
            c.close()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()


# ---------------------------------------------------------------------------------------------
# tokens -> audio
# ---------------------------------------------------------------------------------------------
class Orpheus:
    """Silence seeds: the model opens every line with ~0.3-1 s of silent frames, which cost generation time before
    the first syllable. The prompt can end as if the model had already produced a few of them (start_of_ai,
    start_of_speech and the last silent frames before the voice in an earlier line of the same voice): it then
    starts speaking after ~0.2 s instead of ~0.5 s, equally intelligible (checked with Whisper on 3 voices). The
    first line of each voice runs without a seed and provides it; seeds are kept on disk."""

    def __init__(self, backend, snac: str, seeds_path: str | None = None) -> None:
        import onnxruntime

        self.seeds_path = seeds_path
        try:
            with open(seeds_path, encoding="utf-8") as f:
                self.seeds: dict[str, list[list[int]]] = json.load(f)
        except (OSError, ValueError, TypeError):
            self.seeds = {}
        ok = lambda s: isinstance(s, list) and 0 < len(s) <= 8 and all(  # noqa: E731
            isinstance(f, list) and len(f) == 7 and all(isinstance(c, int) and 0 <= c < 4096 for c in f) for f in s)
        self.seeds = {v: s for v, s in self.seeds.items() if ok(s)} if isinstance(self.seeds, dict) else {}
        self.seed_lock = threading.Lock()
        self.backend = backend
        self.gpu, self.slots = backend.gpu, backend.slots
        t0 = now_ms()
        opts = onnxruntime.SessionOptions()
        opts.intra_op_num_threads = max(2, (os.cpu_count() or 4) // 2)
        self.snac = onnxruntime.InferenceSession(snac, sess_options=opts, providers=["CPUExecutionProvider"])
        self.snac_inputs = [i.name for i in self.snac.get_inputs()]
        _boot("load.snac", t0, seeds=sorted(self.seeds))

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

    def stream(self, text: str, voice: str, cancelled, note=lambda name, **kw: None):
        """Yield PCM chunks (int16 arrays) for `text` while it is being generated. Returns the token count.
        `note(name, ts=None, dur=None, **attrs)` records the timeline."""
        import numpy as np

        prompt = f"<|audio|>{voice}: {text}<|eot_id|><custom_token_4>"
        seed = [list(f) for f in self.seeds.get(voice, [])]
        if seed:  # start_of_ai, start_of_speech, then the seed frames as audio tokens
            prompt += "<custom_token_5><custom_token_1>" + "".join(
                f"<custom_token_{AUDIO_BASE - 128256 + j * 4096 + c}>" for f in seed for j, c in enumerate(f))
        # ~84 tokens per second of speech; allow about twice the expected length (laughs, slow speakers), never a rerun.
        spoken = len(re.sub(r"<[^>]+>", "", text))
        max_tokens = min(int(84 * (2.5 + 2 * spoken / 13)), SLOT_CTX - 200 - 7 * len(seed))
        # Seed frames are context for the decoder (the first block joins them smoothly) but are not sent.
        frames: list[list[int]] = list(seed)
        state = {"done": False, "error": None, "tokens": 0}
        lock = threading.Lock()
        info: dict = {}
        note("gen.request", seed_frames=len(seed), max_tokens=max_tokens, chars=spoken)

        def generate():
            cur: list[int] = []
            audio = False
            reason = "end"
            try:
                for n, tok in enumerate(self.backend.tokens(prompt, max_tokens, cancelled, info)):
                    state["tokens"] = n + 1
                    if n == 0:
                        note("gen.first_token")
                    if n >= max_tokens or cancelled():
                        reason = "max_tokens" if n >= max_tokens else "cancelled"
                        break
                    if tok < AUDIO_BASE:
                        if tok in EOS or audio:
                            reason = "eos" if tok in EOS else "end_of_audio"
                            break
                        continue
                    if not audio:
                        note("gen.first_audio_token", tokens=n + 1)
                    audio = True
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
                reason = "error"
            note("gen.end", reason=reason, tokens=state["tokens"], frames=len(frames) - len(seed), **info)
            state["done"] = True

        t = threading.Thread(target=generate, daemon=True)
        t.start()
        emitted = start = len(seed)
        block = 0
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
                t0 = now_ms()
                pcm = self._decode(window)[left * FRAME:(left + end - emitted) * FRAME]
                peak = int(np.abs(pcm).max(initial=0))
                note("block", ts=t0, dur=round(now_ms() - t0, 2), first=emitted - start, frames=end - emitted,
                     audio_ms=round(len(pcm) / SR * 1000, 1), ready=n - start, voiced=peak > VOICED, peak=peak)
                yield pcm
                if not block:
                    voiced = np.nonzero(np.abs(pcm) > VOICED)[0]
                    if len(voiced):
                        block = 1  # bigger blocks only once the voice has started
                        note("voice.onset",
                             at_audio_ms=round(((emitted - start) * FRAME + int(voiced[0])) / SR * 1000, 1))
                        if not seed:
                            self._keep_seed(voice, frames, emitted + int(voiced[0]) // FRAME)
                            note("seed.saved", voice=voice)
                else:
                    block += 1
                emitted = end
                continue
            if finished:
                break
            time.sleep(0.01)
        t.join()
        if state["error"]:
            raise state["error"]
        if emitted == start and not cancelled():
            raise RuntimeError("o Orpheus não gerou áudio para esse texto")
        return state["tokens"]

    def _keep_seed(self, voice: str, frames: list[list[int]], onset: int) -> None:
        """The last silent frames before the voice (not the one right before it, which already leads into it)."""
        seed = frames[max(0, onset - 5):max(1, onset - 1)]
        with self.seed_lock:
            if not seed or voice in self.seeds:
                return
            self.seeds[voice] = seed
            if not self.seeds_path:
                return
            try:
                tmp = self.seeds_path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.seeds, f)
                os.replace(tmp, self.seeds_path)
            except OSError:
                pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--snac", required=True)
    ap.add_argument("--gpu-layers", type=int, default=-1)
    ap.add_argument("--server", help="llama-server executable; without it the model runs in this process")
    ap.add_argument("--seeds", help="JSON file with each voice's silence seed (read, and written as voices are used)")
    args = ap.parse_args()
    proto = _protocol_stream()
    out_lock = threading.Lock()

    def say(obj: dict) -> None:
        with out_lock:
            proto.write(json.dumps(obj) + "\n")
            proto.flush()

    try:
        _cuda_dlls()
        backend = (LlamaServer(args.server, args.model, args.gpu_layers) if args.server
                   else LocalLlama(args.model, args.gpu_layers))
        engine = Orpheus(backend, args.snac, args.seeds)
    except Exception as e:  # noqa: BLE001
        say({"ready": False, "error": f"{type(e).__name__}: {e}", "events": BOOT})
        return
    say({"ready": True, "gpu": engine.gpu, "slots": engine.slots, "events": BOOT,
         "backend": "llama-server" if args.server else "llama-cpp-python"})

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
                msg["_rx"] = now_ms()
                jobs.put(msg)
        for _ in range(engine.slots):
            jobs.put(None)

    def serve(slot: int):
        while (req := jobs.get()) is not None:
            rid = req.get("id")
            events = [{"ts": req["_rx"], "name": "worker.received", "chars": len(req.get("text", ""))}]

            def note(name, ts=None, events=events, **kw):
                events.append({"ts": ts if ts is not None else now_ms(), "name": name, **kw})
            note("worker.start", slot=slot, waited_ms=round(now_ms() - req["_rx"], 2))
            if rid in cancels:
                note("worker.skipped_cancelled")
                say({"id": rid, "done": True, "seconds": 0, "took": 0, "tps": 0, "cancelled": True,
                     "events": events})
                cancels.discard(rid)
                continue
            t0, samples = time.time(), 0
            try:
                gen = engine.stream(req["text"], req["voice"], lambda: rid in cancels, note)
                tokens = 0
                while True:
                    try:
                        pcm = next(gen)
                    except StopIteration as stop:
                        tokens = stop.value or 0
                        break
                    samples += len(pcm)
                    say({"id": rid, "pcm": base64.b64encode(pcm.tobytes()).decode(), "ts": now_ms()})
                took = time.time() - t0
                note("worker.done", audio_ms=round(samples / SR * 1000, 1), cancelled=rid in cancels)
                say({"id": rid, "done": True, "seconds": round(samples / SR, 2), "took": round(took, 2),
                     "tps": round(tokens / max(took, 0.01), 1), "cancelled": rid in cancels, "events": events})
            except Exception as e:  # noqa: BLE001
                note("worker.error", error=f"{type(e).__name__}: {e}"[:300])
                say({"id": rid, "error": f"{type(e).__name__}: {e}", "events": events})
            cancels.discard(rid)

    threading.Thread(target=reader, daemon=True).start()
    servers = [threading.Thread(target=serve, args=(i,), daemon=True) for i in range(engine.slots)]
    for s in servers:
        s.start()
    for s in servers:
        s.join()
    if isinstance(backend, LlamaServer):
        backend.close()


if __name__ == "__main__":
    main()
