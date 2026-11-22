"""Scenarios, personas and the prompts that implement the teaching method.

Teaching policy (agreed with the learner):
- Goal is INTELLIGIBILITY and clear communication for international dev jobs, NOT a native accent.
- During conversation: never interrupt to correct; use natural recasts only.
- After the session: few, high-impact corrections (what blocks understanding first).
- Then retell the same answer with less time (4/3/2 adapted), with feedback after round 1.
"""
from __future__ import annotations

import json

VOICES = {
    "af_heart": "American female, warm", "af_bella": "American female, energetic",
    "af_nicole": "American female, calm/soft", "am_michael": "American male, neutral",
    "am_adam": "American male, casual", "am_puck": "American male, upbeat",
    "am_eric": "American male, serious", "bf_emma": "British female", "bm_george": "British male, formal",
    "bm_lewis": "British male, relaxed",
}

# ---------- built-in (classic) scenarios ----------

SCENARIOS = {
    "recruiter": {
        "title": "Recruiter screening",
        "title_pt": "Triagem com recruiter",
        "desc_pt": "Primeira call com recruiter de startup americana: sobre você, motivação, remoto, salário.",
        "persona": "Sarah", "voice": "af_heart",
        "brief": (
            "You are Sarah, a friendly technical recruiter at a fast-growing US startup (remote-first, "
            "team spread across the Americas). This is a 30-minute screening call for a Mid-level Software "
            "Developer role. Cover, one at a time and adapting to the answers: a little small talk; "
            "'tell me about yourself'; current role and stack; why they're looking for a new job; why "
            "remote/international; experience working with English-speaking teams; availability and time "
            "zone overlap; salary expectations (in USD); and finally ask if they have questions for you."
        ),
    },
    "technical": {
        "title": "Technical interview",
        "title_pt": "Entrevista técnica",
        "desc_pt": "Engenheiro sênior pede para você explicar projetos, decisões, trade-offs e debugging.",
        "persona": "Mike", "voice": "am_michael",
        "brief": (
            "You are Mike, a senior software engineer at a US product company interviewing a Mid-level "
            "Developer. This is a conversational technical interview (no live coding). Start by asking what "
            "stack they work with, then dig into a real project they built: architecture, why they chose X "
            "over Y, trade-offs, how they'd scale it, a hard bug they debugged, testing, code review. Ask "
            "probing follow-ups like a real interviewer ('Why?', 'What would you do differently?', 'How did "
            "you measure that?'). Adapt technical depth to their stack."
        ),
    },
    "behavioral": {
        "title": "Behavioral interview (STAR)",
        "title_pt": "Entrevista comportamental (STAR)",
        "desc_pt": "Hiring manager britânica: conflitos, falhas, prazos, feedback. Treine respostas STAR.",
        "persona": "Emma", "voice": "bf_emma",
        "brief": (
            "You are Emma, an engineering manager from London at an international company, running a "
            "behavioral interview for a Mid-level Developer. Ask classic behavioral questions one at a time: "
            "a conflict with a teammate, a project that failed, a tight deadline, receiving hard feedback, "
            "disagreeing with a decision, a time they took ownership, explaining something technical to a "
            "non-technical person. If an answer lacks Situation/Task/Action/Result, ask a natural follow-up "
            "to pull out the missing part ('And what was the outcome?')."
        ),
    },
    "daily": {
        "title": "Daily standup & small talk",
        "title_pt": "Daily e small talk",
        "desc_pt": "Colega de time: papo sobre o fim de semana, depois status da daily, bloqueios e dúvidas.",
        "persona": "Jake", "voice": "am_adam",
        "brief": (
            "You are Jake, a teammate (backend engineer from Chicago) on a distributed team. Start with "
            "casual small talk before the standup (weekend, weather, plans). Then run a short daily: ask what "
            "they did yesterday, what they're doing today, any blockers. Sometimes ask them to clarify a "
            "technical detail, propose a quick pairing session, or politely push back on an estimate, so they "
            "practise everyday work communication."
        ),
    },
    "free": {
        "title": "Free conversation",
        "title_pt": "Conversa livre",
        "desc_pt": "Bate-papo descontraído com um americano sobre qualquer assunto: tech, viagens, séries, Brasil.",
        "persona": "Alex", "voice": "am_puck",
        "brief": (
            "You are Alex, a laid-back developer from Seattle who loves chatting. Have a casual conversation: "
            "tech news, side projects, travel, food, series, Brazil, football, whatever the learner enjoys. "
            "Share a bit about yourself too, like a real person, but keep the learner talking most."
        ),
    },
}

