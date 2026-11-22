"use strict";

// =====================================================================
// utils
// =====================================================================
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const view = $("#view");

async function api(path, opts = {}) {
  const init = { ...opts };
  if (opts.json !== undefined) {
    init.method = init.method || "POST";
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(opts.json);
  }
  const res = await fetch(path, init);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  return res.headers.get("content-type")?.includes("json") ? res.json() : res.blob();
}

const store = {
  get(k, d) { try { const v = localStorage.getItem("de." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("de." + k, JSON.stringify(v)); } catch { /* ignore */ } },
};

// Captions: "off" (audio only, like a real call), "reveal" (blurred until clicked), "on" (always visible).
const LEGACY_CC = { real: "off", reveal: "reveal", visible: "on" };
const settings = {
  get level() { return store.get("level", "friendly"); },
  get speed() { return store.get("speed", 0.95); },
  get cc() { return store.get("cc", LEGACY_CC[store.get("textMode", "")] || "reveal"); },
};

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "");
const fmtDay = (iso) => (iso ? new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) : "");
const pct = (x) => (x == null ? "–" : Math.round(x * 100) + "%");
const dash = (x) => (x == null || x === "" ? "–" : x);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const initial = (name) => esc((name || "?").trim().charAt(0).toUpperCase());

// =====================================================================
// icons (Lucide-style line icons)
// =====================================================================
const ICONS = {
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
  square: '<rect width="12" height="12" x="6" y="6" rx="2"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
  star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1Z"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  briefcase: '<rect width="20" height="14" x="2" y="7" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  bug: '<path d="M8 2l1.9 1.9M14.1 3.9 16 2"/><path d="M9 7.1v-1a3 3 0 1 1 6 0v1"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6"/><path d="M12 20v-9M6.5 9C4.6 8.8 3 7.1 3 5M6 13H2M3 21c0-2.1 1.7-3.9 3.8-4M21 5c0 2.1-1.6 3.8-3.5 4M22 13h-4M17.2 17c2.1.1 3.8 1.9 3.8 4"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4.1 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5Z"/>',
  pr: '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M6 9v12"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  message: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
  clapper: '<path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/><path d="m6.2 5.3 3.1 3.9M12.4 3.4l3.1 4"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2Z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7Z"/>',
  history: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  list: '<path d="m3 17 2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8"/>',
  cc: '<rect width="18" height="14" x="3" y="5" rx="2"/><path d="M7 15h4M15 15h2M7 11h2M13 11h4"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  arrowLeft: '<path d="m12 19-7-7 7-7M19 12H5"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  languages: '<path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
  package: '<path d="m7.5 4.3 9 5.1"/><path d="M21 8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
  link: '<path d="M15 3h6v6M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  sparkles: '<path d="m12 3 1.9 5.8L20 10l-5.1 3.7L16.8 20 12 16.4 7.2 20l1.9-6.3L4 10l6.1-1.2Z"/>',
};
const ic = (name, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
const SITUATION_ICONS = { bug: "bug", blocker: "ban", delay: "clock", incident: "flame", review: "pr", clarify: "help", explain: "message" };
const PACK_ICONS = { daily: "clock", bugs: "bug", review: "pr", interview: "briefcase", phrasal: "link", false_friends: "alert", fillers: "message", meetings: "user" };

// =====================================================================
// audio
// =====================================================================
let currentAudio = null;
function stopAudio() { if (currentAudio) { currentAudio.pause(); currentAudio = null; } }

async function speak(text, voice) {
  stopAudio();
  const blob = await api("/api/tts", { json: { text, voice, speed: settings.speed } });
  const audio = new Audio(URL.createObjectURL(blob));
  currentAudio = audio;
  await audio.play().catch(() => {});
  return new Promise((r) => { audio.onended = r; audio.onpause = r; });
}

class Recorder {
  async start() {
    stopAudio();
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream, { mimeType: "audio/webm;codecs=opus" });
    this.rec.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.rec.start();
    this.startedAt = Date.now();
  }
  get active() { return this.rec?.state === "recording"; }
  stop() {
    return new Promise((resolve) => {
      if (!this.active) return resolve(null);
      this.rec.onstop = () => {
        this.stream.getTracks().forEach((t) => t.stop());
        resolve(new Blob(this.chunks, { type: "audio/webm" }));
      };
      this.rec.stop();
    });
  }
}

async function transcribe(blob, language = "en") {
  const fd = new FormData();
  fd.append("audio", blob, "speech.webm");
  fd.append("language", language);
  return api("/api/transcribe", { method: "POST", body: fd });
}

// =====================================================================
// phrase bank: save from anywhere, toast
// =====================================================================
let toastTimer = null;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3500);
}

const starBtn = (obj) => `<button class="icon-btn star" title="Salvar em Minhas frases" aria-label="Salvar em Minhas frases" data-save="${esc(JSON.stringify(obj))}">${ic("star")}</button>`;
const sayBtn = (text, label = "Ouvir") => `<button class="icon-btn" title="${label}" aria-label="${label}" data-say="${esc(text)}">${ic("volume")}</button>`;

async function savePhrase(item) {
  if (!item.text?.trim()) return;
  toast(`Salvando "${item.text}"…`);
  try {
    const r = await api("/api/phrases", { json: item });
    toast(r.existed ? `"${r.text}" já está nas suas frases` : `Salvo: "${r.text}" — ${r.meaning_pt || ""}`);
  } catch (e) { toast("Não deu para salvar: " + e.message); }
}

// Global delegates: [data-save] saves a phrase, [data-say] plays it.
let currentVoice = "af_heart";
document.addEventListener("click", (e) => {
  const save = e.target.closest("[data-save]");
  if (save) {
    e.stopPropagation();
    try { savePhrase(JSON.parse(save.dataset.save)); } catch { /* ignore */ }
    return;
  }
  const say = e.target.closest("[data-say]");
  if (say) { e.stopPropagation(); speak(say.dataset.say, say.dataset.voice || currentVoice); }
}, true);

// =====================================================================
// shell: nav, status, router
// =====================================================================
const NAV = [["home", "Praticar", "mic"], ["phrases", "Minhas frases", "star"], ["history", "Histórico", "history"],
  ["notebook", "Caderno de erros", "list"], ["profile", "Perfil", "user"]];
$("#nav").innerHTML = NAV.map(([id, label, icon]) => `<a href="#${id}" data-nav="${id}">${ic(icon)}<span>${label}</span></a>`).join("");
const NAV_OWNER = { home: "home", jobs: "home", situations: "home", classics: "home", brief: "home", chat: "home", report: "history",
  retell: "history", phrases: "phrases", train: "phrases", history: "history", notebook: "notebook", profile: "profile" };

async function pollStatus() {
  const el = $("#status");
  try {
    const s = await api("/api/status");
    if (s.stt && s.tts) {
      el.textContent = "pronto para falar";
      el.title = `voz: ${s.stt} · conversa: ${s.chat_model} · feedback: ${s.feedback_model}`;
      el.className = "status ok";
      return;
    }
    el.textContent = "carregando voz…";
    el.className = "status";
  } catch { el.textContent = "servidor desligado"; el.className = "status off"; }
  setTimeout(pollStatus, 2500);
}

let SCENARIOS = [];
let cleanup = null;
const scenariosList = async () => (SCENARIOS.length ? SCENARIOS : (SCENARIOS = await api("/api/scenarios")));

async function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  stopAudio();
  const [name, arg, arg2] = (location.hash.slice(1) || "home").split("/");
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === (NAV_OWNER[name] || "home")));
  view.innerHTML = "";
  window.scrollTo({ top: 0 });
  const pages = { home: renderHome, jobs: renderJobs, situations: renderSituations, classics: renderClassics, brief: renderBrief,
    chat: renderChat, report: renderReport, retell: renderRetell, phrases: renderPhrases, train: renderTrain,
    history: renderHistory, notebook: renderNotebook, profile: renderProfile };
  try {
    await (pages[name] || renderHome)(arg, arg2);
  } catch (e) {
    view.innerHTML = `<div class="panel"><p class="error">Algo deu errado: ${esc(e.message)}</p><p class="muted" style="margin-top:8px">
      Verifique se o servidor está rodando (start.bat) e tente de novo.</p><p style="margin-top:12px"><a href="#home">Voltar ao início</a></p></div>`;
  }
}
window.addEventListener("hashchange", route);

const pageHead = (title, lead = "", back = "") => `<header class="page-head">
  ${back ? `<a class="back" href="${back[0]}">${ic("arrowLeft")}${esc(back[1])}</a>` : ""}
  <h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ""}</header>`;
