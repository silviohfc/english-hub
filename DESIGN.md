---
name: english-hub
description: A clean desk app for spoken-English practice where a blue DDI phone hood frames only the moment of the call.
colors:
  ground: "#FFFFFF"
  soft: "#F4F6F9"
  surface-3: "#E9EDF2"
  line: "#E3E7ED"
  line-2: "#CDD3DC"
  ink: "#141821"
  muted: "#596171"
  faint: "#646C79"
  ddi-blue: "#1757B8"
  hood-deep: "#0F4597"
  hood-ink: "#10336E"
  on-hood: "#FFFFFF"
  on-hood-2: "#DCE6F5"
  orelhao-orange: "#B84F0A"
  orelhao-orange-hover: "#A04407"
  ok: "#137A4B"
  warn: "#A35E00"
  err: "#C42B2B"
  on-err: "#FFFFFF"
  dark-ground: "#0E1116"
  dark-surface: "#161A21"
  dark-surface-2: "#1C212A"
  dark-surface-3: "#252B36"
  dark-line: "#262C37"
  dark-line-2: "#343B48"
  dark-ink: "#E8EBF0"
  dark-muted: "#A2AAB8"
  dark-faint: "#8B93A1"
  dark-blue: "#2F6FD6"
  dark-blue-ink: "#7FAEFF"
  dark-hood: "#1A5BC0"
  dark-hood-deep: "#134AA3"
  dark-orange-hover: "#CC5A0E"
  dark-ok: "#3CC489"
  dark-warn: "#F0A43A"
  dark-err: "#FF7B7B"
  dark-on-err: "#1A0B0B"
  dark-seg-on: "#2C3340"
typography:
  display:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  meter:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3.2rem, 6vw, 4.5rem)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.045em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 750
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  spoken-line:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.4rem, 2.3vw, 2rem)"
    fontWeight: 650
    lineHeight: 1.34
  body:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
    lineHeight: 1.4
rounded:
  unit: "2px"
  control: "10px"
  tile: "12px"
  panel: "16px"
  hood-base: "20px"
  hood-top: "clamp(56px, 9vw, 132px)"
  pill: "99px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  section: "44px"
components:
  button-primary:
    backgroundColor: "{colors.orelhao-orange}"
    textColor: "#FFFFFF"
    typography: "{typography.body-sm}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.orelhao-orange-hover}"
  button-primary-lg:
    backgroundColor: "{colors.orelhao-orange}"
    textColor: "#FFFFFF"
    rounded: "{rounded.tile}"
    padding: "14px 22px"
  button-secondary:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.soft}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-on-hood:
    backgroundColor: "#FFFFFF"
    textColor: "{colors.hood-ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-danger-solid:
    backgroundColor: "{colors.err}"
    textColor: "{colors.on-err}"
    rounded: "{rounded.tile}"
    padding: "14px 22px"
  link-button:
    backgroundColor: "transparent"
    textColor: "{colors.ddi-blue}"
    typography: "{typography.body-sm}"
    padding: "0"
  input:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  segmented:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.muted}"
    rounded: "{rounded.tile}"
    padding: "3px"
  segmented-selected:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
  pill:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  hood:
    backgroundColor: "{colors.ddi-blue}"
    textColor: "{colors.on-hood}"
    rounded: "{rounded.hood-top}"
  strip-unit:
    backgroundColor: "{colors.line}"
    rounded: "{rounded.unit}"
    height: "12px"
  strip-unit-on:
    backgroundColor: "{colors.ddi-blue}"
  step-unit:
    backgroundColor: "{colors.line}"
    rounded: "{rounded.unit}"
    width: "28px"
    height: "8px"
  step-unit-done:
    backgroundColor: "{colors.ddi-blue}"
  step-unit-current:
    backgroundColor: "{colors.ink}"
  row-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "18px 8px"
  choice:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "14px"
    padding: "14px 16px"
  panel:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "22px 24px"
  mic:
    backgroundColor: "{colors.orelhao-orange}"
    textColor: "#FFFFFF"
    rounded: "50%"
    size: "80px"
---

# Design System: english-hub

## Overview

**Creative North Star: "Orelhão DDI"**

Practising is placing an international call from a Brazilian orelhão. Most of the app is a calm, standard desk tool: white ground (graphite at night), ink text, hairline rows, familiar controls. The world appears in one object only: the blue DDI hood, a fibreglass-like shell with a big rounded top that frames the live moment, whether that is the model download, the AI line test, the mic test, the voice preview, the first-call picker, the next call on home, the conversation itself, or the farewell after uninstalling. Everywhere else the interface steps back so the call can be the event.