# ---------- work situations (generated on demand) ----------

SITUATIONS = {
    "bug": {
        "title_pt": "Relatar um bug", "icon": "🐞",
        "desc_pt": "Explique com clareza um bug: sintomas, como reproduzir, impacto, o que já investigou.",
        "spec": ("The learner found a bug and must report it clearly to their tech lead (or a QA/PM) on a quick call. "
                 "Invent a concrete, realistic bug in a fictional product built with the learner's stack: exact "
                 "symptoms, error message or wrong behaviour, steps to reproduce, since when (e.g. after a deploy), "
                 "who/how many users are affected, what the learner already checked, their hypothesis, and what "
                 "they need (decision, help, priority). The partner knows the system but not this bug."),
    },
    "blocker": {
        "title_pt": "Bloqueio na daily", "icon": "🚧",
        "desc_pt": "Você está travado por algo externo. Explique o bloqueio e peça ajuda ou escalonamento.",
        "spec": ("During the daily standup the learner is blocked (e.g. waiting for another team's API, missing "
                 "access/credentials, a broken staging environment, an unanswered question). Invent the details: "
                 "what task, what exactly blocks it, since when, what they tried, impact on the sprint, and a "
                 "concrete ask. The partner (scrum master or engineering manager) wants to unblock them quickly."),
    },
    "delay": {
        "title_pt": "Atraso / renegociar prazo", "icon": "⏰",
        "desc_pt": "Sua tarefa vai atrasar. Explique o porquê, dê nova estimativa e proponha opções.",
        "spec": ("The learner's task will not be ready by the promised date. Invent the reason (unexpected "
                 "complexity, legacy code, dependency), the original and realistic new estimates, and 2 options "
                 "(e.g. ship a reduced scope first). The partner is a product manager who cares about a customer "
                 "commitment and will ask about impact, confidence and alternatives."),
    },
    "incident": {
        "title_pt": "Incidente em produção", "icon": "🔥",
        "desc_pt": "Algo caiu em produção. Atualize o time: o que acontece, impacto, mitigação e próximos passos.",
        "spec": ("There is a production incident and the learner is the engineer investigating it. Invent the "
                 "timeline, symptoms (error rates, latency, failing endpoint), customer impact, what was already "
                 "done (rollback? restart?), current hypothesis and next steps. The partner is the engineering "
                 "manager / incident commander who needs a clear status update and an ETA for the next update."),
    },
    "review": {
        "title_pt": "Discordar em code review", "icon": "🔍",
        "desc_pt": "Um sênior pediu uma mudança no seu PR com a qual você não concorda. Argumente com educação.",
        "spec": ("A senior engineer requested changes on the learner's pull request and the learner disagrees. "
                 "Invent the PR (what it does), the reviewer's requested change, and the learner's technical "
                 "reasons (performance, readability, deadline, consistency). The partner is that senior reviewer: "
                 "reasonable but opinionated; they can be convinced by good arguments or reach a compromise."),
    },
    "clarify": {
        "title_pt": "Esclarecer requisito", "icon": "❓",
        "desc_pt": "O PM trouxe uma demanda ambígua. Faça perguntas, levante casos de borda e confirme o entendimento.",
        "spec": ("A product manager brings a new, ambiguous feature request. Invent the request and list (only in "
                 "the learner's briefing) the ambiguities and edge cases the learner should ask about. The partner "
                 "is the PM: only gives details when asked specific questions, and expects the learner to summarise "
                 "the agreed scope at the end."),
    },
    "explain": {
        "title_pt": "Explicar para não-técnico", "icon": "🗣️",
        "desc_pt": "Explique uma decisão técnica ou feature para alguém de negócio, sem jargão.",
        "spec": ("The learner must explain a technical decision or trade-off (e.g. why a migration is needed, why "
                 "a feature takes longer, a security fix) to a non-technical stakeholder (sales, customer success, "
                 "a director). Invent the decision and its business impact. The partner gets lost with jargon and "
                 "asks 'what does that mean for our customers?'."),
    },
}

