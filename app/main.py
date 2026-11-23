"""FastAPI server: serves the UI and the local practice API on http://127.0.0.1:8765"""
from __future__ import annotations

import json
import logging
import threading

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, llm, metrics, prompts, providers, uninstall, voices
from . import setup as setup_mod
from .stt import stt
from .tts import tts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="english-hub")


@app.middleware("http")
async def _no_stale_ui(request, call_next):
    """The UI changes with every update: make the browser revalidate it instead of using a cached copy."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
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
            v = prompts.voice(p.get("voice"))
            name = p.get("name") or prompts.CHARACTERS[v]["name"]
            brief = (f"You are {name}, {p.get('role', '')}. Personality: {p.get('style', 'professional')}.\n\n"
                     f"{c.get('persona_brief_en', '')}")
            return {"id": sid, "kind": c["kind"], "title": c.get("title", ""), "title_pt": c.get("title_pt", ""),
                    "desc_pt": c.get("desc_pt", ""), "persona": name, "voice": v,
                    "brief": brief, "criteria": c.get("success_criteria") or [],
                    "context_en": json.dumps(c.get("briefing_pt") or {}, ensure_ascii=False),
                    "retell_question": c.get("retell_question")}
    raise HTTPException(404, "scenario not found")


def scenario_info(sid: str) -> dict:
    try:
        s = resolve_scenario(sid)
    except HTTPException:
        return {"id": sid, "title_pt": "(cenário apagado)", "persona": "Partner", "voice": prompts.DEFAULT_VOICE, "kind": "?"}
    return {k: s.get(k) for k in ("id", "kind", "title", "title_pt", "persona", "voice", "retell_question")}


@app.on_event("startup")
def _warmup() -> None:
    """Load models in the background when setup already ran and the files are on disk.
    Otherwise the setup screen downloads and loads them with visible progress."""
    def prewarm():
        # Import the heavy libraries and read the hardware now, so the first screen doesn't wait on them.
        try:
            import faster_whisper.utils  # noqa: F401
            import huggingface_hub  # noqa: F401
            setup_mod.hardware()
            setup_mod.models_state()
            for pid in providers.PROVIDERS:
                path = providers.resolve(pid)
                if path:
                    providers.version(pid, path)
        except Exception as e:  # noqa: BLE001
            log.warning("prewarm failed: %s", e)
    threading.Thread(target=prewarm, daemon=True).start()

    if not config.current()["setup_done"]:
        return
    state = setup_mod.models_state()
    if not (state["kokoro"] and all(state["whisper"].values())):
        log.info("Models missing; waiting for the setup screen.")
        return

    if voices.active() == "orpheus":
        voices.worker.warm()

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
    voices.worker.stop()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/status")
def status():
    flags = config.current()
    return {"stt": stt.device and f"{stt.model_name} ({stt.device}, {stt.compute})", "tts": tts._k is not None,
            "chat_model": f"{config.CHAT_PROVIDER}:{config.CHAT_MODEL or 'padrão'}",
            "feedback_model": f"{config.FEEDBACK_PROVIDER}:{config.FEEDBACK_MODEL or 'padrão'}",
            "track": config.TRACK,
            "setup_done": flags["setup_done"], "onboarding_done": flags["onboarding_done"],
            "installing": setup_mod.job.running,
            "voice_engine": voices.active(),
            "voice_rtf": (voices.worker.rtf or voices._mark().get("rtf")) if voices.active() == "orpheus" else None}


# ---------- first-run setup & settings ----------
@app.get("/api/setup")
async def setup_overview():
    return await run_in_threadpool(setup_mod.overview)


@app.get("/api/setup/job")
def setup_job():
    return setup_mod.job.snapshot()


class SettingsReq(BaseModel):
    values: dict


@app.post("/api/setup/settings")
def save_settings(req: SettingsReq):
    if setup_mod.job.running and any(k.startswith("whisper") for k in req.values):
        raise HTTPException(409, "Espere a instalação terminar para trocar o modelo.")
    try:
        return config.apply(req.values)
    except (TypeError, ValueError) as e:
        raise HTTPException(400, f"Valor inválido: {e}") from e


@app.post("/api/setup/install")
def setup_install():
    setup_mod.job.start()
    return setup_mod.job.snapshot()


# ---------- AI providers (Claude Code, Antigravity, Codex): install, sign in, test ----------
def _ai_overview() -> dict:
    roles = {r: dict(zip(("provider", "model"), config.role(r))) for r in providers.ROLES}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(providers.PROVIDERS)) as pool:  # each state runs the CLI's own commands
        states = list(pool.map(providers.state, providers.PROVIDERS))
    return {"providers": states, "roles": roles,
            "catalog": {pid: {"label": p["label"], "models": p["models"], "defaults": p["defaults"]}
                        for pid, p in providers.PROVIDERS.items()},
            "os": providers.system_label()}


@app.get("/api/ai")
async def ai_overview():
    return await run_in_threadpool(_ai_overview)


def _known(pid: str) -> None:
    if pid not in providers.PROVIDERS:
        raise HTTPException(404, "provedor desconhecido")


@app.post("/api/ai/{pid}/install")
def ai_install(pid: str):
    _known(pid)
    return providers.install(pid)


@app.post("/api/ai/{pid}/login")
def ai_login(pid: str):
    _known(pid)
    try:
        return providers.login(pid)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, str(e)) from e


@app.post("/api/ai/{pid}/logout")
def ai_logout(pid: str):
    _known(pid)
    return providers.logout(pid)


@app.post("/api/ai/{pid}/test")
async def ai_test(pid: str):
    _known(pid)
    return await run_in_threadpool(llm.test, pid)


@app.get("/api/ai/{pid}/task")
def ai_task(pid: str):
    _known(pid)
    return providers.TASKS.get(pid) or {"status": "idle"}


# ---------- uninstall ----------
@app.get("/api/uninstall")
async def uninstall_items():
    return {"items": await run_in_threadpool(uninstall.items), "folder": str(config.ROOT)}


class UninstallReq(BaseModel):
    ids: list[str]


@app.post("/api/uninstall")
async def uninstall_run(req: UninstallReq):
    for live in list(LIVE.values()):
        live["chat"].close()
    LIVE.clear()
    return await run_in_threadpool(uninstall.run, req.ids)


@app.post("/api/shutdown")
def shutdown():
    uninstall.shutdown()
    return {"ok": True}


@app.get("/api/scenarios")
def scenarios():
    return [{"id": k, **{f: prompts.SCENARIOS[k][f] for f in ("title", "title_pt", "desc_pt", "persona", "voice")}}
            for k in prompts.scenario_ids()]


# ---------- conversation ----------

class StartReq(BaseModel):
    scenario: str
    level: str = "friendly"


@app.post("/api/session/start")
async def start_session(req: StartReq):
    scn = resolve_scenario(req.scenario)
    sid = db.create_session(req.scenario, req.level, scn.get("title_pt") or scn.get("title"))
    system = prompts.chat_system_prompt(scn, req.level, db.watch_items(), db.training_phrases(),
                                        expressive=voices.expressive())

    def run():
        chat = llm.ChatProcess(system)
        return chat, chat.send("[START]")

    try:
        chat, opening = await run_in_threadpool(run)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Claude CLI error: {e}") from e
    LIVE[sid] = {"chat": chat, "scenario": req.scenario}
    # `say` keeps the sound tags (<laugh>...) for the expressive voice; captions and history get clean text.
    db.add_turn(sid, "assistant", voices.clean(opening))
    return {"session_id": sid, "persona": scn["persona"], "voice": scn["voice"], "reply": voices.clean(opening),
            "say": opening}


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
    db.add_turn(sid, "assistant", voices.clean(reply))
    return {"user": {"text": heard["text"], "words": heard["words"], "metrics": m}, "reply": voices.clean(reply),
            "say": reply}


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
        report = await run_in_threadpool(llm.ask_json, prompt, prompts.feedback_system(), "feedback",
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
    engine: str = ""  # preview a specific engine; default: the active one


@app.post("/api/tts")
async def speak(req: TTSReq):
    try:
        wav, meta = await run_in_threadpool(voices.synth, req.text, req.voice, max(0.6, min(1.4, req.speed)),
                                            req.engine or None)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return Response(wav, media_type="audio/wav", headers={
        "X-TTS-Engine": meta["engine"], "X-TTS-Speed": "native" if meta["speed_applied"] else "browser",
        "X-TTS-Fallback": "1" if meta["fallback"] else ""})


class StreamReq(BaseModel):
    text: str
    voice: str = "af_heart"


@app.post("/api/tts/stream")
async def speak_stream(req: StreamReq, request: Request):
    """Orpheus line as raw PCM (s16le, mono, 24 kHz), sent while it is generated so playback starts early.
    Closing the request (the learner interrupted) cancels what is left."""
    try:
        st = await run_in_threadpool(voices.stream, req.text, req.voice)
        it = iter(st)
        first = await run_in_threadpool(next, it, b"")
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e

    async def body():
        try:
            chunk = first
            # uvicorn doesn't fail the send when the browser hangs up, so check explicitly: an interrupted
            # line must stop generating right away, or the next line waits behind it.
            while chunk and not await request.is_disconnected():
                yield chunk
                chunk = await run_in_threadpool(next, it, b"")
        finally:
            st.close()

    return StreamingResponse(body(), media_type="audio/L16;rate=24000;channels=1",
                             headers={"X-TTS-Engine": "orpheus", "X-Sample-Rate": "24000", "Cache-Control": "no-store"})


# ---------- voice engines (Kokoro neutral, Orpheus expressive) ----------

@app.get("/api/voices")
def voices_overview():
    return voices.overview()


@app.post("/api/voices/install")
def voices_install():
    if not voices.support("orpheus")["ok"]:
        raise HTTPException(409, voices.support("orpheus")["reason"])
    voices.install.start()
    return voices.overview()


class UseReq(BaseModel):
    engine: str


@app.post("/api/voices/use")
def voices_use(req: UseReq):
    try:
        return voices.use(req.engine)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


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
        answer = await run_in_threadpool(llm.ask, prompt, prompts.helper_system(), "helper")
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
                                     prompts.retell_system(), "helper")
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
    return [{"id": k, "title_pt": prompts.SITUATIONS[k]["title_pt"], "desc_pt": prompts.SITUATIONS[k]["desc_pt"],
             "icon": prompts.SITUATIONS[k]["icon"]} for k in prompts.situation_ids()]


def _clean_generated(data: dict) -> dict:
    p = data.get("persona") if isinstance(data.get("persona"), dict) else {}
    ch = prompts.character(p.get("voice"))
    # Each voice is one character: keep its name even if the model invented another one.
    old = (p.get("name") or "").strip()
    p.update(voice=ch["voice"], name=ch["name"])
    if not p.get("style"):
        p["style"] = ch["style"]
    data["persona"] = p
    if not data.get("persona_brief_en"):
        raise llm.LLMError("generated scenario has no persona brief")
    if old and old != ch["name"]:
        for key in ("persona_brief_en", "desc_pt"):
            data[key] = (data.get(key) or "").replace(old, ch["name"])
        b = data.get("briefing_pt")
        if isinstance(b, dict):
            for k, val in b.items():
                if isinstance(val, str):
                    b[k] = val.replace(old, ch["name"])
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
            llm.ask_json, prompt, prompts.gen_system(), "feedback", "", prompts.SCENARIO_SCHEMA))
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
        data = await run_in_threadpool(llm.ask_json, prompt, prompts.JOB_SEARCH_SYSTEM, "feedback",
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
        data = _clean_generated(await run_in_threadpool(llm.ask_json, prompt, prompts.gen_system(),
                                                        "feedback", tools, prompts.SCENARIO_SCHEMA))
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
                                           prompts.phrase_system(), "helper", "", prompts.PHRASE_SCHEMA)
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
                                             prompts.phrase_system(), "helper", "", prompts.PHRASE_USE_SCHEMA)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, str(e)) from e
    updated = db.review_phrase(pid, bool(req.recall_ok and result.get("used_correctly")))
    return {**result, "phrase": updated}


# ---------- vocabulary packs ----------

@app.get("/api/packs")
def packs():
    return [{"id": k, "icon": prompts.PACKS[k]["icon"], "title_pt": prompts.PACKS[k]["title_pt"]} for k in prompts.pack_ids()]


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
        data = await run_in_threadpool(llm.ask_json, prompt, prompts.phrase_system(), "feedback", "",
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
    import webbrowser

    import uvicorn
    url = f"http://{config.HOST}:{config.PORT}"
    if config._env("NO_BROWSER") != "1":
        # Open the browser once the server is accepting connections (setup screen on first run).
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  english-hub rodando em {url}  (feche esta janela para encerrar)\n", flush=True)
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    run()
