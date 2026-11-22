"""FastAPI server: serves the UI and the local practice API on http://127.0.0.1:8765"""
from __future__ import annotations

import json
import logging
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, llm, metrics, prompts
from .stt import stt
from .tts import tts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="dev-english")
STATIC = config.ROOT / "app" / "static"

# Live conversations: session_id -> {"chat": ChatProcess, "scenario": str}
LIVE: dict[int, dict] = {}


def resolve_scenario(sid: str) -> dict:
    """Built-in scenario id (e.g. 'recruiter') or generated one ('c12') -> unified dict."""
    if sid in prompts.SCENARIOS:
        return {"id": sid, "kind": "classic", **prompts.SCENARIOS[sid]}
    if sid.startswith("c") and sid[1:].isdigit():
        c = db.get_custom(int(sid[1:]))
        if c:
            p = c.get("persona") or {}
            name = p.get("name") or "Alex"
            brief = (f"You are {name}, {p.get('role', '')}. Personality: {p.get('style', 'professional')}.\n\n"
                     f"{c.get('persona_brief_en', '')}")
            return {"id": sid, "kind": c["kind"], "title": c.get("title", ""), "title_pt": c.get("title_pt", ""),
                    "desc_pt": c.get("desc_pt", ""), "persona": name, "voice": p.get("voice", "am_michael"),
                    "brief": brief, "criteria": c.get("success_criteria") or [],
                    "context_en": json.dumps(c.get("briefing_pt") or {}, ensure_ascii=False),
                    "retell_question": c.get("retell_question")}
    raise HTTPException(404, "scenario not found")


def scenario_info(sid: str) -> dict:
    try:
        s = resolve_scenario(sid)
    except HTTPException:
        return {"id": sid, "title_pt": "(cenário apagado)", "persona": "Partner", "voice": "am_michael", "kind": "?"}
    return {k: s.get(k) for k in ("id", "kind", "title", "title_pt", "persona", "voice", "retell_question")}


@app.on_event("startup")
def _warmup() -> None:
    def load():
        for name, fn in (("stt", stt.load), ("tts", tts.load)):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                log.error("%s failed to load: %s", name, e)
    threading.Thread(target=load, daemon=True).start()


@app.on_event("shutdown")
def _shutdown() -> None:
    for live in LIVE.values():
        live["chat"].close()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/status")
def status():
    return {"stt": stt.device and f"{stt.model_name} ({stt.device})", "tts": tts._k is not None,
            "chat_model": config.CHAT_MODEL, "feedback_model": config.FEEDBACK_MODEL}


@app.get("/api/scenarios")
def scenarios():
    return [{"id": k, **{f: v[f] for f in ("title", "title_pt", "desc_pt", "persona", "voice")}}
            for k, v in prompts.SCENARIOS.items()]


# ---------- conversation ----------

class StartReq(BaseModel):
    scenario: str
    level: str = "friendly"


@app.post("/api/session/start")
async def start_session(req: StartReq):
    scn = resolve_scenario(req.scenario)
    sid = db.create_session(req.scenario, req.level, scn.get("title_pt") or scn.get("title"))
    system = prompts.chat_system_prompt(scn, req.level, db.watch_items(), db.training_phrases())

    def run():
        chat = llm.ChatProcess(system)
        return chat, chat.send("[START]")

    try:
        chat, opening = await run_in_threadpool(run)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Claude CLI error: {e}") from e
    LIVE[sid] = {"chat": chat, "scenario": req.scenario}
    db.add_turn(sid, "assistant", opening)
    return {"session_id": sid, "persona": scn["persona"], "voice": scn["voice"], "reply": opening}


def _live(sid: int) -> dict:
    live = LIVE.get(sid)
    if not live:
        raise HTTPException(404, "session not active (server restarted?)")
    return live


@app.post("/api/session/{sid}/turn")
async def turn(sid: int, audio: UploadFile | None = File(None), text: str | None = Form(None)):
    live = _live(sid)
    if audio is not None:
        heard = await run_in_threadpool(stt.transcribe, await audio.read(), "en")
    else:
        heard = {"text": (text or "").strip(), "words": [], "duration": 0}
    if not heard["text"]:
        return {"empty": True}
    m = metrics.turn_metrics(heard["words"]) if heard["words"] else None
    db.add_turn(sid, "user", heard["text"], heard["words"], m)
    try:
        reply = await run_in_threadpool(live["chat"].send, metrics.marked_text(heard["words"], heard["text"]))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Claude CLI error: {e}") from e
    db.add_turn(sid, "assistant", reply)
    return {"user": {"text": heard["text"], "words": heard["words"], "metrics": m}, "reply": reply}


