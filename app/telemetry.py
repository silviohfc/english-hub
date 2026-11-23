"""Local telemetry: a detailed, timestamped timeline of every call, kept on disk for analysis.

A *trace* is one unit of work the learner waits on: a call turn, a line spoken from a button, a transcription, an
LLM request, a model load. It collects events from every part that touched it:

  src "server"  this process (STT, the chat model's stream, the text cuts, the voice pipeline, what was sent)
  src "worker"  the Orpheus worker process (queue, first token, each decoded block, llama-server timings)
  src "client"  the browser (recording, request, each frame received, each block scheduled, gaps, the end)
  src "gpu"     GPU samples (utilization, memory, clock, power) taken while the trace was open

Every event carries `ts`: epoch milliseconds from the system clock, which all three processes share (same machine),
so the timelines line up without any conversion. An event with `dur` (ms) is a span; one without it is a mark.

Traces are written as JSON, one file each: data/telemetry/<YYYY-MM-DD>/<HHMMSS>-<kind>-<id>.json (rewritten when
late events, like the browser's, arrive). Nothing leaves the computer. ENGLISH_HUB_TELEMETRY=0 turns it off;
days older than ENGLISH_HUB_TELEMETRY_DAYS (30) are deleted at startup.
"""
from __future__ import annotations

import collections
import contextlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from . import config

log = logging.getLogger("telemetry")

ENABLED = (config._env("TELEMETRY") or "1") != "0"
KEEP_DAYS = int(config._env("TELEMETRY_DAYS") or 30)
DIR = config.DATA_DIR / "telemetry"
MAX_EVENTS = 20_000  # per trace: a runaway loop can't fill the disk


def now_ms() -> float:
    return round(time.time() * 1000, 2)


class Trace:
    """Thread-safe event collector for one unit of work. `mark()` for instants, `span()` for intervals,
    `extend()` for events measured elsewhere (worker, browser). `finish()` saves it; it can still receive events
    afterwards (they are saved again)."""

    def __init__(self, kind: str, **attrs) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.attrs = dict(attrs)
        self.start = now_ms()
        self.end: float | None = None
        self.events: list[dict] = []
        self.metrics: dict = {}
        self._lock = threading.Lock()
        self._path: Path | None = None
        self.mark("trace.start", **attrs)
        if ENABLED:
            gpu.open(self)

    # -- recording -------------------------------------------------------------------------
    def _add(self, ev: dict) -> None:
        with self._lock:
            if len(self.events) < MAX_EVENTS:
                self.events.append(ev)

    def mark(self, name: str, src: str = "server", ts: float | None = None, **attrs) -> None:
        self._add({"ts": ts if ts is not None else now_ms(), "src": src, "name": name, **_clean(attrs)})

    def add_span(self, name: str, start: float, end: float | None = None, src: str = "server", **attrs) -> None:
        end = end if end is not None else now_ms()
        self._add({"ts": start, "dur": round(end - start, 2), "src": src, "name": name, **_clean(attrs)})

    @contextlib.contextmanager
    def span(self, name: str, src: str = "server", **attrs):
        """with trace.span("stt") as s: ...; s["words"] = 12   (keys set on `s` are saved with the span)"""
        t0, extra = now_ms(), {}
        try:
            yield extra
        except Exception as e:
            extra["error"] = f"{type(e).__name__}: {e}"[:300]
            raise
        finally:
            self.add_span(name, t0, src=src, **attrs, **extra)

    def extend(self, events: list[dict], src: str, **attrs) -> None:
        for ev in events or []:
            if isinstance(ev, dict) and isinstance(ev.get("ts"), (int, float)) and isinstance(ev.get("name"), str):
                self._add({**_clean(ev), **_clean(attrs), "src": src})

    def set(self, **attrs) -> None:
        """Attributes of the whole trace (scenario, engine, ...)."""
        self.attrs.update(_clean(attrs))

    def metric(self, **values) -> None:
        """Summary numbers of the trace (first_sound_ms, gaps, ...), shown in the list and easy to aggregate."""
        self.metrics.update(_clean(values))

    # -- saving ----------------------------------------------------------------------------
    def finish(self, **metrics) -> "Trace":
        self.metric(**metrics)
        if self.end is None:
            self.end = now_ms()
            self.mark("trace.end")
            if ENABLED:
                gpu.close(self)
        self.save()
        return self

    def to_dict(self) -> dict:
        with self._lock:
            events = sorted(self.events, key=lambda e: e["ts"])
        return {"id": self.id, "kind": self.kind, "start": self.start, "end": self.end,
                "attrs": self.attrs, "metrics": self.metrics, "events": events}

    def summary(self) -> dict:
        return {"id": self.id, "kind": self.kind, "start": self.start, "end": self.end,
                "attrs": self.attrs, "metrics": self.metrics}

    def save(self) -> None:
        if not ENABLED:
            return
        RECENT[self.id] = self
        while len(RECENT) > 120:  # in memory for late events (the browser's) and fast reads
            RECENT.popitem(last=False)
        try:
            if self._path is None:
                lt = time.localtime(self.start / 1000)
                day = DIR / time.strftime("%Y-%m-%d", lt)
                day.mkdir(parents=True, exist_ok=True)
                self._path = day / f"{time.strftime('%H%M%S', lt)}-{self.kind}-{self.id}.json"
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as e:
            log.warning("cannot save trace %s: %s", self.id, e)


