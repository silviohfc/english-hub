"""Universal speech streaming: text (whole, or arriving token by token from the chat model) -> PCM, for any engine.

Every engine speaks through the same pipeline and the same wire format, so the player in the browser is one:

  text deltas -> Segmenter (sentence-sized pieces, as soon as each is complete)
              -> engine (Kokoro: one synthesis per piece; Orpheus: queued in the worker while earlier pieces play)
              -> edges trimmed of the engine's own silence, plus a pause chosen by the punctuation
              -> ("pcm", bytes) ... ("end", index) per piece

PCM is always 16-bit mono at 24 kHz (both engines' native rate). Pauses are part of the audio, so a boundary
sounds the same on every engine, in the cache and live.
"""
from __future__ import annotations

import logging
import queue
import re
import threading
import time
from typing import Iterable, Iterator

import numpy as np

log = logging.getLogger("speech")

SR = 24_000
_END = re.compile(r"[.!?…]+[\"')\]]*(?=\s|$)")
_CLAUSE = re.compile(r"[,;:](?=\s)")
# Silence a piece starts and ends with in the engine's own audio is cut; these pads keep the attack and the decay.
LEAD_PAD, TAIL_PAD = 0.03, 0.06
SILENCE = 0.012  # |amplitude| (0..1) under which a 10 ms window counts as silence


class Policy:
    """How an engine wants its text cut. The first piece is short (it decides when the voice starts); later ones
    are longer, because every boundary costs a restart on slow engines and a pause on all of them."""

    def __init__(self, first_min: int, rest_min: int, rest_max: int, first_clause: int = 0) -> None:
        self.first_min, self.rest_min, self.rest_max = first_min, rest_min, rest_max
        # > 0: the first piece may end at a comma once it has this many characters (the voice starts sooner).
        self.first_clause = first_clause


POLICY = {
    # Kokoro's time to synthesize grows with the length and its prosody survives a cut at a comma.
    "kokoro": Policy(first_min=12, rest_min=60, rest_max=220, first_clause=20),
    # Orpheus restarts its prompt and its intonation on every piece: fewer, longer ones after the first.
    "orpheus": Policy(first_min=15, rest_min=120, rest_max=240),
}


class Segmenter:
    """Cuts text into sentence-sized pieces as it arrives. `feed()` returns the pieces completed by a delta,
    `flush()` the rest. Never cuts inside a sound tag (<laugh>) and never mid-sentence unless a sentence is
    longer than the policy's maximum (then at a comma or a space)."""

    def __init__(self, policy: Policy) -> None:
        self.p, self.buf, self.count = policy, "", 0

    def _min(self) -> int:
        return self.p.first_min if self.count == 0 else self.p.rest_min

    def feed(self, delta: str) -> list[str]:
        self.buf += delta
        out = []
        while True:
            piece = self._take()
            if piece is None:
                return out
            out.append(piece)

    def _take(self) -> str | None:
        text = self.buf
        cut = None
        for m in _END.finditer(text):
            if "<" in text[:m.end()] and text[:m.end()].count("<") > text[:m.end()].count(">"):
                continue  # inside a tag
            # A sentence end only counts once the next character is known (could be "...", or "3.5").
            if m.end() >= len(text):
                break
            if len(text[:m.end()].strip()) >= self._min():
                cut = m.end()
                break
        if self.count == 0 and self.p.first_clause:
            for m in _CLAUSE.finditer(text, 0, cut or len(text)):
                if len(text[:m.end()].strip()) >= self.p.first_clause and text[:m.end()].count("<") <= text[:m.end()].count(">"):
                    cut = m.end()
                    break
        if cut is None and len(text) > self.p.rest_max and self.count:
            # A run-on sentence: cut at the last comma (or space) before the maximum.
            head = text[:self.p.rest_max]
            cut = max(head.rfind(", ") + 1, head.rfind("; ") + 1) or head.rfind(" ")
            if cut <= 0:
                return None
        if cut is None:
            return None
        piece, self.buf = text[:cut].strip(), text[cut:]
        if not piece:
            return None
        self.count += 1
        return piece

    def flush(self) -> list[str]:
        piece, self.buf = self.buf.strip(), ""
        if not piece:
            return []
        self.count += 1
        return [piece]


