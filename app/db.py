"""SQLite storage: sessions, turns, the mistake notebook and retell rounds."""
from __future__ import annotations

import json
import sqlite3
import threading
import re
from datetime import datetime, timedelta

from . import config, prompts

_lock = threading.Lock()
_conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.executescript("""
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, scenario TEXT, level TEXT, started_at TEXT, ended_at TEXT,
  metrics_json TEXT, report_json TEXT);
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, text TEXT,
  words_json TEXT, metrics_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS mistakes (
  key TEXT PRIMARY KEY, category TEXT, said TEXT, better TEXT, why_pt TEXT,
  count INTEGER DEFAULT 0, correct_count INTEGER DEFAULT 0, first_seen TEXT, last_seen TEXT,
  resolved INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS custom_scenarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, data_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS phrases (
  id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, norm TEXT UNIQUE, meaning_pt TEXT, example TEXT,
  note_pt TEXT, source TEXT, created_at TEXT, level INTEGER DEFAULT 0, next_review TEXT,
  reviews INTEGER DEFAULT 0, successes INTEGER DEFAULT 0, used_in_conversation INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS retells (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, question TEXT, round INTEGER,
  seconds INTEGER, text TEXT, metrics_json TEXT, created_at TEXT);
""")

try:
    _conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
except sqlite3.OperationalError:
    pass  # column already exists