Colour is committed but rationed. DDI blue carries identity, selection, links, the partner's voice and progress. Orelhão orange is the handset: the one primary action per screen, the mic, and recording. Green, amber and red speak only about state. Progress is always a phone card: a strip of discrete units that fill one by one, never a smooth bar. State reads by shape before colour, so a pending, running, done or failed job is legible in greyscale.

The system rejects the language-app default (cards everywhere, mascot green, confetti) and the previous dark "subtitle" stage. Density is medium; type is one family, Figtree, doing all the work with weight and tight tracking.

**Key Characteristics:**
- A clean light app with a real graphite dark theme and a System mode that follows the OS.
- One signature container, the hood, reserved for live moments.
- Blue is identity and selection; orange is the single act of calling.
- Every progress indicator is a segmented phone-card strip.
- Lists are hairline rows, not boxed cards.
- Figtree 400 to 800, display at 800 with tight negative tracking, tabular numerals for every count.

## Colors

A white-and-ink desk tool with one saturated blue object and a single orange handset.

### Primary
- **DDI Blue** (`ddi-blue`): the hood shell, the brand mark, active nav, selected choices and segments (via its 9% wash), links, focus rings, the partner's transcript lines, filled strip units and level meters. In dark mode the fill brightens to `dark-blue` and blue-as-text lifts to `dark-blue-ink` for contrast; the hood itself shifts only slightly to `dark-hood` so it stays the same object at night.
- **Hood Deep** (`hood-deep`): the shell's pressed or shadowed tone; the partner's portrait backing on the call stage.
- **Hood Ink** (`hood-ink`): text on white controls that sit inside the hood (selected segment, the white on-hood button). The translucent navy `rgba(6, 22, 60, .22 to .38)` is its glass form for nameplates, the call timer and unselected controls on the hood.

### Secondary
- **Orelhão Orange** (`orelhao-orange`): the one primary action per screen, the mic at rest, the recording ring and the live self-tile. Adapted from the contract's #D9600C to reach 4.5:1 with white text; the same value serves both themes, only its hover differs (`orelhao-orange-hover` light, `dark-orange-hover` dark). On the blue hood the primary is still orange: the orelhão pairing.

### Tertiary (state only)
- **Line Green** (`ok`): done jobs, passed checks, the "better" correction, phrases used.
- **Amber** (`warn`): warnings, pressure tags, a failed mic check.
- **Fault Red** (`err`): errors, the struck-through "said" form, high-impact fixes, offline status, and the fill of the one confirmed destructive act (remove). Text on that fill is `on-err`: white in light, near-black `dark-on-err` at night, because the dark red is too light to carry white.
Each has a soft wash (9 to 13% alpha) used as pill background; the amber wash also tints a risky row once it is checked.

### Neutral
- **Ground** (`ground`) and **Soft** (`soft`): the page and the tinted ground for hover, segmented tracks and quiet tiles. `surface-3` is the inactive pill and disabled mic fill.
- **Hairline** (`line`) and **Rule** (`line-2`): row dividers and pending strip units; control borders and pending job markers.
- **Ink** (`ink`), **Muted** (`muted`), **Faint** (`faint`): text at three strengths. Faint is held dark enough to stay legible as meta text and placeholders.
- **Graphite** (`dark-ground` through `dark-line-2`, `dark-ink`, `dark-muted`, `dark-faint`): the night booth. The same roles, the same hierarchy. The raised segment, white by day, becomes `dark-seg-on` at night so it still reads as lifted above the track.

### Named Rules
**The One Handset Rule.** Orange appears on at most one primary button per screen, plus the mic and recording. A second orange action means one of them is wrong.

**The State Colour Rule.** Green, amber and red never decorate. They appear only when something has finished, needs attention or failed. A solid red fill is reserved for the confirmed destructive act.

**The Night Booth Rule.** Dark mode is a separate graphite palette, not an inversion; light, dark and System (the OS preference, used when no explicit theme is stored) must all be maintained together.

## Typography