def split(text: str, engine: str) -> list[str]:
    s = Segmenter(POLICY.get(engine, POLICY["kokoro"]))
    return s.feed(text) + s.flush()


def pause_after(piece: str) -> float:
    """Seconds of silence after a piece (when another follows), like a speaker breathing between sentences."""
    t = re.sub(r"<[^>]+>", "", piece).rstrip(" \"')]")
    if t.endswith("?"):
        return 0.22
    if t.endswith(("!", ".", "…")):
        return 0.18
    if t.endswith((",", ";", ":")):
        return 0.08
    return 0.05


def silence(seconds: float) -> bytes:
    return bytes(int(SR * seconds) * 2)


class Trimmer:
    """Removes the silence an engine puts at the start and end of each piece, while streaming: audio is let through
    as soon as it is known not to be trailing silence (a silent run at the end is held until more voice comes)."""

    HOLD = int(0.1 * SR)
    MAX_HOLD = int(1.5 * SR)

    def __init__(self) -> None:
        self.started, self.held = False, np.zeros(0, dtype=np.int16)

    @staticmethod
    def _first_voiced(x: np.ndarray) -> int | None:
        win = SR // 100
        thr = SILENCE * 32768
        for i in range(0, len(x) - win + 1, win):
            if np.abs(x[i:i + win]).max() > thr:
                return i
        return None

    @staticmethod
    def _last_voiced(x: np.ndarray) -> int:
        win = SR // 100
        thr = SILENCE * 32768
        for i in range(len(x) - win, -1, -win):
            if np.abs(x[i:i + win]).max() > thr:
                return i + win
        return 0

    def push(self, pcm: bytes) -> bytes:
        x = np.concatenate([self.held, np.frombuffer(pcm, dtype=np.int16)])
        if not self.started:
            i = self._first_voiced(x)
            if i is None:
                self.held = x[-int(LEAD_PAD * SR):]  # keep only what could become the lead pad
                return b""
            self.started = True
            x = x[max(0, i - int(LEAD_PAD * SR)):]
        # Hold back the trailing silent run (it may be the piece's end) plus a little voiced audio; a pause longer
        # than MAX_HOLD is part of the speech and goes through.
        cut = min(len(x) - self.HOLD, self._last_voiced(x))
        cut = max(cut, len(x) - self.MAX_HOLD)
        if cut <= 0:
            self.held = x
            return b""
        self.held = x[cut:]
        return x[:cut].tobytes()

    def end(self) -> bytes:
        x, self.held = self.held, np.zeros(0, dtype=np.int16)
        if not self.started or not len(x):
            return b""
        stop = min(len(x), self._last_voiced(x) + int(TAIL_PAD * SR))
        return x[:stop].tobytes()