INTERVIEW_STAGES = {
    "recruiter": "Recruiter screening: motivation, background summary, fit with the role, remote work, availability, salary expectations.",
    "technical": "Technical interview (conversational, no live coding): deep-dive into the learner's experience against the job's technical requirements, trade-offs, system design at a mid-level depth, debugging stories.",
    "behavioral": "Hiring-manager / behavioral interview: STAR questions mapped to the job's responsibilities and company values, ownership, teamwork, communication in distributed teams.",
}

LEVELS = {
    "friendly": "Speak clearly and naturally, at a moderate pace, avoiding heavy slang and rare idioms.",
    "realistic": "Speak like a native in a real call: natural speed, contractions, common idioms and phrasal verbs.",
}

LEARNER = ("a Brazilian mid-level software developer with intermediate English, preparing for international jobs. "
           "Their main difficulty is speaking fluently under pressure. Their goal is to communicate clearly and be "
           "easily understood, NOT to sound like a native speaker")


def chat_system_prompt(scn: dict, level: str, watch_items: list[dict], phrases: list[dict] | None = None) -> str:
    watch = ""
    if phrases:
        plist = "\n".join(f'- "{p["text"]}"' for p in phrases)
        watch += ("\nPhrases the learner is practising. Where it fits naturally, create situations or ask questions "
                  "where they could use them, but don't say them yourself first and never mention this list:\n"
                  f"{plist}\n")
    if watch_items:
        lines = "\n".join(f'- they often say "{m["said"]}" -> natural: "{m["better"]}"' for m in watch_items)
        watch += (
            "\nThe learner's recurring mistakes (from previous sessions). When one appears, recast it "
            "naturally in your reply. Where it fits naturally, steer the conversation so they need these "
            f"structures:\n{lines}\n"
        )
    return f"""{scn['brief']}

You are talking by VOICE with {LEARNER}.

How you must behave:
1. Stay fully in character as {scn['persona']}, a real person on a video call. Never say you are an AI and never
   make meta comments about the learner or the role-play. If they get something wrong (e.g. your name), react
   naturally in character ("It's Emma, actually, no worries!").
2. Keep each turn SHORT: 1-3 sentences, and usually end with ONE question. The learner should talk ~70% of the time.
3. {LEVELS.get(level, LEVELS['friendly'])}
4. NEVER explicitly correct the learner and never give English lessons during the conversation.
   When they make a mistake, simply use the correct form naturally in your reply (a recast).
   Example: they say "It depends of the client" -> you say "Right, it really depends on the client. So..."
5. The learner's speech is transcribed automatically. Words marked like word(?) were hard to understand.
   If the meaning is genuinely unclear, react like a real person would: "Sorry, did you say...?" or
   "I didn't quite catch that, could you say it again?". If the meaning is clear from context, just continue.
6. If they are vague, ask for specifics like a real colleague/interviewer would. If they get stuck, encourage
   them naturally ("Take your time") instead of answering for them. Never reveal facts the learner should tell you.
7. Plain spoken text only: no markdown, no emojis, no lists, no stage directions, no translations.
8. If the learner says they want to wrap up, close the conversation politely in one or two sentences.
9. If they ask you to repeat or slow down ("Sorry, could you say that again?"), do it naturally, like a real
   person: repeat a bit slower and, if they still struggle, rephrase with simpler words.
{watch}
The first user message will be [START]. Respond with your natural opening line."""


# ---------- scenario generation ----------

GEN_SYSTEM = f"""You design realistic spoken role-play scenarios to help {LEARNER}.
Scenarios must feel like real situations at international tech companies. Briefings for the learner are in
Brazilian Portuguese (so the learner has to produce the English themselves); everything for the role-play
partner is in English. Output only JSON."""

