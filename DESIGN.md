---
name: dev-english
description: Local voice practice for developers, staged as a scene from a subtitled series.
colors:
  subtitle-yellow: "#FFE14D"
  subtitle-yellow-hover: "#FFE96F"
  subtitle-ink: "#141205"
  subtitle-wash: "rgba(255, 225, 77, .12)"
  screening-black: "#0B0B0C"
  scene-surface: "#141519"
  scene-surface-raised: "#1C1E23"
  scene-surface-high: "#25282E"
  hairline: "#2A2D33"
  hairline-strong: "#3A3E46"
  screen-white: "#F5F5F5"
  muted-grey: "#A3A7B0"
  faint-grey: "#7D828C"
  recording-red: "#E5484D"
  recording-red-text: "#FF8A8D"
  success-green: "#3DD68C"
  warning-orange: "#FF9F43"
typography:
  display:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "4rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.03em"
    fontFeature: "\"tnum\""
  headline:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.074rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  subtitle-line:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 2.4vw, 2.125rem)"
    fontWeight: 600
    lineHeight: 1.32
  title:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.44rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title-sm:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.55
  label-caps:
    fontFamily: "Figtree, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.06em"
rounded:
  xs: "6px"
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "16px"
  pill: "99px"
  round: "50%"
spacing:
  2xs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  section: "40px"
components:
  button-primary:
    backgroundColor: "{colors.subtitle-yellow}"
    textColor: "{colors.subtitle-ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.subtitle-yellow-hover}"
    textColor: "{colors.subtitle-ink}"
  button-primary-lg:
    backgroundColor: "{colors.subtitle-yellow}"
    textColor: "{colors.subtitle-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "14px 22px"
  button-secondary:
    backgroundColor: "{colors.scene-surface-raised}"
    textColor: "{colors.screen-white}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.scene-surface-high}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted-grey}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  mic-button:
    backgroundColor: "{colors.subtitle-yellow}"
    textColor: "{colors.subtitle-ink}"
    rounded: "{rounded.round}"
    size: "76px"
  mic-button-recording:
    backgroundColor: "{colors.recording-red}"
    textColor: "{colors.screen-white}"
  input-text:
    backgroundColor: "{colors.scene-surface}"
    textColor: "{colors.screen-white}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  caption-toggle:
    backgroundColor: "{colors.scene-surface}"
    textColor: "{colors.muted-grey}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px"
  caption-toggle-active:
    backgroundColor: "{colors.subtitle-yellow}"
    textColor: "{colors.subtitle-ink}"
  pill:
    backgroundColor: "{colors.scene-surface-high}"
    textColor: "{colors.muted-grey}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  pill-accent:
    backgroundColor: "{colors.subtitle-wash}"
    textColor: "{colors.subtitle-yellow}"
  panel:
    backgroundColor: "{colors.scene-surface}"
    textColor: "{colors.screen-white}"
    rounded: "{rounded.xl}"
    padding: "20px 22px"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.muted-grey}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  nav-link-active:
    backgroundColor: "{colors.scene-surface-raised}"
    textColor: "{colors.screen-white}"
---

# Design System: dev-english

## Overview

**Creative North Star: "The Subtitled Episode"**

Practice is a scene from a subtitled series, the way Brazil learned English. Every screen sits in a screening room: a near-black ground, scene surfaces graded a few steps lighter, hairlines instead of shadows, and one colour that belongs to the subtitle. The partner speaks on a dark stage; their words arrive at the base of the frame as a yellow subtitle the learner can switch off, reveal on demand, or keep on. The yellow is also what you press: the primary action, the microphone, the selection highlight. Anything else that carries colour is reporting state (recording, success, warning), never decorating.

Density is calm and desk-shaped: a 1180px column, generous 40px section breaks, rows and panels rather than card mosaics. The conversation screen is the focus of the whole product and gets the largest type in the system: the live subtitle line. The voice is a coach, not a game: no mascots, no confetti palette, no streak theatrics.

The world explicitly rejects the category default for language apps: white rounded cards, a chat-bubble column, and a gamified mascot palette.

