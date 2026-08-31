# 001. Match in attribute space, not text space

**Status:** 🟢 decided — this is the project's core idea, do not let refactors erode it
**Date:** 29 Aug 2026

## Context

The obvious approach to "find duplicate material records" is to compare the
description strings — Levenshtein distance, TF-IDF, or embedding cosine
similarity — and merge anything above a threshold.

That approach fails in both directions, and both failures are visible in our own
dataset:

```
"SKF 6205-2RS Deep Groove Ball Bearing"
"FAG 6205-2RSR bearing, 25x52x15mm, sealed"
      almost no shared words  ->  a text matcher MISSES it
      reality: the same bearing. 6205 is an ISO designation, so any
      manufacturer's 6205 is 25mm bore, 52mm OD, 15mm wide.

"GASKET SPIRAL WOUND SS316 4IN 150#"
"GASKET SPIRAL WOUND SS304 4IN 150#"
      one character differs, ~0.97 similar  ->  a text matcher MERGES them
      reality: different items. SS316 contains molybdenum and resists
      corrosion; SS304 does not. In corrosive refinery service the wrong
      one leaks.
```

A threshold that catches the first will definitely merge the second. There is no
setting that gets both right, because the signal being measured is the wrong one.

## Decision

Extract typed specifications from each description first, then compare
specifications rather than text.

```
                   RECORD A            RECORD B
iso_designation:   6205           ✓    6205
bore_mm:           25             ✓    25
seal_type:         2RS            ✓    2RS
brand:             SKF            ⊗    FAG      <- deliberately ignored
```

Three rules make this work, and they matter more than any weighting:

- **Hard blockers.** Material grade, pressure rating and key dimensions are veto
  fields. A mismatch is an instant zero regardless of everything else.
- **Ignored fields.** Brand and vendor part number never count toward a match.
  This is exactly what lets SKF and FAG resolve to one item.
- **Missing is not mismatched.** One record silent on a field is absent
  information, not evidence of difference. No penalty.

## What we rejected

**Pure fuzzy string matching.** Fails both cases above. It is what most competing
teams will build, which is also why demonstrating its failure is our strongest
demo moment.

**Embeddings alone with a tuned threshold.** Better than string distance, but it
still measures textual similarity. It cannot know that molybdenum content makes
two nearly identical strings different items.

**A supervised classifier over pair features.** Would work, and is what the
literature does — but it needs labelled pairs. We have none, and producing enough
would take a domain expert weeks. Ruled out by [003](003-precision-over-recall.md)'s
context, not by preference.

**Asking an LLM "are these the same item?" per pair.** Handles both cases
correctly, and is fatal at scale. See [002](002-llm-once-per-record.md).

## What it buys us

- Both demo cases work, in opposite directions. That contrast is the pitch.
- Merges are explainable field by field — a reviewer sees *which* attributes
  agreed, which is required for the approval workflow the PS asks for.
- The safety story is real, not claimed: grade mismatches are structurally
  incapable of merging.
- It is genuinely differentiating in a hackathon field, even though it is
  standard practice in commercial MDM.

## What it costs us

- **Spec extraction becomes the critical path.** If extraction is unreliable,
  every downstream stage inherits the failure. This is the single biggest
  technical risk in the project.
- **Every category needs its own schema.** A pipe schema and a valve schema share
  almost nothing, so coverage is per-category work rather than one generic model.
- **Sparse descriptions extract badly.** `GASKET SW SS316` yields three fields;
  the same item written fully yields six. Matching a rich record against a sparse
  one leans heavily on the "missing is not mismatched" rule.
- **Unknown categories degrade to nearly nothing.** Records that do not fit a
  known schema fall through to `unknown` and route to human review. In the
  current dataset that is 5 of 100 on the regex fallback.

## When to revisit

Never in spirit. But if extraction accuracy on a real hold-out comes in below
roughly 70%, the weighting between the three signals has to shift toward text and
procurement behaviour until extraction improves — the idea survives, the weights
change.

## Related

- [002](002-llm-once-per-record.md) — how extraction is allowed to run
- [003](003-precision-over-recall.md) — why hard blockers exist at all
- `src/schemas.py` — where hard and ignored fields are actually declared
