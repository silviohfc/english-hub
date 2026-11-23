# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, chosen as a "track" in the app:

- **Developer track (original):** a Brazilian mid-level software developer with intermediate English whose main
  difficulty is speaking fluently under pressure. The job: become confident and clearly understood so they can
  land and keep an international (usually remote) developer job.
- **Everyday track:** a Brazilian adult with intermediate English who wants to handle everyday life in English
  (travel, services, appointments, social conversations) without freezing.

Both practise alone at a desk (Windows or Mac; Chrome, Edge or Safari; microphone, headphones), in short,
frequent sessions whose length varies.

## Product Purpose

english-hub (formerly dev-english) is a local voice practice app. The learner talks out loud with AI role-play partners (recruiters,
interviewers for real job postings, tech leads, PMs, teammates) and gets feedback after each conversation.
Success means being understood easily and communicating clearly at work or in daily life, not sounding native.

## Positioning

- Conversations are realistic and contextual: interviews built from real, currently open job postings and the
  learner's own profile, and work situations (bug report, blocker, delay, incident, code review, ambiguous
  requirement, explaining to non-technical people) with a briefing of concrete facts the learner must convey.
- Teaching method grounded in SLA research: partners never interrupt to correct (natural recasts only);
  feedback keeps to the few highest-impact issues for intelligibility; 4/3/2 retell drill; a mistake notebook
  and a phrase bank with spaced repetition that feed back into the next conversations.
- Everyday track: daily-life classics (meeting someone, immigration, hotel, restaurant, doctor) and generated
  everyday situations (wrong order, returns, customer-service calls, directions, pharmacy, landlord, plans).
- Fully local and free: speech recognition (faster-whisper) and speech synthesis (Kokoro) on the user's GPU/CPU;
  the LLM runs through the user's own plan via its CLI: Claude Code, Antigravity CLI (Gemini) or Codex CLI
  (ChatGPT), chosen per role (conversation, feedback, helpers).

## Operating Context

The core moment is speaking: hold Space or click the microphone, talk, hear the partner reply. Around it:
choosing a practice (real job interview, work situation, classic scenario), reading a briefing, the end-of-session
report, the retell drill, phrase training, history and the mistake notebook, and the profile (mini CV) that
interviewers read. Generation steps (job search, scenario, feedback) take 10-90 seconds.

## Capabilities and Constraints

- Runs on localhost, served by a Python (FastAPI) backend; frontend is plain HTML/CSS/JS with no build step.
- UI copy is in Brazilian Portuguese; practice content is in English.
- Listening modes for the partner's text: audio only ("real"), reveal on click, always visible.
- No paid services, no accounts, no telemetry.

## Brand Commitments

- Feedback targets intelligibility and clear communication, never accent reduction or "sound native" framing.
- Encouraging, honest coaching voice; no gamification hype.

## Evidence on Hand

No testimonials, users or metrics exist. Do not fabricate any.

## Product Principles

1. Speaking first: every screen should get the learner talking with as little friction as possible.
2. Realism over drills: practice mirrors the real conversations of an international dev job.
3. Few, high-impact corrections beat exhaustive ones.
4. The learner's own data (profile, mistakes, phrases) personalises every session.
