# 002. One LLM call per record, never per pair

**Status:** 🟢 decided — a design that violates this is not viable, flag it immediately
**Date:** 29 Aug 2026

## Context

[001](001-match-on-specs-not-text.md) puts an LLM in the pipeline. The question is
*where* it is allowed to run.

The tempting version is to hand two descriptions to a model and ask "are these
the same item?" It works — models are good at this — and it is what a first
prototype naturally becomes.

The arithmetic kills it.

```
                        calls          time           cost        frequency
per record (1M master)  1,000,000      ~3 hrs         ~Rs 17,000  once, cached
per candidate pair      20,000,000+    ~55 hrs        ~Rs 3.4 L   EVERY run
```

Per-pair is not "more expensive". It is a different category of system: it runs
every time thresholds are tuned, every time the dataset is reprocessed, every
time a demo is rehearsed.

## Decision

The LLM runs **once per record, at ingestion**, and the result is written to
`data/output/specs.json` and never recomputed.

Everything after extraction — similarity, scoring, clustering — is pure numeric
maths over that cached file. No model call appears anywhere in the pairwise path.

The cache is also a resume point: re-running the extractor skips records already
in the file, so an interrupted run costs nothing.

## What we rejected

**LLM as the pair judge.** Fatal at scale, as above. Also non-deterministic — the
same pair can score differently on two runs, which is unacceptable for a
government audit trail where the question is "why was this merged?"

**LLM to break ties in the review band only.** Superficially cheap, since only
uncertain pairs would reach it. Rejected because it puts a non-reproducible step
inside the decision path, and because the review band is exactly where a human is
supposed to decide. It would also grow silently — today ties, tomorrow all pairs.

**Batching several records per call** (10 descriptions, one call). Ten times
cheaper and faster. Rejected for now because per-field confidence gets less
reliable when a model handles ten unrelated items in one context, and because a
single malformed response loses ten records instead of one. Worth revisiting if
the dataset grows past a few thousand records.

## What it buys us

- The cost story becomes a slide, not a liability: roughly **₹17,000 of inference
  to process a million-record master, once**. Against ₹31 crore of identified
  savings, that number lands well.
- Scoring is deterministic and reproducible — the same inputs always produce the
  same merge, which is what makes the audit trail meaningful.
- Rehearsing the demo is free. Nothing re-bills.
- The pipeline runs with no network once extraction is done.

## What it costs us

- **Scoring cannot use language understanding.** Anything the extractor missed is
  gone by the time matching runs. A pair that a human would see as obviously the
  same, but whose specs did not extract, will not match.
- **Extraction quality is frozen at ingestion.** Improving the prompt means
  re-running extraction over everything, not just fixing the matcher.
- **The cache can go stale silently.** If `materials.csv` is regenerated but
  `specs.json` is not, the pipeline runs on specs for records that no longer
  exist. Use `--fresh` after any dataset change. This has already bitten us once.

## When to revisit

If per-record extraction ever becomes the bottleneck at scale, batching (rejected
above) is the first thing to reconsider — not per-pair calls, which stay ruled out
permanently.

## Related

- [004](004-gemini-for-extraction.md) — which model, and the privacy cost
- `src/extractor.py` — the cache and resume logic
