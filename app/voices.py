"""Voice engines for the characters.

- kokoro: built in, fast, runs on any CPU. Each character has its own timbre, but speech is always neutral.
- orpheus: Orpheus 3B (Canopy Labs), expressive: it laughs, sighs and changes intonation with the text. Installed on
  demand into its own Python environment (models/engines/orpheus/.venv) and run as a worker process
  (app/orpheus_worker.py), so its native libraries never touch the app's environment. Only offered when the
  hardware can run it: Apple Silicon with 16 GB+ or an NVIDIA GPU with 6 GB+.

The chat model may put sound tags (<laugh>, <sigh>, ...) in the partner's lines when Orpheus is active; `clean()`
removes them for captions, history and the neutral engine."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

from . import config, prompts

log = logging.getLogger("voices")
WIN = sys.platform == "win32"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if WIN else 0

ORPHEUS_DIR = config.ENGINES_DIR / "orpheus"
ORPHEUS_HF = ORPHEUS_DIR / "hf"
ORPHEUS_MARK = ORPHEUS_DIR / "installed.json"
ORPHEUS_SR = 24_000
# Lines that are played again and again (saved phrases, vocabulary) are generated once per engine and kept here:
# tts-cache/<engine>/<hash>.wav. Conversation lines are never cached.
CACHE_DIR = config.DATA_DIR / "tts-cache"
ORPHEUS_PY = ORPHEUS_DIR / ".venv" / ("Scripts/python.exe" if WIN else "bin/python")
ORPHEUS_FILES = [  # (repo, file)
    ("isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF", "orpheus-3b-0.1-ft-q4_k_m.gguf"),
    ("onnx-community/snac_24khz-ONNX", "onnx/decoder_model.onnx"),
]
# Prebuilt llama-cpp-python wheels (GPU builds). Pinned to builds whose archives install cleanly: the newer
# "py3-none" Metal wheels fail their zip checksum.
LLAMA_WHEEL = {
    "mps": "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.19-metal/"
           "llama_cpp_python-0.3.19-cp312-cp312-macosx_11_0_arm64.whl",
    "cuda": "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.4-cu124/"
            "llama_cpp_python-0.3.4-cp312-cp312-win_amd64.whl",
}
# Orpheus ships 8 voices; each character uses the closest one (British characters get an American voice).
ORPHEUS_VOICE = {
    "af_heart": "tara", "af_sarah": "tara", "bf_emma": "tara",
    "af_alloy": "leah", "af_kore": "leah", "bf_isabella": "leah",
    "af_aoede": "jess", "af_jessica": "jess",
    "af_sky": "mia", "af_river": "mia",
    "af_bella": "zoe", "af_nova": "zoe",
    "am_onyx": "leo", "am_eric": "leo", "bm_daniel": "leo",
    "am_adam": "dan", "am_fenrir": "dan", "am_echo": "dan",
    "am_puck": "zac", "am_liam": "zac", "bm_fable": "zac",
}
SOUND_TAGS = ("laugh", "chuckle", "sigh", "gasp", "groan")
_TAG_RE = re.compile(r"\s*<\s*(?:laugh|chuckle|sigh|gasp|groan|yawn|cough|sniffle)\s*>\s*", re.I)

ENGINES = {
    "kokoro": {
        "label": "Kokoro", "emotion": False,
        "summary": "Rápida e leve, roda em qualquer computador. Cada personagem tem um timbre próprio, mas a fala "
                   "sai sempre no mesmo tom, sem emoção.",
        "voices": "21 vozes, uma por personagem",
    },
    "orpheus": {
        "label": "Orpheus 3B", "emotion": True,
        "summary": "Fala com emoção: ri, suspira, se anima ou fica sério conforme a conversa. Tem 8 vozes, então "
                   "alguns personagens dividem a mesma voz, e os britânicos falam com sotaque americano.",
        "voices": "8 vozes compartilhadas entre os personagens",
        "size_mb": 2600,
    },
}


# ---------------------------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------------------------
def clean(text: str) -> str:
    """Text without sound tags (captions, history, neutral engine)."""
    return re.sub(r"\s{2,}", " ", _TAG_RE.sub(" ", text or "")).strip()


def _orpheus_text(text: str) -> str:
    text = re.sub(r"[*_#`]", "", text or "")
    return re.sub(r"\s*<\s*(laugh|chuckle|sigh|gasp|groan|yawn|cough|sniffle)\s*>\s*", lambda m: f" <{m.group(1).lower()}> ", text, flags=re.I).strip()


# ---------------------------------------------------------------------------------------------
# hardware gate
# ---------------------------------------------------------------------------------------------
def support(engine: str) -> dict:
    """{"ok", "device", "reason"}: whether this computer can run the engine."""
    if engine == "kokoro":
        return {"ok": True, "device": "cpu", "reason": ""}
    from .setup import hardware
    hw = hardware()
    gpu, ram = hw.get("gpu") or {}, hw.get("ram_gb") or 0
    forced = (config._env("ORPHEUS_FORCE") or "") == "1"
    if gpu.get("kind") == "mps":
        if ram >= 15.5 or forced:
            return {"ok": True, "device": "mps", "reason": ""}
        return {"ok": False, "device": "mps",
                "reason": f"Precisa de 16 GB de memória; este Mac tem {ram:g} GB."}
    if gpu.get("kind") == "cuda" and WIN:
        vram = gpu.get("vram_mb") or 0
        if vram >= 6000 or forced:
            return {"ok": True, "device": "cuda", "reason": ""}
        return {"ok": False, "device": "cuda",
                "reason": f"Precisa de uma placa NVIDIA com 6 GB ou mais; a sua ({gpu.get('name', 'NVIDIA')}) tem "
                          f"{round(vram / 1024)} GB, que já ficam com o reconhecimento de voz."}
    if gpu.get("kind") == "cuda":
        return {"ok": False, "device": "cuda", "reason": "Disponível só no Windows e no macOS por enquanto."}
    return {"ok": False, "device": "cpu",
            "reason": "Precisa de placa de vídeo: NVIDIA com 6 GB ou mais, ou um Mac com Apple Silicon e 16 GB. "
                      "Só no processador, cada frase levaria muito tempo."}


def _mark() -> dict:
    try:
        return json.loads(ORPHEUS_MARK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _files() -> list[Path] | None:
    """Local paths of the Orpheus model files, or None if any is missing."""
    from huggingface_hub import try_to_load_from_cache
    out = []
    for repo, f in ORPHEUS_FILES:
        p = try_to_load_from_cache(repo, f, cache_dir=str(ORPHEUS_HF))
        if not isinstance(p, str):
            return None
        out.append(Path(p))
    return out


def installed(engine: str) -> bool:
    if engine == "kokoro":
        return config.KOKORO_MODEL.exists() and config.KOKORO_VOICES.exists()
    return bool(_mark().get("ok")) and ORPHEUS_PY.exists() and _files() is not None


def active() -> str:
    """The engine actually in use (falls back to Kokoro if the chosen one can't run)."""
    e = config.TTS_ENGINE
    return e if e == "kokoro" or (installed(e) and support(e)["ok"]) else "kokoro"


def expressive() -> bool:
    return ENGINES[active()]["emotion"]


# ---------------------------------------------------------------------------------------------
# worker process
# ---------------------------------------------------------------------------------------------
def _chunks(text: str) -> list[str]:
    """Sentences grouped to at least ~40 characters: Orpheus sounds best on short inputs, and the next chunk
    is already queued while the current one plays."""
    parts = [p.strip() for p in re.findall(r"[^.!?…]+(?:[.!?…]+[\"')\]]*|$)", text) if p.strip()]
    out: list[str] = []
    for p in parts:  # same rule as sentenceChunks() in app.js
        if out and len(out[-1]) < (15 if len(out) == 1 else 40):
            out[-1] += " " + p
        else:
            out.append(p)
    return out or [text]


class Stream:
    """One line being spoken: queued in the worker as sentence chunks, read back as it is generated.
    Yields ("pcm", bytes) and ("end", index) after each sentence, so the player can pause between sentences."""

    def __init__(self, w: "Worker", chunks: list[str], voice: str) -> None:
        self.w, self.ids, self.cancelled = w, [], False
        for chunk in chunks:
            self.ids.append(w._send({"text": chunk, "voice": voice}))

    def __iter__(self):
        try:
            for i, rid in enumerate(self.ids):
                q = self.w.queues.get(rid)
                if q is None:  # closed
                    return
                while True:
                    try:
                        msg = q.get(timeout=60)
                    except Exception:  # noqa: BLE001
                        self.w._hung()
                        raise RuntimeError("o Orpheus parou de responder") from None
                    if msg.get("closed"):
                        return
                    if "pcm" in msg:
                        yield "pcm", base64.b64decode(msg["pcm"])
                    elif msg.get("done"):
                        self.w._stats(msg)
                        self.w.queues.pop(rid, None)
                        yield "end", i
                        break
                    else:
                        raise RuntimeError(msg.get("error") or "falha ao gerar a voz")
        finally:
            self.close()

    def close(self) -> None:
        """Stop generating what is left (safe to call from any thread, more than once). `cancelled` tells whether
        something was still pending, i.e. the line was cut short."""
        for rid in self.ids:
            q = self.w.queues.pop(rid, None)
            if q is not None:
                q.put({"closed": True})  # wakes a reader blocked on this request
                self.w._send({"cancel": rid}, raw=True)
                self.cancelled = True


class Worker:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.start_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.state = "stopped"             # stopped | loading | ready | error
        self.error = ""
        self.gpu: bool | None = None       # whether llama.cpp is really using the GPU
        self.rtf: float | None = None      # generation time / speech time, measured on real lines
        self.tps: float | None = None
        self.queues: dict[int, "queue.Queue"] = {}
        self._n = 0

    def start(self) -> None:
        with self.start_lock:
            if self.proc and self.proc.poll() is None and self.state in ("loading", "ready"):
                return
            files = _files()
            if not files or not ORPHEUS_PY.exists():
                self.state, self.error = "error", "Orpheus não está instalado."
                return
            dev = support("orpheus")["device"]
            self.state, self.error = "loading", ""
            args = [str(ORPHEUS_PY), str(Path(__file__).with_name("orpheus_worker.py")),
                    "--model", str(files[0]), "--snac", str(files[1]),
                    "--gpu-layers", "0" if dev == "cpu" else "-1"]
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", bufsize=1, creationflags=_NO_WINDOW)
            line = proc.stdout.readline()
            try:
                msg = json.loads(line) if line else {"ready": False, "error": "o processo do Orpheus fechou ao carregar"}
            except ValueError:
                msg = {"ready": False, "error": line.strip()[:200]}
            if not msg.get("ready"):
                self.proc = proc
                self.stop()
                self.state, self.error = "error", msg.get("error") or "falha ao carregar"
                log.warning("Orpheus failed to load: %s", self.error)
                return
            self.proc, self.gpu, self.state = proc, bool(msg.get("gpu")), "ready"
            threading.Thread(target=self._read, args=(proc,), daemon=True).start()
            log.info("Orpheus ready (%s, gpu=%s).", dev, self.gpu)
            if dev != "cpu" and not self.gpu:
                log.warning("Orpheus is running on the CPU: llama.cpp could not use the GPU.")

    def _read(self, proc: subprocess.Popen) -> None:
        """Route the worker's messages to the stream waiting for each request id."""
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            q = self.queues.get(msg.get("id"))
            if q is not None:
                q.put(msg)
        if self.proc is proc:  # died on its own
            self.state, self.error = "error", "o processo do Orpheus fechou"
            for q in list(self.queues.values()):
                q.put({"error": self.error})

    def _send(self, msg: dict, raw: bool = False) -> int:
        with self.write_lock:
            if not raw:
                self._n += 1
                msg = {"id": self._n, **msg}
                self.queues[self._n] = queue.Queue()
            try:
                self.proc.stdin.write(json.dumps(msg) + "\n")
                self.proc.stdin.flush()
            except (OSError, AttributeError, ValueError):
                if not raw:
                    self.queues[msg["id"]].put({"error": "o processo do Orpheus fechou"})
            return msg.get("id", 0)

    def _stats(self, msg: dict) -> None:
        if msg.get("cancelled") or (msg.get("seconds") or 0) < 1:
            return
        rtf = msg["took"] / msg["seconds"]
        self.rtf = round(rtf if self.rtf is None else 0.6 * self.rtf + 0.4 * rtf, 2)
        self.tps = msg.get("tps")

    def _hung(self) -> None:
        self.stop()
        self.state, self.error = "error", "o Orpheus parou de responder"

    def warm(self) -> None:
        threading.Thread(target=self.start, daemon=True).start()

    def stop(self) -> None:
        p, self.proc = self.proc, None
        self.state = "stopped"
        if p and p.poll() is None:
            try:
                p.stdin.close()
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                p.kill()

    def stream(self, text: str, voice: str, chunks: list[str] | None = None) -> Stream:
        self.start()
        if self.state != "ready":
            raise RuntimeError(self.error or "Orpheus indisponível")
        return Stream(self, chunks or _chunks(text), voice)

    def synth(self, text: str, voice: str) -> bytes:
        """The whole line as a WAV (used by the install test and when the speed is not 1×)."""
        return pcm_to_wav(b"".join(data for kind, data in self.stream(text, voice) if kind == "pcm"))


worker = Worker()


def orpheus_ok() -> bool:
    return installed("orpheus") and support("orpheus")["ok"]


def stream(text: str, voice: str, chunks: list[str] | None = None) -> Stream:
    """A character's line with Orpheus, generated sentence by sentence (`chunks`, as split by the player, or split
    here). Raises before anything is generated if the engine can't speak, so the caller can fall back to a WAV."""
    if not orpheus_ok():
        raise RuntimeError("Orpheus não está disponível neste computador.")
    voice = prompts.voice(voice)
    parts = [_orpheus_text(c) for c in chunks if c.strip()] if chunks else None
    return worker.stream(_orpheus_text(text), ORPHEUS_VOICE.get(voice, "tara"), parts)


def cache_file(engine: str, voice: str, text: str, speed: float = 1.0) -> Path:
    # Kokoro bakes the speed into the audio; Orpheus is always natural pace (the browser changes the speed).
    key = f"{prompts.voice(voice)}|{text.strip()}|{round(speed, 2) if engine == 'kokoro' else ''}"
    return CACHE_DIR / engine / (hashlib.sha1(key.encode()).hexdigest() + ".wav")


def _save(path: Path, wav: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(wav)
        tmp.replace(path)
    except OSError as e:
        log.warning("cannot cache %s: %s", path.name, e)


def pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ORPHEUS_SR)
        w.writeframes(pcm)
    return buf.getvalue()


def cached_pcm(voice: str, text: str) -> bytes | None:
    """Orpheus audio of a cached line as raw PCM (for the streaming endpoint), or None."""
    f = cache_file("orpheus", voice, text)
    if not f.exists():
        return None
    with wave.open(str(f), "rb") as w:
        return w.readframes(w.getnframes())


def save_pcm(voice: str, text: str, pcm: bytes) -> None:
    _save(cache_file("orpheus", voice, text), pcm_to_wav(pcm))


def synth(text: str, voice: str, speed: float = 1.0, engine: str | None = None,
          cache: bool = False) -> tuple[bytes, dict]:
    """WAV bytes for a character's line, plus {"engine", "speed_applied", "fallback", "cached"}.
    With `cache`, the line is generated once per engine and then read from disk."""
    voice = prompts.voice(voice)
    engine = engine or active()
    f = cache_file(engine, voice, text, speed) if cache else None
    if f and f.exists():
        return f.read_bytes(), {"engine": engine, "speed_applied": engine == "kokoro", "fallback": "", "cached": True}
    wav, meta = _synth(text, voice, speed, engine)
    if f and not meta["fallback"]:
        _save(f, wav)
    return wav, {**meta, "cached": False}


def _synth(text: str, voice: str, speed: float, engine: str) -> tuple[bytes, dict]:
    from .tts import tts

    if engine == "orpheus":
        if not orpheus_ok():
            raise RuntimeError("Orpheus não está disponível neste computador.")
        try:
            wav = worker.synth(_orpheus_text(text), ORPHEUS_VOICE.get(voice, "tara"))
            # Orpheus has no speed control: the browser applies the speed while playing.
            return wav, {"engine": "orpheus", "speed_applied": False, "fallback": ""}
        except Exception as e:  # noqa: BLE001
            log.warning("Orpheus failed, using Kokoro: %s", e)
            return tts.synth(clean(text), voice, speed), {"engine": "kokoro", "speed_applied": True,
                                                         "fallback": str(e)}
    return tts.synth(clean(text), voice, speed), {"engine": "kokoro", "speed_applied": True, "fallback": ""}


def use(engine: str) -> dict:
    if engine not in ENGINES:
        raise ValueError(engine)
    if engine != "kokoro" and not (installed(engine) and support(engine)["ok"]):
        raise ValueError("Esse motor de voz não está instalado ou não roda neste computador.")
    config.apply({"tts_engine": engine})
    if engine == "orpheus":
        worker.warm()
    else:
        worker.stop()  # frees ~3 GB of memory
    return overview()


# ---------------------------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------------------------
def _uv() -> str | None:
    cands = [os.environ.get("UV"), shutil.which("uv"),
             str(Path.home() / ".local/share/mise/shims/uv"), str(Path.home() / ".local/bin/uv"),
             str(Path.home() / ".cargo/bin/uv")]
    return next((c for c in cands if c and Path(c).exists()), None)


class Install:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.state = {"status": "idle", "items": []}

    def snapshot(self) -> dict:
        with self.lock:
            return {**self.state, "items": [dict(i) for i in self.state["items"]]}

    def _set(self, item_id: str, **kw) -> None:
        with self.lock:
            for it in self.state["items"]:
                if it["id"] == item_id:
                    it.update(kw)

    @property
    def running(self) -> bool:
        return self.state["status"] == "running"

    def start(self) -> bool:
        if self.running:
            return False
        items = [
            {"id": "env", "label": "Ambiente do Orpheus", "detail": "Python 3.12 e llama.cpp com aceleração de GPU"},
            {"id": "model", "label": "Modelo · Orpheus 3B", "detail": "versão compacta (Q4), cerca de 2 GB"},
            {"id": "snac", "label": "Decodificador de áudio · SNAC", "detail": "transforma o modelo em som"},
            {"id": "test", "label": "Carregar e testar", "detail": "gera uma frase e mede o tempo"},
        ]
        for it in items:
            it.update(status="pending", bytes=0, total=None, error=None)
        with self.lock:
            self.state = {"status": "running", "items": items}
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self) -> None:
        from .setup import hf_fetch
        step = "env"
        try:
            self._env()
            for step, (repo, f) in zip(("model", "snac"), ORPHEUS_FILES):
                self._set(step, status="running")
                tot = hf_fetch(repo, ORPHEUS_HF, [f], lambda got, total, s=step: self._set(s, bytes=got, total=total))
                self._set(step, status="done", bytes=tot or 0, total=tot)
            step = "test"
            self._test()
            status = "done"
        except Exception as e:  # noqa: BLE001
            log.exception("orpheus install failed at %s", step)
            self._set(step, status="error", error=str(e))
            status = "error"
        with self.lock:
            self.state["status"] = status

    def _env(self) -> None:
        self._set("env", status="running")
        uv = _uv()
        if not uv:
            raise RuntimeError("Não achei o uv, que instala o ambiente. Abra o app pelo start.command / start.bat.")
        dev = support("orpheus")["device"]
        wheel = LLAMA_WHEEL.get(dev)
        if not wheel:
            raise RuntimeError("Sem build do llama.cpp para este computador.")
        ORPHEUS_DIR.mkdir(parents=True, exist_ok=True)
        pkgs = [f"llama-cpp-python @ {wheel}", "onnxruntime", "numpy"]
        if dev == "cuda":
            pkgs += ["nvidia-cuda-runtime-cu12", "nvidia-cublas-cu12"]
        venv = str(ORPHEUS_DIR / ".venv")
        for cmd in ([uv, "venv", "--allow-existing", "--python", "3.12", venv],
                    [uv, "pip", "install", "--python", str(ORPHEUS_PY), *pkgs]):
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False, creationflags=_NO_WINDOW)
            if r.returncode != 0:
                raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else
                                   "falha ao instalar o ambiente")
        self._set("env", status="done")

    def _test(self) -> None:
        self._set("test", status="running", detail="carregando o modelo na GPU…")
        worker.stop()
        worker.start()
        if worker.state != "ready":
            raise RuntimeError(worker.error)
        t0, first, pcm = time.time(), None, 0
        for kind, chunk in worker.stream("Oh wow, that's great news! <laugh> I'm really happy for you.", "tara"):
            if kind == "pcm":
                first = first or time.time() - t0
                pcm += len(chunk)
        took, seconds = time.time() - t0, pcm / 2 / ORPHEUS_SR
        rtf = took / max(seconds, 0.1)
        ORPHEUS_MARK.write_text(json.dumps({"ok": True, "rtf": round(rtf, 2), "gpu": worker.gpu, "at": time.time()}),
                                encoding="utf-8")
        where = "" if worker.gpu or support("orpheus")["device"] == "cpu" else " · rodando no processador, sem a GPU"
        self._set("test", status="done", detail=(f"começa a falar em {first or 0:.1f} s · {took:.0f} s para gerar "
                                                 f"{seconds:.0f} s de fala{where}").replace(".", ","))
        if config.TTS_ENGINE != "orpheus":
            worker.stop()


install = Install()


def remove() -> None:
    worker.stop()
    if config.TTS_ENGINE == "orpheus":
        config.apply({"tts_engine": "kokoro"})
    shutil.rmtree(ORPHEUS_DIR, ignore_errors=True)
    shutil.rmtree(CACHE_DIR / "orpheus", ignore_errors=True)


def size_bytes() -> int:
    total = 0
    for root, _, files in os.walk(ORPHEUS_DIR):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


# ---------------------------------------------------------------------------------------------
# overview for the UI
# ---------------------------------------------------------------------------------------------
def overview() -> dict:
    out = []
    for eid, e in ENGINES.items():
        item = {"id": eid, **e, "support": support(eid), "installed": installed(eid)}
        if eid == "orpheus":
            mark = _mark()
            gpu = worker.gpu if worker.gpu is not None else mark.get("gpu")
            item.update(rtf=worker.rtf or mark.get("rtf"), job=install.snapshot(), worker=worker.state,
                        worker_error=worker.error,
                        on_cpu=gpu is False and support(eid)["device"] != "cpu")
        out.append(item)
    return {"chosen": config.TTS_ENGINE, "active": active(), "engines": out}
