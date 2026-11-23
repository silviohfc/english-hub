"""First-run setup: hardware detection, quality presets, model downloads with real progress,
and loading/testing everything once, all driven from the setup screen."""
from __future__ import annotations

import fnmatch
import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from . import config

log = logging.getLogger("setup")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
WHISPER_DIR = config.MODELS_DIR / "whisper"
# Files faster-whisper needs from a model repo (mirrors faster_whisper.utils.download_model).
WHISPER_FILES = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]

WHISPER_MODELS = [
    # id, label, approx size in MB (shown before the real size is known)
    ("small", "small", 484),
    ("medium", "medium", 1530),
    ("large-v3-turbo", "large-v3-turbo", 1620),
    ("large-v3", "large-v3", 3090),
    ("distil-large-v3", "distil-large-v3 (só inglês)", 1510),
]
CLAUDE_MODELS = ["haiku", "sonnet", "opus"]


# ---------------------------------------------------------------------------------------------
# hardware
# ---------------------------------------------------------------------------------------------
def _run(args: list[str], timeout: int = 8) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False,
                              creationflags=_NO_WINDOW).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _cpu() -> tuple[str, int | None]:
    name, cores = platform.processor() or platform.machine(), None
    if sys.platform == "darwin":
        name = _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or name
        cores = int(_run(["sysctl", "-n", "hw.physicalcpu"]) or 0) or None
    elif sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                name = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except OSError:
            pass
        out = _run(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"], timeout=15)
        cores = int(out) if out.isdigit() else None
    else:
        try:
            info = Path("/proc/cpuinfo").read_text()
            name = next((ln.split(":", 1)[1].strip() for ln in info.splitlines() if ln.startswith("model name")), name)
            cores = len({ln for ln in info.splitlines() if ln.startswith("core id")}) or None
        except OSError:
            pass
    return name, cores


def _ram_gb() -> float | None:
    try:
        if sys.platform == "darwin":
            return int(_run(["sysctl", "-n", "hw.memsize"])) / 2**30
        if sys.platform == "win32":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("len", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
            ms = MS()
            ms.len = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.total / 2**30
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemTotal"):
                return int(ln.split()[1]) / 2**20
    except Exception as e:  # noqa: BLE001
        log.debug("could not read RAM size: %s", e)
    return None


def _gpu() -> dict | None:
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return {"name": "GPU do Apple Silicon (Metal)", "vram_mb": None, "kind": "mps"}
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    out = _run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if not out:
        return None
    name, _, mem = out.splitlines()[0].rpartition(",")
    try:
        return {"name": name.strip(), "vram_mb": int(mem), "kind": "cuda"}
    except ValueError:
        return {"name": out.splitlines()[0], "vram_mb": None, "kind": "cuda"}


_HW: dict | None = None


def hardware() -> dict:
    global _HW
    if _HW is None:
        cpu, cores = _cpu()
        ram = _ram_gb()
        os_name = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, platform.system())
        os_ver = platform.mac_ver()[0] if sys.platform == "darwin" else platform.release()
        _HW = {"os": f"{os_name} {os_ver}".strip(), "cpu": cpu, "cores": cores, "threads": os.cpu_count(),
               "ram_gb": round(ram, 1) if ram else None, "gpu": _gpu()}
    free = shutil.disk_usage(config.MODELS_DIR).free
    return {**_HW, "disk_free_gb": round(free / 2**30, 1)}


def presets(hw: dict) -> dict:
    """Quality presets for this machine, plus which one is recommended."""
    gpu = hw.get("gpu")
    gpu_ok = gpu and (gpu["kind"] == "mps" or (gpu.get("vram_mb") or 0) >= 3000)
    p = {
        "leve": {"label": "Leve", "hint": "small na CPU. Funciona em qualquer computador.",
                 "values": {"whisper_model": "small", "whisper_device": "cpu", "whisper_compute": "auto"}},
        "recomendado": {"label": "Recomendada", "values": {"whisper_model": "large-v3-turbo", "whisper_device": "auto",
                                                           "whisper_compute": "auto"}},
        "maximo": {"label": "Máxima", "values": {"whisper_model": "large-v3", "whisper_device": "auto",
                                                 "whisper_compute": "auto"}},
    }
    if gpu and gpu["kind"] == "cuda":
        small_gpu = (gpu.get("vram_mb") or 0) <= 6144
        p["recomendado"]["hint"] = ("large-v3-turbo na GPU, em modo econômico para a sua placa."
                                    if small_gpu else "large-v3-turbo na GPU.")
        p["maximo"]["hint"] = "large-v3 na GPU. Mais preciso e mais lento; pesa em placas de 4 GB."
    elif gpu and gpu["kind"] == "mps":
        p["recomendado"]["hint"] = "large-v3-turbo na GPU do Mac (Metal)."
        p["maximo"]["hint"] = "large-v3 na GPU do Mac. Mais preciso e mais lento."
    else:
        p["recomendado"]["hint"] = "large-v3-turbo na CPU. Sem GPU, cada fala demora alguns segundos."
        p["maximo"]["hint"] = "large-v3 na CPU. Lento sem GPU."
    return {"presets": p, "recommended": "recomendado" if gpu_ok else "leve"}


# ---------------------------------------------------------------------------------------------
# model files
# ---------------------------------------------------------------------------------------------
def _whisper_repo(name: str) -> str:
    from faster_whisper.utils import _MODELS
    return name if "/" in name else _MODELS.get(name, name)


def whisper_present(name: str) -> bool:
    from faster_whisper.utils import download_model
    try:
        download_model(name, local_files_only=True, cache_dir=str(WHISPER_DIR))
        return True
    except Exception:  # noqa: BLE001
        return False


def needed_whisper() -> list[str]:
    """Main model, plus the CPU fallback when the device is 'auto' (so a GPU failure works offline)."""
    names = [config.WHISPER_MODEL]
    if config.WHISPER_DEVICE == "auto" and config.WHISPER_CPU_FALLBACK_MODEL not in names:
        names.append(config.WHISPER_CPU_FALLBACK_MODEL)
    return names


def models_state() -> dict:
    return {
        "kokoro": config.KOKORO_MODEL.exists() and config.KOKORO_VOICES.exists(),
        "whisper": {n: whisper_present(n) for n in needed_whisper()},
    }


    path = shutil.which(config.CLAUDE_BIN)
    if not path:
        return {"found": False}
    _CLAUDE = {"found": True, "version": _run([path, "--version"], timeout=20).split(" ")[0] or None}
    return _CLAUDE


# ---------------------------------------------------------------------------------------------
# install job
# ---------------------------------------------------------------------------------------------
class Job:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.state = {"status": "idle", "items": [], "started_at": None, "finished_at": None}

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
            {"id": "kokoro", "group": "voz", "label": "Voz · Kokoro e 10 vozes", "detail": "kokoro-v1.0 · ONNX na CPU"},
        ]
        for i, name in enumerate(needed_whisper()):
            items.append({"id": f"whisper:{name}", "group": "ouvido",
                          "label": f"Ouvido · Whisper {name}" if i == 0 else f"Reserva para CPU · Whisper {name}",
                          "detail": "reconhecimento de fala" if i == 0 else "usado se a GPU falhar"})
        items += [{"id": "load", "group": "teste", "label": "Carregar e testar", "detail": "ouvido e voz"}]
        for it in items:
            it.update(status="pending", bytes=0, total=None, error=None)
        with self.lock:
            self.state = {"status": "running", "items": items, "started_at": time.time(), "finished_at": None}
        threading.Thread(target=self._run, daemon=True).start()
        return True

    # -- steps --
    def _run(self) -> None:
        from .stt import stt
        from .tts import tts

        failed = False
        try:
            self._kokoro()
        except Exception as e:  # noqa: BLE001
            failed = True
            self._set("kokoro", status="error", error=str(e))
        for name in needed_whisper():
            try:
                self._whisper(name)
            except Exception as e:  # noqa: BLE001
                failed = True
                self._set(f"whisper:{name}", status="error", error=str(e))
        if not failed:
            self._set("load", status="running")
            try:
                stt.reset()
                stt.load()
                tts.load()
                self._set("load", status="done", detail=f"Whisper {stt.model_name} em {stt.device} ({stt.compute})")
            except Exception as e:  # noqa: BLE001
                failed = True
                self._set("load", status="error", error=str(e))
        with self.lock:
            self.state["status"] = "error" if failed else "done"
            self.state["finished_at"] = time.time()

    def _download(self, url: str, dest: Path, item_id: str, base: int) -> int:
        if dest.exists() and dest.stat().st_size > 0:
            return dest.stat().st_size
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "english-hub-setup"})
        with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as f:
            got = 0
            while chunk := r.read(1 << 16):
                f.write(chunk)
                got += len(chunk)
                self._set(item_id, bytes=base + got)
        tmp.replace(dest)
        return got

    def _kokoro(self) -> None:
        files = [(KOKORO_BASE + "kokoro-v1.0.onnx", config.KOKORO_MODEL),
                 (KOKORO_BASE + "voices-v1.0.bin", config.KOKORO_VOICES)]
        total = 0
        for url, dest in files:
            if dest.exists():
                total += dest.stat().st_size
                continue
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "english-hub-setup"})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    total += int(r.headers.get("Content-Length") or 0)
            except Exception:  # noqa: BLE001
                total += 0
        self._set("kokoro", status="running", total=total or None)
        done = 0
        for url, dest in files:
            done += self._download(url, dest, "kokoro", done)
        self._set("kokoro", status="done", bytes=done, total=done)

    def _whisper(self, name: str) -> None:
        item = f"whisper:{name}"
        if whisper_present(name):
            self._set(item, status="done", detail="já baixado")
            return
        repo = _whisper_repo(name)
        total = None
        try:
            from huggingface_hub import HfApi
            info = HfApi().model_info(repo, files_metadata=True)
            total = sum(s.size or 0 for s in info.siblings
                        if any(fnmatch.fnmatch(s.rfilename, pat) for pat in WHISPER_FILES)) or None
        except Exception as e:  # noqa: BLE001
            log.warning("could not read size of %s: %s", repo, e)
        self._set(item, status="running", total=total)
        bars: list = []

        def fetch():
            # Same files as faster_whisper.utils.download_model, but with a progress hook:
            # snapshot_download aggregates every file's bytes into one "Reconstructing" bar.
            import huggingface_hub
            from tqdm.auto import tqdm

            class Bar(tqdm):
                def __init__(self, *a, **kw):
                    kw["file"] = open(os.devnull, "w")  # noqa: SIM115
                    kw.pop("name", None)
                    super().__init__(*a, **kw)
                    bars.append(self)

            try:
                huggingface_hub.snapshot_download(repo, cache_dir=str(WHISPER_DIR), allow_patterns=WHISPER_FILES,
                                                  tqdm_class=Bar)
            except Exception as e:  # noqa: BLE001
                err.append(e)

        err: list[Exception] = []
        t = threading.Thread(target=fetch, daemon=True)
        t.start()
        while t.is_alive():
            t.join(0.4)
            done = [b for b in bars if b.unit == "B" and str(b.desc).startswith("Reconstructing")]
            if done:
                got = int(done[0].n)
                self._set(item, bytes=min(got, total) if total else got, total=total or (done[0].total or None))
        if err:
            raise err[0]
        self._set(item, status="done", bytes=total or 0, total=total)

job = Job()


def overview() -> dict:
    hw = hardware()
    return {"settings": config.current(), "hardware": hw, **presets(hw),
            "options": {"whisper_models": [{"id": i, "label": label, "mb": mb} for i, label, mb in WHISPER_MODELS],
                        "devices": ["auto", "cuda" if sys.platform != "darwin" else "mps", "cpu"],
                        "computes": ["auto", "float16", "int8_float16", "int8"],
                        "claude_models": CLAUDE_MODELS},
            "models": models_state(), "job": job.snapshot()}
