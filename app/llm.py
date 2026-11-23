"""Talks to the language model through a local CLI and the user's own plan (no API keys, no extra cost).

Providers (see providers.py): claude (Claude Code), gemini (Antigravity CLI, Google AI plan), codex (Codex CLI,
ChatGPT plan). Each role (chat, feedback, helper) picks its provider and model in config.

- ChatProcess(): the conversation partner. On Claude, one long-lived `claude -p` process per practice session,
  streaming JSON over stdin/stdout, so context stays warm. On the other providers, each turn sends the
  conversation so far (they have no reliable long-lived headless mode).
- ask() / ask_json(): one-shot calls for the report, scenario generation and small helpers.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading

from . import config, providers, telemetry

log = logging.getLogger("llm")
_meta = threading.local()  # what the last CLI run reported about itself (durations, tokens), for telemetry


def _result_meta(ev: dict) -> dict:
    """The timing and usage numbers of a Claude CLI result event."""
    usage = ev.get("usage") or {}
    return {"cli_duration_ms": ev.get("duration_ms"), "api_duration_ms": ev.get("duration_api_ms"),
            "num_turns": ev.get("num_turns"), "cost_usd": ev.get("total_cost_usd"),
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "cache_read_tokens": usage.get("cache_read_input_tokens"),
            "cache_write_tokens": usage.get("cache_creation_input_tokens"),
            "stop_reason": ev.get("stop_reason") or ev.get("subtype")}

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
ROLES = providers.ROLES
WEB_TOOLS = "WebSearch,WebFetch"


class LLMError(RuntimeError):
    pass


def _bin(pid: str) -> str:
    path = providers.resolve(pid)
    if not path:
        p = providers.PROVIDERS[pid]
        raise LLMError(f"{p['cli']} ('{p['bin']}') não encontrado. Instale em Configurações › Inteligência artificial.")
    return path


def _target(role_or_model: str | None, default_role: str = "helper") -> tuple[str, str]:
    """Accepts a role name (chat/feedback/helper) or, for backwards compatibility, a Claude model name."""
    if role_or_model in ROLES:
        return config.role(role_or_model)
    if role_or_model:
        return "claude", role_or_model
    return config.role(default_role)


def _env() -> dict:
    return {**os.environ, "PATH": providers._search_path(), "NO_COLOR": "1"}


def _inline(system_prompt: str, prompt: str) -> str:
    """Providers without a system-prompt flag get the instructions at the top of the prompt."""
    return f"<instructions>\n{system_prompt}\n</instructions>\n\n{prompt}"


# =============================================================================================
# Claude Code
# =============================================================================================
def _claude_args(model: str, system_prompt: str, tools: str = "") -> list[str]:
    # No MCP, no user/project settings, no slash commands. Tools off unless explicitly given
    # (only read-only web tools are ever enabled, for job search).
    args = [
        _bin("claude"), "-p",
        "--system-prompt", system_prompt,
        "--tools", tools,
        "--strict-mcp-config",
        "--setting-sources", "",
        "--disable-slash-commands",
        "--no-session-persistence",
    ]
    if model:
        args += ["--model", model]
    if tools:
        args += ["--allowedTools", tools.replace(",", " ")]
    return args


class ClaudeChat:
    def __init__(self, system_prompt: str, model: str) -> None:
        args = _claude_args(model, system_prompt) + [
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            "--include-partial-messages",
        ]
        self.model = model
        self._proc = subprocess.Popen(
            args, cwd=config.CLAUDE_WORKDIR,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, creationflags=_NO_WINDOW, env=_env(),
        )
        self.turns = 0
        self._lock = threading.Lock()
        self._stderr: list[str] = []
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        for line in self._proc.stderr:
            self._stderr.append(line)
            del self._stderr[:-50]

    streaming = True  # the reply arrives token by token (see stream())

    def send(self, text: str) -> str:
        return "".join(self.stream(text)).strip()

    def stream(self, text: str, trace=telemetry.NULL):
        """Yield the reply as it is written (text deltas from --include-partial-messages). The turn is always read
        to its end, even if the caller stops early, so the next turn starts clean. With a telemetry `trace`, every
        step of the CLI's stream is recorded (request written, API response start, each text delta, result)."""
        t_wait = telemetry.now_ms()
        with self._lock:
            trace.add_span("llm.lock_wait", t_wait)
            if self._proc.poll() is not None:
                raise LLMError("Claude process exited: " + "".join(self._stderr[-5:]))
            self.turns += 1
            msg = {"type": "user", "message": {"role": "user", "content": text}}
            self._proc.stdin.write(json.dumps(msg) + "\n")
            self._proc.stdin.flush()
            trace.mark("llm.sent", provider="claude", model=self.model, chars=len(text), session_turn=self.turns,
                       text=text)
            parts: list[str] = []
            streamed, done = False, False
            n_delta = 0
            try:
                for line in self._proc.stdout:
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    kind = ev.get("type")
                    if kind == "stream_event":
                        inner = ev.get("event") or {}
                        delta = inner.get("delta") or {}
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            streamed = True
                            n_delta += 1
                            trace.mark("llm.first_text" if n_delta == 1 else "llm.delta", n=n_delta,
                                       chars=len(delta["text"]), text=delta["text"])
                            yield delta["text"]
                        elif inner.get("type") == "message_start":
                            usage = (inner.get("message") or {}).get("usage") or {}
                            trace.mark("llm.message_start", input_tokens=usage.get("input_tokens"),
                                       cache_read_tokens=usage.get("cache_read_input_tokens"),
                                       cache_write_tokens=usage.get("cache_creation_input_tokens"))
                        elif inner.get("type") in ("message_delta", "message_stop", "content_block_stop"):
                            trace.mark("llm." + inner["type"], stop_reason=delta.get("stop_reason"),
                                       output_tokens=(inner.get("usage") or {}).get("output_tokens"))
                    elif kind == "assistant" and not streamed:
                        for block in ev.get("message", {}).get("content", []):
                            if block.get("type") == "text":
                                parts.append(block["text"])
                    elif kind == "system":
                        trace.mark("llm.system", subtype=ev.get("subtype"))
                    elif kind == "result":
                        done = True
                        trace.mark("llm.result", deltas=n_delta, error=bool(ev.get("is_error")), **_result_meta(ev))
                        if ev.get("is_error"):
                            raise LLMError(str(ev.get("result") or ev.get("subtype")))
                        if not streamed:  # an older CLI without partial messages: the whole reply at once
                            yield (ev.get("result") or "".join(parts)).strip()
                        return
                raise LLMError("Claude process closed unexpectedly: " + "".join(self._stderr[-5:]))
            finally:
                if not done and self._proc.poll() is None:
                    for line in self._proc.stdout:  # drain the rest of this turn
                        if line.startswith("{") and '"type":"result"' in line.replace(" ", ""):
                            break

    def close(self) -> None:
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            self._proc.kill()