# ---------------------------------------------------------------------------------------------
# engines: each turns a (lazy) stream of pieces into ("piece", text) / ("pcm", bytes) / ("end", i) events
# ---------------------------------------------------------------------------------------------
class Speech:
    """One line being spoken. Pieces can be added while it plays (`add`, then `finish`), or given all at once.
    Iterate for events: ("piece", text) before a piece's audio, ("pcm", bytes), ("end", index) after it.
    `close()` stops generating (safe from any thread); `stats` has the timings."""

    def __init__(self, engine: str, voice: str, speed: float = 1.0) -> None:
        self.engine, self.voice, self.speed = engine, voice, speed
        self.pieces: "queue.Queue[str | None]" = queue.Queue()
        self.closed = threading.Event()
        self.cancelled = False
        self.stats = {"engine": engine, "pieces": 0, "audio_s": 0.0, "gen_s": 0.0, "first_audio_s": None}
        self._t0 = time.time()
        self._orpheus = None

    # producer side
    def add(self, piece: str) -> None:
        if piece.strip():
            self.pieces.put(piece)

    def finish(self) -> None:
        self.pieces.put(None)

    def close(self) -> None:
        if not self.closed.is_set():
            self.closed.set()
            self.pieces.put(None)
        if self._orpheus is not None:
            self.cancelled = self._orpheus.close() or self.cancelled

    # consumer side
    def _next_piece(self) -> str | None:
        while not self.closed.is_set():
            try:
                return self.pieces.get(timeout=0.25)
            except queue.Empty:
                continue
        return None

    def _pieces(self) -> Iterator[tuple[str, float]]:
        """(piece, lead pause): the pause after a piece is played at the start of the next one, so a piece never
        waits for the one after it (the last piece simply gets none)."""
        prev = None
        while (cur := self._next_piece()) is not None:
            yield cur, pause_after(prev) if prev is not None else 0.0
            prev = cur

    def _emit(self, pcm: bytes):
        if pcm:
            if self.stats["first_audio_s"] is None:
                self.stats["first_audio_s"] = round(time.time() - self._t0, 3)
            self.stats["audio_s"] += len(pcm) / 2 / SR
            yield "pcm", pcm

    def __iter__(self):
        try:
            gen = self._kokoro() if self.engine == "kokoro" else self._orpheus_events()
            for ev in gen:
                if self.closed.is_set():
                    self.cancelled = True
                    return
                yield ev
        finally:
            self.stats["audio_s"] = round(self.stats["audio_s"], 2)
            self.stats["gen_s"] = round(self.stats["gen_s"], 2)
            if self._orpheus is not None:
                self._orpheus.close()

    def _kokoro(self):
        from .tts import tts
        from .voices import clean

        for i, (piece, lead) in enumerate(self._pieces()):
            yield "piece", clean(piece)
            t = time.time()
            samples = tts.synth_pcm(clean(piece), self.voice, self.speed)
            self.stats["gen_s"] += time.time() - t
            self.stats["pieces"] += 1
            tr = Trimmer()
            yield from self._emit(silence(lead) + tr.push(samples) + tr.end())
            yield "end", i

    def _orpheus_events(self):
        from . import voices

        live = voices.worker.live(voices.ORPHEUS_VOICE.get(self.voice, "tara"))
        self._orpheus = live
        if self.closed.is_set():
            live.close()
        leads: list[float] = []
        texts: list[str] = []

        def feed():  # hand pieces to the worker as they arrive: it generates the next while this one plays
            try:
                for piece, lead in self._pieces():
                    leads.append(lead)
                    texts.append(voices.clean(piece))
                    live.add(voices._orpheus_text(piece))
            finally:
                live.finish()
        threading.Thread(target=feed, daemon=True).start()
        t = time.time()
        tr, i, fresh = Trimmer(), 0, True
        for kind, data in live:
            if kind == "pcm":
                out = tr.push(data)
                if out and fresh:
                    yield "piece", texts[i] if i < len(texts) else ""
                    out, fresh = silence(leads[i] if i < len(leads) else 0.0) + out, False
                yield from self._emit(out)
            else:  # piece `data` finished
                tail = tr.end()
                if fresh:
                    yield "piece", texts[i] if i < len(texts) else ""
                    if tail:
                        tail = silence(leads[i] if i < len(leads) else 0.0) + tail
                self.stats["pieces"] += 1
                yield from self._emit(tail)
                yield "end", data
                tr, i, fresh = Trimmer(), data + 1, True
        self.stats["gen_s"] = time.time() - t


def engine_for(requested: str | None = None) -> str:
    """The engine that will really speak: the requested (or active) one if it can right now, otherwise Kokoro."""
    from . import voices

    engine = requested or voices.active()
    if engine == "orpheus":
        if not voices.orpheus_ok():
            return "kokoro"
        voices.worker.start()
        if voices.worker.state != "ready":
            log.warning("Orpheus unavailable (%s); speaking with Kokoro.", voices.worker.error)
            return "kokoro"
    return engine


def speak(text: str, engine: str, voice: str, speed: float = 1.0) -> Speech:
    """A whole line, cut by the engine's policy."""
    sp = Speech(engine, voice, speed)
    for piece in split(text, engine):
        sp.add(piece)
    sp.finish()
    return sp


def pieces_from(deltas: Iterable[str], engine: str) -> Iterator[str]:
    seg = Segmenter(POLICY.get(engine, POLICY["kokoro"]))
    for d in deltas:
        yield from seg.feed(d)
    yield from seg.flush()
