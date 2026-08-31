# 003. Precision over recall, with a human in the loop

**Status:** 🟢 decided
**Date:** 29 Aug 2026

## Context

Two kinds of error are possible, and they are not equally bad.

| Error | Name | What it costs |
|---|---|---|
| Two different items merged | false merge | A storekeeper issues the wrong part |
| Two same items left separate | missed duplicate | An opportunity not taken |

A missed duplicate means one item keeps two codes for another month. A false
merge means a system says SS304 and SS316 gaskets are interchangeable, and
eventually someone fits the wrong one into a corrosive line.

The costs differ by orders of magnitude, so the thresholds cannot be tuned to
maximise F1 — that treats both errors as equally weighted, which is exactly wrong
here.

There is also a second, quieter reason. The PS text itself says *recommend*,
*propose*, *review*, *validate* and *approve* throughout, and lists "user
validation and approval workflow" as a required capability. A fully automatic
merger would not satisfy the brief even if it were safe.

## Decision

Precision is the target metric. Recall is allowed to be lower.

```
above 0.90    auto-merge      system proceeds, fully logged, reversible
0.70 - 0.90   review queue    a human approves or rejects
below 0.70    leave alone     kept as separate items
```

Plus hard blockers: a mismatch on grade, pressure rating or a key dimension is an
instant zero, regardless of score. Those pairs never reach any band.

Targets: **precision above 98%**, recall above 85%. Uncertainty routes to a
person rather than being resolved by a threshold.

Across two CPSEs, both sides must approve before a national code is issued — no
company decides on another company's data.

## What we rejected

**Maximise F1.** The standard choice, and wrong here. F1 weights a false merge
and a missed duplicate equally; our costs do not.

**Auto-merge everything above a high threshold, no human.** Faster to demo and
simpler to build. Rejected because the PS explicitly requires an approval
workflow, and because a refinery material master is not a place to be confident.

**Send everything to review.** Safest possible, and it fails for a different
reason: a reviewer facing a queue full of obvious pairs stops reading and starts
blind-approving. That is the most dangerous failure mode in the whole system,
because it looks like the system is working.

## What it buys us

- The safety story is demonstrable, not asserted — we can show the blocked list.
- "Why not auto-merge everything?" has a direct answer that quotes the PS back.
- The blocked-merge count becomes its own slide, and it is more memorable than the
  merge count because nobody else will show it.

## What it costs us

- **We knowingly miss real duplicates.** Recall around 85% means roughly one in
  seven genuine duplicate pairs is left alone. That is a deliberate trade, and it
  should be stated rather than hidden.
- **Someone has to work the queue.** The reviewer does tedious work while
  procurement gets the savings — the classic reason master-data projects die.
  This is why the review UI must be fast, and why it is built before the
  dashboard.
- **Two-sided approval is slow.** A cross-CPSE merge waits on two organisations.
  Correct, but it will be raised as a scaling concern.

## When to revisit

The bands are numbers, not principles. Rashmit's evaluation harness should tune
them against ground truth — if 0.85 gives 98% precision, use 0.85. What does not
move is the ordering: precision first, uncertainty to a human.

## Related

- [001](001-match-on-specs-not-text.md) — hard blockers live in the schema
- [006](006-synthetic-dataset.md) — why our precision number needs a caveat
- `docs/04-risks/honest-limits.md`