RESOLVE_AFTER = 3  # correct uses needed to consider a mistake fixed


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def wipe() -> None:
    """Erase all of the learner's data (used by the uninstall screen); the schema stays."""
    with _lock:
        tables = [r[0] for r in _conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for t in tables:
            _conn.execute(f'DELETE FROM "{t}"')
        _conn.commit()
        _conn.execute("VACUUM")


def _exec(sql: str, args: tuple = ()) -> sqlite3.Cursor:
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur


def _rows(sql: str, args: tuple = ()) -> list[dict]:
    with _lock:
        return [dict(r) for r in _conn.execute(sql, args).fetchall()]


def create_session(scenario: str, level: str, title: str = "") -> int:
    return _exec("INSERT INTO sessions (scenario, level, title, started_at) VALUES (?,?,?,?)",
                 (scenario, level, title, _now())).lastrowid


def add_turn(session_id: int, role: str, text: str, words=None, metrics=None) -> None:
    _exec("INSERT INTO turns (session_id, role, text, words_json, metrics_json, created_at) VALUES (?,?,?,?,?,?)",
          (session_id, role, text, json.dumps(words) if words else None,
           json.dumps(metrics) if metrics else None, _now()))


def get_turns(session_id: int) -> list[dict]:
    rows = _rows("SELECT * FROM turns WHERE session_id=? ORDER BY id", (session_id,))
    for r in rows:
        r["words"] = json.loads(r.pop("words_json") or "null")
        r["metrics"] = json.loads(r.pop("metrics_json") or "null")
    return rows


def finish_session(session_id: int, metrics: dict, report: dict | None) -> None:
    _exec("UPDATE sessions SET ended_at=?, metrics_json=?, report_json=? WHERE id=?",
          (_now(), json.dumps(metrics), json.dumps(report) if report else None, session_id))


def get_session(session_id: int) -> dict | None:
    rows = _rows("SELECT * FROM sessions WHERE id=?", (session_id,))
    if not rows:
        return None
    s = rows[0]
    s["metrics"] = json.loads(s.pop("metrics_json") or "null")
    s["report"] = json.loads(s.pop("report_json") or "null")
    s["turns"] = get_turns(session_id)
    s["retells"] = _rows("SELECT * FROM retells WHERE session_id=? ORDER BY id", (session_id,))
    return s


def list_sessions(limit: int = 50) -> list[dict]:
    rows = _rows("SELECT id, scenario, level, title, started_at, ended_at, metrics_json, report_json FROM sessions "
                 "WHERE ended_at IS NOT NULL ORDER BY id DESC LIMIT ?", (limit,))
    for r in rows:
        r["metrics"] = json.loads(r.pop("metrics_json") or "null")
        rep = json.loads(r.pop("report_json") or "null") or {}
        r["scores"] = rep.get("scores")
    return rows


def notebook(include_resolved: bool = True) -> list[dict]:
    where = "" if include_resolved else "WHERE resolved=0"
    return _rows(f"SELECT * FROM mistakes {where} ORDER BY resolved, count DESC, last_seen DESC")


def watch_items(n: int = 5) -> list[dict]:
    return _rows("SELECT * FROM mistakes WHERE resolved=0 ORDER BY count DESC, last_seen DESC LIMIT ?", (n,))


def update_notebook(mistakes: list[dict], improved_keys: list[str]) -> None:
    now = _now()
    for m in mistakes or []:
        key = (m.get("key") or "").strip().lower()
        if not key or not m.get("said"):
            continue
        _exec("""INSERT INTO mistakes (key, category, said, better, why_pt, count, first_seen, last_seen)
                 VALUES (?,?,?,?,?,1,?,?)
                 ON CONFLICT(key) DO UPDATE SET count=count+1, last_seen=excluded.last_seen,
                   said=excluded.said, better=excluded.better, why_pt=excluded.why_pt, resolved=0""",
              (key, m.get("category"), m.get("said"), m.get("better"), m.get("why_pt"), now, now))
    for key in improved_keys or []:
        _exec("UPDATE mistakes SET correct_count=correct_count+1, "
              "resolved=CASE WHEN correct_count+1>=? THEN 1 ELSE resolved END WHERE key=?",
              (RESOLVE_AFTER, key.strip().lower()))


def set_resolved(key: str, resolved: bool) -> None:
    _exec("UPDATE mistakes SET resolved=? WHERE key=?", (1 if resolved else 0, key))


def add_retell(session_id: int | None, question: str, rnd: int, seconds: int, text: str, metrics: dict) -> None:
    _exec("INSERT INTO retells (session_id, question, round, seconds, text, metrics_json, created_at) "
          "VALUES (?,?,?,?,?,?,?)", (session_id, question, rnd, seconds, text, json.dumps(metrics), _now()))


# ---------- profile & generated scenarios ----------

def get_kv(key: str, default: str = "") -> str:
    rows = _rows("SELECT value FROM kv WHERE key=?", (key,))
    return rows[0]["value"] if rows else default


def set_kv(key: str, value: str) -> None:
    _exec("INSERT INTO kv (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def add_custom(kind: str, data: dict) -> int:
    return _exec("INSERT INTO custom_scenarios (kind, title, data_json, created_at) VALUES (?,?,?,?)",
                 (kind, data.get("title_pt") or data.get("title"), json.dumps(data, ensure_ascii=False), _now())).lastrowid


def get_custom(cid: int) -> dict | None:
    rows = _rows("SELECT * FROM custom_scenarios WHERE id=?", (cid,))
    if not rows:
        return None
    r = rows[0]
    data = json.loads(r["data_json"])
    if isinstance(data.get("persona"), dict):
        data["persona"]["voice"] = prompts.voice(data["persona"].get("voice"))
    return {"id": r["id"], "kind": r["kind"], "created_at": r["created_at"], **data}


def list_custom() -> list[dict]:
    rows = _rows("SELECT c.id, c.kind, c.title, c.created_at, c.data_json, "
                 "(SELECT COUNT(*) FROM sessions s WHERE s.scenario = 'c' || c.id AND s.ended_at IS NOT NULL) AS plays "
                 "FROM custom_scenarios c ORDER BY c.id DESC")
    for r in rows:
        d = json.loads(r.pop("data_json"))
        r["desc_pt"] = d.get("desc_pt")
        r["persona"] = (d.get("persona") or {}).get("name")
        r["voice"] = prompts.voice((d.get("persona") or {}).get("voice"))
        r["source"] = d.get("source")
    return rows


def delete_custom(cid: int) -> None:
    _exec("DELETE FROM custom_scenarios WHERE id=?", (cid,))


# ---------- phrase bank (spaced repetition, Leitner boxes) ----------

INTERVALS_DAYS = [1, 2, 4, 8, 16, 32]


def norm_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", text.lower())).strip()


def find_phrase(text: str) -> dict | None:
    rows = _rows("SELECT * FROM phrases WHERE norm=?", (norm_phrase(text),))
    return rows[0] if rows else None


def add_phrase(text: str, meaning_pt: str, example: str, note_pt: str, source: str) -> dict:
    _exec("""INSERT INTO phrases (text, norm, meaning_pt, example, note_pt, source, created_at, next_review)
             VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(norm) DO NOTHING""",
          (text.strip(), norm_phrase(text), meaning_pt, example, note_pt, source, _now(), _now()))
    return find_phrase(text)


def list_phrases() -> list[dict]:
    return _rows("SELECT * FROM phrases ORDER BY id DESC")


def get_phrase(pid: int) -> dict | None:
    rows = _rows("SELECT * FROM phrases WHERE id=?", (pid,))
    return rows[0] if rows else None


def delete_phrase(pid: int) -> None:
    _exec("DELETE FROM phrases WHERE id=?", (pid,))


def due_phrases(limit: int = 10) -> list[dict]:
    return _rows("SELECT * FROM phrases WHERE next_review IS NULL OR next_review<=? ORDER BY level, next_review LIMIT ?",
                 (_now(), limit))


def training_phrases(n: int = 5) -> list[dict]:
    """Phrases still being learned, offered to the conversation partner."""
    return _rows("SELECT * FROM phrases WHERE level < 4 ORDER BY level, used_in_conversation, id DESC LIMIT ?", (n,))


def review_phrase(pid: int, success: bool) -> dict:
    p = get_phrase(pid)
    if not p:
        return {}
    level = min(p["level"] + 1, len(INTERVALS_DAYS)) if success else 0
    nxt = (datetime.now() + timedelta(days=INTERVALS_DAYS[level - 1])) if success else datetime.now()
    _exec("UPDATE phrases SET level=?, next_review=?, reviews=reviews+1, successes=successes+? WHERE id=?",
          (level, nxt.isoformat(timespec="seconds"), 1 if success else 0, pid))
    return get_phrase(pid)


def mark_phrases_used(texts: list[str]) -> None:
    for t in texts or []:
        p = find_phrase(t)
        if p:
            _exec("UPDATE phrases SET used_in_conversation=used_in_conversation+1 WHERE id=?", (p["id"],))
            review_phrase(p["id"], True)