class EndReq(BaseModel):
    reveals: int = 0
    replays: int = 0
    text_mode: str = ""


@app.post("/api/session/{sid}/end")
async def end_session(sid: int, req: EndReq | None = None):
    live = LIVE.pop(sid, None)
    if live:
        live["chat"].close()
    s = db.get_session(sid)
    if not s:
        raise HTTPException(404)
    turns = s["turns"]
    user_turns = [t for t in turns if t["role"] == "user"]
    sm = metrics.session_metrics([t["metrics"] for t in user_turns])
    if req:
        sm.update({"listening_reveals": req.reveals, "listening_replays": req.replays, "text_mode": req.text_mode})
    if not user_turns:
        db.finish_session(sid, sm, None)
        return {"session_id": sid, "metrics": sm, "report": None}

    try:
        scn = resolve_scenario(s["scenario"])
    except HTTPException:
        scn = {"title": s.get("title") or "", "persona": "Partner"}
    persona = scn["persona"].upper()
    lines = []
    for t in turns:
        if t["role"] == "user":
            lines.append("LEARNER: " + metrics.marked_text(t["words"] or [], t["text"]))
        else:
            lines.append(f"{persona}: {t['text']}")
    prompt = prompts.feedback_prompt(scn, "\n".join(lines), metrics.stats_text(sm),
                                     db.notebook(include_resolved=False), db.training_phrases())
    try:
        report = await run_in_threadpool(llm.ask_json, prompt, prompts.FEEDBACK_SYSTEM, config.FEEDBACK_MODEL,
                                         "", prompts.feedback_schema(scn))
    except Exception as e:  # noqa: BLE001
        db.finish_session(sid, sm, None)
        raise HTTPException(502, f"Feedback failed: {e}") from e
    db.update_notebook(report.get("mistakes", []), report.get("improved_keys", []))
    db.mark_phrases_used(report.get("phrases_used", []))
    db.finish_session(sid, sm, report)
    return {"session_id": sid, "metrics": sm, "report": report}


@app.get("/api/sessions")
def sessions():
    return db.list_sessions()


@app.get("/api/session/{sid}")
def session(sid: int):
    s = db.get_session(sid)
    if not s:
        raise HTTPException(404)
    s["scenario_info"] = scenario_info(s["scenario"])
    return s


# ---------- notebook ----------

@app.get("/api/notebook")
def notebook():
    return db.notebook()


class ResolveReq(BaseModel):
    resolved: bool


@app.post("/api/notebook/{key}")
def resolve(key: str, req: ResolveReq):
    db.set_resolved(key, req.resolved)
    return {"ok": True}


# ---------- voice ----------

class TTSReq(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


@app.post("/api/tts")
async def speak(req: TTSReq):
    wav = await run_in_threadpool(tts.synth, req.text, req.voice, max(0.6, min(1.4, req.speed)))
    return Response(wav, media_type="audio/wav")


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("en")):
    heard = await run_in_threadpool(stt.transcribe, await audio.read(), language)
    heard["metrics"] = metrics.turn_metrics(heard["words"]) if heard["words"] else None
    return heard


# ---------- helpers ----------

class HelpReq(BaseModel):
    text: str
    context: str = ""


@app.post("/api/help")
async def how_do_i_say(req: HelpReq):
    prompt = f"Conversation context (last line): {req.context}\nI want to say (Portuguese): {req.text}"
    try:
        answer = await run_in_threadpool(llm.ask, prompt, prompts.HELPER_SYSTEM, config.HELPER_MODEL)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, str(e)) from e
    return {"answer": answer}


class RetellReq(BaseModel):
    session_id: int | None = None
    question: str
    round: int
    seconds: int
    text: str
    metrics: dict | None = None
    want_feedback: bool = False


@app.post("/api/retell")
async def retell(req: RetellReq):
    db.add_retell(req.session_id, req.question, req.round, req.seconds, req.text, req.metrics or {})
    if not req.want_feedback or not req.text.strip():
        return {"feedback": None}
    stats = metrics.stats_text(req.metrics or {})
    try:
        fb = await run_in_threadpool(llm.ask_json, prompts.retell_prompt(req.question, req.text, stats),
                                     prompts.RETELL_SYSTEM, config.HELPER_MODEL)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, str(e)) from e
    return {"feedback": fb}


