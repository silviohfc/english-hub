"""Voice engines for the characters.

- kokoro: built in, fast, runs on any CPU. Each character has its own timbre, but speech is always neutral.
- orpheus: Orpheus 3B (Canopy Labs), expressive: it laughs, sighs and changes intonation with the text. Installed on
  demand into its own Python environment (models/engines/orpheus/.venv) and run as a worker process
  (app/orpheus_worker.py), so its native libraries never touch the app's environment. Only offered when the
  hardware can run it: Apple Silicon with 16 GB+ or an NVIDIA GPU with 6 GB+.

The chat model may put sound tags (<laugh>, <sigh>, ...) in the partner's lines when Orpheus is active; `clean()`
removes them for captions, history and the neutral engine."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import config, prompts

log = logging.getLogger("voices")
WIN = sys.platform == "win32"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if WIN else 0

ORPHEUS_DIR = config.ENGINES_DIR / "orpheus"
ORPHEUS_HF = ORPHEUS_DIR / "hf"
ORPHEUS_MARK = ORPHEUS_DIR / "installed.json"
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
class Worker:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()       # one request at a time
        self.start_lock = threading.Lock()
        self.state = "stopped"             # stopped | loading | ready | error
        self.error = ""
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
            self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         text=True, encoding="utf-8", bufsize=1, creationflags=_NO_WINDOW)
            line = self.proc.stdout.readline()
            try:
                msg = json.loads(line) if line else {"ready": False, "error": "o processo do Orpheus fechou ao carregar"}
            except ValueError:
                msg = {"ready": False, "error": line.strip()[:200]}
            if msg.get("ready"):
                self.state = "ready"
                log.info("Orpheus ready (%s).", dev)
            else:
                self.state, self.error = "error", msg.get("error") or "falha ao carregar"
                log.warning("Orpheus failed to load: %s", self.error)
                self.stop()
                self.state = "error"

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

    def synth(self, text: str, voice: str, timeout: float = 120) -> tuple[bytes, dict]:
        self.start()
        if self.state != "ready":
            raise RuntimeError(self.error or "Orpheus indisponível")
        with self.lock:
            self._n += 1
            fd, out = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                self.proc.stdin.write(json.dumps({"id": self._n, "text": text, "voice": voice, "out": out}) + "\n")
                self.proc.stdin.flush()
                res: list = []
                t = threading.Thread(target=lambda: res.append(self.proc.stdout.readline()), daemon=True)
                t.start()
                t.join(timeout)
                if not res or not res[0]:
                    self.stop()
                    self.state, self.error = "error", "o Orpheus parou de responder"
                    raise RuntimeError(self.error)
                msg = json.loads(res[0])
                if not msg.get("ok"):
                    raise RuntimeError(msg.get("error") or "falha ao gerar a voz")
                return Path(out).read_bytes(), msg
            finally:
                Path(out).unlink(missing_ok=True)


worker = Worker()


def synth(text: str, voice: str, speed: float = 1.0, engine: str | None = None) -> tuple[bytes, dict]:
    """WAV bytes for a character's line, plus {"engine", "speed_applied", "fallback"}."""
    from .tts import tts

    voice = prompts.voice(voice)
    engine = engine or active()
    if engine == "orpheus":
        if not installed("orpheus") or not support("orpheus")["ok"]:
            raise RuntimeError("Orpheus não está disponível neste computador.")
        try:
            wav, _ = worker.synth(_orpheus_text(text), ORPHEUS_VOICE.get(voice, "tara"))
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
        _, msg = worker.synth("Oh wow, that's great news! <laugh> I'm really happy for you.", "tara")
        rtf = msg["took"] / max(msg["seconds"], 0.1)
        ORPHEUS_MARK.write_text(json.dumps({"ok": True, "rtf": round(rtf, 2), "at": time.time()}), encoding="utf-8")
        self._set("test", status="done",
                  detail=f"{msg['took']:.0f} s para gerar {msg['seconds']:.0f} s de fala".replace(".", ","))
        if config.TTS_ENGINE != "orpheus":
            worker.stop()


install = Install()


def remove() -> None:
    worker.stop()
    if config.TTS_ENGINE == "orpheus":
        config.apply({"tts_engine": "kokoro"})
    shutil.rmtree(ORPHEUS_DIR, ignore_errors=True)


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
            rtf = _mark().get("rtf")
            item.update(rtf=rtf, job=install.snapshot(), worker=worker.state, worker_error=worker.error)
        out.append(item)
    return {"chosen": config.TTS_ENGINE, "active": active(), "engines": out}