SCENARIO_SPEC = """{
  "title": "short English title",
  "title_pt": "título curto em português",
  "desc_pt": "1 frase descrevendo o cenário",
  "persona": {"name": "first name", "role": "job title + team/company", "voice": "one of VOICES", "style": "personality in a few words"},
  "briefing_pt": {
    "contexto": "o produto/empresa/time e o seu papel (2-4 frases)",
    "situacao": "o que está acontecendo agora e com quem você vai falar",
    "objetivo": "o que VOCÊ precisa comunicar/conseguir nesta conversa",
    "fatos": ["fatos concretos que você sabe e deve usar: números, nomes de serviços, horários, mensagens de erro..."]
  },
  "expectations_pt": ["o que o interlocutor espera ouvir de você"],
  "watch_out_pt": ["perguntas difíceis ou armadilhas prováveis"],
  "success_criteria": ["observable criteria in English used to evaluate the learner afterwards (4-6)"],
  "vocabulary": [{"en": "useful phrase for this situation", "pt": "tradução"}],
  "retell_question": "the single most important question of this scenario, for a retell drill",
  "persona_brief_en": "Hidden instructions for the role-play partner, second person ('You are ...'): who they are, what they know and DON'T know, their goals and concerns, the questions to ask (one at a time, adapting), how to react to vague answers, and when the conversation naturally ends."
}"""


def _voices_line() -> str:
    return ", ".join(f"{k} ({v})" for k, v in VOICES.items())


def situation_prompt(kind: str, profile: str, pressure: str) -> str:
    s = SITUATIONS[kind]
    mood = ("The partner is calm and supportive." if pressure == "calm" else
            "The partner is under pressure (deadline/customers): impatient, asks direct follow-ups quickly, "
            "but stays professional.")
    return f"""Create a work-situation role-play.

Situation type: {s['title_pt']}
{s['spec']}
{mood}

Learner profile (use their stack and seniority so the context feels familiar; invent a FICTIONAL company/product):
{profile or '(no profile: assume a mid-level full-stack developer working with TypeScript, Node.js, React and PostgreSQL)'}

The briefing must give the learner ALL the facts they need to explain (concrete and specific), so the challenge is
communicating clearly in English, not inventing content. The partner must not know those facts in advance.

VOICES: {_voices_line()}

Return ONE JSON object with exactly this shape:
{SCENARIO_SPEC}
Use 6-10 facts, 6-8 vocabulary items."""


def job_scenario_prompt(job: dict | str, profile: str, stage: str) -> str:
    job_txt = job if isinstance(job, str) else json.dumps(job, ensure_ascii=False, indent=1)
    return f"""Create a job-interview role-play based on a REAL job posting.

Job posting (structured or raw text; if it is only a URL, open it with WebFetch first):
{job_txt}

Interview stage: {INTERVIEW_STAGES[stage]}

Candidate profile (the interviewer has read this CV):
{profile or '(no profile provided: the interviewer only knows they are a mid-level developer from Brazil)'}

Requirements:
- The interviewer works at the hiring company (real company name and real role from the posting), but the
  interviewer person is fictional.
- The interviewer has EXPECTATIONS about the candidate: they want evidence for each key requirement, and will
  probe the gaps between the CV and the posting.
- briefing_pt.contexto: about the company and role; situacao: which stage and who interviews; objetivo: what the
  candidate must demonstrate; fatos: key requirements + which of the candidate's experiences match them.
- expectations_pt: what this interviewer wants to hear. watch_out_pt: likely gaps/hard questions based on the CV.
- success_criteria: evidence the candidate should show (mapped to the job requirements) + clear communication.
- persona_brief_en: realistic flow for this stage (8-12 questions, one at a time, with follow-ups), the
  requirements to probe, the gaps to investigate, and how a real interviewer at this company would react.

VOICES: {_voices_line()}

Return ONE JSON object with exactly this shape:
{SCENARIO_SPEC}
Use 6-10 facts, 6-8 vocabulary items."""


JOB_SEARCH_SYSTEM = """You are a job research assistant. Use WebSearch (and WebFetch when useful) to find REAL,
currently open job postings. Never invent postings, companies or URLs. Output only JSON."""