# ---------- profile ----------

class ProfileReq(BaseModel):
    text: str


@app.get("/api/profile")
def get_profile():
    return {"text": db.get_kv("profile")}


@app.put("/api/profile")
def put_profile(req: ProfileReq):
    db.set_kv("profile", req.text.strip())
    return {"ok": True}


# ---------- generated scenarios ----------

@app.get("/api/situations")
def situations():
    return [{"id": k, "title_pt": v["title_pt"], "desc_pt": v["desc_pt"], "icon": v["icon"]}
            for k, v in prompts.SITUATIONS.items()]


def _clean_generated(data: dict) -> dict:
    p = data.get("persona") if isinstance(data.get("persona"), dict) else {}
    if p.get("voice") not in prompts.VOICES:
        p["voice"] = "am_michael"
    p.setdefault("name", "Alex")
    data["persona"] = p
    if not data.get("persona_brief_en"):
        raise llm.LLMError("generated scenario has no persona brief")
    return data


class SituationReq(BaseModel):
    kind: str
    pressure: str = "calm"


@app.post("/api/custom/situation")
async def gen_situation(req: SituationReq):
    if req.kind not in prompts.SITUATIONS:
        raise HTTPException(400, "unknown situation")
    prompt = prompts.situation_prompt(req.kind, db.get_kv("profile"), req.pressure)
    try:
        data = _clean_generated(await run_in_threadpool(
            llm.ask_json, prompt, prompts.GEN_SYSTEM, config.FEEDBACK_MODEL, "", prompts.SCENARIO_SCHEMA))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha ao gerar cenário: {e}") from e
    data["source"] = {"type": "situation", "kind": req.kind, "pressure": req.pressure,
                      "label": prompts.SITUATIONS[req.kind]["title_pt"]}
    return _public(db.get_custom(db.add_custom("situation", data)))


class JobSearchReq(BaseModel):
    query: str


@app.post("/api/jobs/search")
async def job_search(req: JobSearchReq):
    prompt = prompts.job_search_prompt(req.query, db.get_kv("profile"))
    try:
        data = await run_in_threadpool(llm.ask_json, prompt, prompts.JOB_SEARCH_SYSTEM, config.FEEDBACK_MODEL,
                                       llm.WEB_TOOLS, prompts.JOBS_SCHEMA)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha na busca: {e}") from e
    return {"jobs": data.get("jobs", [])}


class JobScenarioReq(BaseModel):
    job: dict | None = None
    text: str | None = None
    stage: str = "technical"


STAGE_LABELS = {"recruiter": "Triagem com recruiter", "technical": "Entrevista técnica",
                "behavioral": "Entrevista comportamental"}


@app.post("/api/custom/job")
async def gen_job(req: JobScenarioReq):
    if req.stage not in prompts.INTERVIEW_STAGES:
        raise HTTPException(400, "unknown stage")
    job = req.job or (req.text or "").strip()
    if not job:
        raise HTTPException(400, "job or text required")
    tools = "WebFetch" if isinstance(job, str) and "http" in job else ""
    prompt = prompts.job_scenario_prompt(job, db.get_kv("profile"), req.stage)
    try:
        data = _clean_generated(await run_in_threadpool(llm.ask_json, prompt, prompts.GEN_SYSTEM,
                                                        config.FEEDBACK_MODEL, tools, prompts.SCENARIO_SCHEMA))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha ao gerar entrevista: {e}") from e
    src = req.job or {}
    data["source"] = {"type": "job", "stage": req.stage, "company": src.get("company"), "url": src.get("url"),
                      "job_title": src.get("title"), "label": STAGE_LABELS[req.stage]}
    return _public(db.get_custom(db.add_custom("job", data)))


def _public(c: dict) -> dict:
    c = dict(c)
    c.pop("persona_brief_en", None)  # hidden from the learner: it's the partner's script
    return c


@app.get("/api/custom")
def custom_list():
    return db.list_custom()


@app.get("/api/custom/{cid}")
def custom_get(cid: int):
    c = db.get_custom(cid)
    if not c:
        raise HTTPException(404)
    return _public(c)


