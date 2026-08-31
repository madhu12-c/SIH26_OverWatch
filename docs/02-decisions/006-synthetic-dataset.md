# 006. Generate our own dataset

**Status:** 🟡 decided, and this is a known weak point — read the caveat in full
**Date:** 29 Aug 2026

## Context

The PS says sample material master data will be "provided by participating
CPSEs". It may arrive late, partially, or not at all, and we cannot build a
schedule around it.

Real CPSE material masters are also not public. Nobody publishes their material
codes, prices and vendor lists — that is the same commercial sensitivity that
makes this whole problem hard.

## Decision

Generate a synthetic dataset with `src/generate_dataset.py`, deterministic under
a fixed seed so the demo never changes under us.

It produces 100 records from 15 true items across 5 CPSEs, with corruption
modelled on real variation: abbreviation swaps, word reordering, unit-format
inconsistency, typos, dropped attributes, casing changes, and different vendor
part numbers for the same physical item.

Two cases are injected verbatim so random corruption can never break the demo:
the SKF/FAG functional-equivalence pair, and the SS316/SS304 grade trap.

The ingestion schema stays loose enough that a real CPCL extract drops in without
a rewrite, and `--seed-file` accepts a researched item list.

## What we rejected

**Waiting for the CPSE dataset.** Would block everything on something outside our
control, for an unknown period.

**Scraping GeM/eprocure into a dataset directly.** Gives real descriptions, but no
ground truth — nobody has labelled which of them are the same item. Without that
we can show a demo but cannot report accuracy. Still worth doing as a *hold-out*,
see below.

**Hand-writing 100 records.** No corruption model, no scaling, and the variation
would be whatever we happened to imagine that afternoon.

## What it buys us

- **We know the correct answer for every record.** That is the entire reason we
  can report precision and recall while most competing teams can only show a demo.
- Deterministic, so the demo runs identically every time.
- Scalable to any size, and reproducible from a seed rather than a stored file.
- The trap pairs give us the safety interlock report for free.

## What it costs us

- 🔴 **The accuracy claim is circular.** We designed the corruption, so "98%
  precision" actually means *"we reversed 98% of the errors we ourselves
  introduced."* A sharp judge can puncture this, and the answer must be ready
  before it is asked.

- 🔴 **If the data looks fake, the demo collapses.** A judge from CPCL reading
  descriptions that do not resemble their own master will stop believing
  everything else. We have already had to fix one instance of this — an unbounded
  string replacement was turning `MOTOR INDUCTION` into `MOTOR"DUCTION`, which no
  storekeeper has ever typed.

- **Item names, vendors and prices are not verified.** The engineering standards
  in the seed list are correct and checkable (6205 dimensions, A106 Gr B, ANSI
  classes). The vendor lists are real companies but unconfirmed as CPCL suppliers,
  and the prices are estimates. See `docs/03-reference/domain-facts.md`.

## The two fixes, both worth doing

1. **Observe corruption rather than invent it.** Study real variation in GeM and
   eprocure descriptions and replicate those patterns. Isha's screenshots are the
   evidence that we did this.

2. **Hand-label a small real hold-out.** 200–300 records from public sources,
   labelled by the team. Then report both numbers:

   ```
   Synthetic (100 records)   P = 98%   R = 87%
   Real hold-out (300)       P = 94%   R = 79%   <- the believable one
   ```

   The smaller, weaker number is worth more than the larger one, and volunteering
   it builds more credibility than hiding it.

## The safe way to say this out loud

> "This is a synthetic evaluation dataset, modelled on public GeM and tender
> nomenclature. We do not claim these are CPCL's actual codes or prices. We claim
> the *variation patterns* are realistic — abbreviation, truncation, unit
> inconsistency. On a real extract the pipeline runs identically; only the seed
> list changes."

Stated up front, this is unattackable. Discovered by a judge, it is damaging.

## When to revisit

The moment real CPSE data arrives, or as soon as the hold-out exists — whichever
comes first.

## Related

- [003](003-precision-over-recall.md) — what the numbers are measuring
- `docs/04-risks/honest-limits.md`
- `docs/06-team/isha.md` — the verification work