const loadingPanel = (msg) => `<div class="panel loading" role="status"><div class="skel"><i></i><i></i><i></i></div></div>
  <p class="muted" style="margin-top:12px">${esc(msg)}</p>`;
const emptyState = (icon, text) => `<div class="empty">${ic(icon)}<p>${text}</p></div>`;

// Shows progress while a scenario is generated, then opens its briefing.
async function generate(msg, promise) {
  window.scrollTo({ top: 0 });
  view.innerHTML = pageHead("Preparando a cena…", esc(msg)) + loadingPanel("Isso usa o Claude pela sua assinatura. Pode levar até um minuto.");
  try {
    const c = await promise;
    location.hash = "brief/" + c.id;
  } catch (e) {
    view.innerHTML = pageHead("Não deu para gerar") + `<div class="panel"><p class="error">${esc(e.message)}</p>
      <p style="margin-top:12px"><a href="javascript:history.back()">Voltar</a></p></div>`;
  }
}

let pendingScenario = null;
async function startScenario(id) {
  if (String(id).startsWith("c")) {
    const c = await api("/api/custom/" + String(id).slice(1));
    pendingScenario = { id, title_pt: c.title_pt, title: c.title, persona: c.persona?.name, role: c.persona?.role, briefing: c };
  } else {
    const s = (await scenariosList()).find((x) => x.id === id);
    pendingScenario = { ...s, role: s.title };
  }
  const target = "#chat/" + id;
  if (location.hash === target) route(); else location.hash = target;
}

// =====================================================================
// home: one next episode + three ways to practise
// =====================================================================
async function renderHome() {
  const [scs, custom, profile, ph] = await Promise.all([scenariosList(), api("/api/custom"), api("/api/profile"), api("/api/phrases")]);
  const fresh = custom.find((c) => !c.plays) || custom[0];
  const next = fresh
    ? { id: "c" + fresh.id, title: fresh.title, desc: fresh.desc_pt, persona: fresh.persona, tag: fresh.source?.label || "Cenário salvo" }
    : { id: scs[0].id, title: scs[0].title_pt, desc: scs[0].desc_pt, persona: scs[0].persona, tag: "Clássico" };

  view.innerHTML = `
  <div class="home-grid">
    <div>
      <section class="stage hero" aria-labelledby="next-title">
        <div class="top-line">
          <span class="lower-third"><span class="avatar">${initial(next.persona)}</span>
            <span><span class="name">${esc(next.persona)}</span><br><span class="role">Próxima cena · ${esc(next.tag)}</span></span></span>
        </div>
        <div class="copy">
          <h1 id="next-title">${esc(next.title)}</h1>
          <p>${esc(next.desc)}</p>
          <div class="cta">
            <button class="btn btn-primary btn-lg" id="go-next">${ic("mic")} Falar agora</button>
            ${fresh ? `<a class="btn btn-ghost" href="#brief/${fresh.id}">${ic("file")} Ler o roteiro antes</a>` : ""}
          </div>
        </div>
      </section>

      <section class="section" aria-labelledby="ways">
        <h2 id="ways">Escolha outra prática</h2>
        <nav class="rows">
          <a class="row-item" href="#jobs"><span class="lead-ic">${ic("briefcase")}</span>
            <span class="body"><span class="title">Entrevista para uma vaga real</span>
            <span class="desc">Busque vagas abertas ou cole uma. O entrevistador lê seu perfil e investiga seus gaps.</span></span>${ic("chevron", "chev")}</a>
          <a class="row-item" href="#situations"><span class="lead-ic">${ic("bug")}</span>
            <span class="body"><span class="title">Situação de trabalho</span>
            <span class="desc">Relatar bug, bloqueio, atraso, incidente, code review… com a sua stack.</span></span>${ic("chevron", "chev")}</a>
          <a class="row-item" href="#classics"><span class="lead-ic">${ic("message")}</span>
            <span class="body"><span class="title">Conversas clássicas e cenários salvos</span>
            <span class="desc">Triagem, técnica, comportamental, daily, conversa livre${custom.length ? ` · ${plural(custom.length, "salvo", "salvos")}` : ""}.</span></span>${ic("chevron", "chev")}</a>
        </nav>
      </section>
    </div>

    <aside class="panel today" aria-labelledby="today-title">
      <h3 id="today-title">Hoje</h3>
      <div class="item">${ic("repeat")}<div>
        ${ph.due ? `<strong>${plural(ph.due, "frase para revisar", "frases para revisar")}</strong><p class="muted">Treino falado, leva poucos minutos.</p>
          <a class="btn" href="#train" style="margin-top:10px">Revisar agora</a>`
        : `<strong>Nenhuma frase para revisar</strong><p class="muted">Salve frases com ${ic("star")} durante o feedback.</p>`}</div></div>
      ${!profile.text ? `<div class="item">${ic("user")}<div><strong>Complete seu perfil</strong>
        <p class="muted">Entrevistas e situações usam sua stack e experiência.</p><a class="btn" href="#profile" style="margin-top:10px">Preencher perfil</a></div></div>` : ""}
    </aside>
  </div>`;
  $("#go-next").onclick = () => startScenario(next.id);
}

// =====================================================================
// practice pickers
// =====================================================================
const STAGES = [["recruiter", "Triagem com recruiter"], ["technical", "Entrevista técnica"], ["behavioral", "Entrevista comportamental"]];
const stageOptions = () => STAGES.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");

async function renderJobs() {
  view.innerHTML = pageHead("Entrevista para uma vaga real",
    "Busque vagas abertas na web ou cole uma descrição. Você escolhe a etapa e recebe o roteiro com o que esperam de você.", ["#home", "Praticar"]) + `
    <div class="panel">
      <form class="row" id="job-form">
        <input id="job-query" type="text" placeholder="Ex.: mid-level backend Java remote LATAM" aria-label="O que buscar" style="flex:1 1 220px;min-width:0">
        <button class="btn btn-primary" type="submit">${ic("search")} Buscar vagas</button>
      </form>
      <details style="margin-top:14px"><summary class="muted" style="cursor:pointer">Prefiro colar a descrição ou o link de uma vaga</summary>
        <div class="stack" style="margin-top:12px">
          <textarea id="job-text" rows="6" placeholder="Cole aqui a descrição da vaga ou o link"></textarea>
          <div class="row"><select id="paste-stage" aria-label="Etapa">${stageOptions()}</select>
            <button class="btn btn-primary" id="job-paste-go" type="button">Preparar entrevista</button></div>
        </div></details>
    </div>
    <div id="job-results" class="section"></div>`;
  const results = $("#job-results");
  $("#job-query").value = store.get("jobQuery", "");
  $("#job-paste-go").onclick = () => {
    const text = $("#job-text").value.trim();
    if (!text) return $("#job-text").focus();
    generate("Lendo a vaga e preparando o entrevistador.", api("/api/custom/job", { json: { text, stage: $("#paste-stage").value } }));
  };
  const renderJobsList = (jobs) => {
    if (!jobs.length) { results.innerHTML = emptyState("search", "Nenhuma vaga encontrada. Tente outros termos ou cole uma vaga."); return; }
    results.innerHTML = `<h2 style="margin-bottom:14px">Vagas encontradas</h2><div class="rows">${jobs.map((j, i) => `
      <div class="row-item row-static" style="align-items:flex-start">
        <span class="lead-ic">${ic("briefcase")}</span>
        <div class="body">
          <div class="title">${esc(j.title)} <span class="muted" style="font-weight:500">· ${esc(j.company)}</span></div>
          <div class="desc">${esc(j.location)}${j.seniority ? " · " + esc(j.seniority) : ""}${j.url ? ` · <a href="${esc(j.url)}" target="_blank" rel="noopener">ver vaga ${ic("link")}</a>` : ""}</div>
          <p style="margin-top:8px;max-width:70ch">${esc(j.summary_pt)}</p>
          <div class="row" style="margin-top:10px;gap:6px">${(j.must_have || []).slice(0, 6).map((r) => `<span class="pill">${esc(r)}</span>`).join("")}</div>
          <div class="row" style="margin-top:14px"><select data-stage="${i}" aria-label="Etapa da entrevista">${stageOptions()}</select>
            <button class="btn btn-primary" data-job="${i}">Preparar entrevista</button></div>
        </div></div>`).join("")}</div>`;
    results.onclick = (e) => {
      const b = e.target.closest("[data-job]");
      if (!b) return;
      generate("Preparando o entrevistador com base na vaga e no seu perfil.",
        api("/api/custom/job", { json: { job: jobs[b.dataset.job], stage: $(`select[data-stage="${b.dataset.job}"]`).value } }));
    };
  };
  const cached = store.get("jobs", null);
  if (cached) renderJobsList(cached);
  $("#job-form").onsubmit = async (e) => {
    e.preventDefault();
    const q = $("#job-query").value.trim();
    if (!q) return $("#job-query").focus();
    store.set("jobQuery", q);
    results.innerHTML = loadingPanel("Buscando vagas reais na web… pode levar até 90 segundos.");
    try {
      const r = await api("/api/jobs/search", { json: { query: q } });
      store.set("jobs", r.jobs);
      renderJobsList(r.jobs);
    } catch (err) { results.innerHTML = `<div class="panel"><p class="error">A busca falhou: ${esc(err.message)}</p></div>`; }
  };
}