**Display Font:** Figtree (self-hosted variable woff2, 400 to 800, with ui-sans-serif, system-ui fallback)
**Body Font:** Figtree
**Label/Mono Font:** none for interface text; numerals switch to tabular figures instead. A system monospace stack (ui-monospace, SFMono-Regular, Menlo, Consolas) appears only inside `code` for literal data the learner must copy exactly, such as the project folder path, on a soft fill with a hairline and 6px radius.

**Character:** One friendly geometric-humanist sans carrying the whole hierarchy through weight. Heavy, tightly tracked headings feel like signage on the booth; regular body stays plain and readable.

### Hierarchy
- **Display** (800, 2.75rem; flow screens clamp 2.1 to 2.9rem; 2rem under 720px; tracking -0.03em): page titles, the next-call title in the home hood.
- **Meter** (800, clamp 3.2 to 4.5rem, line-height 1, tracking -0.045em, tabular): the download percentage in the setup hood; on the AI line test it states the result in a word or two ("2 s" with a small "por resposta" unit, "Chamando…", "Sem sinal"); on the farewell, "Até logo."; the retell timer uses the same voice at 4rem.
- **Headline** (750, 1.5rem, -0.02em): section headings.
- **Title** (700, 1.1875rem): sub-sections, settings section names, row titles at body size.
- **Spoken line** (650, clamp 1.4 to 2rem, line-height 1.34, balanced): the partner's line on the call stage and the read-aloud sentence in onboarding.
- **Body** (400, 1rem, 1.55): running text, capped at 66 to 70ch; leads run at 1.1875rem in muted.
- **Body small** (400 to 650, 0.9375rem): buttons, row descriptions, meta, tables.
- **Label** (700, 0.8125rem, sentence case, no tracking): field-group labels above a control ("Tema", "Seu computador"), table headers, score labels.

### Named Rules
**The Weight Not Family Rule.** Hierarchy comes from Figtree's weight and size only. No second typeface for interface text; monospace is a property of literal data, never a style.

**The Counting Rule.** Every number that counts or ticks (percent, timers, sizes in KB, MB and GB, stats, step numbers) is tabular.

## Layout

Content sits in a 1200px container (32px gutters, 16px under 720px). A sticky 64px top bar with a translucent blurred ground carries the hood mark, wordmark, nav and status; in flow mode (setup, onboarding and the farewell) nav and status give way to the step indicator: six 28px units (Configurar, Conectar a IA, Microfone e fone, Voz e legendas, Seu perfil, Primeira ligação), the count taken from the step list, followed by "N de 6" and the step name; the name shrinks to 13px under 980px and is hidden under 560px, where units narrow to 18px. Main screens use a two-column split: a fluid primary column with a fixed aside (360px for practice, 320px on home, 440px on setup and onboarding), collapsing to one column at 980px. Settings use a 240px header column beside the controls, stacking at 980px. Long selection pages (uninstall) end in a sticky bottom bar on a translucent blurred ground with a hairline top, carrying the running total on the left and the act on the right. Vertical rhythm: 32px under page heads, 44px between sections, 12 to 18px inside stacks. Under 720px the nav becomes a horizontally scrolling icon row, the call controls stack and the call nameplate moves above the self-tile.

## Elevation & Depth

Flat by default. Depth comes from the hood's saturated mass against the white ground, hairlines and tonal grounds, not from shadows. Shadows exist only where something physically lifts or floats.

### Shadow Vocabulary
- **Handset lift** (`0 1px 2px rgba(0,0,0,.12), 0 4px 12px` orange 10%): the primary button and mic; a warm halo, not a grey drop.
- **On-hood lift** (`0 2px 4px rgba(6,22,60,.3), 0 8px 20px rgba(6,22,60,.25)`): orange and white controls inside the hood, shadowed in navy.
- **Float** (`0 10px 32px rgba(20,24,33,.16)`; dark `0 12px 36px rgba(0,0,0,.5)`): the briefing drawer and the toast only.
- **Selected thumb** (`0 1px 3px rgba(20,24,33,.14)`): the raised segment in a segmented control.

### Named Rules
**The Lift Means Act Rule.** If it casts a shadow, you can press it or it is floating over the page. Containers never cast shadows.

## Shapes

Soft, consistent rounding with one dramatic exception. Controls are 10px, tiles and segmented tracks 12px, choice buttons and the facts list 14px, panels 16px, pills fully round. The hood breaks the scale: a huge top radius (clamp 56 to 132px) over a 20px base, with a 1px translucent inner rim inset 10px that fades downward like the moulded edge of the shell. The same silhouette, miniaturised (rounded top, small square-ish base), is the brand mark and the job and check markers. Strip units are nearly square-cornered (2px) so the strip reads as discrete card cells.

