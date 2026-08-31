# 007. No Postgres, no pgvector, no blocking — yet

**Status:** 🟢 decided for now
**Date:** 30 Aug 2026

## Context

The architecture calls for Postgres with pgvector, an HNSW index, and a blocking
stage that narrows candidate pairs before scoring. All of that is correct — at a
million records.

We have 100.

```
100 records  ->  4,950 pairs   ->  instant in pandas
1M records   ->  500 billion pairs  ->  ~6 days, and blocking becomes mandatory
```

Building blocking at 100 records means building, testing and debugging a stage
that eliminates 4,950 comparisons that take milliseconds anyway.

## Decision

Skip all of it for now. Files on disk, all-pairs comparison, plain numpy.

| Called for by architecture | Built now | Why not |
|---|---|---|
| Postgres | ❌ CSV and JSON files | Nothing needs transactions or concurrency yet |
| pgvector + HNSW | ❌ a numpy array | 100 vectors — exact search is instant |
| Blocking | ❌ all-pairs | 4,950 comparisons is not a scaling problem |
| FAISS | ❌ | Same reason, one level further out |
| Docker | ❌ | One machine, one Python environment |

Every one of these stays in the architecture document as designed. They are
deferred, not abandoned, and `docs/03-reference/pipeline-stages.md` documents
stage 04 (blocking) fully even though it is not implemented.

## What we rejected

**Build the full stack now, so it scales later.** The standard instinct, and
wrong for a two-day sprint. Every hour spent on infrastructure is an hour not
spent on extraction quality, which is the actual critical path. Infrastructure
also produces nothing a judge can see.

**Build blocking to demonstrate we understand scale.** Tempting, because the
reduction-ratio number is genuinely good on a slide. Rejected because the number
can be *computed and stated* without the stage existing — and stating it honestly
as a design property is better than implementing it against 100 records where it
does nothing.

## What it buys us

- The whole pipeline runs in under a minute, so iteration is fast.
- No environment setup for anyone joining — clone and run.
- Time goes to extraction, scoring and the demo, which is where it should.
- No dependency that can fail on demo day.

## What it costs us

- 🔴 **"Scales to millions" is argued, not demonstrated.** If a judge asks what
  happens at four lakh codes, we have arithmetic and an architecture, not a
  benchmark. That is an honest answer but a weaker one.

  The prepared response: *"Blocking is designed and documented but not
  implemented, because at 100 records it would eliminate 4,950 comparisons that
  take milliseconds. The reduction it gives at a million records is about
  99.996%. We built the part that is hard — extraction — and deferred the part
  that is well understood."*

- **The port to a database is real work later**, not a config change.
- **Someone may read "no database" as unfinished** rather than as a decision. This
  file exists so it can be shown as the latter.

## When to revisit

| Trigger | Do |
|---|---|
| Dataset above ~5,000 records | Add blocking. All-pairs starts to hurt. |
| Above ~50,000 records | Move vectors to pgvector or FAISS |
| Real CPSE pilot | Postgres, properly, with the audit tables |
| Anyone wants concurrent reviewers | Postgres — files cannot do this |

## Related

- [009](009-static-demo-no-backend.md) — the same reasoning applied to the UI
- `docs/03-reference/pipeline-stages.md` — stage 04, documented but not built