async function renderSituations() {
  const sits = await api("/api/situations");
  view.innerHTML = pageHead("Situação de trabalho",
    "Cada escolha gera uma cena nova e fictícia com a sua stack. O roteiro traz todos os fatos em português; o desafio é comunicar em inglês.",
    ["#home", "Praticar"]) + `
    <div class="row" style="margin-bottom:16px"><span class="muted">Interlocutor</span>
      <div class="seg" role="group" aria-label="Clima da conversa">
        <button type="button" data-pressure="calm" aria-pressed="true">Tranquilo</button>
        <button type="button" data-pressure="pressured" aria-pressed="false">Sob pressão</button></div></div>
    <nav class="rows">${sits.map((s) => `<button class="row-item" data-kind="${s.id}">
      <span class="lead-ic">${ic(SITUATION_ICONS[s.id] || "message")}</span>
      <span class="body"><span class="title">${esc(s.title_pt)}</span><span class="desc">${esc(s.desc_pt)}</span></span>
      <span class="meta">gerar cena</span>${ic("chevron", "chev")}</button>`).join("")}</nav>`;
  let pressure = "calm";
  $$("[data-pressure]").forEach((b) => (b.onclick = () => {
    pressure = b.dataset.pressure;
    $$("[data-pressure]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  }));
  $$("[data-kind]").forEach((b) => (b.onclick = () => generate("Criando a situação com a sua stack.",
    api("/api/custom/situation", { json: { kind: b.dataset.kind, pressure } }))));
}

async function renderClassics() {
  const [scs, custom] = await Promise.all([scenariosList(), api("/api/custom")]);
  view.innerHTML = pageHead("Conversas clássicas e cenários salvos", "", ["#home", "Praticar"]) + `
    <h2 style="margin-bottom:14px">Clássicas</h2>
    <nav class="rows">${scs.map((s) => `<button class="row-item" data-start="${s.id}">
      <span class="avatar">${initial(s.persona)}</span>
      <span class="body"><span class="title">${esc(s.title_pt)}</span><span class="desc">${esc(s.persona)} · ${esc(s.desc_pt)}</span></span>
      ${ic("mic", "chev")}</button>`).join("")}</nav>
    <section class="section"><h2>Cenários salvos</h2>
      ${custom.length ? `<div class="rows">${custom.map((c) => `<div class="row-item row-static">
        <span class="avatar">${initial(c.persona)}</span>
        <a class="body" href="#brief/${c.id}" style="color:inherit;text-decoration:none"><span class="title">${esc(c.title)}</span>
          <span class="desc">${esc(c.source?.label || c.kind)}${c.source?.company ? " · " + esc(c.source.company) : ""} · com ${esc(c.persona)}</span></a>
        <span class="meta">${c.plays ? `${c.plays}× praticado` : "nunca praticado"}</span>
        <button class="icon-btn" data-del="${c.id}" title="Apagar cenário" aria-label="Apagar cenário">${ic("trash")}</button></div>`).join("")}</div>`
      : `<div class="panel">${emptyState("clapper", "Cenários de vagas e situações que você gerar ficam aqui para repetir.")}</div>`}
    </section>`;
  $$("[data-start]").forEach((b) => (b.onclick = () => startScenario(b.dataset.start)));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Apagar este cenário? As sessões feitas com ele continuam no histórico.")) return;
    await api("/api/custom/" + b.dataset.del, { method: "DELETE" });
    route();
  }));
}

// =====================================================================
// briefing ("roteiro")
// =====================================================================
function briefHTML(c, blurVocab = true) {
  const b = c.briefing_pt || {};
  const list = (xs) => (xs?.length ? `<ul>${xs.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  return `<dl class="brief">
    <div><dt>Contexto</dt><dd>${esc(b.contexto)}</dd></div>
    <div><dt>Situação</dt><dd>${esc(b.situacao)}</dd></div>
    <div><dt>Seu objetivo</dt><dd>${esc(b.objetivo)}</dd></div>
    ${b.fatos?.length ? `<div><dt>Fatos que você sabe</dt><dd>${list(b.fatos)}</dd></div>` : ""}
    ${c.expectations_pt?.length ? `<div><dt>O que ${esc(c.persona?.name || "o interlocutor")} espera ouvir</dt><dd>${list(c.expectations_pt)}</dd></div>` : ""}
    ${c.watch_out_pt?.length ? `<div><dt>Cuidado com</dt><dd>${list(c.watch_out_pt)}</dd></div>` : ""}
    ${c.vocabulary?.length ? `<div><dt>Vocabulário útil${blurVocab ? " · clique para revelar" : ""}</dt>
      <dd class="${blurVocab ? "vocab-hidden" : ""}" data-unblur><ul>${c.vocabulary.map((v) => `<li><strong>${esc(v.en)}</strong> — ${esc(v.pt)}
        ${starBtn({ text: v.en, meaning_pt: v.pt, context: c.title, source: "roteiro" })}</li>`).join("")}</ul></dd></div>` : ""}
  </dl>`;
}
document.addEventListener("click", (e) => { const d = e.target.closest("[data-unblur]"); if (d) d.classList.remove("vocab-hidden"); });

async function renderBrief(id) {
  const c = await api("/api/custom/" + id);
  const src = c.source || {};
  const who = c.persona || {};
  currentVoice = who.voice || currentVoice;
  view.innerHTML = pageHead(esc(c.title_pt || c.title), esc(c.desc_pt), ["#classics", "Cenários"]) + `
    <div class="split">
      <div class="panel">${briefHTML(c)}</div>
      <aside class="stack sticky">
        <div class="panel"><div class="lower-third"><span class="avatar">${initial(who.name)}</span>
          <span><span class="name">${esc(who.name)}</span><br><span class="role">${esc(who.role)}</span></span></div>
          <p class="muted" style="margin-top:12px;font-size:var(--fs-sm)">${esc(who.style)}</p>
          <div class="row" style="margin-top:12px;gap:6px"><span class="pill">${esc(src.label || c.kind)}</span>
            ${src.pressure === "pressured" ? `<span class="pill warn">sob pressão</span>` : ""}
            ${src.company ? `<span class="pill">${esc(src.company)}</span>` : ""}</div>
          ${src.url ? `<p style="margin-top:12px;font-size:var(--fs-sm)"><a href="${esc(src.url)}" target="_blank" rel="noopener">Vaga original ${ic("link")}</a></p>` : ""}
        </div>
        <button class="btn btn-primary btn-lg" id="go">${ic("mic")} Começar a conversa</button>
        <p class="faint" style="font-size:var(--fs-sm)">Pense um minuto em <em>como</em> vai explicar, na ordem das ideias. Evite ler frases prontas; o roteiro fica disponível durante a conversa.</p>
      </aside>
    </div>`;
  $("#go").onclick = () => startScenario("c" + c.id);
}

// =====================================================================
// conversation: a scene with subtitles
// =====================================================================
const CC_MODES = [["off", "Sem legenda"], ["reveal", "Sob demanda"], ["on", "Sempre"]];

async function renderChat(arg, ccArg) {
  if (ccArg && CC_MODES.some(([v]) => v === ccArg)) store.set("cc", ccArg);
  if (!pendingScenario && arg) { await startScenario(arg); return; }
  if (!pendingScenario) { location.hash = "home"; return; }
  const scenario = pendingScenario;
  pendingScenario = null;
  let cc = settings.cc;

  view.innerHTML = `
  <section class="talk" aria-label="Conversa">
    <div class="talk-head">
      <div><span class="title">${esc(scenario.title_pt || scenario.title)}</span></div>
      <div class="row">
        <label class="muted" style="display:inline-flex;align-items:center;gap:8px">Voz
          <input id="speed" type="range" min="0.7" max="1.2" step="0.05" aria-label="Velocidade da voz" style="width:96px"></label>
      </div>
    </div>

    <div class="stage scene">
      <div class="bar">
        <div class="lower-third"><span class="avatar">${initial(scenario.persona)}</span>
          <span><span class="name">${esc(scenario.persona)}</span><br><span class="role">${esc(scenario.briefing?.persona?.role || scenario.role || "")}</span></span></div>
        <div class="seg" role="group" aria-label="Legendas">${CC_MODES.map(([v, l]) => `<button type="button" data-cc="${v}" aria-pressed="${v === cc}">${v === "off" ? ic("cc") : ""}${l}</button>`).join("")}</div>
      </div>
      <div></div>
      <div class="line" aria-live="polite">
        <div id="sub-slot"></div>
        <div id="you"></div>
      </div>
    </div>

    <div class="controls">
      <div class="left">
        ${scenario.briefing ? `<button class="btn" id="btn-brief">${ic("file")} Roteiro</button>` : ""}
        <button class="btn" id="btn-help" title="Fale em português o que você quer dizer">${ic("languages")} Como se diz?</button>
      </div>
      <div class="mic-wrap">
        <button class="mic" id="btn-mic" disabled aria-label="Falar">${ic("mic")}</button>
        <div class="mic-hint" id="mic-hint">Conectando…</div>
      </div>
      <div class="right"><button class="btn btn-ghost" id="btn-replay" title="Ouvir de novo">${ic("volume")} Ouvir de novo</button>
        <button class="btn" id="btn-end">${ic("check")} Encerrar e ver feedback</button></div>
    </div>
    <p class="tip" id="real-tip">Sem legenda, como numa call real. Não entendeu? Peça: <em>"Sorry, could you say that again?"</em></p>

    <div id="help-box" class="panel help-panel hidden" aria-live="polite"></div>

    <details class="panel transcript"><summary>${ic("list")} Transcrição da conversa</summary><div id="lines"></div></details>
  </section>
  ${scenario.briefing ? `<aside class="drawer" id="drawer" aria-label="Roteiro"><div class="head"><h3>Roteiro</h3>
    <button class="icon-btn" id="drawer-close" aria-label="Fechar roteiro">${ic("x")}</button></div>${briefHTML(scenario.briefing, false)}</aside>` : ""}`;

  const mic = $("#btn-mic"), hint = $("#mic-hint"), subSlot = $("#sub-slot"), you = $("#you"), lines = $("#lines");
  const speed = $("#speed");
  speed.value = settings.speed;
  speed.oninput = () => store.set("speed", Number(speed.value));

  const rec = new Recorder();
  let session = null, busy = true, lastAssistant = "", helpRec = null;
  const listening = { reveals: 0, replays: 0 };
  const turns = [];

  // ---- captions ----
  function renderSubtitle(speaking = false) {
    $("#btn-replay").classList.toggle("hidden", cc === "off");
    $("#real-tip").classList.toggle("hidden", cc !== "off");
    if (!lastAssistant) { subSlot.innerHTML = `<span class="placeholder">${ic("volume")} ${esc(scenario.persona)} está entrando na call…</span>`; return; }
    if (cc === "off") {
      subSlot.innerHTML = `<span class="placeholder">${ic("volume")}
        ${esc(scenario.persona)} ${speaking ? "está falando" : "falou"}</span>`;
    } else {
      subSlot.innerHTML = `<p class="subtitle ${cc === "reveal" ? "blurred" : ""}" id="sub" title="${cc === "reveal" ? "Clique para revelar a legenda" : ""}">${esc(lastAssistant)}</p>
        ${cc === "reveal" ? `<span class="hint">Clique na legenda para revelar</span>` : ""}`;
      const s = $("#sub");
      if (cc === "reveal") s.onclick = () => { if (s.classList.contains("blurred")) { listening.reveals++; s.classList.remove("blurred"); s.nextElementSibling?.remove(); } };
    }
    $("#btn-replay").classList.toggle("hidden", cc === "off");
    $("#real-tip").classList.toggle("hidden", cc !== "off");
  }
  function renderLines() {
    lines.innerHTML = turns.map((t) => t.role === "assistant"
      ? `<div class="t-line persona"><span class="who">${esc(scenario.persona)}</span><span class="txt ${cc === "on" ? "" : "blurred"}" data-reveal>${esc(t.text)}
          <button class="icon-btn star" data-phrase-from="${esc(t.text)}" title="Salvar um trecho" aria-label="Salvar um trecho">${ic("star")}</button></span></div>`
      : `<div class="t-line"><span class="who">Você</span><span class="txt">${esc(t.text)}</span></div>`).join("")
      || `<p class="faint">A conversa aparece aqui.</p>`;
    $$("[data-reveal]", lines).forEach((el) => (el.onclick = () => el.classList.remove("blurred")));
    $$("[data-phrase-from]", lines).forEach((b) => (b.onclick = (e) => {
      e.stopPropagation();
      const text = b.dataset.phraseFrom;
      const sel = String(window.getSelection() || "").trim();
      const phrase = prompt("Qual palavra ou frase você quer salvar?", sel && text.includes(sel) ? sel : "");
      if (phrase) savePhrase({ text: phrase, context: text, source: "conversa" });
    }));
  }
  $$("[data-cc]").forEach((b) => (b.onclick = () => {
    cc = b.dataset.cc;
    store.set("cc", cc);
    $$("[data-cc]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderSubtitle(); renderLines();
  }));

  function showYou(u) {
    const words = u.words?.length
      ? u.words.map((w) => (w.p < 0.45 && !/^(um|uh|uhm|er|ah|hmm)[.,]?$/i.test(w.w)
          ? `<span class="unclear" title="pouco claro para o reconhecedor (${Math.round(w.p * 100)}%)">${esc(w.w)}</span>` : esc(w.w))).join(" ")
      : esc(u.text);
    const m = u.metrics;
    you.innerHTML = `<div class="you"><span class="lbl">Você disse</span>${words}
      ${m ? `<div class="chips">
        ${m.wpm ? `<span class="pill">${m.wpm} palavras/min</span>` : ""}
        ${m.long_pauses ? `<span class="pill warn">${plural(m.long_pauses, "pausa longa", "pausas longas")}</span>` : ""}
        ${m.fillers ? `<span class="pill">${plural(m.fillers, "hesitação", "hesitações")}</span>` : ""}
        ${m.unclear.length ? `<span class="pill warn">${plural(m.unclear.length, "palavra pouco clara", "palavras pouco claras")}</span>` : ""}</div>` : ""}</div>`;
  }

  const setBusy = (b, text) => {
    busy = b;
    mic.disabled = b;
    hint.innerHTML = text || (b ? "…" : `Clique no microfone ou segure <kbd>Espaço</kbd> para falar`);
  };

  async function personaSays(text) {
    lastAssistant = text;
    turns.push({ role: "assistant", text });
    renderLines();
    renderSubtitle(true);
    busy = false; mic.disabled = false;
    hint.textContent = `${scenario.persona} está falando… você já pode responder`;
    await speak(text, session.voice);
    renderSubtitle(false);
    if (!rec.active) setBusy(false);
  }

  async function startRec() {
    if (busy || rec.active) return;
    try { await rec.start(); } catch (e) { hint.textContent = "Sem acesso ao microfone: " + e.message; return; }
    mic.classList.add("rec");
    mic.setAttribute("aria-label", "Parar e enviar");
    mic.innerHTML = ic("square");
    hint.innerHTML = "Gravando… clique de novo ou solte <kbd>Espaço</kbd> para enviar";
  }
  async function stopRec() {
    if (!rec.active) return;
    mic.classList.remove("rec");
    mic.setAttribute("aria-label", "Falar");
    mic.innerHTML = ic("mic");
    const blob = await rec.stop();
    if (Date.now() - rec.startedAt < 600) { setBusy(false, "Muito curto. Tente de novo."); return; }
    setBusy(true, "Transcrevendo…");
    const fd = new FormData();
    fd.append("audio", blob, "speech.webm");
    try {
      const r = await api(`/api/session/${session.session_id}/turn`, { method: "POST", body: fd });
      if (r.empty) { setBusy(false, "Não ouvi nada. Fale mais perto do microfone e tente de novo."); return; }
      turns.push({ role: "user", text: r.user.text });
      showYou(r.user);
      hint.textContent = `${scenario.persona} está pensando…`;
      await personaSays(r.reply);
    } catch (e) { setBusy(false, "Erro: " + esc(e.message)); }
  }

  mic.onclick = () => (rec.active ? stopRec() : startRec());
  const onKey = (e) => {
    if (e.code !== "Space" || e.target.closest("input,select,textarea")) return;
    if (e.target.closest("button") && e.target.closest("button") !== mic) return;
    e.preventDefault();
    if (e.type === "keydown" && !e.repeat) startRec();
    if (e.type === "keyup") stopRec();
  };
  document.addEventListener("keydown", onKey);
  document.addEventListener("keyup", onKey);
  cleanup = () => {
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("keyup", onKey);
    rec.stop();
    helpRec?.stop();
  };

  $("#btn-replay").onclick = () => {
    if (!lastAssistant) return;
    if (cc === "reveal") listening.replays++;
    speak(lastAssistant, session.voice);
  };

  const drawer = $("#drawer");
  if (drawer) {
    $("#btn-brief").onclick = () => drawer.classList.add("open");
    $("#drawer-close").onclick = () => drawer.classList.remove("open");
  }

  // "Como se diz?": record in Portuguese, get natural English options.
  $("#btn-help").onclick = async () => {
    const btn = $("#btn-help"), box = $("#help-box");
    if (!helpRec?.active) {
      helpRec = new Recorder();
      try { await helpRec.start(); } catch (e) { box.classList.remove("hidden"); box.textContent = e.message; return; }
      btn.innerHTML = `${ic("square")} Parar (fale em português)`;
      btn.classList.add("btn-primary");
      return;
    }
    btn.innerHTML = `${ic("languages")} Como se diz?`;
    btn.classList.remove("btn-primary");
    box.classList.remove("hidden");
    box.textContent = "Pensando…";
    try {
      const heard = await transcribe(await helpRec.stop(), "pt");
      const r = await api("/api/help", { json: { text: heard.text, context: lastAssistant } });
      box.textContent = `Você: "${heard.text}"\n\n${r.answer}`;
      const opts = [...r.answer.matchAll(/Option \d[^:]*:\s*(.+)/g)].map((m) => m[1].trim());
      const row = document.createElement("div");
      row.className = "row";
      row.style.marginTop = "12px";
      opts.forEach((o, i) => {
        const b = document.createElement("button");
        b.className = "btn";
        b.innerHTML = `${ic("star")} Salvar opção ${i + 1}`;
        b.onclick = () => savePhrase({ text: o, context: `Em português: ${heard.text}`, source: "como se diz" });
        row.append(b);
      });
      box.append(row);
    } catch (e) { box.textContent = "Erro: " + e.message; }
  };

  $("#btn-end").onclick = async () => {
    if (!session || !confirm("Encerrar a conversa e gerar o feedback?")) return;
    cleanup(); cleanup = null; stopAudio();
    setBusy(true, "Gerando seu feedback… cerca de 30 segundos");
    $("#btn-end").disabled = true;
    try {
      await api(`/api/session/${session.session_id}/end`, { json: { ...listening, text_mode: { off: "real", reveal: "reveal", on: "visible" }[cc] } });
      location.hash = "report/" + session.session_id;
    } catch (e) { setBusy(true, "Erro ao gerar o feedback: " + esc(e.message)); }
  };

  renderSubtitle(); renderLines();
  try {
    session = await api("/api/session/start", { json: { scenario: scenario.id, level: settings.level } });
    currentVoice = session.voice;
    await personaSays(session.reply);
  } catch (e) { setBusy(true, "Não conectou: " + esc(e.message)); }
}

// =====================================================================
// report
// =====================================================================
const metricRow = (label, value) => `<div class="metric"><span class="muted">${esc(label)}</span><b>${esc(dash(value))}</b></div>`;
const GOAL_LABEL = { met: ["ok", "Atingido"], partial: ["warn", "Parcial"], missed: ["rec", "Faltou"] };

async function renderReport(id) {
  const s = await api("/api/session/" + id);
  const r = s.report, m = s.metrics || {};
  const scen = s.scenario_info || {};
  currentVoice = scen.voice || "af_heart";
  if (!r) {
    view.innerHTML = pageHead("Sessão sem feedback", "Nenhuma fala foi registrada nesta sessão.", ["#history", "Histórico"]);
    return;
  }
  const listen = m.text_mode === "real" ? "Sem legenda"
    : m.text_mode === "reveal" ? `${plural(m.listening_reveals ?? 0, "revelada", "reveladas")} · ${plural(m.listening_replays ?? 0, "replay", "replays")}` : null;
  view.innerHTML = pageHead("Seu feedback", `${esc(scen.title_pt || scen.title)} · com ${esc(scen.persona)} · ${fmtDate(s.started_at)}`, ["#history", "Histórico"]) + `
  <div class="split">
    <div>
      <div class="panel"><p class="prose" style="font-size:var(--fs-lg)">${esc(r.summary_pt)}</p></div>

      ${r.interviewer_view_pt ? `<div class="panel view-panel"><h3>${ic("briefcase")} Como o entrevistador te veria</h3><p class="prose">${esc(r.interviewer_view_pt)}</p></div>` : ""}

      ${r.goals?.length ? `<section class="section"><h2>${scen.kind === "job" ? "O que você demonstrou da vaga" : "Objetivos da conversa"}</h2>
        <div class="panel">${r.goals.map((g) => { const [cls, lbl] = GOAL_LABEL[g.status] || ["", g.status]; return `<div class="goal">
          <span><span class="pill ${cls}">${lbl}</span></span><div><div>${esc(g.criterion)}</div><div class="comment">${esc(g.comment_pt)}</div></div></div>`; }).join("")}</div></section>` : ""}

      <section class="section"><h2>Prioridades de correção</h2>
        <div class="panel">${(r.mistakes || []).map((x) => `<div class="fix">
          <div class="pair"><span class="said">${esc(x.said)}</span>${ic("arrowRight")}<span class="better">${esc(x.better)}</span>
            ${sayBtn(x.better)}${starBtn({ text: x.better, meaning_pt: "", context: `Correção de: ${x.said}`, source: "feedback" })}</div>
          <div class="row" style="gap:6px"><span class="pill ${x.impact === "high" ? "rec" : x.impact === "medium" ? "warn" : ""}">${{ high: "impacto alto", medium: "impacto médio", low: "impacto baixo" }[x.impact] || esc(x.impact)}</span>
            <span class="pill">${esc(x.category)}</span></div>
          <p class="why">${esc(x.why_pt)}</p></div>`).join("") || `<p class="muted">Nada que atrapalhe a comunicação. Muito bem!</p>`}</div></section>

      ${r.expressions?.length ? `<section class="section"><h2>Expressões para usar</h2><div class="panel">${r.expressions.map((x) => `<div class="expr">
        <div class="row" style="gap:4px"><strong>${esc(x.expression)}</strong>${starBtn({ text: x.expression, meaning_pt: x.meaning_pt, example: x.example, source: "feedback" })}
          <span class="muted">— ${esc(x.meaning_pt)}</span></div>
        <div class="row" style="gap:4px"><span class="ex">${esc(x.example)}</span>${sayBtn(x.example)}</div></div>`).join("")}</div></section>` : ""}

      ${r.pronunciation?.length ? `<section class="section"><h2>Pronúncia que atrapalhou</h2><div class="panel"><ul class="clean">${r.pronunciation.map((x) => `<li>
        <strong>${esc(x.word)}</strong> ${sayBtn(x.word)} <span class="muted">${esc(x.tip_pt)}</span></li>`).join("")}</ul></div></section>` : ""}

      ${r.strengths_pt?.length || r.fluency_tips_pt?.length ? `<section class="section"><h2>Para a próxima</h2><div class="panel">
        ${r.strengths_pt?.length ? `<h3>O que foi bem</h3><ul class="clean">${r.strengths_pt.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
        ${r.fluency_tips_pt?.length ? `<h3 style="margin-top:16px">Fluência</h3><ul class="clean">${r.fluency_tips_pt.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
      </div></section>` : ""}

      <details class="panel transcript section"><summary>${ic("list")} Transcrição completa</summary>
        ${s.turns.map((t) => `<div class="t-line ${t.role === "user" ? "" : "persona"}"><span class="who">${t.role === "user" ? "Você" : esc(scen.persona)}</span><span class="txt">${esc(t.text)}</span></div>`).join("")}
      </details>
    </div>

    <aside class="stack sticky">
      ${r.retell?.question ? `<div class="panel" style="border-color:rgba(255,225,77,.35)"><h3>${ic("repeat")} Responda de novo</h3>
        <p style="margin-top:4px">${esc(r.retell.question)}</p><p class="muted" style="font-size:var(--fs-sm);margin-top:8px">${esc(r.retell.why_pt)}</p>
        <a class="btn btn-primary" href="#retell/${id}" style="margin-top:14px;width:100%">Fazer o re-tell 4/3/2</a></div>` : ""}
      <div class="panel"><h3>Comunicação</h3>
        ${metricRow("Clareza", r.scores?.clarity == null ? null : r.scores.clarity + " / 5")}${metricRow("Fluência", r.scores?.fluency == null ? null : r.scores.fluency + " / 5")}
        ${metricRow("Gramática", r.scores?.grammar == null ? null : r.scores.grammar + " / 5")}${metricRow("Vocabulário", r.scores?.vocabulary == null ? null : r.scores.vocabulary + " / 5")}</div>
      <div class="panel"><h3>Sua fala</h3>
        ${metricRow("Palavras por minuto", m.wpm)}${metricRow("Pausas longas por minuto", m.pauses_per_min)}
        ${metricRow("Hesitações por minuto", m.fillers_per_min)}${metricRow("Entendido pelo reconhecedor", m.clarity == null ? null : Math.round(m.clarity * 100) + "%")}
        ${metricRow("Palavras por resposta", m.avg_turn_words)}${listen ? metricRow("Legendas", listen) : ""}</div>
      ${r.phrases_used?.length ? `<div class="panel"><h3>${ic("star")} Frases em treino que você usou</h3>
        <div class="row" style="gap:6px">${r.phrases_used.map((p) => `<span class="pill ok">${esc(p)}</span>`).join("")}</div></div>` : ""}
      ${scen.kind !== "?" ? `<button class="btn" id="again">${ic("repeat")} Repetir esta cena</button>` : ""}
    </aside>
  </div>`;
  const again = $("#again");
  if (again) again.onclick = () => startScenario(scen.id);
}

// =====================================================================
// retell (4/3/2 adapted: 2 min -> 1:30 -> 1 min)
// =====================================================================
const ROUNDS = [120, 90, 60];
const fmtSec = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;

async function renderRetell(id) {
  const s = await api("/api/session/" + id);
  const scen = s.scenario_info || {};
  const question = s.report?.retell?.question || scen.retell_question;
  if (!question) { location.hash = "report/" + id; return; }
  currentVoice = scen.voice || "af_heart";
  const results = [];
  let round = 0, timer = null;
  const rec = new Recorder();

  view.innerHTML = pageHead("Re-tell 4/3/2", "Responda a mesma pergunta três vezes, com menos tempo a cada rodada. Não decore: diga a mesma ideia com mais fluidez.",
    ["#report/" + id, "Feedback"]) + `
    <div class="panel" style="max-width:760px">
      <div class="row" style="justify-content:space-between"><p style="font-size:var(--fs-lg);font-weight:700;max-width:56ch">${esc(question)}</p>${sayBtn(question, "Ouvir a pergunta")}</div>
      <div class="rounds">${ROUNDS.map((t, i) => `<div class="round" data-r="${i}">Rodada ${i + 1}<strong class="num">${fmtSec(t)}</strong></div>`).join("")}</div>
      <div class="timer" id="timer" aria-live="polite">${fmtSec(ROUNDS[0])}</div>
      <div class="row" style="justify-content:center"><button class="btn btn-primary btn-lg" id="rt-btn">${ic("mic")} Começar a rodada 1</button></div>
    </div>
    <div id="rt-out" class="stack section" style="max-width:760px"></div>`;
  const btn = $("#rt-btn"), out = $("#rt-out"), timerEl = $("#timer");
  const markRounds = () => $$(".round").forEach((el, i) => { el.classList.toggle("active", i === round); el.classList.toggle("done", i < round); });
  markRounds();

  async function finishRound() {
    clearInterval(timer);
    btn.disabled = true;
    btn.innerHTML = "Analisando…";
    const blob = await rec.stop();
    const seconds = Math.round((Date.now() - rec.startedAt) / 1000);
    const heard = await transcribe(blob, "en");
    const r = await api("/api/retell", { json: { session_id: Number(id), question, round: round + 1, seconds,
      text: heard.text, metrics: heard.metrics || {}, want_feedback: round === 0 } });
    const m = heard.metrics || {};
    results.push({ seconds, ...m });
    const fb = r.feedback;
    out.insertAdjacentHTML("beforeend", `<div class="panel"><h3>Rodada ${round + 1}</h3>
      <p class="prose">${esc(heard.text) || "<em class='muted'>(nada transcrito)</em>"}</p>
      <div class="row" style="gap:6px;margin-top:10px"><span class="pill">${dash(m.wpm)} palavras/min</span><span class="pill">${dash(m.long_pauses)} pausas longas</span>
        <span class="pill">${dash(m.fillers)} hesitações</span><span class="pill">${dash(m.words)} palavras</span></div>
      ${fb ? `<h3 style="margin-top:18px">Antes da próxima rodada</h3>
        ${(fb.fixes || []).map((x) => `<div class="fix"><div class="pair"><span class="said">${esc(x.said)}</span>${ic("arrowRight")}<span class="better">${esc(x.better)}</span></div><p class="why">${esc(x.why_pt)}</p></div>`).join("")}
        <p style="margin-top:8px">${esc(fb.structure_pt)}</p>
        ${fb.phrases?.length ? `<p class="muted" style="margin-top:10px">Frases para reutilizar</p><ul class="clean">${fb.phrases.map((p) => `<li><em>${esc(p)}</em> ${starBtn({ text: p, source: "re-tell" })}</li>`).join("")}</ul>` : ""}
        <p class="muted" style="margin-top:10px">${esc(fb.encouragement_pt)}</p>` : ""}</div>`);
    round++;
    markRounds();
    btn.disabled = false;
    if (round < ROUNDS.length) {
      timerEl.textContent = fmtSec(ROUNDS[round]);
      btn.innerHTML = `${ic("mic")} Começar a rodada ${round + 1}`;
    } else {
      btn.classList.add("hidden");
      timerEl.innerHTML = ic("check");
      out.insertAdjacentHTML("beforeend", `<div class="panel"><h3>Comparação</h3><div class="table-wrap" style="border:0"><table>
        <thead><tr><th></th>${results.map((_, i) => `<th class="num">Rodada ${i + 1}</th>`).join("")}</tr></thead><tbody>
        <tr><td>Palavras/min</td>${results.map((x) => `<td class="num">${dash(x.wpm)}</td>`).join("")}</tr>
        <tr><td>Pausas longas</td>${results.map((x) => `<td class="num">${dash(x.long_pauses)}</td>`).join("")}</tr>
        <tr><td>Hesitações</td>${results.map((x) => `<td class="num">${dash(x.fillers)}</td>`).join("")}</tr>
        <tr><td>Palavras</td>${results.map((x) => `<td class="num">${dash(x.words)}</td>`).join("")}</tr>
        <tr><td>Entendido pelo reconhecedor</td>${results.map((x) => `<td class="num">${pct(x.clarity)}</td>`).join("")}</tr>
      </tbody></table></div><p class="muted" style="margin-top:10px">O esperado: mais palavras por minuto e menos pausas a cada rodada.</p>
      <div class="row" style="margin-top:14px"><a class="btn btn-primary" href="#home">Nova conversa</a><a class="btn" href="#report/${id}">Voltar ao feedback</a></div></div>`);
    }
    out.lastElementChild.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  btn.onclick = async () => {
    if (rec.active) { finishRound(); return; }
    try { await rec.start(); } catch (e) { out.innerHTML = `<div class="panel error">${esc(e.message)}</div>`; return; }
    let left = ROUNDS[round];
    btn.innerHTML = `${ic("square")} Terminar agora`;
    timerEl.textContent = fmtSec(left);
    timer = setInterval(() => {
      left--;
      timerEl.textContent = fmtSec(Math.max(0, left));
      if (left <= 0) finishRound();
    }, 1000);
  };
  cleanup = () => { clearInterval(timer); rec.stop(); };
}

// =====================================================================
// phrases, packs and spaced-repetition speaking practice
// =====================================================================
const levelDots = (lvl) => `<span class="level" title="nível ${lvl} de 6" aria-label="nível ${lvl} de 6">${[1, 2, 3, 4, 5, 6].map((i) => `<i class="${i <= lvl ? "on" : ""}"></i>`).join("")}</span>`;

async function renderPhrases() {
  const [{ phrases, due }, packs, custom] = await Promise.all([api("/api/phrases"), api("/api/packs"), api("/api/custom")]);
  currentVoice = "af_heart";
  view.innerHTML = pageHead("Minhas frases",
    "Palavras e expressões para treinar falando. As frases em treino voltam nas conversas: o interlocutor cria chances de você usá-las.") + `
    <div class="split">
      <div>
        <form class="panel row" id="add-form">
          <input id="new-phrase" type="text" placeholder='Uma palavra ou frase, ex.: "catch up on work"' aria-label="Nova frase" style="flex:1 1 200px;min-width:0">
          <button class="btn btn-primary" id="add" type="submit">${ic("plus")} Adicionar</button>
        </form>
        <p class="faint" style="font-size:var(--fs-sm);margin:8px 2px 0">A IA corrige a forma, explica o significado e cria um exemplo.</p>
        <div id="pack-out" class="section hidden"></div>
        <section class="section"><h2>Suas frases <span class="faint num" style="font-weight:500">${phrases.length}</span></h2>
          ${phrases.length ? `<div class="rows">${phrases.map((p) => `<div class="phrase">
            <div class="body">
              <div class="en">${esc(p.text)} ${sayBtn(p.text)}${levelDots(p.level)}</div>
              <div>${esc(p.meaning_pt)}</div>
              ${p.example ? `<div class="row" style="gap:2px"><span class="ex">${esc(p.example)}</span>${sayBtn(p.example)}</div>` : ""}
              ${p.note_pt ? `<div class="note">${esc(p.note_pt)}</div>` : ""}
              <div class="stats">${esc(p.source || "")} · ${plural(p.reviews, "revisão", "revisões")} · ${plural(p.successes, "acerto", "acertos")} · usada ${p.used_in_conversation}× em conversa · próxima ${fmtDay(p.next_review)}</div>
            </div>
            <button class="icon-btn" data-del="${p.id}" title="Apagar frase" aria-label="Apagar frase">${ic("trash")}</button></div>`).join("")}</div>`
          : `<div class="panel">${emptyState("star", "Nenhuma frase ainda. Adicione uma acima, gere um pacote ou salve no feedback.")}</div>`}
        </section>
      </div>
      <aside class="stack sticky">
        <div class="panel"><h3>${ic("repeat")} Revisão</h3>
          ${due ? `<p><strong class="num">${plural(due, "frase", "frases")}</strong> para revisar agora.</p><a class="btn btn-primary" href="#train" style="margin-top:12px;width:100%">Treinar agora</a>`
            : `<p class="muted">Nada para revisar agora. As frases voltam em 1, 2, 4, 8… dias.</p>`}</div>
        <div class="panel"><h3>${ic("package")} Pacotes de vocabulário</h3>
          <p class="muted" style="font-size:var(--fs-sm);margin-bottom:12px">10 frases novas sobre um tema, com a sua stack e sem repetir as que você tem.</p>
          <div class="pack-list" id="packs">${packs.map((p) => `<button class="pack" data-pack="${p.id}">${ic(PACK_ICONS[p.id] || "sparkles")}<span>${esc(p.title_pt)}</span>${ic("chevron", "chev")}</button>`).join("")}</div>
          ${custom.length ? `<div class="stack" style="margin-top:16px"><label class="field">Preparar para um cenário salvo
            <select id="prep-scn">${custom.map((c) => `<option value="${c.id}">${esc(c.title)}${c.source?.company ? " · " + esc(c.source.company) : ""}</option>`).join("")}</select></label>
            <button class="btn" id="prep-go">${ic("target")} Gerar vocabulário da cena</button></div>` : ""}
        </div>
      </aside>
    </div>`;

  $("#add-form").onsubmit = async (e) => {
    e.preventDefault();
    const t = $("#new-phrase").value.trim();
    if (!t) return $("#new-phrase").focus();
    $("#add").disabled = true;
    await savePhrase({ text: t, source: "manual" });
    renderPhrases();
  };
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Apagar esta frase?")) return;
    await api("/api/phrases/" + b.dataset.del, { method: "DELETE" });
    renderPhrases();
  }));

  const out = $("#pack-out");
  async function runPack(body, label) {
    out.classList.remove("hidden");
    out.innerHTML = `<h2 style="margin-bottom:14px">${esc(label)}</h2>` + loadingPanel("Gerando o pacote… cerca de 20 segundos.");
    out.scrollIntoView({ behavior: "smooth", block: "start" });
    let items;
    try { items = (await api("/api/packs/generate", { json: body })).items; } catch (e) {
      out.innerHTML = `<div class="panel error">Não deu para gerar: ${esc(e.message)}</div>`; return;
    }
    out.innerHTML = `<h2 style="margin-bottom:6px">${esc(label)}</h2><p class="muted" style="margin-bottom:14px">Desmarque o que você já domina. As marcadas entram no treino.</p>
      <div class="rows">${items.map((it, i) => `<label class="phrase" style="cursor:pointer">
        <input type="checkbox" data-i="${i}" checked style="margin-top:6px">
        <div class="body"><div class="en">${esc(it.text)} ${sayBtn(it.text)}</div><div>${esc(it.meaning_pt)}</div>
          <div class="ex">${esc(it.example)}</div><div class="note">${esc(it.note_pt)}</div></div></label>`).join("")}</div>
      <div class="row" style="margin-top:14px"><button class="btn btn-primary" id="pack-add">${ic("check")} Adicionar selecionadas</button>
        <button class="btn btn-ghost" id="pack-cancel">Descartar</button></div>`;
    $("#pack-cancel").onclick = () => { out.innerHTML = ""; out.classList.add("hidden"); };
    $("#pack-add").onclick = async () => {
      const chosen = $$("input[data-i]:checked", out).map((cb) => items[cb.dataset.i]);
      const r = await api("/api/phrases/bulk", { json: { items: chosen, source: "pacote: " + label } });
      toast(r.added === 1 ? "1 frase adicionada ao treino" : `${r.added} frases adicionadas ao treino`);
      renderPhrases();
    };
  }
  $$("[data-pack]").forEach((b) => (b.onclick = () => runPack({ pack: b.dataset.pack }, b.textContent.trim())));
  const prep = $("#prep-go");
  if (prep) prep.onclick = () => runPack({ custom_id: Number($("#prep-scn").value) }, "Vocabulário: " + $("#prep-scn").selectedOptions[0].textContent);
}

// Recall check without an LLM: did the transcript contain (almost) all words of the phrase?
function saidPhrase(transcript, phrase) {
  const toks = (s) => s.toLowerCase().replace(/[^a-z0-9' ]/g, " ").split(/\s+/).filter(Boolean);
  const heard = toks(transcript), target = toks(phrase);
  if (!target.length) return false;
  const hit = target.filter((t) => heard.some((h) => h === t || (t.length > 4 && h.startsWith(t.slice(0, 4))))).length;
  return hit / target.length >= 0.75;
}

async function renderTrain() {
  const items = await api("/api/phrases/due");
  currentVoice = "af_heart";
  if (!items.length) {
    view.innerHTML = pageHead("Treino de frases", "", ["#phrases", "Minhas frases"]) + `<div class="panel">${emptyState("check", "Nada para revisar agora. Volte amanhã ou adicione frases novas.")}</div>`;
    return;
  }
  let i = 0, correct = 0;
  const rec = new Recorder();
  cleanup = () => rec.stop();

  function micButton(label, onDone, language = "en") {
    const wrap = document.createElement("div");
    wrap.className = "row";
    wrap.innerHTML = `<button class="mic small" aria-label="Gravar">${ic("mic")}</button><span class="muted">${label}</span>`;
    const btn = wrap.querySelector("button"), hint = wrap.querySelector("span");
    btn.onclick = async () => {
      if (!rec.active) {
        try { await rec.start(); } catch (e) { hint.textContent = e.message; return; }
        btn.classList.add("rec"); btn.innerHTML = ic("square"); hint.textContent = "Gravando… clique para parar";
        return;
      }
      btn.classList.remove("rec"); btn.disabled = true; hint.textContent = "Transcrevendo…";
      const heard = await transcribe(await rec.stop(), language);
      wrap.remove();
      onDone(heard.text || "");
    };
    return wrap;
  }

  function show() {
    if (i >= items.length) {
      view.innerHTML = pageHead("Treino concluído", "", ["#phrases", "Minhas frases"]) + `<div class="panel train-card">
        <p class="train-card prompt"><span class="num">${correct}/${items.length}</span> frases certas.</p>
        <p class="muted">As certas voltam em alguns dias; as outras, na próxima revisão.</p>
        <div class="row" style="margin-top:16px"><a class="btn btn-primary" href="#home">${ic("mic")} Praticar uma conversa</a><a class="btn" href="#phrases">Minhas frases</a></div></div>`;
      return;
    }
    const p = items[i];
    view.innerHTML = pageHead("Treino de frases", `Frase ${i + 1} de ${items.length}`, ["#phrases", "Minhas frases"]) + `
      <div class="panel train-card">
        <div class="row" style="justify-content:space-between"><span class="faint">Como se diz em inglês…</span>${levelDots(p.level)}</div>
        <p class="prompt">${esc(p.meaning_pt)}</p>
        <div id="s1" class="stack"></div>
        <div id="s2" class="step hidden"></div>
      </div>`;
    const s1 = $("#s1"), s2 = $("#s2");
    let recallOk = false;
    const reveal = (heardText) => {
      recallOk = heardText !== null && saidPhrase(heardText, p.text);
      s1.innerHTML = `${heardText !== null ? `<p>Você disse: <em>${esc(heardText) || "(nada)"}</em>
          <span class="${recallOk ? "ok-t" : "nok-t"}">${recallOk ? "Isso!" : "Não exatamente"}</span></p>` : ""}
        <div class="row" style="gap:4px"><span class="subtitle reveal">${esc(p.text)}</span>${sayBtn(p.text)}</div>
        ${p.note_pt ? `<p class="muted">${esc(p.note_pt)}</p>` : ""}`;
      speak(p.text, "af_heart");
      s2.classList.remove("hidden");
      s2.innerHTML = `<p><strong>Agora fale uma frase sua usando <span class="subtitle">${esc(p.text)}</span></strong>
        <span class="muted"> · de preferência sobre o seu trabalho</span></p>`;
      s2.append(micButton("Clique, fale a frase e clique de novo", async (sentence) => {
        s2.insertAdjacentHTML("beforeend", `<p>Você disse: <em>${esc(sentence) || "(nada)"}</em></p><p class="muted" id="judging">Avaliando…</p>`);
        try {
          const r = await api(`/api/phrases/${p.id}/review`, { json: { recall_ok: recallOk, sentence } });
          const ok = recallOk && r.used_correctly;
          if (ok) correct++;
          $("#judging")?.remove();
          s2.insertAdjacentHTML("beforeend", `
            <p class="${r.used_correctly ? "ok-t" : "nok-t"}">${r.used_correctly ? "Uso correto" : "Ainda não"}</p>
            <p>${esc(r.feedback_pt)}</p>
            ${r.better ? `<div class="row" style="gap:4px"><span class="muted">Mais natural:</span><span class="better">${esc(r.better)}</span>${sayBtn(r.better)}</div>` : ""}
            <p class="faint">${ok ? "Próxima revisão: " + fmtDay(r.phrase?.next_review) : "Esta volta na próxima revisão."}</p>
            <div><button class="btn btn-primary" id="next">Próxima ${ic("arrowRight")}</button></div>`);
          $("#next").onclick = () => { i++; show(); };
        } catch (e) { s2.insertAdjacentHTML("beforeend", `<p class="error">${esc(e.message)}</p>`); }
      }));
    };
    s1.append(micButton("Clique e diga a expressão em inglês", reveal));
    const skip = document.createElement("button");
    skip.className = "btn btn-ghost";
    skip.style.width = "fit-content";
    skip.textContent = "Não lembro, mostrar";
    skip.onclick = () => { rec.stop(); reveal(null); };
    s1.append(skip);
  }
  show();
}

// =====================================================================
// history, notebook, profile
// =====================================================================
async function renderHistory() {
  const [rows, sc] = await Promise.all([api("/api/sessions"), scenariosList()]);
  const name = (id) => sc.find((x) => x.id === id)?.title_pt || id;
  view.innerHTML = pageHead("Histórico", "Sinais de progresso: mais palavras por resposta e por minuto, menos pausas longas e hesitações.") +
    (rows.length ? `<div class="table-wrap"><table>
      <thead><tr><th>Data</th><th>Cena</th><th class="num">Clareza</th><th class="num">Fluência</th><th class="num">Palavras/min</th>
        <th class="num">Pausas/min</th><th class="num">Hesitações/min</th><th class="num">Palavras/resposta</th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="click" data-id="${r.id}" tabindex="0">
        <td class="num">${fmtDate(r.started_at)}</td><td>${esc(r.title || name(r.scenario))}</td>
        <td class="num">${dash(r.scores?.clarity)}</td><td class="num">${dash(r.scores?.fluency)}</td>
        <td class="num">${dash(r.metrics?.wpm)}</td><td class="num">${dash(r.metrics?.pauses_per_min)}</td>
        <td class="num">${dash(r.metrics?.fillers_per_min)}</td><td class="num">${dash(r.metrics?.avg_turn_words)}</td></tr>`).join("")}
      </tbody></table></div>`
    : `<div class="panel">${emptyState("history", 'Nenhuma sessão ainda. <a href="#home">Comece a primeira conversa</a>.')}</div>`);
  $$("tr.click").forEach((tr) => {
    tr.onclick = () => (location.hash = "report/" + tr.dataset.id);
    tr.onkeydown = (e) => { if (e.key === "Enter") tr.click(); };
  });
}

async function renderNotebook() {
  const rows = await api("/api/notebook");
  view.innerHTML = pageHead("Caderno de erros",
    "Erros que se repetem entre sessões. Os cinco mais frequentes entram na próxima conversa, e depois de três acertos o erro é marcado como resolvido.") +
    (rows.length ? `<div class="table-wrap"><table>
      <thead><tr><th>Você disse</th><th>Forma natural</th><th>Por quê</th><th class="num">Erros</th><th class="num">Acertos</th><th>Resolvido</th></tr></thead><tbody>
      ${rows.map((m) => `<tr class="${m.resolved ? "resolved" : ""}">
        <td class="said">${esc(m.said)}</td><td><span class="better">${esc(m.better)}</span> ${sayBtn(m.better)}</td>
        <td class="muted">${esc(m.why_pt)}</td><td class="num">${m.count}</td><td class="num">${m.correct_count}</td>
        <td><input type="checkbox" data-key="${esc(m.key)}" ${m.resolved ? "checked" : ""} aria-label="Marcar como resolvido"></td></tr>`).join("")}
      </tbody></table></div>`
    : `<div class="panel">${emptyState("list", "Ainda vazio. Ele é preenchido com o feedback de cada conversa.")}</div>`);
  $$("input[data-key]").forEach((cb) => (cb.onchange = async () => {
    await api("/api/notebook/" + encodeURIComponent(cb.dataset.key), { json: { resolved: cb.checked } });
    renderNotebook();
  }));
}

const PROFILE_TEMPLATE = `Cargo atual: Desenvolvedor pleno (backend/frontend/full-stack)
Anos de experiência:
Stack principal: (linguagens, frameworks, bancos, cloud)
Projetos relevantes: (2-3 projetos: o que fazia, sua parte, resultados)
Experiência com times internacionais / inglês:
Tipo de vaga que busco: remota, internacional, ...
Pontos fortes:
Pontos a melhorar / gaps:`;

async function renderProfile() {
  const p = await api("/api/profile");
  view.innerHTML = pageHead("Perfil", "Os entrevistadores leem isto antes da conversa, para ter expectativas e investigar gaps. As situações de trabalho usam a sua stack.") + `
    <div class="split">
      <form class="panel stack" id="profile-form">
        <label class="field" for="profile-text">Seu mini-CV, em português ou inglês. Pode colar o CV inteiro.</label>
        <textarea id="profile-text" rows="16"></textarea>
        <div class="row"><button class="btn btn-primary" type="submit">${ic("check")} Salvar perfil</button><span id="saved" class="muted" role="status"></span></div>
      </form>
      <aside class="panel stack sticky"><h3>Preferências da conversa</h3>
        <label class="field">Nível do interlocutor
          <select id="level"><option value="friendly">Amigável: claro, sem muita gíria</option><option value="realistic">Realista: velocidade e expressões nativas</option></select></label>
        <label class="field">Legendas ao começar
          <select id="cc-default">${CC_MODES.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
        <label class="field">Velocidade da voz <span class="num" id="speed-val"></span>
          <input id="speed" type="range" min="0.7" max="1.2" step="0.05"></label>
      </aside>
    </div>`;
  const ta = $("#profile-text");
  ta.value = p.text || PROFILE_TEMPLATE;
  $("#profile-form").onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/profile", { method: "PUT", json: { text: ta.value } });
    $("#saved").textContent = "Salvo.";
  };
  const level = $("#level"), ccSel = $("#cc-default"), speed = $("#speed");
  level.value = settings.level; ccSel.value = settings.cc; speed.value = settings.speed;
  const showSpeed = () => ($("#speed-val").textContent = Number(speed.value).toFixed(2) + "×");
  showSpeed();
  level.onchange = () => store.set("level", level.value);
  ccSel.onchange = () => store.set("cc", ccSel.value);
  speed.oninput = () => { store.set("speed", Number(speed.value)); showSpeed(); };
}

pollStatus();
route();
