"""Speaking metrics from word timestamps. Focus: fluency and intelligibility, not accent."""
from __future__ import annotations

import re

from . import config

FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm"}


def _norm(w: str) -> str:
    return re.sub(r"[^a-z']", "", w.lower())


def turn_metrics(words: list[dict]) -> dict:
    content = [w for w in words if _norm(w["w"]) and _norm(w["w"]) not in FILLERS]
    fillers = sum(1 for w in words if _norm(w["w"]) in FILLERS)
    pauses = []
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap >= config.LONG_PAUSE_S:
            pauses.append(round(gap, 1))
    speak_time = (words[-1]["end"] - words[0]["start"]) if words else 0.0
    unclear = [w["w"] for w in content if w["p"] < config.UNCLEAR_PROB]
    return {
        "words": len(content),
        "speak_time": round(speak_time, 1),
        "wpm": round(len(content) / speak_time * 60) if speak_time > 2 else None,
        "long_pauses": len(pauses),
        "longest_pause": max(pauses) if pauses else 0,
        "fillers": fillers,
        "unclear": unclear,
        "clarity": round(1 - len(unclear) / len(content), 2) if content else None,
    }


def marked_text(words: list[dict], fallback: str) -> str:
    """Transcript with low-confidence words marked as word(?) for the LLM."""
    if not words:
        return fallback
    out = []
    for w in words:
        t = w["w"]
        if _norm(t) and _norm(t) not in FILLERS and w["p"] < config.UNCLEAR_PROB:
            t = f"{t}(?)"
        out.append(t)
    return " ".join(out)


def session_metrics(turn_ms: list[dict]) -> dict:
    ms = [m for m in turn_ms if m and m.get("words")]
    if not ms:
        return {}
    words = sum(m["words"] for m in ms)
    time = sum(m["speak_time"] for m in ms)
    unclear = sum(len(m["unclear"]) for m in ms)
    fillers = sum(m["fillers"] for m in ms)
    return {
        "turns": len(ms),
        "words": words,
        "speak_time": round(time, 1),
        "wpm": round(words / time * 60) if time > 2 else None,
        "long_pauses": sum(m["long_pauses"] for m in ms),
        "pauses_per_min": round(sum(m["long_pauses"] for m in ms) / (time / 60), 1) if time > 10 else None,
        "fillers_per_min": round(fillers / (time / 60), 1) if time > 10 else None,
        "clarity": round(1 - unclear / words, 3) if words else None,
        "avg_turn_words": round(words / len(ms), 1),
    }


def stats_text(m: dict) -> str:
    if not m:
        return "(no speech data)"
    return (f"words={m.get('words')}, speaking_time={m.get('speak_time')}s, wpm={m.get('wpm')}, "
            f"long_pauses(>{config.LONG_PAUSE_S}s)={m.get('long_pauses')}, "
            f"fillers_per_min={m.get('fillers_per_min')}, recognised_clearly={m.get('clarity')}, "
            f"avg_words_per_answer={m.get('avg_turn_words')}")