**Key Characteristics:**
- Screening-room dark only (`color-scheme: dark`); no light theme.
- One accent, subtitle yellow, for action, the mic, selection and the live subtitle.
- Red, green and orange appear only as state.
- One family, Figtree 400 to 800, on a 1.2 type scale.
- Lucide-style 1.75px line icons, inline SVG, `currentColor`.
- Depth by tonal grading and hairlines; shadow only on things that float.
- The stage: a radial-lit, vignetted frame with a lower-third and a subtitle line.

## Colors

A near-black screening room graded in cool greys, lit by a single subtitle yellow.

### Primary
- **Subtitle Yellow** (`subtitle-yellow`): the only accent. Primary buttons, the microphone at rest, the active caption mode, focus rings, text selection, links, list markers, leading row icons, and the live subtitle text itself. Its hover step is **Lit Subtitle** (`subtitle-yellow-hover`).
- **Subtitle Ink** (`subtitle-ink`): the warm near-black that sits on yellow (button labels, the brand mark glyph, selected text).
- **Subtitle Wash** (`subtitle-wash`): yellow at 12% for the focus halo on inputs and the accent pill background.

### Neutral
- **Screening Black** (`screening-black`): page ground and the translucent top bar (at 92% with an 8px blur).
- **Scene Surface** (`scene-surface`): panels, row lists, tables, inputs, the drawer, the caption toggle track.
- **Scene Surface Raised** (`scene-surface-raised`): secondary buttons, hovered rows and nav items, score tiles, retell rounds.
- **Scene Surface High** (`scene-surface-high`): button hover, neutral pills, avatars, leading icon wells, the toast.
- **Hairline** (`hairline`): every divider and container border at rest.
- **Hairline Strong** (`hairline-strong`): control borders (buttons, inputs, kbd, avatar ring), scrollbar thumb.
- **Screen White** (`screen-white`): body text and headings.
- **Muted Grey** (`muted-grey`): secondary copy, descriptions, inactive nav, labels.
- **Faint Grey** (`faint-grey`): metadata, placeholders, chevrons, table headers, hints. Lowest text tier; still about 4.7:1 on Scene Surface.

### State
- **Recording Red** (`recording-red`): the mic while recording (with a pulsing ring), the "offline" status dot, the strike-through on what the learner said. On text, use **Recording Red Text** (`recording-red-text`), the lighter readable tint for danger buttons, errors, wrong answers and the high-impact pill.
- **Success Green** (`success-green`): the corrected phrasing, ready status dot, phrase level dots, done states.
- **Warning Orange** (`warning-orange`): loading status dot, pressure and pause pills, the wavy underline under unclear words.

State pills use their colour at 12 to 14% alpha as background with the full colour as text.

### Named Rules
**The One Subtitle Rule.** Subtitle Yellow is the only accent, and it means either "this is the line" or "press this". If a yellow element is neither, it should be grey.

**The State-Only Rule.** Red, green and orange never decorate. They appear only when they report a state: recording, offline, correct, improved, unclear, under pressure.

## Typography

**Display Font:** Figtree (with ui-sans-serif, system-ui, sans-serif), self-hosted variable woff2, weights 400 to 800, latin and latin-ext subsets.
**Body Font:** Figtree, same file.

**Character:** One friendly, slightly geometric grotesque doing everything, from 800-weight headlines to the 600-weight subtitle. Hierarchy comes from weight and the 1.2 scale (0.75, 0.875, 1, 1.2, 1.44, 1.728, 2.074rem), not from a second family.

### Hierarchy
- **Display** (800, 4rem, tabular figures, -0.03em): the retell countdown timer only.
- **Headline** (800, 2.074rem, 1.2, -0.015em, balanced wrap): page and episode titles. Drops to 1.728rem under 720px.
- **Subtitle Line** (600, clamp(1.5rem, 2.4vw, 2.125rem), 1.32, max 32em, centred, balanced): the partner's current line on the stage, in Subtitle Yellow with a dark legibility shadow. The largest reading text in the product.
- **Title** (700, 1.44rem): section headings, and score values (at 800, tabular). **Title Small** (700, 1.2rem): panel headings, the wordmark, phrase text, the training reveal.
- **Body** (400, 1rem, 1.55): default copy; prose capped at 68 to 70ch. **Body Small** (0.875rem): descriptions, metrics, tables, buttons (at 600), nav (at 500).
- **Label** (600, 0.75rem): pills, caption toggle, hints, "you said" labels. **Label Caps** (700, 0.75rem, 0.06em, uppercase): definition terms in the briefing and table headers (0.05em) only.