def job_search_prompt(query: str, profile: str) -> str:
    return f"""Find up to 5 real, currently open job postings matching: "{query}".
Prefer remote roles at international companies that accept candidates based in Brazil / Latin America, with
interviews in English. Candidate profile, for relevance:
{profile or '(not provided)'}

Return ONE JSON object:
{{"jobs": [{{"company": "...", "title": "...", "url": "...", "location": "remote / region",
  "seniority": "...", "summary_pt": "2 frases sobre a vaga e a empresa",
  "must_have": ["..."], "nice_to_have": ["..."], "responsibilities": ["..."]}}]}}"""


# ---------- feedback ----------

FEEDBACK_SYSTEM = """You are an expert ESL speaking coach for Brazilian software developers preparing for
international jobs. You analyse a transcript of a spoken practice conversation and produce feedback in
Brazilian Portuguese (explanations) with English examples.

Core policy: the goal is INTELLIGIBILITY and clear, natural-enough professional communication, NOT a native
accent. Prioritise what would make an international interviewer or teammate misunderstand, get confused, or
lose confidence. Ignore accent features that don't block understanding. Don't nitpick: choose few,
high-impact points. Be encouraging but honest. Output only JSON."""


def feedback_prompt(scn: dict, transcript: str, stats: str, notebook: list[dict],
                    phrases: list[dict] | None = None) -> str:
    practising = "\n".join(f'- "{p["text"]}"' for p in phrases or []) or "(none)"
    known = "\n".join(f'- key "{m["key"]}": "{m["said"]}" -> "{m["better"]}"' for m in notebook) or "(none yet)"
    goals_ctx, goals_field = "", ""
    if scn.get("criteria"):
        crit = "\n".join(f"- {c}" for c in scn["criteria"])
        goals_ctx = f"\nScenario context for the learner:\n{scn.get('context_en', '')}\nSuccess criteria:\n{crit}\n"
        goals_field = ('  "goals": [{"criterion": "...", "status": "met|partial|missed", "comment_pt": "..."}],\n')
        if scn.get("kind") == "job":
            goals_field += ('  "interviewer_view_pt": "como um entrevistador real desta empresa provavelmente avaliaria '
                            'esta conversa e se avançaria para a próxima etapa, e por quê",\n')
    return f"""Scenario: {scn['title']}
{goals_ctx}
Transcript (LEARNER lines are automatic speech transcription; word(?) = low recognition confidence,
which can indicate unclear pronunciation, or just a recognition glitch):
{transcript}

Automatic speaking stats:
{stats}

Known recurring mistakes in the learner's notebook (reuse the same key if the same mistake happens again):
{known}

Phrases the learner is practising (report the ones they used correctly and naturally):
{practising}

Return ONE JSON object with exactly these fields:
{{
  "summary_pt": "2-3 frases: como foi a comunicação no geral",
  "scores": {{"clarity": 1-5, "fluency": 1-5, "grammar": 1-5, "vocabulary": 1-5}},
{goals_field}  "strengths_pt": ["até 3 pontos fortes concretos"],
  "mistakes": [
    {{"key": "short-stable-kebab-id", "category": "grammar|vocabulary|false-friend|clarity|structure|pronunciation|naturalness",
      "impact": "high|medium|low", "said": "what the learner said (short excerpt)",
      "better": "natural version", "why_pt": "explicação curta"}}
  ],
  "expressions": [{{"expression": "useful phrase for this situation", "meaning_pt": "...", "example": "example sentence"}}],
  "pronunciation": [{{"word": "...", "tip_pt": "dica curta, só se atrapalhar o entendimento"}}],
  "fluency_tips_pt": ["1-2 dicas práticas sobre fluência, hesitações, como ganhar tempo ou reformular"],
  "improved_keys": ["keys from the notebook the learner used CORRECTLY this session"],
  "phrases_used": ["practising phrases (exact text from the list) the learner used correctly"],
  "retell": {{"question": "one question from this conversation the learner should answer again, better", "why_pt": "..."}}
}}
Rules: max 5 mistakes ordered by impact on understanding; 3 expressions; pronunciation max 3 and only when it
likely hurt understanding (can be empty); ignore transcription glitches that are obviously not the learner's fault."""


