# 009. The demo reads precomputed JSON — no backend, no live AI call

**Status:** 🟢 decided
**Date:** 30 Aug 2026

## Context

The demo has to survive a venue. Venue wifi fails, APIs rate-limit at the worst
moment, ports get taken, a laptop sleeps and loses a server process. A broken
demo erases everything the deck built, and there is no recovering from it in the
room.

The demo also has to work on a phone as a backup.

## Decision

The pipeline runs **in advance** on a laptop and writes one
`data/output/results.json` containing everything the interface needs — the two
demo cases with their scores, all clusters, the review queue, the blocked list
and the savings report.

The React app imports that file at build time. `npm run build` produces a folder
that opens by double-clicking `index.html`.

```
No server. No API. No fetch. No internet. Nothing to crash.
```

**No live LLM call appears anywhere in the demo path.** If one ever does, remove
it.

Vite needs `base: './'` or the build requests assets from the filesystem root and
renders a blank page — tested by opening `dist/index.html` directly, never only
`npm run dev`.

## What we rejected

**A live FastAPI backend with the React app calling it.** Closest to the real
product, and best if everything works. Rejected because it adds a process, a
port, a Python environment and a startup order to a five-minute slot — four new
ways to fail in front of judges, for a benefit nobody in the room can see.

**Streamlit.** Much less work than React and Aditya could build it in Python.
Rejected because the demo is meant to look like a product, it still needs a
running environment on the demo machine, and it is awkward on a phone. Worth
keeping as a fallback if the React build runs out of time.

**Live extraction on stage** — paste a description, watch specs appear. This is
the most impressive version and we deliberately are not doing it. It requires a
network round-trip to Gemini at the exact moment attention is highest. If asked,
the honest answer is that extraction is a batch ingestion step by design, not an
interactive one.

## What it buys us

- **The demo cannot fail.** No dependency exists that could take it down.
- Works on a laptop and a phone from the same build; the phone copy is genuinely
  offline once the file is saved.
- Aditya starts immediately against a stub `results.json`, without waiting for the
  scorer to exist.
- Rehearsal costs nothing and is identical every time.

## What it costs us

- **It is not live, and someone may notice.** A judge could ask whether it is
  computing anything or just replaying a recording.

  The prepared answer: *"The pipeline ran before we walked in — these are its real
  outputs, not a mock-up. We can run it again on any machine in a minute. We
  deliberately don't call an AI service live on stage, because extraction is a
  one-time ingestion step, not something that happens per query."*

  That is true, and it converts the weakness into a design point.

- **No interactive search.** A judge cannot type their own description and see it
  matched. This is the real loss, and it is the one thing a live version would buy.
- **`results.json` must be regenerated** whenever anything upstream changes, or
  the demo silently shows stale numbers.

## When to revisit

After the internal round. If the finale allows a longer slot and a reliable
connection, a live search box over precomputed embeddings — still no LLM call —
is a good middle path: interactive, but with nothing external to fail.

## Related

- [007](007-no-infrastructure-yet.md) — the same reasoning on the backend side
- `docs/06-team/aditya.md` — the design spec
- `docs/05-runbook/demo-day.md`
