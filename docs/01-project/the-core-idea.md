# The core idea

Everything else in this project is implementation. This is the idea.

> **We do not ask whether two descriptions look alike. We ask whether two items
> are the same thing.**

---

## Why text similarity is the wrong question

Not "insufficient" — *wrong*. It fails in both directions, and no threshold fixes
both.

### Case A — different words, same item

```
"SKF 6205-2RS Deep Groove Ball Bearing"
"FAG 6205-2RSR bearing, 25x52x15mm, sealed"
```

Shared words: essentially just "bearing". Different brand, different part number
format, one lists dimensions and one does not.

A fuzzy matcher scores this low and moves on.

**But `6205` is an ISO designation.** Any manufacturer's 6205 is 25 mm bore, 52 mm
outer diameter, 15 mm wide. `2RS` and `2RSR` both mean rubber sealed both sides.
These two bearings are physically interchangeable. For purchasing they are one
item.

### Case B — same words, different item

```
"GASKET SPIRAL WOUND SS316 4IN 150#"
"GASKET SPIRAL WOUND SS304 4IN 150#"
```

One character differs. Text similarity around 0.97.

A fuzzy matcher merges them.

**But SS316 contains molybdenum and SS304 does not.** That is what gives SS316
resistance to chloride and acid corrosion. In a corrosive refinery line, the wrong
one pits, fails, and leaks.

### There is no threshold that gets both right

Set it low enough to catch Case A and you certainly merge Case B. Set it high
enough to reject Case B and you certainly miss Case A.

**The problem is not the threshold. It is that text similarity measures the wrong
thing.**

---

## What we do instead

Extract typed specifications first. Compare specifications.

```
                   RECORD A            RECORD B
category      :    bearing        ✓    bearing
iso_designation:   6205           ✓    6205
bore_mm       :    25             ✓    25
od_mm         :    52             ✓    52
width_mm      :    15             ✓    15
seal_type     :    2RS            ✓    2RS
brand         :    SKF            ⊗    FAG      <- deliberately ignored

                                       -> MATCH
```

```
                   RECORD C            RECORD D
nominal_size_in:   4.0            ✓    4.0
pressure_class:    150#           ✓    150#
material_grade:    SS316          ✗    SS304    <- HARD BLOCK

                                       -> score 0, regardless
```

---

## The three rules that make it work

These matter more than any weighting.

**1. Hard blockers veto.**
Material grade, pressure rating and key dimensions are veto fields. A mismatch is
an instant zero, however well everything else lines up. This is not a tuning
choice — it is a safety property.

**2. Ignored fields never count.**
Brand and vendor part number contribute nothing to a match. This is precisely what
lets SKF and FAG resolve to one item. If brand contributes even slightly, Case A
breaks.

**3. Missing is not mismatched.**
If one record states a field and the other is silent, that is absent information,
not evidence of difference. No penalty.

This one is easy to implement wrong. In our own data, R00001 extracts two fields
and R00002 extracts five. They must still match.

---

## Why this needs an LLM at all

A regex can find `SS316` in a string. It cannot know that `6205` implies a 25 mm
bore.

That knowledge is public — ISO 15, ASTM specifications, ANSI classes, manufacturer
catalogues — and large models have absorbed it. That is the specific capability we
are buying, and it is why extraction runs once per record rather than being
replaced by rules.

The regex fallback in `src/schemas.py` still exists, still runs when the API is
unavailable, and still gets both demo cases right. It just extracts less.

---

## Where the LLM is NOT allowed

**It never decides a merge.**

The model reads one description and reports what it sees. Comparison, scoring and
clustering are pure arithmetic over the extracted data.

Three reasons:

- **Cost.** Per-record on a million records is one run. Per-pair is 20 million
  calls, every run.
- **Determinism.** The same inputs must always produce the same merge. A
  government audit trail cannot answer "why was this merged?" with "the model said
  so that time."
- **Explainability.** A reviewer must see *which fields agreed*. That only exists
  if the comparison is structural.

---

## Honest positioning

Attribute-based matching is what commercial MDM tools already do. Informatica, SAP
MDG, Verdantis and PROSOL all do it, and entity resolution dates to 1969.

**We do not claim invention.** We claim:

- **Scope** — cross-CPSE, not single-enterprise. A different problem: trust, data
  sharing, one national code.
- **Self-configuration** — abbreviation vocabulary learned from the corpus rather
  than consultants building it per client over months.
- **Sovereignty** — national strategic procurement data not sitting on a foreign
  vendor's platform.

In a hackathon field this idea is still differentiating, because most teams will
build a fuzzy matcher. That is why the demo shows a fuzzy matcher failing — twice,
in opposite directions.

---

## Do not let refactors erode this

The pipeline will change. Stages will be added, merged and rewritten. This
inversion — specs before text — is the thing that must survive all of it.

If a change makes text similarity the deciding signal, or lets brand influence a
match, or removes the hard-blocker veto, it has broken the project regardless of
what the metrics say.

Full reasoning: [`../02-decisions/001-match-on-specs-not-text.md`](../02-decisions/001-match-on-specs-not-text.md)