HELPER_SYSTEM = """You help a Brazilian developer say things in natural, clear spoken English during a job
interview or work conversation. Be very concise. Answer in this format, plain text, no markdown:
Option 1 (simple): ...
Option 2 (more natural): ...
Dica: uma dica curta escrita em português do Brasil (opcional)."""


RETELL_SYSTEM = """You are a speaking coach for a Brazilian developer (intermediate English). They answered a
question out loud (4/3/2 retell technique: they will answer again with less time). Give feedback in Brazilian
Portuguese focused on clarity and communication, not accent. Output only JSON."""


def retell_prompt(question: str, answer: str, stats: str) -> str:
    return f"""Question: {question}
Learner's spoken answer (automatic transcription): {answer}
Stats: {stats}

Return ONE JSON object:
{{
  "fixes": [{{"said": "...", "better": "...", "why_pt": "..."}}],
  "structure_pt": "uma dica curta para organizar melhor a resposta (ex: começar pela conclusão, STAR)",
  "phrases": ["2-3 natural English phrases they could reuse in the next round"],
  "encouragement_pt": "uma frase curta"
}}
Max 3 fixes, highest impact on clarity first."""


# ---------- JSON schemas (validated by the CLI's --json-schema) ----------

def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or list(props)}


_S = {"type": "string"}
_SA = {"type": "array", "items": _S}

SCENARIO_SCHEMA = _obj({
    "title": _S, "title_pt": _S, "desc_pt": _S,
    "persona": _obj({"name": _S, "role": _S, "voice": {"type": "string", "enum": list(VOICES)}, "style": _S}),
    "briefing_pt": _obj({"contexto": _S, "situacao": _S, "objetivo": _S, "fatos": _SA}),
    "expectations_pt": _SA, "watch_out_pt": _SA, "success_criteria": _SA,
    "vocabulary": {"type": "array", "items": _obj({"en": _S, "pt": _S})},
    "retell_question": _S, "persona_brief_en": _S,
})

JOBS_SCHEMA = _obj({"jobs": {"type": "array", "items": _obj({
    "company": _S, "title": _S, "url": _S, "location": _S, "seniority": _S, "summary_pt": _S,
    "must_have": _SA, "nice_to_have": _SA, "responsibilities": _SA})}})


def feedback_schema(scn: dict) -> dict:
    score = {"type": "integer", "minimum": 1, "maximum": 5}
    props = {
        "summary_pt": _S,
        "scores": _obj({"clarity": score, "fluency": score, "grammar": score, "vocabulary": score}),
        "strengths_pt": _SA,
        "mistakes": {"type": "array", "items": _obj({
            "key": _S, "category": _S, "impact": {"type": "string", "enum": ["high", "medium", "low"]},
            "said": _S, "better": _S, "why_pt": _S})},
        "expressions": {"type": "array", "items": _obj({"expression": _S, "meaning_pt": _S, "example": _S})},
        "pronunciation": {"type": "array", "items": _obj({"word": _S, "tip_pt": _S})},
        "fluency_tips_pt": _SA, "improved_keys": _SA, "phrases_used": _SA,
        "retell": _obj({"question": _S, "why_pt": _S}),
    }
    if scn.get("criteria"):
        props["goals"] = {"type": "array", "items": _obj({
            "criterion": _S, "status": {"type": "string", "enum": ["met", "partial", "missed"]}, "comment_pt": _S})}
        if scn.get("kind") == "job":
            props["interviewer_view_pt"] = _S
    return _obj(props)



# ---------- phrase bank ----------

PHRASE_SYSTEM = """You help a Brazilian developer (intermediate English) learn useful spoken English phrases for
international tech jobs. Explanations in Brazilian Portuguese, examples in natural English. Output only JSON."""


