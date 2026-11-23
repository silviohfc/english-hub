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

const fmtSec = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "");
const fmtDay = (iso) => (iso ? new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) : "");
const pct = (x) => (x == null ? "–" : Math.round(x * 100) + "%");
const dash = (x) => (x == null || x === "" ? "–" : x);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const VOICES = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_adam", "am_puck", "am_eric", "bf_emma", "bm_george", "bm_lewis"];
// Portrait for a voice (photos in /static/avatars, see CREDITS.md); falls back to the initial if missing.
const avatar = (voice, name, cls = "") => `<span class="avatar ${cls}">${initial(name)}${VOICES.includes(voice)
  ? `<img src="/static/avatars/${voice}.jpg" alt="" loading="lazy" onerror="this.remove()">` : ""}</span>`;
const initial = (name) => esc((name || "?").trim().charAt(0).toUpperCase());

// =====================================================================
// icons (Lucide-style line icons)
// =====================================================================
const ICONS = {
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
  micOff: '<path d="m2 2 20 20"/><path d="M18.9 13.2A7 7 0 0 0 19 12v-2"/><path d="M5 10v2a7 7 0 0 0 12 5"/><path d="M15 9.3V5a3 3 0 0 0-5.7-1.3"/><path d="M9 9v3a3 3 0 0 0 5.1 2.1"/><path d="M12 19v3"/>',
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
  settings: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8M12 17v4"/>',
  headphones: '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
  play: '<path d="m6 3 14 9-14 9Z"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>',
  download: '<path d="M12 15V3M7 10l5 5 5-5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
  map: '<path d="M14.1 5.9 9.9 3.8a2 2 0 0 0-1.8 0L3.6 6.1A1 1 0 0 0 3 7v12.4a1 1 0 0 0 1.4.9l3.7-1.9a2 2 0 0 1 1.8 0l4.2 2.1a2 2 0 0 0 1.8 0l4.5-2.3a1 1 0 0 0 .6-.9V4.6a1 1 0 0 0-1.4-.9l-3.7 1.9a2 2 0 0 1-1.8 0Z"/><path d="M15 6v15M9 3.5v15"/>',
  receipt: '<path d="M4 2v20l3-2 3 2 2-2 2 2 3-2 3 2V2l-3 2-3-2-2 2-2-2-3 2Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  bag: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18M16 10a4 4 0 0 1-8 0"/>',
  pill: '<path d="m10.5 20.5 10-10a5 5 0 1 0-7-7l-10 10a5 5 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1Z"/>',
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  plane: '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2Z"/>',
  trashAll: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6"/>',
  plug: '<path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M8 16H3v5"/>',
};
const ic = (name, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
const SITUATION_ICONS = { bug: "bug", blocker: "ban", delay: "clock", incident: "flame", review: "pr", clarify: "help", explain: "message",
  order: "receipt", return: "bag", phone: "phone", directions: "map", pharmacy: "pill", landlord: "home", plans: "calendar" };
const PACK_ICONS = { daily: "clock", bugs: "bug", review: "pr", interview: "briefcase", phrasal: "link", false_friends: "alert", fillers: "message", meetings: "user",
  travel: "plane", food: "receipt", health: "pill", shopping: "bag", smalltalk: "message", phrasal_daily: "link", false_friends_daily: "alert", fillers_daily: "clock" };
const isDev = () => (FLAGS?.track || "dev") !== "daily";

// =====================================================================
// audio
// =====================================================================
let currentAudio = null;
function stopAudio() { if (currentAudio) { currentAudio.pause(); currentAudio = null; } }

// Live audio level (0..1) from any audio node, like the speaking indicator of meeting apps.
let actx = null;
function audioCtx() {
  if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
  if (actx.state === "suspended") actx.resume().catch(() => {});
  return actx;
}
function meter(node, onLevel) {
  const an = audioCtx().createAnalyser();
  an.fftSize = 512;
  node.connect(an);
  const buf = new Uint8Array(an.fftSize);
  let raf = 0, smooth = 0;
  const tick = () => {
    an.getByteTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) { const x = (v - 128) / 128; sum += x * x; }
    const lvl = Math.min(1, Math.sqrt(sum / buf.length) * 5);
    smooth = lvl > smooth ? lvl : smooth * 0.85 + lvl * 0.15;
    onLevel(smooth);
    raf = requestAnimationFrame(tick);
  };
  tick();
  return () => { cancelAnimationFrame(raf); onLevel(0); try { node.disconnect(an); } catch { /* ignore */ } };
}
let speakLevel = null; // set by the call screen to animate the partner's portrait

async function speak(text, voice) {
  stopAudio();
  const blob = await api("/api/tts", { json: { text, voice, speed: settings.speed } });
  const audio = new Audio(URL.createObjectURL(blob));
  currentAudio = audio;
  let stopMeter = null;
  // Route through the meter only when the audio context is already running; otherwise the voice would be muted.
  if (speakLevel && audioCtx().state === "running") {
    try {
      const src = audioCtx().createMediaElementSource(audio);
      src.connect(audioCtx().destination);
      stopMeter = meter(src, speakLevel);
    } catch { /* metering is optional */ }
  }
  await audio.play().catch(() => {});
  return new Promise((r) => {
    const done = () => { stopMeter?.(); r(); };
    audio.onended = done; audio.onpause = done;
  });
}

// Chrome/Edge/Firefox record webm/opus; Safari (macOS) records mp4/aac. The server decodes either.
const REC_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4;codecs=mp4a.40.2", "audio/mp4"];
const recMime = () => REC_TYPES.find((t) => window.MediaRecorder?.isTypeSupported?.(t)) || "";
const blobName = (blob) => (blob?.type.includes("mp4") ? "speech.m4a" : "speech.webm");

class Recorder {
  async start() {
    stopAudio();
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    this.chunks = [];
    const mimeType = recMime();
    this.rec = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
    this.rec.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.rec.start();
    this.startedAt = Date.now();
    if (this.onLevel) {
      try { this.stopMeter = meter(audioCtx().createMediaStreamSource(this.stream), this.onLevel); } catch { /* optional */ }
    }
  }
  get active() { return this.rec?.state === "recording"; }
  stop() {
    return new Promise((resolve) => {
      if (!this.active) return resolve(null);
      this.rec.onstop = () => {
        this.stopMeter?.(); this.stopMeter = null;
        this.stream.getTracks().forEach((t) => t.stop());
        resolve(new Blob(this.chunks, { type: (this.rec.mimeType || "audio/webm").split(";")[0] }));
      };
      this.rec.stop();
    });
  }
}

