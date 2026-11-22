"""Talks to Claude through the local Claude Code CLI (your subscription; no API key, no extra cost).

- ChatProcess: one long-lived `claude -p` process per practice session, streaming JSON over
  stdin/stdout, so the conversation keeps context and avoids process start-up on every turn.
- ask(): one-shot call for the end-of-session report and small helpers.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import threading

from . import config

log = logging.getLogger("llm")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _claude_bin() -> str:
    path = shutil.which(config.CLAUDE_BIN)
    if not path:
        raise RuntimeError("Claude Code CLI ('claude') not found on PATH.")
    return path


def _base_args(model: str, system_prompt: str, tools: str = "") -> list[str]:
    # No MCP, no user/project settings, no slash commands. Tools off unless explicitly given
    # (only read-only web tools are ever enabled, for job search).
    args = [
        _claude_bin(), "-p",
        "--model", model,
        "--system-prompt", system_prompt,
        "--tools", tools,
        "--strict-mcp-config",
        "--setting-sources", "",
        "--disable-slash-commands",
        "--no-session-persistence",
    ]
    if tools:
        args += ["--allowedTools", tools.replace(",", " ")]
    return args


class LLMError(RuntimeError):
    pass


class ChatProcess:
    def __init__(self, system_prompt: str, model: str | None = None) -> None:
        args = _base_args(model or config.CHAT_MODEL, system_prompt) + [
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
        ]
        self._proc = subprocess.Popen(
            args, cwd=config.CLAUDE_WORKDIR,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, creationflags=_NO_WINDOW,
        )
        self._lock = threading.Lock()
        self._stderr: list[str] = []
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        for line in self._proc.stderr:
            self._stderr.append(line)
            del self._stderr[:-50]

    def send(self, text: str) -> str:
        with self._lock:
            if self._proc.poll() is not None:
                raise LLMError("Claude process exited: " + "".join(self._stderr[-5:]))
            msg = {"type": "user", "message": {"role": "user", "content": text}}
            self._proc.stdin.write(json.dumps(msg) + "\n")
            self._proc.stdin.flush()
            parts: list[str] = []
            for line in self._proc.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "assistant":
                    for block in ev.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            parts.append(block["text"])
                elif ev.get("type") == "result":
                    if ev.get("is_error"):
                        raise LLMError(str(ev.get("result") or ev.get("subtype")))
                    return (ev.get("result") or "".join(parts)).strip()
            raise LLMError("Claude process closed unexpectedly: " + "".join(self._stderr[-5:]))

    def close(self) -> None:
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            self._proc.kill()


WEB_TOOLS = "WebSearch,WebFetch"


def _run(prompt: str, system_prompt: str, model: str | None, timeout: int, tools: str,
         schema: dict | None = None) -> dict:
    args = _base_args(model or config.HELPER_MODEL, system_prompt, tools) + ["--output-format", "json"]
    if schema:
        args += ["--json-schema", json.dumps(schema)]
    res = subprocess.run(args, input=prompt, capture_output=True, text=True, encoding="utf-8",
                         cwd=config.CLAUDE_WORKDIR, timeout=timeout, creationflags=_NO_WINDOW)
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"Bad CLI output: {res.stdout[:300]} {res.stderr[:300]}") from e
    if data.get("is_error"):
        raise LLMError(str(data.get("result")))
    return data


def ask(prompt: str, system_prompt: str, model: str | None = None, timeout: int = 300, tools: str = "") -> str:
    return (_run(prompt, system_prompt, model, timeout, tools).get("result") or "").strip()


def ask_json(prompt: str, system_prompt: str, model: str | None = None, tools: str = "",
             schema: dict | None = None, timeout: int = 400) -> dict:
    """One-shot call that must return a JSON object.
    With `schema`, the CLI validates structured output (robust for long generated texts).
    Without it, the JSON is parsed from the text reply, retrying once on failure."""
    if schema:
        data = _run(prompt, system_prompt, model, timeout, tools, schema)
        out = data.get("structured_output")
        if isinstance(out, dict):
            return out
        raise LLMError("No structured output: " + str(data.get("result"))[:300])
    last = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else prompt + "\n\nIMPORTANT: reply with ONLY one valid JSON object."
        last = ask(p, system_prompt, model, timeout=timeout, tools=tools)
        m = re.search(r"\{.*\}", last, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("Model did not return valid JSON: " + last[:300])