@app.delete("/api/custom/{cid}")
def custom_delete(cid: int):
    db.delete_custom(cid)
    return {"ok": True}


# ---------- phrase bank ----------

class PhraseReq(BaseModel):
    text: str
    meaning_pt: str | None = None
    example: str | None = None
    context: str = ""
    source: str = "manual"


@app.get("/api/phrases")
def phrases():
    return {"phrases": db.list_phrases(), "due": len(db.due_phrases(1000))}


@app.post("/api/phrases")
async def add_phrase(req: PhraseReq):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "empty")
    if existing := db.find_phrase(text):
        return {**existing, "existed": True}
    meaning, example, note = req.meaning_pt, req.example, ""
    if not meaning or not example:  # let the model clean the phrase and explain it
        try:
            info = await run_in_threadpool(llm.ask_json, prompts.phrase_enrich_prompt(text, req.context),
                                           prompts.PHRASE_SYSTEM, config.HELPER_MODEL, "", prompts.PHRASE_SCHEMA)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"Falha ao explicar a frase: {e}") from e
        if existing := db.find_phrase(info.get("text") or text):
            return {**existing, "existed": True}
        text = info.get("text") or text
        meaning, example, note = meaning or info.get("meaning_pt"), example or info.get("example"), info.get("note_pt")
    return db.add_phrase(text, meaning or "", example or "", note or "", req.source)


@app.delete("/api/phrases/{pid}")
def del_phrase(pid: int):
    db.delete_phrase(pid)
    return {"ok": True}


@app.get("/api/phrases/due")
def due():
    return db.due_phrases()


class PhraseReviewReq(BaseModel):
    recall_ok: bool
    sentence: str = ""


@app.post("/api/phrases/{pid}/review")
async def review(pid: int, req: PhraseReviewReq):
    p = db.get_phrase(pid)
    if not p:
        raise HTTPException(404)
    result = {"used_correctly": False, "better": "", "feedback_pt": "Nada foi transcrito."}
    if req.sentence.strip():
        try:
            result = await run_in_threadpool(llm.ask_json, prompts.phrase_use_prompt(p, req.sentence),
                                             prompts.PHRASE_SYSTEM, config.HELPER_MODEL, "", prompts.PHRASE_USE_SCHEMA)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, str(e)) from e
    updated = db.review_phrase(pid, bool(req.recall_ok and result.get("used_correctly")))
    return {**result, "phrase": updated}


# ---------- vocabulary packs ----------

@app.get("/api/packs")
def packs():
    return [{"id": k, "icon": v["icon"], "title_pt": v["title_pt"]} for k, v in prompts.PACKS.items()]


class PackReq(BaseModel):
    pack: str | None = None
    custom_id: int | None = None


@app.post("/api/packs/generate")
async def gen_pack(req: PackReq):
    if req.custom_id:
        c = db.get_custom(req.custom_id)
        if not c:
            raise HTTPException(404, "scenario not found")
        theme = (f"the vocabulary needed for this specific conversation: {c.get('title')}. Context: "
                 f"{json.dumps(c.get('briefing_pt'), ensure_ascii=False)}. Requirements/expectations: "
                 f"{json.dumps(c.get('expectations_pt'), ensure_ascii=False)}")
    elif req.pack in prompts.PACKS:
        theme = prompts.PACKS[req.pack]["spec"]
    else:
        raise HTTPException(400, "unknown pack")
    known = [p["text"] for p in db.list_phrases()]
    prompt = prompts.pack_prompt(theme, db.get_kv("profile"), known, db.watch_items(10))
    try:
        data = await run_in_threadpool(llm.ask_json, prompt, prompts.PHRASE_SYSTEM, config.FEEDBACK_MODEL, "",
                                       prompts.PACK_SCHEMA)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha ao gerar pacote: {e}") from e
    items = [i for i in data.get("items", []) if i.get("text") and not db.find_phrase(i["text"])]
    return {"items": items}


class BulkReq(BaseModel):
    items: list[dict]
    source: str = "pacote"


@app.post("/api/phrases/bulk")
def add_bulk(req: BulkReq):
    added = 0
    for i in req.items:
        if i.get("text") and not db.find_phrase(i["text"]):
            db.add_phrase(i["text"], i.get("meaning_pt", ""), i.get("example", ""), i.get("note_pt", ""), req.source)
            added += 1
    return {"added": added}


def run() -> None:
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    run()