async function transcribe(blob, language = "en") {
  const fd = new FormData();
  fd.append("audio", blob, blobName(blob));
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
$("#settings-link").innerHTML = ic("settings");
const NAV_OWNER = { settings: "settings", uninstall: "settings", home: "home", jobs: "home", situations: "home", classics: "home", brief: "home", chat: "home", report: "history",
  retell: "history", phrases: "phrases", train: "phrases", history: "history", notebook: "notebook", profile: "profile" };

async function pollStatus() {
  const el = $("#status");
  try {
    const s = await api("/api/status");
    FLAGS = { ...(FLAGS || {}), setup_done: s.setup_done, onboarding_done: s.onboarding_done, track: s.track };
    if (!s.setup_done) { el.textContent = "configuração pendente"; el.className = "status"; setTimeout(pollStatus, 4000); return; }
    if (s.stt && s.tts) {
      el.textContent = "pronto para falar";
      el.title = `ouvido: ${s.stt} · conversa: ${s.chat_model} · feedback: ${s.feedback_model}`;
      el.className = "status ok";
      return;
    }
    el.textContent = "carregando voz…";
    el.className = "status";
  } catch { el.textContent = "servidor desligado"; el.className = "status off"; }
  setTimeout(pollStatus, 2500);
}

let SCENARIOS = [];
let FLAGS = null; // {setup_done, onboarding_done} from the server
let cleanup = null;
const scenariosList = async () => (SCENARIOS.length ? SCENARIOS : (SCENARIOS = await api("/api/scenarios")));

// Loading: the first view keeps the static boot screen (index.html) until it renders; later views get a
// small one only when they take longer than 250 ms, so fast pages never flash.
const BOOT_STEPS = ["Abrindo a linha com o servidor local", "Carregando o reconhecimento de voz", "Detectando placa de vídeo e processador",
  "Quase lá: na primeira vez o Python prepara as bibliotecas"];
const loadingHTML = (title = "Carregando…", step = "") => `<section class="boot small" role="status" aria-live="polite">
  <div class="hood boot-hood">${strip(12, "lg busy")}</div><p class="boot-title">${esc(title)}</p><p class="boot-step">${esc(step)}</p></section>`;
let booting = !!document.querySelector(".boot");
let bootTimer = booting ? setInterval(() => {
  const el = $("#boot-step");
  if (!el) return clearInterval(bootTimer);
  const i = Math.min(BOOT_STEPS.length - 1, BOOT_STEPS.indexOf(el.textContent) + 1);
  el.textContent = BOOT_STEPS[i];
  if (i === BOOT_STEPS.length - 1) el.closest(".boot")?.classList.add("slow");
}, 2600) : null;

async function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  stopAudio();
  const [name, arg, arg2] = (location.hash.slice(1) || "home").split("/");
  if (!FLAGS) FLAGS = await api("/api/status").catch(() => ({ setup_done: true, onboarding_done: true }));
  // First run: setup before anything else, then the introduction (skippable).
  if (!FLAGS.setup_done && name !== "setup") { location.hash = "setup"; return; }
  if (FLAGS.setup_done && !FLAGS.onboarding_done && name === "home") { location.hash = "onboard/mic"; return; }
  flow(null);
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === (NAV_OWNER[name] || "home")));
  let slow = null;
  if (booting) {
    booting = false; // keep the boot screen on screen until this first view replaces it
  } else {
    view.innerHTML = "";
    slow = setTimeout(() => { if (!view.childElementCount) view.innerHTML = loadingHTML(); }, 250);
  }
  window.scrollTo({ top: 0 });
  const pages = { home: renderHome, jobs: renderJobs, situations: renderSituations, classics: renderClassics, brief: renderBrief,
    chat: renderChat, report: renderReport, retell: renderRetell, phrases: renderPhrases, train: renderTrain,
    history: renderHistory, notebook: renderNotebook, profile: renderProfile,
    setup: renderSetup, onboard: renderOnboard, settings: renderSettings, uninstall: renderUninstall };
  try {
    await (pages[name] || renderHome)(arg, arg2);
    clearTimeout(slow);
    clearInterval(bootTimer);
  } catch (e) {
    clearTimeout(slow);
    clearInterval(bootTimer);
    view.innerHTML = `<div class="panel"><p class="error">Algo deu errado: ${esc(e.message)}</p><p class="muted" style="margin-top:8px">
      Verifique se o english-hub está aberto (start.bat no Windows, start.command no Mac) e tente de novo.</p><p style="margin-top:12px"><a href="#home">Voltar ao início</a></p></div>`;
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
  view.innerHTML = pageHead("Preparando a cena…", esc(msg)) + loadingPanel("Isso usa a IA do seu plano. Pode levar até um minuto.");
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
    pendingScenario = { id, title_pt: c.title_pt, title: c.title, persona: c.persona?.name, role: c.persona?.role, voice: c.persona?.voice, briefing: c };
  } else {
    const s = (await scenariosList()).find((x) => x.id === id);
    pendingScenario = { ...s, role: s.title_pt };
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
    ? { id: "c" + fresh.id, title: fresh.title, desc: fresh.desc_pt, persona: fresh.persona, voice: fresh.voice, tag: fresh.source?.label || "Cenário salvo" }
    : { id: scs[0].id, title: scs[0].title_pt, desc: scs[0].desc_pt, persona: scs[0].persona, voice: scs[0].voice, tag: "Clássico" };

  view.innerHTML = `
  <div class="home-grid">
    <div>
      <section class="hood hero" aria-labelledby="next-title">
        <div class="top-line">
          <span class="lower-third">${avatar(next.voice, next.persona, "lg")}
            <span><span class="name">${esc(next.persona)}</span><br><span class="role">Próxima ligação · ${esc(next.tag)}</span></span></span>
        </div>
        <div class="copy">
          <h1 id="next-title">${esc(next.title)}</h1>
          <p>${esc(next.desc)}</p>
          <div class="cta">
            <button class="btn btn-primary btn-lg" id="go-next">${ic("phone")} Ligar agora</button>
            ${fresh ? `<a class="btn" href="#brief/${fresh.id}">${ic("file")} Ler o roteiro antes</a>` : ""}
          </div>
        </div>
      </section>

      <section class="section" aria-labelledby="ways">
        <h2 id="ways">Escolha outra prática</h2>
        <nav class="rows">
          ${isDev() ? `<a class="row-item" href="#jobs"><span class="lead-ic">${ic("briefcase")}</span>
            <span class="body"><span class="title">Entrevista para uma vaga real</span>
            <span class="desc">Busque vagas abertas ou cole uma. O entrevistador lê seu perfil e investiga seus gaps.</span></span>${ic("chevron", "chev")}</a>` : ""}
          <a class="row-item" href="#situations"><span class="lead-ic">${ic(isDev() ? "bug" : "map")}</span>
            <span class="body"><span class="title">${isDev() ? "Situação de trabalho" : "Situação do dia a dia"}</span>
            <span class="desc">${isDev() ? "Relatar bug, bloqueio, atraso, incidente, code review… com a sua stack."
              : "Pedido errado, troca de compra, atendimento por telefone, farmácia, apartamento, combinar um programa."}</span></span>${ic("chevron", "chev")}</a>
          <a class="row-item" href="#classics"><span class="lead-ic">${ic("message")}</span>
            <span class="body"><span class="title">Conversas clássicas e cenários salvos</span>
            <span class="desc">${isDev() ? "Triagem, técnica, comportamental, daily, conversa livre" : "Conhecer alguém, aeroporto, hotel, restaurante, médico, conversa livre"}${custom.length ? ` · ${plural(custom.length, "salvo", "salvos")}` : ""}.</span></span>${ic("chevron", "chev")}</a>
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
        <p class="muted">${isDev() ? "Entrevistas e situações usam sua stack e experiência." : "As conversas ficam mais pessoais com o que você contar."}</p><a class="btn" href="#profile" style="margin-top:10px">Preencher perfil</a></div></div>` : ""}
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
  view.innerHTML = pageHead(isDev() ? "Situação de trabalho" : "Situação do dia a dia",
    isDev() ? "Cada escolha gera uma cena nova e fictícia com a sua stack. O roteiro traz todos os fatos em português; o desafio é comunicar em inglês."
      : "Cada escolha gera uma cena nova e fictícia. O roteiro traz todos os fatos em português; o desafio é resolver em inglês.",
    ["#home", "Praticar"]) + `
    <div class="row" style="margin-bottom:16px"><span class="muted">Interlocutor</span>
      <div class="seg" role="group" aria-label="Clima da conversa">
        <button type="button" data-pressure="calm" aria-pressed="true">Tranquilo</button>
        <button type="button" data-pressure="pressured" aria-pressed="false">${isDev() ? "Sob pressão" : "Com pressa"}</button></div></div>
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
      ${avatar(s.voice, s.persona)}
      <span class="body"><span class="title">${esc(s.title_pt)}</span><span class="desc">${esc(s.persona)} · ${esc(s.desc_pt)}</span></span>
      ${ic("mic", "chev")}</button>`).join("")}</nav>
    <section class="section"><h2>Cenários salvos</h2>
      ${custom.length ? `<div class="rows">${custom.map((c) => `<div class="row-item row-static">
        ${avatar(c.voice, c.persona)}
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
        <div class="panel"><div class="lower-third">${avatar(who.voice, who.name, "lg")}
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

    <div class="hood scene call">
      <div class="bar">
        <span class="pill call-time"><span class="live-dot" aria-hidden="true"></span><span id="call-time" class="num">00:00</span></span>
        <div class="seg" role="group" aria-label="Legendas">${CC_MODES.map(([v, l]) => `<button type="button" data-cc="${v}" aria-pressed="${v === cc}">${v === "off" ? ic("cc") : ""}${l}</button>`).join("")}</div>
      </div>
      <div class="speaker" id="speaker" style="--lvl:0">
        <span class="ring" aria-hidden="true"></span>${avatar(scenario.voice, scenario.persona, "face")}
      </div>
      <div class="line" aria-live="polite">
        <div id="sub-slot"></div>
        <div id="you"></div>
      </div>
      <div class="nameplate" id="nameplate" style="--lvl:0">
        <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
        <span><strong>${esc(scenario.persona)}</strong> <span class="role">· ${esc(scenario.briefing?.persona?.role || scenario.role || "")}</span></span>
      </div>
      <div class="self-tile" id="self-tile" style="--lvl:0" aria-label="Seu microfone">
        <span class="avatar">VC</span><span class="self-name">Você</span>
        <span class="self-mic" id="self-mic">${ic("micOff")}</span>
        <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
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

  // ---- meeting-style speaking indicators driven by real audio levels ----
  const speakerEl = $("#speaker"), plate = $("#nameplate"), selfTile = $("#self-tile");
  speakLevel = (l) => { speakerEl.style.setProperty("--lvl", l.toFixed(3)); plate.style.setProperty("--lvl", l.toFixed(3)); };
  rec.onLevel = (l) => selfTile.style.setProperty("--lvl", l.toFixed(3));
  const setPartnerSpeaking = (on) => { speakerEl.classList.toggle("speaking", on); plate.classList.toggle("speaking", on); };
  const setSelfLive = (on) => {
    selfTile.classList.toggle("live", on);
    $("#self-mic").innerHTML = ic(on ? "mic" : "micOff");
  };
  const t0 = Date.now();
  const clock = setInterval(() => { const s = Math.floor((Date.now() - t0) / 1000); $("#call-time").textContent = fmtSec(s).padStart(5, "0"); }, 1000);

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
    setPartnerSpeaking(true);
    await speak(text, session.voice);
    setPartnerSpeaking(false);
    renderSubtitle(false);
    if (!rec.active) setBusy(false);
  }

  async function startRec() {
    if (busy || rec.active) return;
    try { await rec.start(); } catch (e) { hint.textContent = "Sem acesso ao microfone: " + e.message; return; }
    setPartnerSpeaking(false);
    setSelfLive(true);
    mic.classList.add("rec");
    mic.setAttribute("aria-label", "Parar e enviar");
    mic.innerHTML = ic("square");
    hint.innerHTML = "Gravando… clique de novo ou solte <kbd>Espaço</kbd> para enviar";
  }
  async function stopRec() {
    if (!rec.active) return;
    setSelfLive(false);
    mic.classList.remove("rec");
    mic.setAttribute("aria-label", "Falar");
    mic.innerHTML = ic("mic");
    const blob = await rec.stop();
    if (Date.now() - rec.startedAt < 600) { setBusy(false, "Muito curto. Tente de novo."); return; }
    setBusy(true, "Transcrevendo…");
    const fd = new FormData();
    fd.append("audio", blob, blobName(blob));
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
    speakLevel = null;
    clearInterval(clock);
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
      ${r.retell?.question ? `<div class="panel retell-panel"><h3>${ic("repeat")} Responda de novo</h3>
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

const PROFILE_TEMPLATE_DAILY = `Nome e cidade:
Trabalho ou estudo:
Por que estou aprendendo inglês: (viagem, morar fora, amigos, séries...)
Viagens ou planos que vêm por aí:
Hobbies e assuntos de que gosto:
Situações que me deixam travado em inglês:`;
const profileTemplate = () => (isDev() ? PROFILE_TEMPLATE : PROFILE_TEMPLATE_DAILY);
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
  view.innerHTML = pageHead("Perfil", isDev() ? "Os entrevistadores leem isto antes da conversa, para ter expectativas e investigar gaps. As situações de trabalho usam a sua stack."
    : "Os interlocutores usam isto para deixar as conversas mais pessoais: sua cidade, seus planos, o que você gosta.") + `
    <div class="split">
      <form class="panel stack" id="profile-form">
        <label class="field" for="profile-text">Seu mini-CV, em português ou inglês. Pode colar o CV inteiro.</label>
        <textarea id="profile-text" rows="16"></textarea>
        <div class="row"><button class="btn btn-primary" type="submit">${ic("check")} Salvar perfil</button><span id="saved" class="muted" role="status"></span></div>
      </form>
      <aside class="panel stack sticky"><h3>O que escrever</h3>
        <p class="muted" style="font-size:var(--fs-sm)">${isDev() ? "Cargo, anos de experiência, stack, 2 ou 3 projetos com resultados e o tipo de vaga que você busca. Quanto mais concreto, mais realistas ficam as perguntas."
          : "De onde você é, o que faz, por que está aprendendo, viagens e planos, o que gosta. Quanto mais concreto, mais naturais ficam as conversas."}</p>
        <p style="font-size:var(--fs-sm)">Velocidade da voz, legendas e nível do interlocutor ficam em <a href="#settings">Configurações</a>.</p>
      </aside>
    </div>`;
  const ta = $("#profile-text");
  ta.value = p.text || profileTemplate();
  $("#profile-form").onsubmit = async (e) => {
    e.preventDefault();
    await api("/api/profile", { method: "PUT", json: { text: ta.value } });
    $("#saved").textContent = "Salvo.";
  };
}

// =====================================================================
// theme, progress strip, flow shell (setup + onboarding)
// =====================================================================
const THEMES = [["light", "Claro", "sun"], ["dark", "Escuro", "moon"], ["system", "Sistema", "monitor"]];
const theme = {
  get() { return store.get("theme", "system"); },
  set(t) {
    store.set("theme", t);
    if (t === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = t;
  },
};
const themeSeg = () => `<div class="seg wide" role="group" aria-label="Tema">${THEMES.map(([v, l, i]) =>
  `<button type="button" data-theme-pick="${v}" aria-pressed="${theme.get() === v}">${ic(i)} ${l}</button>`).join("")}</div>`;
function bindTheme(root) {
  $$("[data-theme-pick]", root).forEach((b) => (b.onclick = () => {
    theme.set(b.dataset.themePick);
    $$("[data-theme-pick]", root).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  }));
}

// The phone-card strip: every progress indicator fills unit by unit.
const strip = (n = 24, cls = "", id = "") => `<div class="strip ${cls}" style="--n:${n}"${id ? ` id="${id}"` : ""} aria-hidden="true">${
  Array.from({ length: n }, (_, i) => `<i style="--i:${i}"></i>`).join("")}</div>`;
function fillStrip(el, frac) {
  if (!el) return;
  const units = el.children, k = Math.round(Math.max(0, Math.min(1, frac)) * units.length);
  for (let i = 0; i < units.length; i++) units[i].classList.toggle("on", i < k);
}
const fmtBytes = (b) => {
  if (b == null) return "–";
  if (b >= 1e9) return (b / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " GB";
  if (b < 1e6) return Math.max(1, Math.round(b / 1e3)).toLocaleString("pt-BR") + " KB";
  return Math.max(1, Math.round(b / 1e6)).toLocaleString("pt-BR") + " MB";
};

const FLOW_STEPS = [["setup", "Configurar"], ["ai", "Conectar a IA"], ["mic", "Microfone e fone"], ["voice", "Voz e legendas"], ["profile", "Seu perfil"], ["call", "Primeira ligação"]];
// Step indicator: a 5-unit phone-card strip plus the current step's name.
function flow(step) {
  document.body.classList.toggle("flow", !!step);
  const box = $("#steps");
  if (!step) { box.innerHTML = ""; return; }
  const at = FLOW_STEPS.findIndex(([id]) => id === step);
  box.style.setProperty("--n", FLOW_STEPS.length);
  box.innerHTML = `<ol>${FLOW_STEPS.map(([, label], i) => `<li class="${i < at ? "done" : i === at ? "on" : ""}" title="${label}"
      ${i === at ? 'aria-current="step"' : ""}><span class="hidden">${label}</span></li>`).join("")}</ol>
    <span class="step-name"><span>${at + 1} de ${FLOW_STEPS.length}</span>${FLOW_STEPS[at][1]}</span>`;
}
async function setFlags(values) {
  const r = await api("/api/setup/settings", { json: { values } });
  FLAGS = { ...(FLAGS || {}), setup_done: r.setup_done, onboarding_done: r.onboarding_done };
  return r;
}

// =====================================================================
// hardware facts, quality presets and advanced model settings (setup + settings)
// =====================================================================
function factsHTML(hw) {
  const g = hw.gpu;
  const gpu = g ? `${esc(g.name)}${g.vram_mb ? ` · ${Math.round(g.vram_mb / 1024)} GB` : ""}` : "Nenhuma compatível (usa a CPU)";
  return `<div class="facts">
    <div><span>Placa de vídeo</span><b>${gpu}</b></div>
    <div><span>Processador</span><b>${esc(hw.cpu || "–")}${hw.cores ? ` · ${hw.cores} núcleos` : ""}</b></div>
    <div><span>Memória</span><b class="num">${hw.ram_gb ? Math.round(hw.ram_gb) + " GB" : "–"}</b></div>
    <div><span>Espaço livre</span><b class="num">${hw.disk_free_gb != null ? Math.round(hw.disk_free_gb) + " GB" : "–"}</b></div>
    <div><span>Sistema</span><b>${esc(hw.os)}</b></div></div>`;
}
const PRESET_ORDER = ["recomendado", "leve", "maximo"];
function presetOf(o) {
  return PRESET_ORDER.find((k) => Object.entries(o.presets[k].values).every(([f, v]) => o.settings[f] === v)) || "custom";
}
function presetHTML(o, locked) {
  const cur = presetOf(o);
  const hint = cur === "custom" ? "Personalizada no Avançado." : o.presets[cur].hint + (cur === o.recommended ? " Indicada para este computador." : "");
  return `<div class="seg wide" role="group" aria-label="Qualidade do reconhecimento">${PRESET_ORDER.map((k) =>
    `<button type="button" data-preset="${k}" aria-pressed="${cur === k}" ${locked ? "disabled" : ""}>${esc(o.presets[k].label)}</button>`).join("")}</div>
    <p class="hint-line">${esc(hint)}</p>`;
}
const DEVICE_LABEL = { auto: "Automático (GPU, senão CPU)", cuda: "GPU NVIDIA (CUDA)", mps: "GPU do Mac (Metal)", cpu: "Só CPU" };
const COMPUTE_LABEL = { auto: "Automática", float16: "float16 (GPU grande)", int8_float16: "int8 + float16 (GPU até 6 GB)", int8: "int8 (menos memória)" };
function advancedHTML(o, locked) {
  const s = o.settings, opt = o.options, dis = locked ? "disabled" : "";
  const models = opt.whisper_models.some((m) => m.id === s.whisper_model) ? opt.whisper_models
    : [...opt.whisper_models, { id: s.whisper_model, label: s.whisper_model }];
  const sel = (key, items) => `<select data-set="${key}" ${dis}>${items.map(([v, l]) => `<option value="${esc(v)}" ${String(s[key]) === String(v) ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
  const wm = models.map((m) => [m.id, m.mb ? `${m.label} · ${fmtBytes(m.mb * 1e6)}` : m.label]);
  return `<details class="adv"><summary>Avançado ${ic("chevron")}</summary><div class="grid2">
    <label class="field">Modelo de reconhecimento ${sel("whisper_model", wm)}</label>
    <label class="field">Dispositivo ${sel("whisper_device", opt.devices.map((d) => [d, DEVICE_LABEL[d] || d]))}</label>
    <label class="field">Precisão ${sel("whisper_compute", opt.computes.map((c) => [c, COMPUTE_LABEL[c] || c]))}</label>
    <label class="field">Reserva para CPU ${sel("whisper_cpu_fallback_model", wm)}<span class="help">Usado se a GPU falhar.</span></label>
    <label class="field">Threads na CPU <input type="number" min="1" max="64" data-set="whisper_cpu_threads" value="${s.whisper_cpu_threads}" ${dis}></label>
  </div></details>`;
}
// Wires presets and advanced fields; calls onChange(overview) after each save.
function bindModelControls(root, o, onChange) {
  const save = async (values) => {
    try { await api("/api/setup/settings", { json: { values } }); } catch (e) { toast(e.message); return; }
    onChange(await api("/api/setup"));
  };
  $$("[data-preset]", root).forEach((b) => (b.onclick = () => save(o.presets[b.dataset.preset].values)));
  $$("[data-set]", root).forEach((el) => (el.onchange = () => save({ [el.dataset.set]: el.type === "number" ? Number(el.value) : el.value })));
}

// Planned job rows before the install runs, from what is already on disk.
function plannedItems(o) {
  const mb = (id) => (o.options.whisper_models.find((m) => m.id === id)?.mb || 0) * 1e6;
  const items = [{ id: "kokoro", label: "Voz · Kokoro e 10 vozes", detail: "kokoro-v1.0 · ONNX na CPU", status: o.models.kokoro ? "done" : "pending", est: o.models.kokoro ? 0 : 354e6 }];
  Object.entries(o.models.whisper).forEach(([name, ok], i) => items.push({ id: "whisper:" + name,
    label: i === 0 ? `Ouvido · Whisper ${name}` : `Reserva para CPU · Whisper ${name}`,
    detail: i === 0 ? "reconhecimento de fala" : "usado se a GPU falhar", status: ok ? "done" : "pending", est: ok ? 0 : mb(name) }));
  items.push({ id: "load", label: "Carregar e testar", detail: "ouvido e voz", status: "pending" });
  return items;
}
function jobRowHTML(it) {
  const st = it.status;
  let v = "";
  if (st === "done") v = it.id.startsWith("whisper") || it.id === "kokoro" ? (it.total ? "Baixado" : "Já baixado") : "Pronto";
  else if (st === "running") v = it.total ? `${fmtBytes(it.bytes)} de ${fmtBytes(it.total)}` : it.id === "load" ? "testando…" : "baixando…";
  else if (st === "error") v = "Falhou";
  else v = it.est ? fmtBytes(it.est) : "aguardando";
  const fill = it.total ? Math.round((it.bytes / it.total) * 100) : 40;
  return `<div class="job ${st}" style="--fill:${fill}%"><span class="mk" aria-hidden="true"></span>
    <div><div class="t">${esc(it.label)}</div><div class="d">${esc(it.detail || "")}</div></div>
    <span class="v">${esc(v)}</span>${it.error ? `<p class="e">${esc(it.error)}</p>` : ""}</div>`;
}
// Aggregate hood state for a job snapshot (or planned items when idle).
function hoodState(items, status) {
  const dl = items.filter((i) => i.id === "kokoro" || i.id.startsWith("whisper"));
  const total = dl.reduce((a, i) => a + (i.total || i.est || 0), 0);
  const got = dl.reduce((a, i) => a + (i.status === "done" ? (i.total || i.est || 0) : i.bytes || 0), 0);
  const running = items.find((i) => i.status === "running");
  const frac = total ? got / total : 1;
  if (status === "done") return { text: "Ouvido e voz prontos.", frac: 1, pct: 100, busy: false };
  if (status === "error") return { text: "Uma etapa falhou. Veja abaixo e tente de novo.", frac, pct: Math.round(frac * 100), busy: false };
  if (status === "running" && running) {
    if (running.id === "load") return { text: "Carregando o ouvido e a voz…", frac: 1, pct: 100, busy: true };
    return { text: `Baixando ${running.label.split(" · ")[1] || running.label}…`, frac, pct: Math.floor(frac * 100), busy: false, got, total };
  }
  return { text: total ? "Para baixar, uma vez só" : "Os modelos já estão no seu computador. Falta carregar e testar.", frac: 0, pct: 0, busy: false, idle: true, got, total };
}

// =====================================================================
// first-run setup
// =====================================================================
async function renderSetup(sub) {
  if (sub === "ai") return renderAISetup();
  flow("setup");
  let o = await api("/api/setup");
  let job = o.job, stale = false, timer = null;
  const rerun = o.settings.setup_done;

  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Preparando sua linha internacional</h1>
        <p class="lead">Ouvido e voz rodam no seu computador. Só a conversa usa a IA do seu plano: Claude, Gemini ou ChatGPT. Escolha a qualidade e baixe uma vez só.</p></div>
      <div class="hood setup-hood" aria-live="polite">
        <p class="state" id="h-state"></p>
        <p class="pct num" id="h-pct"></p>
        ${strip(24, "lg", "h-strip")}
        <div class="sub"><span id="h-a"></span><span id="h-b"></span></div>
      </div>
      <div class="jobs" id="jobs"></div>
    </section>
    <aside class="flow-aside" id="setup-side"></aside>
  </div>`;

  const locked = () => job.status === "running";
  function paintSide() {
    $("#setup-side").innerHTML = `
      <div><span class="label">Seu computador</span>${factsHTML(o.hardware)}</div>
      <div><span class="label">Qualidade do reconhecimento</span>${presetHTML(o, locked())}</div>
      <div><span class="label">Tema</span>${themeSeg()}</div>
      ${advancedHTML(o, locked())}
      <div class="flow-actions"><button class="btn btn-primary btn-lg btn-block" id="go"></button>
        ${rerun ? `<a class="skip" href="#settings">Voltar às configurações</a>` : ""}</div>`;
    bindTheme($("#setup-side"));
    bindModelControls($("#setup-side"), o, (next) => { o = next; stale = true; paint(); });
    $("#go").onclick = onGo;
  }
  function paintJob() {
    const items = stale || job.status === "idle" ? plannedItems(o) : job.items;
    const status = stale ? "idle" : job.status;
    const h = hoodState(items, status);
    $("#h-state").textContent = h.text;
    $("#h-pct").classList.toggle("hidden", !!(h.idle && !h.total));
    $("#h-pct").innerHTML = h.idle && h.total ? `${fmtBytes(h.total - h.got).replace(/ (GB|MB)$/, "<small>$1</small>")}` : `${h.pct}<small>%</small>`;
    const st = $("#h-strip");
    fillStrip(st, h.busy ? 1 : h.frac);
    st.classList.toggle("busy", h.busy);
    $("#h-a").textContent = h.got != null && h.total && !h.idle ? `${fmtBytes(h.got)} de ${fmtBytes(h.total)}` : "";
    $("#h-b").textContent = `${Math.round(o.hardware.disk_free_gb)} GB livres no disco`;
    $("#jobs").innerHTML = items.map(jobRowHTML).join("");
    const go = $("#go");
    go.disabled = status === "running";
    go.innerHTML = status === "running" ? "Preparando…" : status === "done" ? `Continuar: conectar a IA ${ic("arrowRight")}`
      : status === "error" ? `${ic("refresh")} Tentar de novo` : h.total - (h.got || 0) > 0 ? `${ic("download")} Baixar e preparar` : `Carregar e testar ${ic("arrowRight")}`;
  }
  function paint() { paintSide(); paintJob(); }

  async function poll() {
    job = await api("/api/setup/job").catch(() => job);
    paintJob();
    if (job.status === "running") timer = setTimeout(poll, 600);
    else { o = await api("/api/setup"); paintSide(); paintJob(); }
  }
  async function onGo() {
    if (!stale && job.status === "done") { location.hash = "setup/ai"; return; }
    stale = false;
    job = await api("/api/setup/install", { method: "POST" });
    paint();
    poll();
  }
  cleanup = () => clearTimeout(timer);
  paint();
  if (job.status === "running") poll();
}

// =====================================================================
// onboarding: mic + headphones, voice + captions, profile, first call
// =====================================================================
const OB_NEXT = { mic: "voice", voice: "profile", profile: "call" };
async function finishOnboarding(hash = "home") {
  await setFlags({ onboarding_done: true }).catch(() => {});
  location.hash = hash;
}
const obActions = (step, primaryLabel = "Continuar") => `<div class="flow-actions">
  <button class="btn btn-primary btn-lg" id="ob-next">${primaryLabel} ${ic("arrowRight")}</button>
  <button class="skip" id="ob-skip" type="button">Pular a introdução</button></div>`;
function bindObActions(step, before) {
  $("#ob-skip").onclick = () => finishOnboarding("home");
  $("#ob-next").onclick = async () => {
    if (before && (await before()) === false) return;
    location.hash = "onboard/" + OB_NEXT[step];
  };
}

async function renderOnboard(step = "mic") {
  if (!["mic", "voice", "profile", "call"].includes(step)) step = "mic";
  flow(step);
  ({ mic: obMic, voice: obVoice, profile: obProfile, call: obCall })[step]();
}

const micLine = () => (isDev() ? "I'm a software developer, and I'd like to practise speaking English at work."
  : "Hi, I'd like a table for two, please. Could we sit by the window?");
function obMic() {
  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Teste o microfone e o fone</h1>
        <p class="lead">Use fone de ouvido. Assim o microfone não capta a voz do interlocutor e o reconhecimento fica limpo.</p></div>
      <div class="hood ob-hood">
        <p class="say"><span class="lbl">Leia em voz alta</span>“${esc(micLine())}”</p>
        <div class="rec-row"><button class="mic" id="ob-mic" aria-label="Gravar">${ic("mic")}</button>${strip(32, "lg", "lvl")}</div>
        <p class="heard" id="heard">Clique no microfone, leia a frase e clique de novo.</p>
      </div>
    </section>
    <aside class="flow-aside">
      <div><span class="label">Verificação</span><div class="check-list">
        <div class="check-item" id="c-mic"><span class="mk"></span><div><b>Microfone</b><div class="d" id="c-mic-d">Ainda não testado</div></div></div>
        <div class="check-item" id="c-ear"><span class="mk"></span><div><b>Fone de ouvido</b><div class="d" id="c-ear-d">Toque uma frase e diga se ouviu</div></div>
          <button class="btn" id="ear-play">${ic("headphones")} Tocar</button></div>
      </div>
      <div class="row hidden" id="ear-ask" style="margin-top:14px"><span class="muted">Ouviu bem?</span>
        <button class="btn" data-ear="ok">${ic("check")} Ouvi</button><button class="btn btn-ghost" data-ear="bad">Não ouvi</button></div>
      <p class="hint-line hidden" id="ear-tip">Confira a saída de som do sistema e o volume. No Windows, clique no ícone de som da barra de tarefas; no Mac, em Ajustes › Som.</p>
      </div>
      ${obActions("mic")}
    </aside></div>`;
  const rec = new Recorder(), lvl = $("#lvl"), mic = $("#ob-mic"), heard = $("#heard");
  rec.onLevel = (l) => fillStrip(lvl, l);
  cleanup = () => rec.stop();
  const mark = (id, ok, text) => { $(id).classList.toggle("ok", ok === true); $(id).classList.toggle("bad", ok === false); $(id + "-d").textContent = text; };
  mic.onclick = async () => {
    if (!rec.active) {
      try { await rec.start(); } catch (e) { heard.textContent = "Sem acesso ao microfone: " + e.message + ". Permita o microfone no navegador."; mark("#c-mic", false, "Sem permissão"); return; }
      mic.classList.add("rec"); mic.innerHTML = ic("square"); mic.setAttribute("aria-label", "Parar");
      heard.textContent = "Gravando… leia a frase e clique para parar.";
      return;
    }
    mic.classList.remove("rec"); mic.innerHTML = ic("mic"); mic.disabled = true;
    heard.textContent = "Transcrevendo…";
    try {
      const r = await transcribe(await rec.stop(), "en");
      const toks = (t) => t.toLowerCase().replace(/[^a-z' ]/g, " ").split(/\s+/).filter(Boolean);
      const target = toks(micLine()), got = toks(r.text || "");
      const hit = target.filter((w) => got.includes(w)).length;
      heard.innerHTML = r.text ? `Entendi: <b>${esc(r.text)}</b>` : "Não ouvi nada. Fale mais perto do microfone.";
      const ok = hit / target.length >= 0.7;
      mark("#c-mic", r.text ? ok : false, r.text ? `${ok ? "Funcionando" : "Entendi pouco"}: ${hit} de ${target.length} palavras` : "Não captou som");
    } catch (e) { heard.textContent = "Erro: " + e.message; mark("#c-mic", false, "Erro ao transcrever"); }
    mic.disabled = false;
  };
  $("#ear-play").onclick = async () => {
    $("#ear-play").disabled = true;
    try { await speak("Hi! Can you hear me clearly? If so, you're all set for your first call.", "af_heart"); } catch (e) { toast(e.message); }
    $("#ear-play").disabled = false;
    $("#ear-ask").classList.remove("hidden");
  };
  $$("[data-ear]").forEach((b) => (b.onclick = () => {
    const ok = b.dataset.ear === "ok";
    mark("#c-ear", ok, ok ? "Funcionando" : "Sem som");
    $("#ear-tip").classList.toggle("hidden", ok);
    $("#ear-ask").classList.add("hidden");
  }));
  bindObActions("mic");
}

const voiceSample = () => (isDev()
  ? { voice: "am_michael", name: "Mike", role: "Senior engineer · exemplo", line: "So, tell me a bit about the last project you worked on. What was your part in it?" }
  : { voice: "af_nicole", name: "Jessica", role: "Garçonete · exemplo", line: "Hi there! Are you ready to order, or do you need a few more minutes with the menu?" });
function obVoice() {
  const vs = voiceSample();
  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Ajuste a voz e as legendas</h1>
        <p class="lead">Comece num ritmo confortável. Dá para mudar tudo no meio da ligação e em Configurações.</p></div>
      <div class="hood ob-hood">
        <div class="lower-third">${avatar(vs.voice, vs.name, "lg")}<span><span class="name">${vs.name}</span><br><span class="role">${vs.role}</span></span></div>
        <p class="say subtitle" id="v-sub" style="text-align:left">${esc(vs.line)}</p>
        <p class="heard" id="v-hint"></p>
        <div><button class="btn btn-on-hood" id="v-play">${ic("play")} Ouvir nessa velocidade</button></div>
      </div>
    </section>
    <aside class="flow-aside">
      <div><span class="label">Velocidade da voz <span class="num" id="speed-val"></span></span>
        <input id="v-speed" type="range" min="0.7" max="1.2" step="0.05" style="width:100%" aria-label="Velocidade da voz"></div>
      <div><span class="label">Legendas ao começar</span><div class="choice" id="v-cc">
        <button type="button" data-cc="off"><span><span class="t">Sem legenda</span><span class="d">Só áudio, como numa call real. Peça para repetir.</span></span></button>
        <button type="button" data-cc="reveal"><span><span class="t">Sob demanda</span><span class="d">Borrada até você clicar. Conta como ajuda de escuta.</span></span></button>
        <button type="button" data-cc="on"><span><span class="t">Sempre</span><span class="d">Texto visível o tempo todo.</span></span></button></div></div>
      <div><span class="label">Interlocutor</span><div class="seg wide" role="group" aria-label="Nível do interlocutor">
        <button type="button" data-level="friendly">Amigável</button><button type="button" data-level="realistic">Realista</button></div>
        <p class="hint-line" id="v-level-hint"></p></div>
      ${obActions("voice")}
    </aside></div>`;
  const speed = $("#v-speed");
  speed.value = settings.speed;
  const show = () => {
    $("#speed-val").textContent = "· " + Number(speed.value).toFixed(2).replace(".", ",") + "×";
    const cc = settings.cc;
    $$("[data-cc]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cc === cc)));
    $$("[data-level]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.level === settings.level)));
    $("#v-level-hint").textContent = settings.level === "friendly" ? "Claro e paciente, sem muita gíria." : "Velocidade e expressões de nativo.";
    const sub = $("#v-sub");
    sub.classList.toggle("blurred", cc === "reveal");
    sub.style.filter = cc === "reveal" ? "blur(8px)" : "";
    sub.style.visibility = cc === "off" ? "hidden" : "";
    $("#v-hint").textContent = cc === "off" ? "Sem legenda: você só ouve." : cc === "reveal" ? "Clique na legenda para revelar." : "";
  };
  $("#v-sub").onclick = () => { $("#v-sub").style.filter = ""; };
  speed.oninput = () => { store.set("speed", Number(speed.value)); show(); };
  $$("[data-cc]").forEach((b) => (b.onclick = () => { store.set("cc", b.dataset.cc); show(); }));
  $$("[data-level]").forEach((b) => (b.onclick = () => { store.set("level", b.dataset.level); show(); }));
  $("#v-play").onclick = () => speak(vs.line, vs.voice).catch((e) => toast(e.message));
  show();
  bindObActions("voice");
}

async function obProfile() {
  const p = await api("/api/profile");
  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Para que você vai usar?</h1>
        <p class="lead">Isso muda as conversas, as situações e os pacotes de vocabulário. Dá para trocar em Configurações.</p></div>
      <div style="margin-top:28px" id="ob-track">${trackChoice()}</div>
      <label class="label" for="ob-profile" style="display:block;margin:32px 0 10px">Conte quem você é <span class="faint">· em português ou inglês; pode colar o CV inteiro</span></label>
      <textarea id="ob-profile" rows="10"></textarea>
    </section>
    <aside class="flow-aside">
      <div><span class="label">O que ajuda</span><ul class="clean muted" style="font-size:var(--fs-sm)" id="ob-tips"></ul></div>
      <p class="hint-line">Fica salvo em <a href="#profile">Perfil</a> e pode ser editado quando quiser.</p>
      <div class="flow-actions"><button class="btn btn-primary btn-lg" id="ob-next">Salvar e continuar ${ic("arrowRight")}</button>
        <button class="skip" id="ob-later" type="button">Preencher depois</button></div>
    </aside></div>`;
  const ta = $("#ob-profile");
  const tips = () => ($("#ob-tips").innerHTML = (isDev()
    ? ["Cargo e anos de experiência", "Stack: linguagens, frameworks, bancos, cloud", "2 ou 3 projetos: o que você fez e o resultado", "O tipo de vaga que você busca", "Gaps que você sabe que tem"]
    : ["De onde você é e o que faz", "Por que está aprendendo inglês", "Viagens ou planos que vêm por aí", "Hobbies e assuntos de que gosta", "Situações em que você trava"]).map((t) => `<li>${t}</li>`).join(""));
  const isTemplate = (v) => !v.trim() || v === PROFILE_TEMPLATE || v === PROFILE_TEMPLATE_DAILY;
  ta.value = p.text || profileTemplate();
  tips();
  bindTrack($("#ob-track"), () => { if (isTemplate(ta.value)) ta.value = profileTemplate(); tips(); });
  $("#ob-later").onclick = () => (location.hash = "onboard/call");
  $("#ob-next").onclick = async () => {
    if (!isTemplate(ta.value)) await api("/api/profile", { method: "PUT", json: { text: ta.value } });
    location.hash = "onboard/call";
  };
}

async function obCall() {
  const scs = await scenariosList();
  const picks = (isDev() ? ["free", "recruiter"] : ["chat", "restaurant"]).map((id) => scs.find((s) => s.id === id)).filter(Boolean);
  let chosen = picks[0]?.id;
  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Sua primeira ligação</h1>
        <p class="lead">Uma conversa curta para sentir o ritmo. Encerre quando quiser: o feedback aponta só o que mais atrapalhou.</p></div>
      <div class="hood ob-hood"><div class="choice" id="call-pick">${picks.map((s) => `<button type="button" data-pick="${s.id}">
        ${avatar(s.voice, s.persona, "lg")}<span><span class="t">${esc(s.title_pt)}</span><span class="d">com ${esc(s.persona)} · ${esc(s.desc_pt)}</span></span></button>`).join("")}</div></div>
    </section>
    <aside class="flow-aside">
      <div><span class="label">Durante a ligação</span><ul class="keys">
        <li><b>Falar</b><span>Segure <kbd>Espaço</kbd> ou clique no microfone laranja</span></li>
        <li><b>Legendas</b><span>Troque no canto da ligação</span></li>
        <li><b>Travou?</b><span><em>Como se diz?</em>: fale em português e receba duas formas em inglês</span></li>
        <li><b>Terminar</b><span><em>Encerrar e ver feedback</em></span></li></ul></div>
      <div class="flow-actions"><button class="btn btn-primary btn-lg" id="ob-next">${ic("phone")} Ligar agora</button>
        <button class="skip" id="ob-skip" type="button">Ir para o início</button></div>
    </aside></div>`;
  const mark = () => $$("[data-pick]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pick === chosen)));
  $$("[data-pick]").forEach((b) => (b.onclick = () => { chosen = b.dataset.pick; mark(); }));
  mark();
  $("#ob-skip").onclick = () => finishOnboarding("home");
  $("#ob-next").onclick = async () => {
    await setFlags({ onboarding_done: true }).catch(() => {});
    startScenario(chosen);
  };
}

// =====================================================================
// settings
// =====================================================================
async function renderSettings() {
  let o = await api("/api/setup");
  let job = o.job, timer = null, dirty = false, aiP = null;
  view.innerHTML = pageHead("Configurações", "Aparência, ritmo da conversa e os modelos que rodam no seu computador.") + `<div class="settings" id="set"></div>`;
  const root = $("#set");
  function paint() {
    const running = job.status === "running";
    const missing = !o.models.kokoro || Object.values(o.models.whisper).some((x) => !x);
    root.innerHTML = `
      <section class="set-sec"><header><h2>Aparência</h2><p>Sistema acompanha o claro ou escuro do seu computador.</p></header>
        <div class="body">${themeSeg()}</div></section>
      <section class="set-sec"><header><h2>Foco</h2><p>Muda as conversas, as situações e os pacotes de vocabulário.</p></header>
        <div class="body" id="s-track">${trackChoice()}</div></section>
      <section class="set-sec"><header><h2>Conversa</h2><p>Valem para as próximas ligações.</p></header><div class="body">
        <label class="field"><span class="inline">Velocidade da voz <span class="num" id="s-speed-val"></span></span><input id="s-speed" type="range" min="0.7" max="1.2" step="0.05"></label>
        <label class="field">Legendas ao começar <select id="s-cc">${CC_MODES.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
        <label class="field">Nível do interlocutor <select id="s-level"><option value="friendly">Amigável: claro, sem muita gíria</option><option value="realistic">Realista: velocidade e expressões nativas</option></select></label>
      </div></section>
      <section class="set-sec"><header><h2>Reconhecimento e modelos</h2><p>Trocar o modelo baixa o novo e recarrega o ouvido.</p></header><div class="body">
        ${presetHTML(o, running)}
        ${advancedHTML(o, running)}
        <div id="s-job"></div>
      </div></section>
      <section class="set-sec"><header><h2>Inteligência artificial</h2><p>Instale, entre e teste a CLI de cada plano, e escolha quem faz cada parte.</p></header>
        <div class="body"><div id="s-ai"></div><div class="roles stack" id="s-roles"></div></div></section>
      <section class="set-sec"><header><h2>Seu computador</h2></header><div class="body">${factsHTML(o.hardware)}</div></section>
      <section class="set-sec"><header><h2>Introdução</h2><p>Teste de microfone e fone, voz, perfil e uma primeira ligação.</p></header><div class="body">
        <div class="row"><button class="btn" id="s-onboard">${ic("repeat")} Refazer a introdução</button>
          <a class="btn btn-ghost" href="#setup">Abrir a configuração inicial</a></div></div></section>
      <section class="set-sec"><header><h2>Desinstalar</h2><p>Escolha o que remover: cada modelo, seus dados, o app ou as CLIs.</p></header>
        <div class="body"><div><a class="btn btn-danger" href="#uninstall">${ic("trashAll")} Desinstalar…</a></div></div></section>`;
    bindTheme(root);
    bindModelControls(root, o, (next) => { o = next; dirty = true; paint(); });
    const sp = $("#s-speed"), cc = $("#s-cc"), lv = $("#s-level");
    sp.value = settings.speed; cc.value = settings.cc; lv.value = settings.level;
    const showSpeed = () => ($("#s-speed-val").textContent = Number(sp.value).toFixed(2).replace(".", ",") + "×");
    showSpeed();
    sp.oninput = () => { store.set("speed", Number(sp.value)); showSpeed(); };
    cc.onchange = () => store.set("cc", cc.value);
    lv.onchange = () => store.set("level", lv.value);
    $("#s-onboard").onclick = async () => { await setFlags({ onboarding_done: false }); location.hash = "onboard/mic"; };
    bindTrack($("#s-track"), () => toast(isDev() ? "Foco: trabalho como desenvolvedor" : "Foco: dia a dia"));
    aiP?.stop();
    aiP = aiPanel($("#s-ai"), $("#s-roles"));
    aiP.load();
    paintJob(missing);
  }
  function paintJob(missing) {
    const box = $("#s-job");
    const status = dirty ? "idle" : job.status;
    if (status === "idle" && !dirty && !missing) { box.innerHTML = ""; return; }
    const items = status === "idle" ? plannedItems(o) : job.items;
    const h = hoodState(items, status);
    box.innerHTML = `<div class="panel stack"><div class="row" style="justify-content:space-between"><b>${esc(h.text)}</b>
        <span class="num muted">${status === "running" && !h.busy ? h.pct + "%" : ""}</span></div>
      ${strip(32, h.busy ? "busy" : status === "done" ? "ok" : "", "s-strip")}
      <div class="jobs">${items.map(jobRowHTML).join("")}</div>
      ${status === "running" ? "" : `<div><button class="btn btn-primary" id="s-apply">${status === "done" ? ic("check") + " Feito" : ic("refresh") + " Aplicar e preparar"}</button></div>`}</div>`;
    fillStrip($("#s-strip"), h.busy ? 1 : h.frac);
    const apply = $("#s-apply");
    if (apply) apply.onclick = async () => {
      if (status === "done") { box.innerHTML = ""; return; }
      dirty = false;
      job = await api("/api/setup/install", { method: "POST" });
      paint(); poll();
    };
  }
  async function poll() {
    job = await api("/api/setup/job").catch(() => job);
    if (job.status === "running") { paintJob(true); timer = setTimeout(poll, 700); } else { o = await api("/api/setup"); paint(); }
  }
  cleanup = () => { clearTimeout(timer); aiP?.stop(); };
  paint();
  if (job.status === "running") poll();
}

// =====================================================================
// track (dev | daily)
// =====================================================================
const TRACKS = [
  ["dev", "Trabalho como desenvolvedor", "Entrevistas para vagas internacionais reais, daily, bugs, incidentes, code review, com a sua stack."],
  ["daily", "Dia a dia", "Viagem, aeroporto, hotel, restaurante, médico, compras, atendimento por telefone e fazer amigos."],
];
const trackChoice = () => `<div class="choice" role="group" aria-label="Para que você vai usar">${TRACKS.map(([v, t, d]) =>
  `<button type="button" data-track="${v}" aria-pressed="${(FLAGS?.track || "dev") === v}">${ic(v === "dev" ? "briefcase" : "map")}
    <span><span class="t">${t}</span><span class="d">${d}</span></span></button>`).join("")}</div>`;
async function setTrack(t) {
  const r = await api("/api/setup/settings", { json: { values: { track: t } } });
  FLAGS = { ...(FLAGS || {}), track: r.track };
  SCENARIOS = [];
  store.set("jobs", null);
}
function bindTrack(root, onChange) {
  $$("[data-track]", root).forEach((b) => (b.onclick = async () => {
    await setTrack(b.dataset.track);
    $$("[data-track]", root).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    onChange?.(b.dataset.track);
  }));
}

// =====================================================================
// AI providers: install, sign in (terminal), test, and who does what
// =====================================================================
const ROLE_INFO = [["chat", "Conversa", "Responde ao vivo."],
  ["feedback", "Feedback e cenários", "Relatório, roteiros e pacotes; vale o modelo mais forte."],
  ["helper", "Ajudas", "“Como se diz?”, re-tell e frases."]];
const PROVIDER_SPEED = { claude: "Mais rápido na conversa (1 a 3 s por fala).", gemini: "Cada fala leva uns 10 s.", codex: "Cada fala leva alguns segundos." };

function providerStatus(p) {
  const t = p.task;
  if (t?.status === "running") return { st: "running", text: t.kind === "install" ? "Instalando…" : "Removendo…", log: t.log?.at(-1) };
  if (p.testing) return { st: "running", text: "Testando… (até 90 s)" };
  if (!p.installed) return { st: t?.status === "error" ? "error" : "pending", text: t?.status === "error" ? t.error : "Não instalado" };
  if (p.test?.ok) return { st: "done", text: `Pronto: ${p.test.message}` };
  if (p.test && !p.test.ok) return { st: "error", text: p.test.message };
  if (p.signed_in === false) return { st: "error", text: "Sem login. Entre na sua conta." };
  if (p.signed_in === true) return { st: "partial", text: "Conectado, ainda não testado." };
  return { st: "partial", text: "Instalado. Falta entrar na sua conta e testar." };
}
function providerRowHTML(p) {
  const s = providerStatus(p);
  const busy = s.st === "running";
  let acts = "";
  if (p.confirmInstall) {
    acts = `<span class="muted">Instalar com o instalador oficial?</span>
      <button class="btn" data-ai="install-yes" data-pid="${p.id}">Instalar</button>
      <button class="btn btn-ghost" data-ai="install-no" data-pid="${p.id}">Cancelar</button>`;
  } else if (!p.installed) {
    acts = p.can_install ? `<button class="btn" data-ai="install" data-pid="${p.id}" ${busy ? "disabled" : ""}>${ic("download")} Instalar</button>` : "";
  } else if (!p.test?.ok) {
    acts = `<button class="btn" data-ai="login" data-pid="${p.id}" ${busy ? "disabled" : ""}>${ic("user")} Entrar</button>
      <button class="btn" data-ai="test" data-pid="${p.id}" ${busy ? "disabled" : ""}>${ic("refresh")} Testar</button>`;
  }
  const retest = p.test?.ok && !busy ? ` · <button class="link-btn" data-ai="test" data-pid="${p.id}">testar de novo</button>` : "";
  return `<div class="job prov ${s.st}" data-row="${p.id}"><span class="mk" aria-hidden="true"></span>
    <div><div class="t">${esc(p.label)} <span class="muted" style="font-weight:500">· ${esc(p.cli)}${p.version ? " " + esc(p.version) : ""}</span></div>
      <div class="d">${esc(p.plan)}</div>
      <div class="d prov-state">${esc(s.text)}${retest}</div>
      ${s.log ? `<div class="d prov-log num">${esc(s.log)}</div>` : ""}
      ${busy ? strip(16, "sm busy", "") : ""}
      ${p.note && !p.installed ? `<div class="d">${esc(p.note)}</div>` : ""}
      ${p.hint ? `<p class="hint-line">${esc(p.hint)}</p>` : ""}</div>
    <div class="row prov-acts">${acts}</div></div>`;
}
const MODEL_LABEL = { haiku: "Haiku · mais rápido", sonnet: "Sonnet · equilibrado", opus: "Opus · mais forte" };
function rolesHTML(ai) {
  return ROLE_INFO.map(([role, label, help]) => {
    const r = ai.roles[role], cat = ai.catalog[r.provider];
    const model = cat.models.length
      ? `<select data-role-model="${role}" aria-label="Modelo para ${label}">${cat.models.map((m) => `<option value="${m}" ${m === r.model ? "selected" : ""}>${MODEL_LABEL[m] || m}</option>`).join("")}</select>`
      : `<input type="text" data-role-model="${role}" value="${esc(r.model)}" placeholder="padrão do plano" aria-label="Modelo para ${label}">`;
    return `<div class="field role-field"><span>${label}</span>
      <div class="role-pick"><select data-role-provider="${role}" aria-label="Provedor para ${label}">${Object.entries(ai.catalog).map(([pid, c]) =>
        `<option value="${pid}" ${pid === r.provider ? "selected" : ""}>${esc(c.label)}</option>`).join("")}</select>${model}</div>
      <span class="help">${help}${role === "chat" && PROVIDER_SPEED[r.provider] ? " " + esc(PROVIDER_SPEED[r.provider]) : ""}</span></div>`;
  }).join("");
}

// Providers list into `root`, role pickers into `rolesBox`. Returns {load, test, ai, stop}.
function aiPanel(root, rolesBox, { onState } = {}) {
  let ai = null, timer = null;
  const testing = new Set(), hints = {}, confirming = new Set();
  function paint() {
    ai.providers.forEach((p) => { p.testing = testing.has(p.id); p.hint = hints[p.id]; p.confirmInstall = confirming.has(p.id); });
    root.innerHTML = `<div class="jobs">${ai.providers.map(providerRowHTML).join("")}</div>`;
    rolesBox.innerHTML = rolesHTML(ai);
    onState?.(ai);
  }
  async function load() {
    ai = await api("/api/ai");
    paint();
    clearTimeout(timer);
    if (ai.providers.some((p) => p.task?.status === "running")) timer = setTimeout(load, 1200);
  }
  async function test(pid) {
    testing.add(pid); hints[pid] = "";
    if (ai) paint();
    try { await api(`/api/ai/${pid}/test`, { method: "POST" }); } catch (e) { toast(e.message); }
    testing.delete(pid);
    load();
  }
  root.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-ai]");
    if (!b) return;
    const pid = b.dataset.pid, act = b.dataset.ai, p = ai.providers.find((x) => x.id === pid);
    if (act === "test") return test(pid);
    if (act === "install") { confirming.add(pid); return paint(); }
    if (act === "install-no") { confirming.delete(pid); return paint(); }
    if (act === "install-yes") {
      confirming.delete(pid);
      await api(`/api/ai/${pid}/install`, { method: "POST" });
      return load();
    }
    if (act === "login") {
      try { const r = await api(`/api/ai/${pid}/login`, { method: "POST" }); hints[pid] = r.message + " Depois clique em Testar."; } catch (err) { hints[pid] = err.message; }
      return load();
    }
  });
  rolesBox.addEventListener("change", async (e) => {
    const prov = e.target.closest("[data-role-provider]"), mod = e.target.closest("[data-role-model]");
    if (!prov && !mod) return;
    const role = prov ? prov.dataset.roleProvider : mod.dataset.roleModel;
    const values = prov ? { [role + "_provider"]: prov.value, [role + "_model"]: ai.catalog[prov.value].defaults[role] }
      : { [role + "_model"]: mod.value.trim() };
    try { await api("/api/setup/settings", { json: { values } }); } catch (err) { toast(err.message); }
    load();
  });
  return { load, test, get ai() { return ai; }, stop: () => clearTimeout(timer) };
}
const providersInUse = (ai) => [...new Set(Object.values(ai.roles).map((r) => r.provider))];

async function renderAISetup() {
  flow("ai");
  view.innerHTML = `<div class="flow-grid">
    <section>
      <div class="flow-head"><h1>Conecte a IA do seu plano</h1>
        <p class="lead">O english-hub conversa pela CLI de um plano que você já tem: Claude, Gemini (Antigravity) ou ChatGPT (Codex). Sem chave de API e sem custo extra; conta nos limites do seu plano.</p></div>
      <div class="hood setup-hood" aria-live="polite">
        <p class="state" id="ai-state">Procurando as CLIs no seu computador</p>
        <p class="pct num" id="ai-count">Um instante</p>
        ${strip(3, "lg busy", "ai-strip")}
        <div class="sub"><span id="ai-sub">Claude Code, Antigravity e Codex</span></div>
      </div>
      <div id="ai-panel"><p class="hint-line" style="padding:16px 0">Lendo versões e logins…</p></div>
    </section>
    <aside class="flow-aside">
      <div><h2 class="aside-title">Quem faz o quê</h2><div class="roles stack" id="ai-roles"><p class="hint-line">Carregando…</p></div></div>
      <div class="flow-actions"><button class="btn btn-primary btn-lg btn-block" id="ai-go">Continuar ${ic("arrowRight")}</button>
        <p class="hint-line" id="ai-warn"></p></div>
    </aside></div>`;
  // The hood shows the lines the roles actually use: one working line is enough.
  const panel = aiPanel($("#ai-panel"), $("#ai-roles"), { onState: (ai) => {
    const used = providersInUse(ai), find = (pid) => ai.providers.find((p) => p.id === pid);
    const ok = used.filter((pid) => find(pid)?.test?.ok), busy = used.some((pid) => find(pid)?.testing);
    // One unit per role (conversa, feedback, ajudas), lit when that role's line has passed the test.
    const st = $("#ai-strip");
    const roleOk = ROLE_INFO.map(([r]) => !!find(ai.roles[r].provider)?.test?.ok);
    [...st.children].forEach((u, i) => u.classList.toggle("on", busy || roleOk[i]));
    st.classList.toggle("busy", busy);
    const names = used.map((pid) => ai.catalog[pid].label).join(" + ");
    if (busy) { $("#ai-state").textContent = `Testando a linha · ${names}`; $("#ai-count").innerHTML = "Chamando…"; }
    else if (ok.length === used.length) {
      $("#ai-state").textContent = `Linha liberada · ${names}`;
      $("#ai-count").innerHTML = `${esc(find(used[0]).test.message.match(/\d+ s/)?.[0] || "Pronta")}<small>${find(used[0]).test.message.match(/\d+ s/) ? "por resposta" : ""}</small>`;
    } else { $("#ai-state").textContent = `Linha ainda não testada · ${names}`; $("#ai-count").innerHTML = "Sem sinal"; }
    $("#ai-sub").textContent = "Uma linha basta. As outras são opcionais: use se quiser trocar de plano em alguma parte.";
    const bad = used.filter((pid) => !find(pid)?.test?.ok).map((pid) => ai.catalog[pid].label);
    $("#ai-warn").textContent = bad.length && !busy ? `Atenção: ${bad.join(" e ")} ainda não respondeu ao teste.` : "";
  } });
  cleanup = () => panel.stop();
  await panel.load();
  // Test the providers in use once, when there is no result yet.
  providersInUse(panel.ai).filter((pid) => { const p = panel.ai.providers.find((x) => x.id === pid); return p.installed && !p.test; })
    .forEach((pid) => panel.test(pid));
  $("#ai-go").onclick = async () => {
    await setFlags({ setup_done: true });
    location.hash = FLAGS.onboarding_done ? "home" : "onboard/mic";
  };
}

// =====================================================================
// uninstall
// =====================================================================
const UNINSTALL_GROUPS = [["models", "Modelos de voz", "Baixados na configuração. Dá para baixar de novo depois."],
  ["data", "Seus dados", "Ficam só neste computador."], ["app", "O app", ""],
  ["cli", "CLIs de IA", ""]];

async function renderUninstall() {
  const { items, folder } = await api("/api/uninstall");
  const byId = Object.fromEntries(items.map((i) => [i.id, i]));
  const chosen = new Set();
  view.innerHTML = pageHead("Desinstalar", "Escolha o que remover. Nada sai antes de você confirmar.", ["#settings", "Configurações"]) + `
    <div class="uninstall">
      <div class="row" role="group" aria-label="Seleção rápida">
        <button class="btn" type="button" data-preset="models">Marcar só os modelos</button>
        <button class="btn" type="button" data-preset="all">Marcar tudo do english-hub</button>
        <button class="btn btn-ghost" type="button" data-preset="none">Limpar seleção</button></div>
      ${UNINSTALL_GROUPS.map(([g, title, help]) => {
        const list = items.filter((i) => i.group === g);
        if (!list.length) return "";
        return `<section class="un-group"><h2>${title}${g === "cli" ? ` <span class="pill warn">${ic("alert")} usadas fora do english-hub</span>` : ""}</h2>
          ${help ? `<p class="muted">${help}</p>` : ""}
          ${g === "cli" ? `<p class="warn-line">Remover uma CLI tira o programa do computador: se você usa no terminal ou em outro app, ela para de funcionar lá também. Sair da conta desconecta em todos os lugares.</p>` : ""}
          <div class="rows">${list.map((i) => `<label class="row-item un-item ${g === "cli" ? "risky" : ""}">
            <input type="checkbox" data-id="${esc(i.id)}" ${i.manual ? "disabled" : ""}>
            <span class="body"><span class="title">${esc(i.label)}</span><span class="desc">${esc(i.manual || i.detail)}</span></span>
            <span class="meta num">${i.bytes != null ? fmtBytes(i.bytes) : ""}</span></label>`).join("")}</div></section>`;
      }).join("")}
      <div class="un-bar" id="un-bar"><span id="un-total" class="muted"></span>
        <div class="row" id="un-acts"><button class="btn btn-danger-solid btn-lg" id="un-go" disabled>${ic("trashAll")} Remover</button></div></div>
      <div id="un-out"></div>
    </div>`;
  const sync = () => {
    $$("input[data-id]").forEach((cb) => (cb.checked = chosen.has(cb.dataset.id)));
    const bytes = [...chosen].reduce((a, id) => a + (byId[id]?.bytes || 0), 0);
    $("#un-total").textContent = chosen.size ? `${plural(chosen.size, "item", "itens")}${bytes ? " · " + fmtBytes(bytes) : ""}` : "Nada selecionado";
    $("#un-go").disabled = !chosen.size;
    $("#un-go").innerHTML = `${ic("trashAll")} Remover ${chosen.size ? plural(chosen.size, "item", "itens") : ""}`;
  };
  $$("input[data-id]").forEach((cb) => (cb.onchange = () => { cb.checked ? chosen.add(cb.dataset.id) : chosen.delete(cb.dataset.id); sync(); }));
  $$("[data-preset]").forEach((b) => (b.onclick = () => {
    chosen.clear();
    items.forEach((i) => { if ((b.dataset.preset === "models" && i.group === "models") || (b.dataset.preset === "all" && i.all)) chosen.add(i.id); });
    sync();
  }));
  sync();
  // Confirmation happens in the bar itself: list what goes, then confirm or go back.
  const bar = $("#un-bar");
  const askConfirm = () => {
    const names = [...chosen].map((id) => byId[id].label);
    const closes = [...chosen].some((id) => byId[id].closes);
    bar.classList.add("confirming");
    $("#un-total").innerHTML = `<strong>Remover ${plural(chosen.size, "item", "itens")}?</strong> ${esc(names.join(", "))}${closes ? ". O english-hub fecha no final." : "."}`;
    $("#un-acts").innerHTML = `<button class="btn btn-ghost" id="un-back">Voltar</button>
      <button class="btn btn-danger-solid btn-lg" id="un-yes">${ic("trashAll")} Confirmar e remover</button>`;
    $$("input[data-id]").forEach((cb) => (cb.disabled = true));
    $("#un-back").onclick = () => { bar.classList.remove("confirming"); $("#un-acts").innerHTML = `<button class="btn btn-danger-solid btn-lg" id="un-go">${ic("trashAll")} Remover</button>`;
      $$("input[data-id]").forEach((cb) => (cb.disabled = !!byId[cb.dataset.id]?.manual)); $("#un-go").onclick = askConfirm; sync(); };
    $("#un-yes").onclick = doRemove;
  };
  async function doRemove() {
    $("#un-total").innerHTML = `<strong>Removendo…</strong>`;
    $("#un-acts").innerHTML = `<div style="width:220px">${strip(16, "busy", "")}</div>`;
    fillStrip($("#un-acts .strip"), 1);
    let r;
    try { r = await api("/api/uninstall", { json: { ids: [...chosen] } }); } catch (e) { toast(e.message); return route(); }
    if (r.closes) return farewell(r, folder);
    bar.remove();
    $("#un-out").innerHTML = `<div class="jobs">${r.results.map((x) => `<div class="job ${x.ok ? "done" : "error"}"><span class="mk"></span>
      <div><div class="t">${esc(byId[x.id]?.label || x.id)}</div>${x.error ? `<p class="e">${esc(x.error)}</p>` : ""}</div>
      <span class="v">${x.ok ? "Removido" : "Falhou"}</span></div>`).join("")}</div>
      <div class="row" style="margin-top:16px"><a class="btn" href="#uninstall">Ver o que sobrou</a>
        ${r.results.some((x) => x.ok && x.id.startsWith("model:")) ? `<a class="btn btn-primary" href="#setup">Baixar modelos de novo</a>` : ""}</div>`;
    FLAGS = await api("/api/status");
  }
  $("#un-go").onclick = askConfirm;
}
function farewell(r, folder) {
  flow(null);
  document.body.classList.add("flow");
  view.innerHTML = `<div class="farewell"><div class="hood setup-hood">
      <p class="state">Linha encerrada</p>
      <p class="pct">${r.everything ? "Até logo." : "Fechando…"}</p>
      ${strip(24, "lg", "bye-strip")}
      <div class="sub"><span>${r.everything ? "O english-hub foi removido deste computador." : "O que você escolheu foi removido."}</span></div></div>
    <div class="stack" style="margin-top:28px;max-width:62ch">
      <p>O app fechou e termina a limpeza em alguns segundos. Pode fechar esta aba.</p>
      ${r.everything ? `<p class="muted">Para apagar de vez, apague também a pasta do projeto:<br><code>${esc(folder)}</code></p>` : ""}
      ${r.results.some((x) => !x.ok) ? `<p class="error">Alguns itens falharam: ${r.results.filter((x) => !x.ok).map((x) => esc(x.error)).join("; ")}</p>` : ""}
    </div></div>`;
  fillStrip($("#bye-strip"), 1);
  let k = 24;
  const t = setInterval(() => { k--; fillStrip($("#bye-strip"), k / 24); if (k <= 0) clearInterval(t); }, 90);
  api("/api/shutdown", { method: "POST" }).catch(() => {});
}

pollStatus();
route();