def _claude_run(prompt: str, system_prompt: str, model: str, timeout: int, tools: str,
                schema: dict | None = None) -> tuple[str, dict | None]:
    args = _claude_args(model, system_prompt, tools) + ["--output-format", "json"]
    if schema:
        args += ["--json-schema", json.dumps(schema)]
    res = subprocess.run(args, input=prompt, capture_output=True, text=True, encoding="utf-8", check=False,
                         cwd=config.CLAUDE_WORKDIR, timeout=timeout, creationflags=_NO_WINDOW, env=_env())
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"Resposta inválida do Claude: {res.stdout[:300]} {res.stderr[:300]}") from e
    _meta.last = _result_meta(data)
    if data.get("is_error"):
        raise LLMError(str(data.get("result")))
    out = data.get("structured_output")
    return (data.get("result") or "").strip(), out if isinstance(out, dict) else None


# =============================================================================================
# Codex CLI (ChatGPT plan)
# =============================================================================================
def _strict(schema: dict) -> dict:
    """OpenAI structured outputs want additionalProperties:false on every object."""
    if isinstance(schema, dict):
        schema = {k: _strict(v) for k, v in schema.items()}
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
    elif isinstance(schema, list):
        schema = [_strict(x) for x in schema]
    return schema


def _codex_run(prompt: str, system_prompt: str, model: str, timeout: int, tools: str,
               schema: dict | None = None) -> tuple[str, dict | None]:
    with tempfile.TemporaryDirectory(prefix="eh-codex-") as tmp:
        out_file = os.path.join(tmp, "last.txt")
        # `--search` (live web search) is a top-level flag: it must come before `exec`.
        args = [_bin("codex"), *(["--search"] if tools else []), "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--ephemeral",
                "--color", "never", "--json", "-C", str(config.CLAUDE_WORKDIR), "-o", out_file]
        if model:
            args += ["-m", model]
        if schema:
            sf = os.path.join(tmp, "schema.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(_strict(schema), f)
            args += ["--output-schema", sf]
        args.append("-")  # prompt from stdin
        res = subprocess.run(args, input=_inline(system_prompt, prompt), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=False, cwd=config.CLAUDE_WORKDIR,
                             timeout=timeout, creationflags=_NO_WINDOW, env=_env())
        text = ""
        if os.path.exists(out_file):
            with open(out_file, encoding="utf-8") as f:
                text = f.read().strip()
    if not text:
        err = ""
        for line in res.stdout.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") in ("error", "turn.failed"):
                err = ev.get("message") or (ev.get("error") or {}).get("message") or err
            elif ev.get("type") == "item.completed" and (ev.get("item") or {}).get("type") == "agent_message":
                text = (ev["item"].get("text") or "").strip()
        if not text:
            msg = err or res.stderr.strip()[-300:] or f"código {res.returncode}"
            if "refresh token" in msg or "sign in again" in msg or "401" in msg:
                msg = "Sua sessão do ChatGPT expirou. Faça login de novo em Configurações › Inteligência artificial."
            raise LLMError("Codex: " + msg)
    data = None
    if schema:
        try:
            data = json.loads(text)
        except ValueError:
            data = None
    return text, data


# =============================================================================================
# Antigravity CLI (Gemini, Google AI plan)
# =============================================================================================
def _agy_run(prompt: str, system_prompt: str, model: str, timeout: int, tools: str,
             schema: dict | None = None) -> tuple[str, dict | None]:
    args = [_bin("gemini"), "-p", _inline(system_prompt, prompt), "--output-format", "json",
            "--mode", "plan", "--disable-slash-commands", "--print-timeout", f"{max(30, timeout - 5)}s"]
    if model:
        args += ["--model", model]
    if schema:
        args += ["--json-schema", json.dumps(schema)]
    try:
        res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
                             stdin=subprocess.DEVNULL, cwd=config.CLAUDE_WORKDIR, timeout=timeout,
                             creationflags=_NO_WINDOW, env=_env())
    except subprocess.TimeoutExpired as e:
        raise LLMError("O Antigravity não respondeu a tempo. Confira se você fez login (Configurações › "
                       "Inteligência artificial › Fazer login).") from e
    out = res.stdout.strip()
    m = re.search(r"\{.*\}", out, re.DOTALL)
    data = None
    if m:
        try:
            data = json.loads(m.group(0))
        except ValueError:
            data = None
    if not data:
        err = (res.stderr or out).strip()
        if "not logged" in err.lower() or "login" in err.lower():
            raise LLMError("Antigravity sem login. Faça login em Configurações › Inteligência artificial.")
        raise LLMError("Antigravity: " + (err[-300:] or "sem resposta (atualize com 'agy update')."))
    if data.get("status") not in (None, "success", "ok", "completed") and not data.get("response"):
        raise LLMError("Antigravity: " + str(data.get("error") or data.get("status")))
    structured = data.get("structured_output")
    return str(data.get("response") or "").strip(), structured if isinstance(structured, dict) else None