def _clean(d: dict) -> dict:
    """JSON-safe values (numbers, strings, bools, None, short lists/dicts of those)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, float):
            v = round(v, 3)
        elif isinstance(v, str) and len(v) > 2000:
            v = v[:2000] + "…"
        elif not isinstance(v, (int, str, bool, type(None), list, dict)):
            v = str(v)
        out[k] = v
    return out


class _Null:
    """Stands in for a trace where there is none, so callers never need `if trace:`."""
    id = ""

    def mark(self, *a, **k): pass
    def add_span(self, *a, **k): pass
    def extend(self, *a, **k): pass
    def set(self, *a, **k): pass
    def metric(self, *a, **k): pass
    def finish(self, *a, **k): return self

    @contextlib.contextmanager
    def span(self, *a, **k):
        yield {}


NULL = _Null()
RECENT: "collections.OrderedDict[str, Trace]" = collections.OrderedDict()


def start(kind: str, **attrs):
    return Trace(kind, **attrs) if ENABLED else NULL


# ---------------------------------------------------------------------------------------------
# reading back
# ---------------------------------------------------------------------------------------------
def _files(days: int = KEEP_DAYS) -> list[Path]:
    if not DIR.exists():
        return []
    out = []
    for day in sorted(DIR.iterdir(), reverse=True)[:days]:
        if day.is_dir():
            out += sorted(day.glob("*.json"), reverse=True)
    return out


def listing(limit: int = 200, kind: str = "") -> list[dict]:
    rows = []
    for f in _files():
        if kind and f"-{kind}-" not in f.name:
            continue
        tid = f.stem.rsplit("-", 1)[-1]
        if tid in RECENT:
            rows.append(RECENT[tid].summary())
        else:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                rows.append({k: d.get(k) for k in ("id", "kind", "start", "end", "attrs", "metrics")})
            except (OSError, ValueError):
                continue
        if len(rows) >= limit:
            break
    return rows


def get(tid: str) -> dict | None:
    if tid in RECENT:
        return RECENT[tid].to_dict()
    for f in _files():
        if f.stem.endswith("-" + tid):
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
    return None


def find(tid: str) -> Trace | None:
    """A trace still in memory (to add late events to it)."""
    return RECENT.get(tid)


_req_lock = threading.Lock()


def request_log(method: str, path: str, status: int, t0: float, trace_id: str | None = None) -> None:
    """One line per API request (until the response headers; streams have their own trace) in
    data/telemetry/<day>/requests.jsonl."""
    if not ENABLED:
        return
    line = json.dumps({"ts": t0, "dur": round(now_ms() - t0, 2), "method": method, "path": path,
                       "status": status, "trace": trace_id}, separators=(",", ":"))
    try:
        day = DIR / time.strftime("%Y-%m-%d", time.localtime(t0 / 1000))
        day.mkdir(parents=True, exist_ok=True)
        with _req_lock, open(day / "requests.jsonl", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def prune() -> None:
    if not DIR.exists():
        return
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - KEEP_DAYS * 86400))
    for day in DIR.iterdir():
        if day.is_dir() and day.name < cutoff:
            shutil.rmtree(day, ignore_errors=True)


# ---------------------------------------------------------------------------------------------
# GPU sampling (NVIDIA): one nvidia-smi process streams samples while any trace is open
# ---------------------------------------------------------------------------------------------
class GpuSampler:
    PERIOD_MS = 200
    FIELDS = "utilization.gpu,memory.used,memory.total,clocks.sm,power.draw"

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.open_traces: dict[str, Trace] = {}
        self.samples: list[dict] = []
        self.proc: subprocess.Popen | None = None
        self.exe = shutil.which("nvidia-smi")
        self.idle_since: float | None = None

    def open(self, trace: Trace) -> None:
        if not self.exe:
            return
        with self.lock:
            self.open_traces[trace.id] = trace
            self.idle_since = None
            if self.proc is None or self.proc.poll() is not None:
                try:
                    self.proc = subprocess.Popen(
                        [self.exe, f"--query-gpu={self.FIELDS}", "--format=csv,noheader,nounits",
                         f"-lms={self.PERIOD_MS}"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                except OSError:
                    self.exe = None
                    return
                threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _read(self, proc: subprocess.Popen) -> None:
        for line in proc.stdout:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue

            def num(x):
                try:
                    return float(x)
                except ValueError:
                    return None
            s = {"ts": now_ms(), "name": "gpu", "util": num(parts[0]), "mem_mb": num(parts[1]),
                 "mem_total_mb": num(parts[2]), "sm_mhz": num(parts[3]), "power_w": num(parts[4])}
            with self.lock:
                self.samples.append(s)
                del self.samples[:-36_000]  # 2 h at 5 samples/s
                for tid, tr in list(self.open_traces.items()):  # never finished (a bug): stop sampling for it
                    if s["ts"] - tr.start > 15 * 60_000:
                        del self.open_traces[tid]
                if not self.open_traces:
                    # keep a little history for the next trace; stop after 30 s with nothing open
                    del self.samples[:-10]
                    self.idle_since = self.idle_since or time.time()
                    if time.time() - self.idle_since > 30:
                        proc.terminate()
                        self.proc = None
                        return

    def close(self, trace: Trace) -> None:
        with self.lock:
            if self.open_traces.pop(trace.id, None) is None:
                return
            mine = [s for s in self.samples if s["ts"] >= trace.start - self.PERIOD_MS]
            if not self.open_traces:
                del self.samples[:-10]
        trace.extend(mine, "gpu")

    def stop(self) -> None:
        with self.lock:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
            self.proc = None


gpu = GpuSampler()
