# Yash — scoring, clustering, hard blockers

You own the part that decides whether two records are the same item. Everything
upstream produces evidence; you turn it into a number and a group.

---

## What you get

| File | What it holds |
|---|---|
| `data/output/specs.json` | Extracted attributes + per-field confidence, per record |
| `data/output/embeddings.npz` | One 384-dim vector per record |
| `data/input/purchases.csv` | Vendor, price, qty, plant — signal 3 |
| `src/schemas.py` | **Read this first.** It already tells you which fields veto a match and which are ignored. |

**Do not hard-code field names anywhere.** Ask the schema:

```python
import schemas

schemas.hard_fields("gasket")      # ['material_grade', 'nominal_size_in', 'pressure_class']
schemas.ignored_fields("bearing")  # ['brand', 'part_number']
schemas.scoring_fields("valve")    # Field objects with .weight
```

Reading embeddings — always through the lookup, never by position:

```python
from embed import load_embeddings
ids, vectors, lookup = load_embeddings()
sim = float(np.dot(vectors[lookup["R00001"]], vectors[lookup["R00002"]]))
```

---

## What you produce

| File | Shape |
|---|---|
| `data/output/pair_scores.json` | every scored pair **plus the signal values behind it** |
| `data/output/clusters.json` | groups of record_ids that are one item |

The signal breakdown is not optional. The review screen has to show a human *why*
two records matched, and the audit trail has to store it. A bare score is not
enough.

```json
{ "a": "R00001", "b": "R00002",
  "text_sim": 0.31, "spec_sim": 0.97, "proc_sim": 0.88,
  "final": 0.94,
  "matched_fields": ["iso_designation", "seal_type"],
  "ignored_fields": ["brand"],
  "blocked_by": null }
```

---

## The three rules that matter more than the weights

**1. Hard blockers veto.**
A mismatch on any field where `hard=True` is an instant zero, however well
everything else lines up. Grade, pressure rating, key dimensions. Record which
field did it in `blocked_by` — that field feeds the safety interlock report.

**2. Ignored fields never count.**
Brand and vendor part number. This is exactly what lets SKF and FAG resolve to one
item. If brand contributes even a little, the headline demo case breaks.

**3. Missing is not mismatched.**
If one record states a field and the other is silent, that is absent information —
not evidence of difference. No penalty, no credit.

This one is easy to get wrong and it matters a lot here. R00001 extracts 2 fields;
R00002 extracts 5. They must still match.

---

## Signal fusion

```
score = w1 * text_sim          (weakest — shortlisting, not deciding)
      + w2 * spec_agreement    (heaviest — this is the whole idea)
      + w3 * procurement_sim   (same vendor, similar price band, similar qty)

any hard blocker -> score = 0
```

Start with roughly `w1=0.2, w2=0.6, w3=0.2` and let Rashmit's harness tune them.
Do not tune by eye — tune against measured precision.

**Weight fields by confidence.** A spec extracted at 0.95 should pull harder than
one at 0.45. The confidence numbers are in `specs.json` for exactly this.

**Price as a guard, not just evidence.** Identical text, identical specs, 100×
price difference means these are not the same item. Something real distinguishes
them that the description never captured.

---

## Clustering

Union-find over the pairs above threshold. Each connected group becomes one item.

**The hazard, and it is a real one:** A matches B, B matches C, but A and C are
unrelated. Connected components still groups all three, and one bad bridging
record can drag hundreds of unrelated items into a single blob.

Three defences, use all of them:

1. Keep the threshold high — precision first.
2. After forming a group, check that **every** pair inside it scores well, not
   just the connected ones. Split the group if not.
3. Cap cluster size. Anything oversized goes straight to human review.

---

## Skip blocking

At 100 records all-pairs is 4,950 comparisons — instant. Blocking exists in the
architecture and is documented in
[`../03-reference/pipeline-stages.md`](../03-reference/pipeline-stages.md), but
building it now would eliminate comparisons that take milliseconds.

Reasoning: [`../02-decisions/007-no-infrastructure-yet.md`](../02-decisions/007-no-infrastructure-yet.md).
Write it when the dataset passes ~5,000 records.

---

## Done when

- [ ] **R00001 and R00002 merge.** Different brands, same bearing.
- [ ] **R00003 and R00004 never merge**, and the run says `blocked_by:
      material_grade`.
- [ ] No cluster contains two records whose true item ids differ (check against
      `data/truth/ground_truth.csv` — in the *evaluation*, never in the scorer).
- [ ] `pair_scores.json` carries the full signal breakdown, not just a number.
- [ ] The count of merges blocked by each rule is available — that is the safety
      interlock slide.

---

## If you are stuck

- Why hard blockers exist at all: [`../02-decisions/003-precision-over-recall.md`](../02-decisions/003-precision-over-recall.md)
- Why we match on specs rather than text: [`../02-decisions/001-match-on-specs-not-text.md`](../02-decisions/001-match-on-specs-not-text.md)
- What each field means: [`../03-reference/schemas-and-blockers.md`](../03-reference/schemas-and-blockers.md)