_RUNNERS = {"claude": _claude_run, "codex": _codex_run, "gemini": _agy_run}


def _call(prompt: str, system_prompt: str, target: str | None, timeout: int, tools: str,
          schema: dict | None = None, trace=None) -> tuple[str, dict | None]:
    """Runs one CLI call, recorded as a span of `trace` or, without one, as its own "llm" trace."""
    pid, model = _target(target)
    own = trace is None
    tr = telemetry.start("llm", role=target if target in ROLES else "", provider=pid, model=model) if own else trace
    _meta.last = {}
    attrs = {"provider": pid, "model": model, "role": target if target in ROLES else "", "prompt_chars": len(prompt),
             "system_chars": len(system_prompt), "tools": tools, "schema": bool(schema)}
    try:
        with tr.span("llm.call", **attrs) as sp:
            text, data = _RUNNERS[pid](prompt, system_prompt, model, timeout, tools, schema)
            sp.update(reply_chars=len(text), structured=data is not None, **(getattr(_meta, "last", {}) or {}))
    except Exception as e:
        if own:
            tr.finish(ok=False, error=f"{type(e).__name__}: {e}"[:300])
        raise
    if own:
        tr.finish(ok=True, reply_chars=len(text), **(getattr(_meta, "last", {}) or {}))
    return text, data


