"""AI providers that run through the user's own CLI and subscription: Claude Code, Antigravity (Gemini) and Codex.

Finding the binaries, versions, installing with the official installers, opening a terminal for the interactive
sign-in, signing out, and uninstalling. The actual model calls live in llm.py."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger("providers")

WIN = sys.platform == "win32"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if WIN else 0
HOME = Path.home()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))

ROLES = ("chat", "feedback", "helper")

PROVIDERS: dict[str, dict] = {
    "claude": {
        "label": "Claude", "cli": "Claude Code", "bin": "claude", "plan": "Assinatura Claude (Pro ou Max)",
        "models": ["haiku", "sonnet", "opus"],
        "defaults": {"chat": "haiku", "feedback": "sonnet", "helper": "haiku"},
        "install": {"unix": "curl -fsSL https://claude.ai/install.sh | bash",
                    "win": "irm https://claude.ai/install.ps1 | iex"},
        "login": ["auth", "login"], "logout": ["auth", "logout"], "status": ["auth", "status"],
        "login_hint": "O navegador abre para você entrar na sua conta Claude. Depois feche o terminal.",
        "brew": "claude-code", "npm": "@anthropic-ai/claude-code",
        "native_data": [HOME / ".local" / "share" / "claude"],
        "config_dirs": [HOME / ".claude"],
    },
    "gemini": {
        "label": "Gemini", "cli": "Antigravity CLI", "bin": "agy", "plan": "Plano Google AI (Antigravity)",
        "models": [],
        "defaults": {"chat": "", "feedback": "", "helper": ""},
        "install": {"unix": "curl -fsSL https://antigravity.google/cli/install.sh | bash",
                    "win": "irm https://antigravity.google/cli/install.ps1 | iex"},
        "login": [], "logout": None, "status": None,
        "login_hint": ("O Antigravity pede login na primeira vez que abre: escolha entrar com o Google, "
                       "termine no navegador e depois digite /exit no terminal."),
        "logout_hint": "Abra o Antigravity no terminal e digite /logout.",
        "brew": "antigravity-cli", "npm": None,
        "native_data": [],
        "config_dirs": [HOME / ".gemini" / "antigravity-cli"],
        "note": "A Gemini CLI antiga foi desligada para contas pessoais em junho de 2026; o Antigravity a substitui.",
    },
    "codex": {
        "label": "ChatGPT", "cli": "Codex CLI", "bin": "codex", "plan": "Plano ChatGPT (Plus, Pro ou Business)",
        "models": [],
        "defaults": {"chat": "", "feedback": "", "helper": ""},
        "install": {"unix": None, "win": "irm https://chatgpt.com/codex/install.ps1 | iex"},
        "login": ["login"], "logout": ["logout"], "status": ["login", "status"],
        "login_hint": "O navegador abre para você entrar na sua conta ChatGPT. Depois feche o terminal.",
        "brew": "codex", "npm": "@openai/codex",
        "native_data": [],
        "config_dirs": [HOME / ".codex"],
    },
}


def _search_path() -> str:
    """PATH plus the folders the official installers use, so a CLI installed while the app runs is found."""
    extra = [HOME / ".local" / "bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin"),
             HOME / ".local" / "share" / "mise" / "shims"]
    if WIN:
        extra += [LOCALAPPDATA / "agy" / "bin", LOCALAPPDATA / "Antigravity", LOCALAPPDATA / "Programs" / "agy",
                  APPDATA / "npm", LOCALAPPDATA / "codex", HOME / ".local" / "bin"]
    return os.pathsep.join([os.environ.get("PATH", "")] + [str(p) for p in extra])


def resolve(pid: str) -> str | None:
    from . import config
    name = config.CLAUDE_BIN if pid == "claude" else PROVIDERS[pid]["bin"]
    return shutil.which(name, path=_search_path())


def _run(args: list[str], timeout: int = 20, **kw) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": _search_path(), "NO_COLOR": "1"}
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          check=False, creationflags=_NO_WINDOW, env=env, **kw)


_VERSIONS: dict[str, str | None] = {}


def version(pid: str, path: str) -> str | None:
    if path not in _VERSIONS:
        try:
            out = _run([path, "--version"], timeout=20).stdout.strip().splitlines()
            words = out[0].split() if out else []
            _VERSIONS[path] = next((w for w in words if w[:1].isdigit()), words[-1] if words else None)
        except Exception:  # noqa: BLE001
            _VERSIONS[path] = None
    return _VERSIONS[path]


def install_method(pid: str, path: str) -> str:
    real = os.path.realpath(path).replace("\\", "/")
    if "/Caskroom/" in real or "/Cellar/" in real or real.startswith(("/opt/homebrew/", "/usr/local/Homebrew")):
        return "brew"
    if "node_modules" in real:
        return "npm"
    if "/mise/" in real:
        return "mise"
    return "native"


# ---------- sign-in state: the CLIs' own status command when it exists, plus our last real test ----------
TESTS: dict[str, dict] = {}  # pid -> {"ok": bool, "at": ts, "message": str}


def auth_hint(pid: str, path: str) -> bool | None:
    """True/False from the CLI's status command, None when the CLI has no such command."""
    cmd = PROVIDERS[pid]["status"]
    if not cmd:
        return None
    try:
        return _run([path, *cmd], timeout=20).returncode == 0
    except Exception:  # noqa: BLE001
        return None