def phrase_enrich_prompt(text: str, context: str) -> str:
    return f"""The learner saved this word/phrase to practise: "{text}"
Context where they saw it (may be empty): {context or '(none)'}

It may be written oddly (e.g. as a kebab-case id like "catch-up-on-work"). Return the clean, natural form.
JSON fields: "text" (clean phrase as people say it, e.g. "catch up on work"), "meaning_pt" (significado curto),
"example" (one natural example sentence in a work/interview context), "note_pt" (uso: registro formal/informal,
quando usar, armadilhas para brasileiros; 1-2 frases)."""


PHRASE_SCHEMA = _obj({"text": _S, "meaning_pt": _S, "example": _S, "note_pt": _S})


def phrase_use_prompt(phrase: dict, sentence: str) -> str:
    return f"""Target phrase: "{phrase['text']}" (meaning: {phrase.get('meaning_pt')})
The learner said this sentence out loud trying to use it (automatic transcription): "{sentence}"

Judge only: did they use the target phrase (or a natural inflection of it) correctly, with the right meaning,
in an understandable sentence? Ignore small grammar slips unrelated to the phrase, but mention one if it
hurts clarity. JSON fields: "used_correctly" (bool), "better" (a natural version of THEIR sentence),
"feedback_pt" (1-2 frases, encorajador e direto)."""


PHRASE_USE_SCHEMA = _obj({"used_correctly": {"type": "boolean"}, "better": _S, "feedback_pt": _S})



# ---------- vocabulary packs ----------

PACKS = {
    "daily": {"icon": "📅", "title_pt": "Daily e status",
              "spec": "giving status updates in standups: progress, plans, being on track or behind, blockers, asking for help"},
    "bugs": {"icon": "🐞", "title_pt": "Bugs e incidentes",
             "spec": "reporting and discussing bugs and production incidents: reproducing, impact, root cause, workaround, rollback, hotfix, postmortem"},
    "review": {"icon": "🔍", "title_pt": "Code review e discordar com educação",
               "spec": "code review comments and polite disagreement: suggesting changes, pushing back, finding compromise, nitpicks"},
    "interview": {"icon": "🎯", "title_pt": "Entrevista: você e seus projetos",
                  "spec": "job interviews: introducing yourself, describing projects, your role, impact, trade-offs, what you learned, motivation"},
    "phrasal": {"icon": "🔗", "title_pt": "Phrasal verbs de trabalho",
                "spec": "the most common phrasal verbs in software teams (follow up, figure out, ramp up, roll out, catch up on, set up, ...)"},
    "false_friends": {"icon": "⚠️", "title_pt": "Falsos cognatos para brasileiros",
                      "spec": "false friends that confuse Brazilian Portuguese speakers at work (actually, pretend, eventually, push, realize, ...): each item is the CORRECT English word/phrase for what the Brazilian means"},
    "fillers": {"icon": "⏳", "title_pt": "Ganhar tempo e reformular",
                "spec": "phrases to buy time, think out loud, rephrase, ask for clarification and recover when stuck, in calls and interviews"},
    "meetings": {"icon": "💬", "title_pt": "Reuniões e calls",
                 "spec": "participating in meetings: interrupting politely, agreeing/disagreeing, summarising, action items, scheduling, async follow-ups"},
}

PACK_SCHEMA = _obj({"items": {"type": "array", "items": _obj({"text": _S, "meaning_pt": _S, "example": _S, "note_pt": _S})}})


def pack_prompt(theme: str, profile: str, known: list[str], mistakes: list[dict]) -> str:
    known_txt = ", ".join(f'"{k}"' for k in known[:200]) or "(none)"
    mist = "\n".join(f'- "{m["said"]}" -> "{m["better"]}"' for m in mistakes[:10]) or "(none)"
    return f"""Create a vocabulary pack of 10 useful spoken English words/phrases about: {theme}

Learner profile (adapt examples to their stack and work):
{profile or '(mid-level developer)'}

Their recurring mistakes (prefer items that help with these, when relevant):
{mist}

Do NOT include any of these, which they already know/save: {known_txt}

Choose high-frequency, natural phrases that real colleagues at international tech companies use; mix easy and
slightly challenging items; avoid rare idioms. For each item: "text" (the phrase as people say it),
"meaning_pt" (significado curto), "example" (natural sentence in THEIR work context), "note_pt" (quando usar /
armadilha para brasileiros, 1 frase)."""