## Components

### Buttons
Familiar and confident; colour says what the button does.
- **Shape:** gently rounded (10px; 12px at large size).
- **Primary:** orelhão orange, white text, 650 weight, handset lift. Large size (14px 22px) for the screen's main act ("Ligar agora", "Continuar").
- **Secondary:** ground fill, 1px rule border, ink text; hover to soft fill with a darker border.
- **Ghost:** transparent, muted text; hover to soft.
- **On the hood:** default buttons become transparent with a translucent white border; the primary stays orange with navy lift; **on-hood** is white with hood-ink text, the secondary-on-hood for a non-calling act (voice preview).
- **Danger solid:** `err` fill and border with `on-err` text, large size, hover darkens by brightness (92%). Only for the final remove on uninstall, never beside an orange primary. The quiet danger variant is a secondary button with red text.
- **Link button:** an inline text action inside a row's sentence ("testar de novo"): blue-ink text, 1px underline at 40% blue offset 3px, full on hover. For repeat or minor acts that should not compete with the row's buttons.
- **Hover / Focus / Active:** 200ms ease-out colour shifts; 1px press-down on active; a 2px blue-ink focus outline offset 2px (white inside the hood). Disabled at 50% opacity.

### Segmented control
A soft track (3px padding, 12px radius) with 9px-radius segments; the selected segment is raised to ground with a small shadow. Inside the hood the track turns navy glass and the selected segment turns solid white with hood-ink text. Used for quality presets, theme (Claro / Escuro / Sistema) and partner level.

### Choice list
Stacked option buttons (14px radius, rule border) with a bold title and muted description, optionally led by a 22px blue-ink line icon. Selected: blue-ink border plus a 3px blue wash ring. Inside the hood: navy glass at rest, solid white with ink text and lift when selected; the icon takes the text colour. The same list carries any either-or setting that changes what the app is for, such as the track (work as a developer or day to day), in both onboarding and settings.

### Chips (pills)
Fully round, 13px label weight on a surface-3 fill. Variants by meaning only: blue wash for subject or category, green for used or passed, amber for warning, red for recording or high impact. On the hood they become 14% white.

### Inputs / Fields
Ground fill, 1px rule border, 10px radius, 10px 12px padding. Focus: border shifts to blue-ink with a 3px blue-wash ring, no outline. Field labels sit above in muted 600; help text below in faint 13px. Checkboxes and radios take the blue accent; range sliders use a 4px rule track with a blue thumb ringed in ground (white on the hood).

**Role picker.** One field per job the AI does (Conversa, Feedback e cenários, Ajudas): the role name in ink 650 above, then a provider select (140px) beside a model select, or a free text input when the provider has no fixed model list; the pair stacks under 720px. Model options carry human labels ("Sonnet · equilibrado"), never raw ids alone. Help text sits below in faint 13px. On flow screens the group sits in the aside under a title-size heading.

### Rows
The default list form. A hairline top and bottom around the group, hairlines between items, 18px 8px padding, no box. Leading blue line icon, bold title, muted description, faint meta, a chevron that turns blue and nudges 2px on hover. Empty states are the same hairline row with a blue icon and muted text.

**Checkbox rows.** For choosing what to act on, each hairline row is a whole-row label: a leading blue checkbox, title, description and a tabular size in meta. Rows are grouped under title-size headings with a muted line of context. A group that reaches outside the app carries an amber warning pill in its heading and an amber warn line (15px, up to 72ch) above its rows; its rows tint with the amber wash once checked.

### Panels
A ground container with a 1px hairline and 16px radius (22px 24px padding), no shadow. Used for grouped report content, the briefing, the home "today" aside and error or loading messages. A panel holding only an empty state collapses to the bare hairline row.

### Facts list
A 14px-radius bordered list of label and value pairs separated by hairlines (detected hardware on setup).

### Bottom action bar
A sticky bar at the foot of a long selection page: translucent blurred ground, hairline top, muted running total ("3 itens · 1,2 GB") on the left, the act on the right. Confirmation happens in the bar itself, never in a native dialog: the total is replaced by a bold question and the list of what goes, the hairline turns red, the actions become a ghost "Voltar" and the danger-solid confirm, and the rows lock. While the act runs, the actions give way to a busy 16-unit strip.

