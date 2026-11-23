"""Friendly uninstall: pick what to remove (each model, your data, settings, the Python environment, each CLI).

Models and data are removed right away. The Python environment (.venv) and the "everything" cleanup of data/
and models/ run after the server exits, from a small detached shell, because the running app lives in them."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config, db, providers, telemetry, voices

log = logging.getLogger("uninstall")
WIN = sys.platform == "win32"
VENV = config.ROOT / ".venv"
WHISPER_DIR = config.MODELS_DIR / "whisper"


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


def _whisper_repos() -> list:
    if not WHISPER_DIR.exists():
        return []
    try:
        from huggingface_hub import scan_cache_dir
        return list(scan_cache_dir(WHISPER_DIR).repos)
    except Exception as e:  # noqa: BLE001
        log.warning("cannot scan whisper cache: %s", e)
        return []


def items() -> list[dict]:
    """Everything that can be removed, grouped, with sizes. `all` marks what "Tudo do english-hub" includes."""
    out: list[dict] = []
    kokoro = [f for f in (config.KOKORO_MODEL, config.KOKORO_VOICES) if f.exists()]
    if kokoro:
        out.append({"id": "model:kokoro", "group": "models", "label": "Voz · Kokoro (21 personagens)",
                    "detail": "síntese de voz", "bytes": sum(_size(f) for f in kokoro), "all": True})
    for r in _whisper_repos():
        name = r.repo_id.split("/")[-1].replace("faster-whisper-", "").replace("faster-distil-whisper-", "distil-")
        out.append({"id": "model:whisper:" + r.repo_id, "group": "models", "label": f"Ouvido · Whisper {name}",
                    "detail": "reconhecimento de fala", "bytes": r.size_on_disk, "all": True})
    if voices.ORPHEUS_DIR.exists():
        out.append({"id": "engine:orpheus", "group": "models", "label": "Voz com emoção · Orpheus 3B",
                    "detail": "modelo, decodificador e o ambiente dele (volta para a voz Kokoro)",
                    "bytes": voices.size_bytes(), "all": True})
    out.append({"id": "data:db", "group": "data", "label": "Histórico, frases e perfil",
                "detail": "conversas, frases (e o áudio delas), caderno de erros, perfil e cenários salvos",
                "bytes": _size(config.DB_PATH) if config.DB_PATH.exists() else 0, "all": True})
    if telemetry.DIR.exists():
        out.append({"id": "data:telemetry", "group": "data", "label": "Telemetria",
                    "detail": "linha do tempo de cada fala e chamada (data/telemetry)", "bytes": _size(telemetry.DIR),
                    "all": True})
    out.append({"id": "data:settings", "group": "data", "label": "Configurações",
                "detail": "qualidade, modelos e provedores escolhidos (voltam ao padrão)",
                "bytes": _size(config.SETTINGS_PATH) if config.SETTINGS_PATH.exists() else 0, "all": True})
    if VENV.exists():
        out.append({"id": "env:venv", "group": "app", "label": "Ambiente Python do app (.venv)",
                    "detail": "bibliotecas instaladas pelo uv; removido quando o app fechar. Para usar de novo, "
                              "é só abrir o app (ele reinstala).", "bytes": _size(VENV), "all": True, "closes": True})
    for pid, p in providers.PROVIDERS.items():
        path = providers.resolve(pid)
        if not path:
            continue
        plan = providers.uninstall_plan(pid) or {}
        how = {"brew": "pelo Homebrew", "npm": "pelo npm", "mise": "manual (mise)", "native": "apagando o programa"}
        out.append({"id": "cli:" + pid, "group": "cli", "label": f"{p['cli']} ({p['label']})",
                    "detail": f"remove o programa do computador ({how.get(plan.get('method'), '')})",
                    "bytes": None, "all": False, "manual": plan.get("manual")})
        if p["logout"]:
            out.append({"id": "logout:" + pid, "group": "cli", "label": f"Sair da conta no {p['cli']}",
                        "detail": "desconecta a sua conta também fora do english-hub", "bytes": None, "all": False})
    return out


def _schedule_after_exit(paths: list[Path]) -> None:
    """Delete paths after this process exits (they hold the running app)."""
    pid = os.getpid()
    if WIN:
        rm = "; ".join(f"Remove-Item -LiteralPath '{p}' -Recurse -Force -ErrorAction SilentlyContinue" for p in paths)
        script = f"Wait-Process -Id {pid} -ErrorAction SilentlyContinue; Start-Sleep -Seconds 3; {rm}"
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        rm = " ".join("'" + str(p).replace("'", "'\\''") + "'" for p in paths)
        script = f"while kill -0 {pid} 2>/dev/null; do sleep 0.5; done; sleep 2; rm -rf {rm}"
        subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(ids: list[str]) -> dict:
    from .stt import stt
    from .tts import tts

    results, after_exit = [], []
    reset_setup = reset_onboarding = False
    everything = {i["id"] for i in items() if i["all"]} <= set(ids)
    for item_id in ids:
        try:
            if item_id == "model:kokoro":
                tts._k = None
                for f in (config.KOKORO_MODEL, config.KOKORO_VOICES):
                    f.unlink(missing_ok=True)
                reset_setup = True
            elif item_id.startswith("model:whisper:"):
                repo = item_id.split(":", 2)[2]
                stt.reset()
                for r in _whisper_repos():
                    if r.repo_id == repo:
                        from huggingface_hub import scan_cache_dir
                        scan_cache_dir(WHISPER_DIR).delete_revisions(*[x.commit_hash for x in r.revisions]).execute()
                reset_setup = True
            elif item_id == "engine:orpheus":
                voices.remove()
            elif item_id == "data:db":
                db.wipe()
                shutil.rmtree(voices.CACHE_DIR, ignore_errors=True)
                reset_onboarding = True
            elif item_id == "data:telemetry":
                telemetry.RECENT.clear()
                shutil.rmtree(telemetry.DIR, ignore_errors=True)
            elif item_id == "data:settings":
                config.SETTINGS_PATH.unlink(missing_ok=True)
            elif item_id == "env:venv":
                after_exit.append(VENV)
            elif item_id.startswith("cli:"):
                t = providers.uninstall(item_id[4:])
                if t["status"] == "error":
                    raise RuntimeError(t["error"])
            elif item_id.startswith("logout:"):
                r = providers.logout(item_id[7:])
                if not r["ok"]:
                    raise RuntimeError(r["message"])
            else:
                raise ValueError("item desconhecido")
            results.append({"id": item_id, "ok": True})
        except Exception as e:
            log.exception("uninstall %s failed", item_id)
            results.append({"id": item_id, "ok": False, "error": str(e)})
    if everything:
        after_exit += [config.MODELS_DIR, config.DATA_DIR]
    elif "data:settings" not in ids and (reset_setup or reset_onboarding):
        flags = {}
        if reset_setup:
            flags["setup_done"] = False
        if reset_onboarding:
            flags["onboarding_done"] = False
        config.apply(flags)
    if after_exit:
        _schedule_after_exit(after_exit)
    return {"results": results, "closes": bool(after_exit), "everything": everything,
            "folder": str(config.ROOT)}


def shutdown() -> None:
    """Stop the server shortly after answering, so the after-exit cleanup can run."""
    import threading
    threading.Timer(0.8, lambda: os._exit(0)).start()