# =============================================================================================
# public API
# =============================================================================================
def ask(prompt: str, system_prompt: str, model: str | None = None, timeout: int = 300, tools: str = "",
        trace=None) -> str:
    """`model` is a role (chat/feedback/helper) or, for compatibility, a Claude model name."""
    return _call(prompt, system_prompt, model, timeout, tools, trace=trace)[0]


def ask_json(prompt: str, system_prompt: str, model: str | None = None, tools: str = "",
             schema: dict | None = None, timeout: int = 400) -> dict:
    """One-shot call that must return a JSON object.
    With `schema`, the CLI validates structured output where it can (robust for long generated texts).
    Otherwise (or when that fails), the JSON is parsed from the text reply, retrying once."""
    last = ""
    if schema:
        try:
            text, data = _call(prompt, system_prompt, model, timeout, tools, schema)
            if isinstance(data, dict):
                return data
            last = text
        except LLMError as e:
            if "schema" not in str(e).lower():
                raise
            log.warning("structured output failed, falling back to text JSON: %s", e)
    for attempt in range(2):
        p = prompt if attempt == 0 and not last else prompt + "\n\nIMPORTANT: reply with ONLY one valid JSON object."
        if schema:
            p += "\nJSON Schema of the object:\n" + json.dumps(schema)
        last = last or ask(p, system_prompt, model, timeout=timeout, tools=tools)
        m = re.search(r"\{.*\}", last, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        last = ""
    raise LLMError("O modelo não devolveu um JSON válido.")


class HistoryChat:
    """Conversation for providers without a long-lived headless mode: each turn sends the dialogue so far.
    No streaming: the reply arrives whole, so the voice can only start after it."""

    streaming = False

    def __init__(self, system_prompt: str, role: str = "chat") -> None:
        self.system, self.role = system_prompt, role
        self.turns: list[tuple[str, str]] = []
        self._lock = threading.Lock()

    def send(self, text: str, trace=None) -> str:
        with self._lock:
            if text == "[START]":
                prompt = "The call is starting now. Say your natural opening line."
            else:
                so_far = "\n".join(f"{'LEARNER' if who == 'user' else 'YOU'}: {t}" for who, t in self.turns)
                prompt = (f"Conversation so far:\n{so_far}\n\n" if so_far else "") + f"LEARNER: {text}\n\n" \
                         "Write ONLY your next spoken reply (plain text, in character)."
            reply = ask(prompt, self.system, self.role, timeout=120, trace=trace)
            if text != "[START]":
                self.turns.append(("user", text))
            self.turns.append(("assistant", reply))
            return reply

    def stream(self, text: str, trace=telemetry.NULL):
        yield self.send(text, trace)

    def close(self) -> None:
        pass


def ChatProcess(system_prompt: str, model: str | None = None):
    pid, role_model = config.role("chat")
    if model or pid == "claude":
        return ClaudeChat(system_prompt, model or role_model)
    return HistoryChat(system_prompt, "chat")


def test(pid: str) -> dict:
    """A real round-trip through the provider's CLI, the only reliable sign-in check."""
    import time
    p = providers.PROVIDERS[pid]
    model = config.role("chat")[1] if config.role("chat")[0] == pid else p["defaults"]["chat"]
    t0 = time.time()
    try:
        out = _RUNNERS[pid]("Reply with exactly: ok", "You are a connectivity check. Reply with one word.",
                            model, 90, "")[0]
        res = {"ok": True, "message": f"respondeu “{out[:24]}” em {time.time() - t0:.0f} s"}
    except subprocess.TimeoutExpired:
        res = {"ok": False, "message": "não respondeu em 90 s (login pendente?)"}
    except Exception as e:  # noqa: BLE001
        res = {"ok": False, "message": str(e)[:300]}
    res["at"] = time.time()
    providers.TESTS[pid] = res
    return res
