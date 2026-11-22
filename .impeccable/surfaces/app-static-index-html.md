---
version: 1
slug: "app-static-index-html"
primary_target: "app/static/index.html"
related_targets: ["app/static/app.js","app/static/style.css"]
---

# dev-english app shell (all screens in app/static)

Scope: the whole local web app (home, practice pickers, briefing, conversation, report, retell, phrases, training, history, notebook, profile). Mode: Operate.

Audience/job: Brazilian mid-level dev practising spoken English alone at a desk, headphones on, often evening. Task: start talking within seconds, survive a realistic conversation, read a short prioritised report, drill phrases.

Constraints: plain HTML/CSS/JS, no build, offline-capable (self-hosted Figtree), UI in pt-BR, content in English. Preserve every existing function and API call.

User priorities: home was too crowded; the conversation must be the focus; the old look was generic.

## Direction contract

THESIS: Practice is a scene from a subtitled series, the way Brazil learned English. The partner speaks; the subtitle is the learner's choice (off, on demand, always). Refuses the category default: white rounded cards, a chat-bubble column and a gamified mascot palette.

OWN-WORLD: Screening-room dark. Ground #0B0B0C, scene surfaces graded #141519/#1C1E23, hairlines #2A2D33, white #F5F5F5 text, muted #A3A7B0. Subtitle yellow #FFE14D is the single accent: primary actions, the mic, selection, the live subtitle. Recording red #E5484D, success green #3DD68C, warning orange #FF9F43 only as state. One family, Figtree, scale 1.2. Lucide-style 1.75px line icons. Soft-offset shadows, 12px radius.

STORY: The learner opens the app, sees the next episode, presses one yellow button, talks to a person on a dark stage whose words arrive as subtitles, then reads a short report and retells.

FIRST VIEWPORT: Top bar (wordmark, Praticar, Minhas frases, Histórico, Caderno de erros, Perfil). Home: one wide dark "next episode" stage with title, persona and a yellow "Falar agora"; below it three entry tiles (Vaga real, Situação de trabalho, Clássicos) and a due-phrases line. Conversation: full-width stage, persona lower-third top-left, CC control top-right, current line as a yellow subtitle at the stage base, mic centred below with briefing, "Como se diz?" and end beside it. Signature interaction: the caption control, with subtitles that reveal on click and blur when hidden.

FORM: Legendas (subtitled series). Position 1 on the ordered list. seed:7850607ce883399d

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