def state(pid: str) -> dict:
    p = PROVIDERS[pid]
    path = resolve(pid)
    out = {"id": pid, "label": p["label"], "cli": p["cli"], "plan": p["plan"], "note": p.get("note"),
           "installed": bool(path), "path": path, "version": None, "signed_in": None,
           "test": TESTS.get(pid), "can_install": bool(install_command(pid)),
           "can_logout": bool(p["logout"]) or bool(p.get("logout_hint")), "task": TASKS.get(pid)}
    if path:
        out["version"] = version(pid, path)
        out["method"] = install_method(pid, path)
        out["signed_in"] = auth_hint(pid, path)
    return out


# ---------- background tasks (install / uninstall), one per provider ----------
TASKS: dict[str, dict] = {}


def install_command(pid: str) -> list[str] | None:
    p = PROVIDERS[pid]
    if WIN:
        script = p["install"]["win"]
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script] if script else None
    if p["install"]["unix"]:
        return ["bash", "-lc", p["install"]["unix"]]
    if p["brew"] and shutil.which("brew", path=_search_path()):
        return ["brew", "install", "--cask", p["brew"]]
    if p["npm"] and shutil.which("npm", path=_search_path()):
        return ["npm", "install", "-g", p["npm"]]
    return None


def _task(pid: str, kind: str, cmd: list[str] | None, after=None) -> dict:
    if TASKS.get(pid, {}).get("status") == "running":
        return TASKS[pid]
    t = {"kind": kind, "status": "running", "log": [], "started_at": time.time(), "error": None}
    TASKS[pid] = t

    def run():
        try:
            if cmd:
                env = {**os.environ, "PATH": _search_path(), "NO_COLOR": "1", "CI": "1"}
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                        text=True, encoding="utf-8", errors="replace", creationflags=_NO_WINDOW, env=env)
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        t["log"].append(line[-300:])
                        del t["log"][:-40]
                rc = proc.wait()
                if rc != 0:
                    raise RuntimeError(f"o comando terminou com código {rc}")
            if after:
                after(t)
            t["status"] = "done"
        except Exception as e:  # noqa: BLE001
            t["status"], t["error"] = "error", str(e)
        _VERSIONS.clear()
        t["finished_at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return t


def install(pid: str) -> dict:
    cmd = install_command(pid)
    if not cmd:
        t = {"kind": "install", "status": "error", "log": [], "error":
             "Não há instalador automático aqui. Instale o Node.js (nodejs.org) e tente de novo, ou instale pelo site oficial."}
        TASKS[pid] = t
        return t
    return _task(pid, "install", cmd)


def uninstall_plan(pid: str) -> dict | None:
    """What uninstalling this CLI would do, shown before confirming."""
    path = resolve(pid)
    if not path:
        return None
    p, method = PROVIDERS[pid], install_method(pid, path)
    if method == "brew":
        return {"method": method, "command": ["brew", "uninstall", "--cask", p["brew"]], "paths": []}
    if method == "npm" and p["npm"]:
        return {"method": method, "command": ["npm", "uninstall", "-g", p["npm"]], "paths": []}
    if method == "mise":
        return {"method": method, "command": None, "paths": [], "manual": f"Instalado pelo mise: rode 'mise uninstall {p['bin']}'."}
    paths = [Path(path)] + [d for d in p["native_data"] if d.exists()]
    return {"method": method, "command": None, "paths": paths}


def _remove(paths: list[Path]) -> None:
    for pth in paths:
        if pth.is_dir() and not pth.is_symlink():
            shutil.rmtree(pth, ignore_errors=True)
        elif pth.exists() or pth.is_symlink():
            pth.unlink()


def uninstall(pid: str) -> dict:
    plan = uninstall_plan(pid)
    if not plan:
        TASKS[pid] = {"kind": "uninstall", "status": "done", "log": ["Não estava instalado."], "error": None}
        return TASKS[pid]
    if plan.get("manual"):
        TASKS[pid] = {"kind": "uninstall", "status": "error", "log": [], "error": plan["manual"]}
        return TASKS[pid]
    TESTS.pop(pid, None)
    return _task(pid, "uninstall", plan["command"], after=(lambda t: _remove(plan["paths"])) if plan["paths"] else None)


def logout(pid: str) -> dict:
    p, path = PROVIDERS[pid], resolve(pid)
    if not path:
        return {"ok": False, "message": "Não instalado."}
    TESTS.pop(pid, None)
    if p["logout"]:
        r = _run([path, *p["logout"]], timeout=30)
        return {"ok": r.returncode == 0, "message": (r.stdout or r.stderr).strip()[-300:]}
    open_terminal(path, [], p.get("logout_hint", ""))
    return {"ok": True, "message": p.get("logout_hint", ""), "terminal": True}


# ---------- interactive sign-in in a real terminal window ----------
def _quote(a: str) -> str:
    if WIN:
        return f'"{a}"' if " " in a else a
    return "'" + a.replace("'", "'\\''") + "'"


def open_terminal(path: str, args: list[str], hint: str = "") -> None:
    cmdline = " ".join(_quote(x) for x in [path, *args])
    banner = f"english-hub: {hint}" if hint else "english-hub"
    if sys.platform == "darwin":
        script = f"echo {_quote(banner)}; {cmdline}"
        esc = script.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{esc}"',
                          "-e", 'tell application "Terminal" to activate'])
    elif WIN:
        subprocess.Popen(["cmd", "/k", f"echo {banner} & {cmdline}"], creationflags=subprocess.CREATE_NEW_CONSOLE,
                         env={**os.environ, "PATH": _search_path()})
    else:
        for term in (["x-terminal-emulator", "-e"], ["gnome-terminal", "--"], ["konsole", "-e"], ["xterm", "-e"]):
            if shutil.which(term[0]):
                subprocess.Popen([*term, "bash", "-lc", f"echo {_quote(banner)}; {cmdline}; exec bash"])
                return
        raise RuntimeError("Nenhum terminal encontrado. Rode no terminal: " + cmdline)


def login(pid: str) -> dict:
    p, path = PROVIDERS[pid], resolve(pid)
    if not path:
        return {"ok": False, "message": "Instale a CLI primeiro."}
    TESTS.pop(pid, None)
    open_terminal(path, p["login"], p["login_hint"])
    return {"ok": True, "message": p["login_hint"]}


def system_label() -> str:
    return {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, platform.system())