### Named Rules
**The Subtitle Is Biggest Rule.** On the conversation screen nothing outsizes the subtitle line. Chrome stays at Body Small or below so the line reads first.

**The Tabular Numbers Rule.** Every number that changes or is compared (scores, timers, metrics, table numerics) uses tabular figures.

## Layout

A single centred column, max 1180px, padded 32px (16px under 720px), with 96px of bottom air. Pages open with a heading block (8px gap, 28px below); sections are separated by 40px with headings 14px above their content.

Two asymmetric splits carry the wider screens: content plus a 340px sticky sidebar (sticky at 88px, clearing the 64px top bar), and on home content plus a 320px "today" panel. Both collapse to one column under 900px, where the sidebar stops being sticky.

The conversation screen is a vertical stack (16px gap): title row, the stage (min 440px, 360px on mobile), then a three-column control row with the mic centred and secondary actions either side, collapsing to a centred single column under 720px. The briefing opens as a right drawer (min(440px, 100%)) rather than a new page.

Spacing steps observed: 4, 8, 12, 16, 24, 32, 40px, with 6, 10, 14, 20 and 22px used inside components for optical fit. Under 720px the top bar wraps and the nav becomes a horizontally scrolling, icon-only row.

## Elevation & Depth

Flat by default, depth by tonal grading: Screening Black, then Scene Surface, Raised, High, each a few lightness steps up, separated by 1px hairlines. Shadows are reserved for things that float above the page or need to read against the stage.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 8px 24px rgba(0, 0, 0, .35)`): the toast.
- **Drawer** (`box-shadow: -12px 0 32px rgba(0, 0, 0, .45)`): the briefing drawer's left edge.
- **Mic lift** (`box-shadow: 0 6px 16px rgba(0, 0, 0, .45)`): the resting microphone.
- **Recording pulse** (`0 0 0 0 → 0 0 0 16px rgba(229, 72, 77, 0)`, 1.4s infinite): the recording mic.
- **Stage vignette** (`box-shadow: inset 0 0 120px rgba(0, 0, 0, .55)`): inside every stage.
- **Subtitle legibility** (`text-shadow: 0 2px 4px rgba(0, 0, 0, .9), 0 0 18px rgba(0, 0, 0, .6)`): the subtitle line on the stage.

### Named Rules
**The Hairline-First Rule.** Containers are separated by a 1px hairline and a tonal step, never by a drop shadow. A shadow means "this floats" (toast, drawer, mic).

## Shapes

Gently rounded, never pillowy. Containers (panels, row lists, tables, stages) use 16px; large buttons 12px; buttons, inputs, icon wells and tiles 10px; nav items, icon buttons, packs and the brand mark 8px; kbd 5px; the focus ring 6px. Pills and the caption toggle are full capsules (99px). Avatars and the mic are circles. Borders are always 1px (kbd adds a 2px bottom edge for a keycap feel). Lists of rows share one bordered, clipped container with hairlines between rows instead of separate boxes.

## Components

### Buttons
Quiet and solid; one yellow per view.
- **Shape:** gently curved (10px), large variant 12px.
- **Primary:** Subtitle Yellow fill and border, Subtitle Ink label, 600 Body Small, 10px 16px (large: Body, 14px 22px). Hover lightens to Lit Subtitle.
- **Secondary:** Scene Surface Raised fill, Hairline Strong border, Screen White label; hover steps to Scene Surface High with a Faint Grey border.
- **Ghost:** transparent, Muted Grey label; hover gains a Raised fill and white text.
- **Danger:** secondary with a Recording Red Text label.
- **States:** 180ms `cubic-bezier(.16, 1, .3, 1)` transitions; press nudges down 1px; disabled at 45% opacity with not-allowed cursor; icon and label separated by 8px.
- **Icon button:** 32px square, 8px radius, transparent, Faint Grey glyph; hover goes white on Scene Surface High (the favourite star goes yellow).

### The Microphone (signature)
A 76px yellow circle with a 30px, 2px-stroke mic icon, centred under the stage with a hint line beneath. Hover scales to 1.04. Recording turns it Recording Red with white glyph and a 1.4s expanding red ring. Disabled drops to Scene Surface High with a Faint Grey glyph and no shadow. A 56px small variant serves the retell and training screens.

### The Stage (signature)
A 16px-radius frame with a hairline border and a radial key light (`radial-gradient(120% 90% at 25% 20%, #2D323A 0%, #181A1E 55%, #0F1012 100%)`) under an inset vignette. Top-left carries a **lower-third**: a 44px circular avatar with the persona's initial, name in 700 and role in Muted Grey. On home it frames the "next episode" with headline, copy and the yellow call to action; in the conversation it holds the caption toggle top-right and the subtitle line at its base, with "you said" below in white.

### Caption Toggle (signature)
A capsule segmented control on Scene Surface with a Hairline border and 3px inset; segments are Label type in Muted Grey, the pressed segment fills Subtitle Yellow with Subtitle Ink. Its three modes drive the subtitle: off, reveal (blurred 9px until clicked), always on. Hidden text elsewhere (transcript lines, vocabulary) blurs at 6px and reveals on click.

### Chips / Pills
- **Style:** capsule, Label type, 3px 10px, neutral on Scene Surface High with Muted Grey text.
- **Variants:** accent (Subtitle Wash and yellow), success, warning and recording, each its state colour at 12 to 14% behind the full-strength text.

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** Scene Surface; inner tiles (scores, rounds) on Scene Surface Raised at 10px.
- **Shadow Strategy:** none; see the Hairline-First Rule.
- **Border:** 1px Hairline; an emphasised panel (help answer, active round) borders in Subtitle Yellow.
- **Internal Padding:** 20px 22px; stacked panels sit 12px apart.

### Row Lists
One bordered 16px container, rows divided by hairlines, each row 16px 20px: a 40px icon well (Scene Surface High, yellow 20px icon), a 700 title with Muted Grey description, Faint Grey meta, and a chevron that turns yellow on hover while the row fills Raised.

### Inputs / Fields
- **Style:** Scene Surface fill, 1px Hairline Strong border, 10px radius, 10px 12px, Faint Grey placeholder.
- **Focus:** border turns Subtitle Yellow with a 3px Subtitle Wash halo; no outline.
- **Choice controls:** checkboxes, radios and ranges take Subtitle Yellow as accent colour.

### Navigation
A sticky 64px top bar on Screening Black at 92% with 8px backdrop blur and a hairline below. The wordmark pairs a 30px yellow rounded mark (8px radius) with "dev-english" in 800. Nav links are Body Small 500 in Muted Grey with a leading icon, 8px 12px, 8px radius; hover and active both go white on Scene Surface Raised. A status line sits far right with an 8px dot (orange loading, green ready, red offline). Under 720px the nav wraps to its own scrolling row and drops labels to icons.

### Drawer and Toast
The briefing drawer slides in from the right over 240ms on the house easing, Scene Surface with a hairline left edge and the Drawer shadow. The toast is a bottom-centred capsule on Scene Surface High with a Hairline Strong border and the Float shadow.

### Loading
Skeleton bars (12px tall, 6px radius) shimmer between Raised and High over 1.4s; empty states centre a 32px Faint Grey icon over Muted Grey copy.

## Do's and Don'ts

### Do:
- **Do** keep Subtitle Yellow (#FFE14D) to the line and the action: one yellow primary button per view, the mic, the active caption mode, focus and selection.
- **Do** separate surfaces with a 1px hairline (#2A2D33) and one tonal step rather than a shadow.
- **Do** put the partner's words on a stage as a centred yellow subtitle line, and respect the learner's caption mode (off, reveal-on-click with blur, always).
- **Do** use inline 1.75px-stroke line icons in `currentColor`, sized 1.15em.
- **Do** animate state changes at 180ms `cubic-bezier(.16, 1, .3, 1)` and honour `prefers-reduced-motion`.
- **Do** use tabular figures for every score, timer and metric.

### Don't:
- **Don't** introduce a light theme, white rounded cards, or a chat-bubble column for the conversation.
- **Don't** add a gamified mascot palette: red, green and orange (#E5484D, #3DD68C, #FF9F43) appear only as state, never as decoration or category colour.
- **Don't** add a second accent hue or a second type family.
- **Don't** put Recording Red (#E5484D) directly on text; use the readable tint (#FF8A8D).
- **Don't** let any chrome on the conversation screen outsize the subtitle line.
