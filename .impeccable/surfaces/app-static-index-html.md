---
version: 1
slug: "app-static-index-html"
primary_target: "app/static/index.html"
related_targets: ["app/static/app.js","app/static/style.css"]
---

# english-hub app shell (all screens in app/static)

Scope: the whole local web app: first-run setup (models, hardware, basic + advanced config, download progress), the guided onboarding (repeatable from settings), home, practice pickers, briefing, conversation, report, retell, phrases, training, history, notebook, profile, settings. Mode: Operate.

Audience/job: Brazilian mid-level dev practising spoken English alone at a desk, headphones on, often evening (hence a real light and dark theme plus System). Task: get set up without touching a terminal, prove mic and voice work, start talking within seconds, read a short prioritised report, drill phrases.

Constraints: plain HTML/CSS/JS, no build, offline-capable (self-hosted Figtree), UI in pt-BR, content in English. Preserve every existing function and API call. User: "bonita, nada genérico", but clean; rejected the Concreto direction and the generic canon; asked for Orelhão DDI blended with the category's clarity.

## Direction contract

THESIS: Practising is placing an international call from a Brazilian orelhão. A clean, standard app (white or graphite ground, familiar controls) where the DDI hood appears only where the call happens. Refuses the language-app default (cards everywhere, mascot green, confetti) and the old dark subtitle stage.

OWN-WORLD: Ground white #FFFFFF / soft #F4F6F9 (dark: #0F1217 / #171B22). Ink #141821, muted #596171, hairlines #E3E7ED. DDI blue #1757B8 is the committed colour: the hood, selection, links, partner. Orelhão orange #D9600C only for the one primary action per screen and recording. Figtree 400-800, tight display tracking, tabular numerals. Phone-card segmented strip as every progress indicator.

STORY: The learner opens the app, sees the hood fill with segments as models download beside detected GPU/CPU, tests mic and headphones, writes a short profile, then makes a first short call inside the same hood.

FIRST VIEWPORT: Setup: thin top bar (hood mark, wordmark, 4-step indicator). Left: headline, lead, the blue hood (120px top radius) with percent and 24-segment strip, then model rows. Right 480px column: detected hardware, quality segmented control, theme control, collapsed Avançado, orange Continue. Signature interaction: the hood, a blue shell with a big rounded top that frames the live moment (download, call stage, mic), and the segmented card strip that fills unit by unit.

FORM: Orelhão DDI, chosen as Impeccable's pick (position 1 on the ordered list), refined to the "Concha" variant on the user's steer. seed:385ce303ae478af9

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
