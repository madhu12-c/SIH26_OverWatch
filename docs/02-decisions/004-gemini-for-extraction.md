# 004. Gemini API for spec extraction

**Status:** 🟡 decided, but this is our weakest position — revisit before the finale
**Date:** 30 Aug 2026

## Context

Spec extraction needs something that knows domain standards. The hard part is not
parsing — it is knowing that `6205` implies a 25mm bore, that `2RSR` and `2RS1`
both mean rubber sealed both sides, and that `A106 GR B` is a carbon steel
seamless pipe specification.

That knowledge is published and public, and large models have absorbed it. A
regex has not and cannot.

## Decision

Use the Gemini API (`gemini-2.5-pro` by default, configurable via `GEMINI_MODEL`)
for spec extraction, with:

- **A regex fallback** in `src/schemas.py` that runs when the API is unavailable,
  rate-limited, or returns something unusable. It currently recovers about 2.3
  fields per record and — critically — gets **both demo cases right**.
- **A cache** so a record is never extracted twice.
- **Rate pacing** at 14 requests/minute to stay inside the free tier.

## What we rejected

**A local open model** (Llama, Mistral, Qwen on Rashmit's GPU). Keeps everything
on-premise and matches our sovereignty argument exactly. Rejected for now on time:
getting reliable structured JSON with per-field confidence out of a small local
model is a tuning project, and we have two days. **This is the decision most
likely to be reversed.**

**Regex only.** Free, offline, deterministic, and already written. Rejected as the
primary path because it cannot derive dimensions from a designation — the exact
capability that makes the demo work. It stays as the fallback.

**Claude API.** Equivalent quality for this task. Gemini chosen because the free
tier covers our volume outright.

**Fine-tuning anything.** No labelled data, and no time. Ruled out by the same
constraint as a supervised matcher.

## What it buys us

- Extraction quality that a rule-based system cannot reach.
- Roughly 5–7 fields per record expected against 2.3 from regex, which directly
  improves match quality — and the difference is measurable, which makes it a
  defensible slide.
- Near-zero cost at our scale. Around ₹10 for the full 100-record dataset with
  development re-runs included.

## What it costs us

- 🔴 **It contradicts our own strongest argument.** We tell judges that CPSEs will
  not put procurement data on a foreign vendor's platform — and then send material
  descriptions to a foreign API. A sharp judge can put those two statements side
  by side.

  **The honest answer, and it must be said before being asked:** *"The prototype
  uses a hosted model. In deployment this is an on-premise model — the
  architecture does not change, only the endpoint. Descriptions never leave the
  CPSE in production."* Volunteering this is far stronger than being caught by it.

- **A network dependency at ingestion.** Mitigated by the cache and the fallback:
  once `specs.json` exists, nothing else needs the network, and the demo never
  makes a live call.
- **Non-determinism.** Temperature is 0, but model outputs are not guaranteed
  identical across runs or versions. Since results are cached and committed, the
  demo is stable — but a re-extraction could shift numbers slightly.
- **A model we do not control can change or be deprecated** under us.

## When to revisit

Three triggers, any one of them:

1. A judge challenges the sovereignty contradiction — then it becomes urgent.
2. Before any real CPSE pilot. No CPSE will approve sending its master to an
   external API.
3. If Rashmit has spare GPU time after the internal round, a local model becomes
   the highest-value experiment we can run.

## Related

- [002](002-llm-once-per-record.md) — how it is allowed to run
- [005](005-local-embeddings-no-api.md) — the same question, answered the other way
- `docs/04-risks/judge-questions.md` — the prepared answer