### Navigation
Top-bar links in muted 600 at 15px with line icons, 10px radius; hover to soft, active to blue-ink text on blue wash. Status is a pill-shaped link with a ring dot: amber ring loading, solid green ready, solid red offline.

### The Hood (signature)
Blue shell, `hood-top` radius over a 20px base, inner rim, on-hood text in white and `on-hood-2`. It frames only live moments: the setup download (status, meter percentage, 24-unit strip), the AI line test, the mic test, voice preview, the first-call picker, the next call on home, the conversation stage (portrait with a voice-level ring, nameplate, self-tile, subtitles and controls) and the farewell. Never a generic card.

**AI line test.** The status line names the lines in use ("Linha liberada · Claude"); the meter states the result (response time, "Chamando…" while testing, "Sem sinal" untested); a large three-unit strip holds one unit per role (Conversa, Feedback, Ajudas), lit only when that role's provider has passed a real test, all units waving while a test runs.

**Farewell.** After uninstalling: "Linha encerrada" as status, "Até logo." as meter, and a full 24-unit strip that drains one unit every 90ms as the app shuts down.

### Phone-card Strip (signature)
A grid of N equal units (default 24, 3px gap, 12px tall; 16px large, 6px small) with 2px corners. Pending units are hairline, filled units blue; a completed strip may turn green; inside the hood units are 20% white, filled solid white. While busy, units pulse in a 55ms-staggered wave. The same grammar drives the download, the live mic level meter, the phrase level pips, the three-unit AI line strip and the six-unit flow step indicator (done blue, current ink, pending hairline).

### Job and check markers
A 16px miniature hood (8px top radius, 3px base) whose shape carries state: rule outline for pending or not installed, a dashed blue-ink outline for waiting on the learner (sign in, then test), filling from the bottom in blue while running (fill follows progress), solid green done, red hatching on error. Dashed and filling must never be confused: one waits on a person, the other on the machine. Check rows use the same marker solid green for pass, solid amber for a problem.

**Provider rows** are job rows with the marker top-aligned: name with the CLI and version in muted 500, the plan, a state line (ink; green when done, red on error) that may end in a link button, a faint single-line log while installing, and a small busy strip. Actions sit on the right and drop under the text below 720px. Installing asks first inside the row itself: a muted question with confirm and cancel buttons replaces the actions.

### Mic
An 80px orange disc (56px small) with a white line mic icon and handset lift; hover scales 4%. Recording turns it to a ground disc with a 3px orange inset ring and an expanding orange pulse every 1.4s. Inside the hood it gains a 4px white collar. Disabled is surface-3 with faint icon.

### Call stage
Inside the hood: a 172px portrait (128px on mobile) with a white ring that scales and brightens with the real voice level, navy-glass nameplate with three level bars, and a self-tile that turns orange glass with live bars while the learner speaks. Subtitles can be blurred and revealed on click.

## Do's and Don'ts

### Do:
- **Do** reserve the hood for live moments (download, mic, voice, call picker, next call, the call itself).
- **Do** use exactly one orange primary per screen; keep it orange even inside the blue hood.
- **Do** show every progress, level or step count as a segmented strip of discrete units.
- **Do** encode state by shape first (outline, filling, solid, hatched), then colour.
- **Do** list things as hairline rows and show empty states as an inline hairline row.
- **Do** keep light, dark and System themes in step; apply the stored theme before first paint.
- **Do** use tabular numerals for every count, timer and percentage.
- **Do** honour reduced motion: the strip wave, recording pulse and transitions collapse to near zero.
- **Do** confirm destructive or installing acts inline, in the row or the bottom bar that holds them, with a way back; never a native dialog.
- **Do** set a strip's unit count from what it counts (six steps, three roles), not a fixed number.

### Don't:
- **Don't** use green, amber or red for anything but done, warning or error.
- **Don't** use orange for links, selection, decoration or a second action.
- **Don't** wrap list items in boxed cards or put shadows on containers.
- **Don't** draw progress as a continuous bar or spinner where a strip fits.
- **Don't** add a second typeface for interface text, uppercase tracked labels, or mascot and confetti celebration. Monospace is only for literal data inside `code`.
- **Don't** fill a button with red except the confirmed destructive act, and never put white text on the dark-theme red.
- **Don't** use the hood as a generic hero or decorative card on screens with no live moment.
