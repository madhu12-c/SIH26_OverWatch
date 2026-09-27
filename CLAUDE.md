# CLAUDE.md — One Nation, One Material Code

> Working instructions for this repo. Read fully before writing code.
> Companion document: `architecture.html` / `Architecture.pdf` — the full stage-by-stage
> flow, written in plain English for the whole team. This file is the decision record.
>
> **The final design is `finalarchitecture.md` (24 Sept 2026).** Pipeline, features, rules,
> data, evaluation, claims, PPT and build plan all live there. Where this file and that one
> differ, **that one wins** — update this file to match rather than acting on the older text.

---

## 1. The project

**Smart India Hackathon 2026. Team: Overwatch. Lead: Madhu (3rd year, VCET).**

**Problem statement SIH26099** — Ministry of Petroleum & Natural Gas
Department: **Chennai Petroleum Corporation Limited (CPCL)**
*"AI-Driven Standardization and Harmonization of Material Codes Across CPSEs"*
Category: Software · Theme: Smart Automation

**CPCL is a refinery** (Manali, Chennai; IOCL subsidiary). The judging panel will think in
refinery MRO terms. Seed data must lean that way — pipes, valves, flanges, gaskets, pumps,
bearings, seals, motors, instrumentation, safety consumables — not steel-plant or mining stock.

### The problem

CPSEs (ONGC, IOCL, CPCL, BPCL, SAIL, NTPC, GAIL, BHEL, Coal India) each keep their own material
master. The same physical item is coded differently across companies and often duplicated within
one company. Result: duplicate stock, no collaborative procurement, fragmented analytics, painful
ERP migration. Published case studies report ~5–7% inventory cost reduction from standardisation.

**Why descriptions are cryptic — say this carefully.** Several reasons, not one: SAP's standard
description field `MAKT-MAKTX` is **40 characters — still, today, not a legacy limit**; data
migrated from older systems with even shorter fields; and, most importantly, there was never an
enforced cataloguing standard, so every storekeeper invented their own shorthand.

Do **not** say "descriptions are cryptic because SAP capped the field at 40 characters." A CPCL
person may well answer that the real cause was the absence of a cataloguing policy — and they
would be right. The multi-cause version invites agreement instead of correction. Verification
route and confidence levels: `docs/03-reference/domain-facts.md`.

### What we build

Ingest messy material masters from multiple CPSEs, identify which records refer to the same
physical item, assign a single **Common National Material Code**, and retain a mapping back to
every CPSE's original code.

---

## 2. The core technical problem

> High-precision **entity resolution** over short, noisy, domain-specific text, with **no labelled
> training data**, where a match means **functional equivalence** rather than textual similarity,
> at a scale that forbids all-pairs comparison.

| Difficulty | Implication |
|---|---|
| Descriptions are 8–15 words | Weak signal; text embeddings alone insufficient |
| Heavy abbreviation (`M.S.`, `SS316`, `SCH40`, `NB`) | Out-of-vocabulary; needs a normalisation layer |
| No training labels | Unsupervised only. No supervised classifier. |
| Functional equivalence | Two records can be interchangeable while sharing ~no words |
| Millions of records | Blocking mandatory; never O(n²) |
| Asymmetric error cost | Wrong merge ≫ missed duplicate. **Precision-first.** |

### The central design decision

**Match in attribute space, not text space.** Extract structured specs first, compare specs.

```
"SKF 6205-2RS Deep Groove Ball Bearing"
"FAG 6205-2RSR bearing, 25x52x15mm, sealed"
   text similarity: 0.31   -> a fuzzy matcher MISSES it
   reality:         SAME BEARING (6205 is an ISO designation)

"GASKET SPIRAL WOUND SS316 4IN 150#"
"GASKET SPIRAL WOUND SS304 4IN 150#"
   text similarity: 0.97   -> a fuzzy matcher WRONGLY MERGES
   reality:         DIFFERENT ITEMS (grade matters in corrosive service)
```

This inversion is the project's main technical contribution and the centrepiece of the demo.
**Do not let refactors erode it.**

---

## 3. Architecture

```
CPSE uploads (CSV/XLSX) + purchase history
  |
  v  [01] Normaliser        abbreviations, UoM canonicalisation, text cleanup
  v  [02] Spec extractor    LLM -> typed attributes + per-field confidence   [CRITICAL PATH]
  v  [03] Embeddings (GPU)  -> pgvector
  v  [04] Blocking          category + key attribute + top-k vector neighbours
  v  [05] Hybrid scorer     text + specs + procurement behaviour
  v  [06] Clustering        union-find over the similarity graph
  v  [07] Confidence bands  auto-merge / review queue / leave alone
  v  [08] Canonicaliser     golden record + standard description + national code + UNSPSC
  v  [09] Outputs           mappings, savings report, safety interlock, audit log, export API
```

### The three matching signals

1. **Text** — embedding cosine similarity. Weakest; useful only in combination.
2. **Specifications** — attribute agreement after extraction. **Highest weight.** Catches
   functional equivalence.
3. **Procurement behaviour** — same vendor / price band / order size / plant. Explicitly requested
   by the PS ("...and historical procurement data") and most competing teams will ignore it.
   Critically, **price also guards against false merges**: a ₹42 bolt and a ₹4,200 bolt with
   identical text and identical specs cannot be the same item.

### Scorer rules that matter more than the weights

- **Hard blockers** — material grade, pressure rating, key dimensions are veto fields. Mismatch
  is an instant zero regardless of everything else.
- **Ignored fields** — brand and vendor part number never count toward a match. This is what
  lets SKF and FAG resolve to one item.
- **Missing ≠ mismatched** — one record silent on a field is absent information, not evidence of
  difference. No penalty.

### Clustering hazard

Transitive closure explosion: A~B, B~C, but A≁C — connected components still group all three, and
one bridging record can pull hundreds of unrelated items into a blob. Defences: high threshold;
validate that *every* intra-cluster pair scores well and split if not; cap cluster size and route
oversized clusters to review.

---

## 4. Stack (decided)

- **Backend:** FastAPI (Python)
- **DB:** Postgres + pgvector (HNSW index)
- **Embeddings:** sentence-transformers, local GPU (Rashmit's machine)
- **Vector search:** pgvector; FAISS only if scale demands
- **LLM:** Claude or Gemini API — spec extraction only
- **Frontend:** React
- **Deploy:** Docker

**Cost/latency rule:** the LLM is called **once per record at ingestion**. **Never per candidate
pair.** Pairwise scoring must be pure vector/numeric maths. Per-record ≈ 1M calls run once and
stored; per-pair ≈ 20M+ calls run every time. Violating this makes the system unviable — flag it
if any design drifts that way.

**Scale note:** at ~100 records none of this infrastructure is needed. All-pairs is ~5,000
operations, instant in pandas. Build infrastructure when record count demands it, not before.

---

## 5. Repo state

```
README.md                 entry point
CLAUDE.md                 this file — the decision record
finalarchitecture.md      THE FINAL DESIGN — pipeline, features, rules, PPT, build plan
buildplan.md              how each feature is built — one design card per feature
docs/                     full documentation, indexed at docs/README.md
  01-project/             problem, core idea, glossary
  02-decisions/           every decision with what we rejected  <- read before changing anything
  03-reference/           data dictionary, pipeline stages, schemas, domain facts
  04-risks/               honest limits, technical + demo risks, judge Q&A
  05-runbook/             setup, running, demo day
  06-team/                one self-serve file per person
src/                      paths.py, schemas.py, normalise.py, rules.py, standards.py,
                          selfcheck.py, catalogue.py, render.py, generate_dataset.py, extractor.py,
                          embed.py, blocking.py, scorer.py, evaluate.py, baselines.py,
                          real_eval.py, real_view.py, canonicalise.py, savings.py, uom.py,
                          gate.py, govern.py, evidence.py, results.py, run_all.py
tests/                    python -m pytest tests/  — real-text reading, real pairs, blocking at
                          15,000 records, hard negatives. Must pass before any scorer/schema change.
data/input/               materials.csv, purchases.csv        (what a CPSE gives us)
data/truth/               ground_truth.csv, traps.json        (evaluation ONLY, never the pipeline)
data/real/                candidates.csv — 902 real material lines (Oil India 546, NTPC 351, IOCL 5)
                          labels/ — dev 485 (labelled, for building) · test 417 (labelled by Claude
                          after freeze 1, claude.csv; isha/meghna sheets still blank) · frozen.json
                          (freeze 2, 25 Sept, with freeze 1 and its result kept in history)
                          (CC-BY-4.0; see data/real/README.md; src/mine_real.py, src/labels.py)
data/output/              specs.json, embeddings.npz, uom.json, gate.json, ... (regenerable)
data/runs/15k/            the 15,000-record run (SIH_RUN=15k) - input, truth, output; git-ignored,
                          rebuilt by: python src/run_all.py --run 15k --generate 15000
ui/                       React portal (government style) — role sign-in + 11 pages, offline
deliverables/             LOCAL ONLY (git-ignored): architecture doc, PDF, decks, slide-numbers.md, ppt-kit/
brag-output/              LOCAL ONLY (git-ignored): SIH video clip + walkthrough and the scripts that build them
```

**Built and working — the pipeline runs end to end.** Dataset generator (100 records, 15 items,
84% duplication, 245 POs), category schemas with hard blockers, spec extractor (Gemini + regex
fallback, cached, resumable), local embeddings, hybrid scorer, clustering, evaluation harness,
canonicaliser, savings report, UoM harmonisation, creation gate, and a government-style React
portal: role-based sign-in (registrar / CPSE reviewer / procurement / ministry), dashboard,
analytics, catalogue + item pages, migration with a SAP-shaped CSV download, review queue, and a
live audit trail. The sign-in picks a role — there is no real authentication and no server.
Both demo cases pass on the regex fallback alone — no API, no internet.

Current measured numbers — demo set (`data/output/metrics.json`, 24 Sept 2026, late): precision
1.0, recall 1.0, 141 auto-merged pairs, 0 false merges, 0 trap violations, 97 safety blocks among
the 407 pairs blocking lets through, 100 raw → 15 unique (85% duplication, = ground truth).
Savings: ₹22.6 cr total spend, ₹2.31 cr upper / ₹0.92 cr realistic, k-anonymity 3.

**15,000-record run** (`data/runs/15k/output/metrics.json`; item factory, real notations, 20%
duplication, 3,338 records in test families locked before tuning): **860 pairs auto-merged, 0
wrong, 0 of 104,994 near-miss traps** — dev 643/0 wrong, test 217/0 wrong. Recall (auto +
review) 82% (dev 82.6%, test 81.9%). Blocking skips 99.80% of pairs; 83% of true pairs meet —
the rest are records missing their identity (a seal with no shaft size). Review queue: the true
match is ranked first for 50% of records, in the top three for 78%. The first 15,000 run was
NOT safe — 2,625 wrong auto-merges (31% precision); see buildplan A6 for what fixed it.
**Error bound** (`evaluate.error_bound`, Clopper–Pearson, one-sided): with 95% confidence the
auto-merge error rate is below **0.35%** (test families alone: below 1.37%; demo set: 2.1%).
Locked at tag `ppt-numbers-2026-09-25` from a clean regenerate + re-read (the data came back
byte-identical; the re-read with freeze-2 code moved 846 → 860 auto-merges, still 0 wrong).
**What-if** (`scorer.counterfactual`): every blocked pair stores the score it would get if the
blocking field agreed. At 15,000, **13,128 refusals were one field from an automatic merge —
13,127 truly different items**; the other is a pack-size price gap (C13). Demo: "if the
material grade matched, this pair would score 0.956".
**Baselines** (`baselines.py`, same candidate pairs, thresholds tuned on dev families, scored on
test families): at their best F1, fuzzy / TF-IDF / embedding matching are 6–8% right — TF-IDF
merges 2,112 pairs, 1,953 wrong, 1,121 across traps. No text threshold reaches zero wrong:
different items share identical text once SAP's 40 characters cut them. Ours auto-merges 217
there, 0 wrong, finding 18% of duplicates with no person — about what the text matchers find.
(Before the A1–A5 work: recall 0.942, 16 clusters, 282 safety blocks under all-pairs. Recall rose
because a grade-spelling bug and a cast-vs-carbon-steel veto were falsely blocking true pairs;
the block count fell because blocking no longer compares every look-alike.)

**Real test result** (`python src/real_eval.py --test claude`, 252 real material lines).
*Freeze 1, 24 Sept:* category right 97.9%, two or more facts 86.9%, 4 auto-merged, **0 wrong**,
51 of 59 true pairs found (86.4%), review precision 17.8% (that code was never committed; its
result is kept in `frozen.json` history). *Freeze 2, 25 Sept* (the locked code): category 97.9%,
two or more facts 90.3%, 4 auto-merged, **0 wrong**, 49 of 59 found (83.1%) — the A6 safety rules
hold more pairs back — review precision 17.9%. **Caveats to state every time:** the labels are
Claude's (the builder), one labeller; the builder had read the test rows before freeze 2 (no
change since freeze 1 was made from a test row); Isha's and Meghna's blind labels, scored on
freeze 2, replace them.

✅ **25 Sept — pulled forward from October, so the demo and slides can show them.**
Counterfactual ("what if" on every refused pair), self-check (`selfcheck.py`; a record that
contradicts itself never auto-merges, gate verdict CONTRADICTS; 0 flags on 308 real dev lines
and 15,000 generated ones), cross-standard equivalence with supersession (`standards.EQUIVALENCE`),
baselines, the 95% error bound, governance (sealed audit log in the portal, `govern.py` verifies
and replays it and refuses what the consent rules forbid), the Real tender text page, the review
queue as one record with its top candidates, and the dashboard evidence panel
(`evidence.py` → `data/output/evidence.json`, three datasets, stamped, never blended).
Numbers locked at tag `ppt-numbers-2026-09-25`; `deliverables/slide-numbers.md` traces each.

**Not yet built:** the five relationships (B4), the staged migration pack with dry-run and
rollback (C8; today it is a SAP-shaped CSV download), an ERP export API (capability 8), the
data-quality scorecard (C9), review priority (C4), pack-size algebra (C13), and the rest of
`finalarchitecture.md` §12 "October to December".

✅ **Fixed 24 Sept 2026 — the extractor now reads real Indian text** (buildplan A1, A2, A4, A5).
`normalise.py` + `rules.py` treat NB/DN/inch as size *names* and OD/wall as measurements, give
unlabelled NTPC millimetre numbers a role by rule, settle 101.6 mm by the stated weight, read
FE410 / TP304L / A213 T91 / API 5L X46 on a grade-family ladder, API 6A psi ratings, motors,
transformers and cables, and keep an evidence span per value. Four new categories (cable,
fitting, plate, tube) and an "other" path that can reach review but never auto. On dev: two or
more facts 3% → 93%, category right 87% → 99%. `blocking.py` (keys + meta-blocking) replaces
all-pairs. (Its first figures, 99.92% / 98.4%, were on clean test specs; on the real-notation
15,000 run it skips 99.80% of pairs and 83% of true pairs meet - see A6 below.)

✅ **A6, 24 Sept late — the 15,000-record run, and what it exposed.** Built `catalogue.py` (11,815
valid items from ISO 15 / B36.10 / IEC tables in `standards.py`), `render.py` (NTPC, Oil India,
SAP-40, plain; vendor and sentence styles for test families only), `run_all.py`, run folders
(`SIH_RUN`). At scale the scorer auto-merged 2,625 wrong pairs. Fixes, all from dev families:
variant fields (seal, filler, ends, face, armour, bore, faces, elastomer, connection) are now
veto fields; **a veto field stated on one side and silent on the other holds the pair for
review**; **variant awareness** — both silent while the registry holds several values also holds
it; family-only grades ("SS" vs "SS") are a doubt where several grades exist; groups that fail
cohesion are split, not issued one code; reader fixes (seals, typo'd nouns, SAP 40-character cut,
bare stainless numbers, NTPC OD-before-wall). A relaxation (use variant knowledge to excuse
one-sided silence) was tried and rejected: the default variant is the unwritten one.

🔴 **Known issues from the real test (do NOT fix by looking at test rows — reproduce on dev):**
review-queue noise from one-side-silent safety fields (needs a "minimum agreed hard fields"
rule before proposing); plate dims written `(1.6X 2500X 1250MM)`; slash-less `1.13 16 inchs`;
an inch value in brackets that restates a bare OD (`114.3 mm (4.1/2")`). Any fix is post-freeze:
re-freeze deliberately and report its test number as post-freeze.

⚠️ **Keep this section current.** It was stale for several days — it listed `scorer.py`,
`canonicalise.py`, `savings.py`, `results.py` and the whole UI as unbuilt while all of them
existed and ran. Advice given against a stale decision record is worse than no advice, because
it recommends rebuilding what is finished and misses what is actually missing.

**Paths are defined once in `src/paths.py`.** Never build a path from string pieces elsewhere.

⚠️ **Known trap:** `specs.json` is a cache keyed by `record_id`. After any
`generate_dataset.py` run, re-extract with `--fresh` or the pipeline runs on specs for records
that no longer exist — silently. This has already happened once.

What the generator produces:
- `materials.csv` — records with realistic corruption: abbreviation swaps, word reordering,
  unit-format variation, typos, dropped attributes, casing changes, and **different vendor part
  numbers for the same physical item** (the functional-equivalence cases)
- `purchases.csv` — vendor, unit price, qty, PO date, plant
- `ground_truth.csv` — `record_id → true_item_id`

**Extend `SEED_ITEMS` with real item nomenclature** from GeM catalogue, eprocure.gov.in tender
BOQs, and supplier catalogues (SKF/FAG bearings, fasteners, pipes, valves). Target 200–300 seed
items, refinery-weighted.

**Guarantee in the seed data:** at least one clean functional-equivalence pair (different brand,
same ISO designation) and at least one grade-mismatch trap (SS304 vs SS316), so the demo cannot
fail live.

### Honest caveat about our own evaluation

We design the corruption, so "98% precision" really means *"we reversed 98% of the errors we
ourselves introduced."* That claim is circular and a sharp judge can puncture it. Two fixes,
both worth doing:

1. **Observe corruption, don't invent it.** Study real variation in GeM/eprocure descriptions and
   replicate those patterns rather than inventing plausible-looking ones.
2. **Hand-label a small real hold-out** — 200–300 records from public sources, labelled by the
   team. Report both numbers. The smaller, weaker real number is the more believable one, and
   volunteering it builds more credibility than hiding it.

---

## 6. Build order (do not reorder)

1. **Spec extractor** — critical path. Validate on 50 records by hand before anything downstream.
   Strict schema per material category, per-field confidence, regex fallback.
2. **Normaliser** — abbreviation dictionary + UoM canonicalisation. Build alongside (1).
3. **Evaluation harness** — precision/recall against `ground_truth.csv`. Build early so every
   later change is measurable.
4. **Embeddings + vector index.**
5. **Blocking** — measure reduction ratio (>99.9%) and pair completeness (>98%).
6. **Hybrid scorer + clustering** — tune thresholds against the harness. Precision-first.
7. **Canonicaliser** — golden record, standard description, national code, UNSPSC, mappings.
8. **Review UI**, then dashboard.
9. **Audit log + export API.**

---

## 7. PS requirements → components

The PS lists 8 Key Capabilities. Judges score against these.

| # | Capability | Component |
|---|---|---|
| 1 | AI Material Matching & Recommendation | Three-signal hybrid scorer |
| 2 | Material Standardization & Classification | Canonicaliser + UNSPSC mapper |
| 3 | Duplicate / Near-Duplicate Detection | Blocking + clustering + confidence bands |
| 4 | Common National Material Code Generation | Code generator |
| 5 | CPSE Code Mapping & Migration Support | Mapping table (source ↔ national) |
| 6 | Material Master Dashboard & Analytics | Dashboard |
| 7 | Audit Trail & Governance | Immutable change log + approval workflow |
| 8 | SAP / ERP Integration | Export API + adapter interface |

### Four things the official PS text calls for that are easy to under-build

1. **Standardised description generation is its own deliverable**, not a footnote of the
   canonicaliser. Use industry noun-modifier format — once specs are typed this is a template
   render, and it makes the extraction work visible:
   ```
   BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED
   PIPE, SEAMLESS, CARBON STEEL, ASTM A106 GR B, 4 IN, SCH 40
   ```
2. **Units of measurement** are named explicitly in the PS Background. UoM harmonisation
   (EA/NOS/PCS, M/MTR/MTS, KG/KGS) is a small named feature with its own conflict rule — surface
   it separately in the dashboard. Watch pack sizes: per-piece vs per-box-of-100 breaks price
   comparison.
3. **Rationalisation ≠ mapping.** Mapping is source↔national. Rationalisation is *shrinking the
   estate* — flagging redundant, obsolete and never-procured codes for retirement. Our headline
   "N raw → M unique, X% duplication" **is** the rationalisation metric; state it in the PS's own
   words (Expected Impact bullet 2).
4. **Use UNSPSC.** Do not invent a taxonomy. Only the 20–30 classes our categories touch.

**Capability 7 is not optional.** Government data requires "who approved this merge, when, and
can it be reversed."

The PS says *recommend / propose / review / validate / approve* throughout — **human-in-the-loop
is the specified design, not a hedge.** That is the answer to "why not auto-merge everything?"

---

## 8. Non-negotiable design rules

- **Precision over recall.** A wrong merge in a refinery material master could mean the wrong
  valve installed. Conservative thresholds; uncertainty goes to human review.
- **Nothing is destroyed.** `materials` is append-only. Original codes always retained and mapped.
  Merges reversible — undoing a merge deletes mapping rows, never restores deleted data.
- **Every merge is explainable.** Store *why* two records matched (which signals, what scores,
  which fields). The review UI must show it.
- **LLM never decides a merge.** It extracts attributes only. Matching is deterministic scoring
  over extracted data. Keeps the system auditable and prevents hallucinated merges.
- **One LLM call per record, never per pair.**
- **Consent scales with harm.** Revised 23 Sept 2026, replacing "both sides must approve
  before a national code is issued" — see the reasoning below.

  | Action | Who decides |
  |---|---|
  | Link two codes under one national code | National registrar. No veto. |
  | Retire or deactivate a code | **Only the company that owns it.** Nobody else, ever. |
  | Show a price or vendor across companies | Never raw. Bands and hashes, suppressed below 3 CPSEs. |
  | **Dispute a link** | **Any affected company, at any time.** Returns the pair to review. |

  **Why this changed.** Requiring both companies to sign off on every cross-CPSE code
  deadlocks the registry: nothing is issued until two busy people in two organisations
  both act, and neither gains from acting — the reviewer gets a queue, procurement gets
  the savings. One silent company blocks a code forever. That is the adoption trap in
  section 9, written into the governance model.

  The escape is that **a national code changes nothing inside a CPSE's system.** It sits
  above the existing codes and links them; every original code stays active and in use.
  An additive, reversible link does not need permission the way an edit would. UPI did
  not ask each bank to approve each account linkage.

  So the registry moves by default and stops on evidence. A company cannot block a code
  being issued, but it can say "those are not the same item" at any point, and the link
  returns to a human with the objection recorded in the audit log.

  **A right to dispute, not a right to veto.** This is stronger than the centralised
  alternative, where a national registrar issues codes and a company has no recourse at all.

---

## 9. Who the user actually is

Four personas, one primary.

| Who | Does | Wants |
|---|---|---|
| **Material master reviewer** (cataloguer) | Clears the review queue. Domain expert — already knows SS304 ≠ SS316. | Fast decisions, evidence on one screen |
| Storekeeper / indent raiser | Searches for material, requests new codes | Search that works, no accidental duplicates |
| Procurement officer | Raises tenders | Demand aggregation, best price, joint tenders |
| Ministry / national registry | Owns the system | National code, savings number, governance |

**The reviewer is the primary user.** Every CPSE has their own; they approve only their own
company's records.

**The adoption trap:** the person doing the work is not the person getting the benefit. The
reviewer gets a queue; procurement gets the savings; the ministry gets the credit. This is how
master-data projects die worldwide. Therefore:

- Review UI must be **obsessively fast** — keyboard shortcuts (`A`/`R`/`S`), all evidence on one
  screen, batch approve for high-confidence.
- Only send genuinely uncertain cases. If obvious pairs reach the queue, the reviewer loses trust
  and starts blind-approving — the most dangerous failure mode.
- **Review UI before dashboard.** A dashboard is one slide; the review queue is the product.

---

## 10. Differentiators (build these, in this order)

The matching engine is table stakes — everyone will have one. These are what separate us.

### A. Savings report — highest value per unit of effort
Once clusters exist, group `purchases.csv` by national code. Roughly one day's work; it turns a
data-cleaning project into a money project.

```
3,847 materials bought separately by 2+ CPSEs.
Combined annual value ₹412 cr.
Consolidating at best-observed-price alone: ₹31 cr.
```

The PS Expected Impact asks for demand aggregation and strategic sourcing, but it is not in the
Key Capabilities list — so almost nobody will build it, and it is exactly what the ministry wants.

### B. Safety interlock report — cheap and memorable
Everyone shows merges. Show what we **refused** to merge:

```
4,312 merges BLOCKED
  material grade mismatch (SS304 vs SS316)   1,204
  pressure rating (150# vs 300#)               887
  price anomaly (>10x)                         412
```

One day's work. Shows we think like a refinery, not like an ML exercise.

### C. Federated matching — the strongest strategic argument
This is the answer to *"why not just buy Informatica / SAP MDG?"* Those tools need all data
centralised, and **no CPSE will hand over its prices and vendor list.** That is architectural, not
a missing feature, and it is the real reason a national material master has never existed.

```
stays inside the company        crosses the boundary
  raw description                 embedding vector
  exact price   ₹1,310            price band    B4
  vendor name   SKF India         vendor hash   7b21e4
  exact quantity                  order-size band
```

Matching still works: equal hashes prove "same vendor" without naming it; band comparison catches
a 100× price gap without revealing either price.

**Show benchmark, never attribution** — a company learns a better price exists and how far above
it they are, not who achieved it. **k-anonymity:** suppress the benchmark when fewer than 3 CPSEs
are in a cluster, because with only two the minimum price *is* the other party's price.

**Do not overclaim.** Say "significantly reduces data exposure", never "cryptographically secure".
Embeddings are partially invertible; Bloom-filter encodings have known attacks. Full MPC /
homomorphic encryption is roadmap. Volunteering the limitation raises credibility.

### D. Learned abbreviation vocabulary — only after A–C
Mine `M.S.` ≈ `MILD STEEL` from corpus co-occurrence instead of hand-coding. Supports the
"self-configuring" claim: commercial tools need consultants building per-client dictionaries for
months.

---

## 11. Team

| Person | Owns | Done when |
|---|---|---|
| **Madhu** (lead) | Architecture, normaliser, spec extractor, canonicaliser | Any description in → correct typed specs out, with confidence, across all six categories |
| **Yash** | Blocking, scorer, clustering | Given specs + vectors, emits scored clusters with hard blockers enforced |
| **Rashmit** | Embeddings, evaluation harness, tuning, deployment. **Owns the GPU machine.** | One command prints precision, recall, duplication rate vs ground truth |
| **Aditya** | Review queue UI, then dashboard | A reviewer clears 100 decisions without touching the mouse |
| **Meghna** | Deck, narrative, domain research, presenting | She can answer a hostile domain question without slides |
| **Isha** | Dataset building, demo operation | 200–300 real refinery items sourced; demo runs identically every time |

**Realistic capacity:** the team works in bursts around deadlines; momentum depends heavily on
Madhu pushing. Competing commitments: semester work, Madhu's other projects (Ara, freelance CA
automation).

**Implication for code:** keep the core small enough that Madhu + Yash could finish it alone.
Prefer modular, independently-completable chunks. **Every burst must end at a working
checkpoint** — assume a two-week gap may follow.

**Presenter risk:** finale judges will be ministry/PSU domain people who cross-question. Meghna
should carry the story while Madhu or Yash handle technical Q&A — that split is normal and
allowed. Start domain prep now, not in December.

---

## 12. Timeline

- **29 Aug 2026** — planning handover written
- **30 Aug 2026** — architecture doc written; repo found empty
- **1 Sept 2026 (Tue)** — college internal round. Done.
- **17 Sept 2026** — architecture frozen
- **24 Sept 2026** — final architecture written (`finalarchitecture.md`)
- **27 Sept 2026 (Sat)** — **SIH idea submission — PPT as PDF, six slides maximum**
- **Dec 2026** — Grand Finale (if selected)

**The real risk is October.** After the 27 Sept submission there is a dead zone — submission done,
finale far away, semester exams. Most SIH teams lose there, not in December. Keep a weekly
checkpoint through Oct–Nov, however small.

The order of work to December is `finalarchitecture.md` §12. December is for rehearsal only,
not new features.

---

## 13. Honest positioning

**Commercial MDM exists** — Informatica, SAP MDG, Verdantis, PROSOL (the last serves oil & gas in
India). Entity resolution dates to 1969. Attribute-based matching is what those tools already do.
**Claim execution, not invention.**

| Our claim | Meaning |
|---|---|
| **Scope** | They deploy single-enterprise. This is cross-CPSE — a different problem: trust, data sharing, one national code. |
| **Self-configuration** | Consultants build rules and dictionaries per client over months. We learn abbreviation vocabulary from the corpus. |
| **Sovereignty** | National strategic procurement data should not sit on a foreign vendor's platform. |

Expect "why not just buy an MDM tool?" and answer it directly with the federated argument.

**Other honest risks:** spec extraction reliability is the biggest technical risk (validate first);
dataset realism is the biggest demo risk (if the synthetic data looks fake the demo collapses);
the problem is unglamorous and wins on measured numbers, so **lead with money impact**.

---

## 14. Demo design

Do **not** demo obvious duplicates merging — it looks like string matching.

The final 90-second demo is `finalarchitecture.md` §11. The core argument, with the numbers
the system actually produces (the old 0.31 / 0.94 figures in section 2 were illustrative):

1. Two records sharing almost no words (`SKF 6205-2RS...` vs `FAG 6205-2RSR...`).
2. Real-embedding text similarity **0.833** — not low; a text matcher would probably accept it.
3. Extracted specs align field by field; brand deliberately ignored. System matches at **0.971**.
4. **Reverse it:** SS316 vs SS304 — text similarity **0.989**, blocked on grade.
5. **The inversion:** the pair that must never merge scores *higher* than the pair that should.
   No threshold can fix an inverted ordering — so we changed what is measured.
6. *"We match on specifications, not spelling."*

**Never make a live LLM call during a demo.** Pre-extract specs to JSON and have the script read
from it. Venue internet fails; a broken demo erases everything.

---

## 15. Immediate next steps

The day-by-day plan to 27 Sept is `finalarchitecture.md` §12. Status, 24 Sept evening:

1. ✅ **Extraction on real text** (A1, A2) — done; dev two-or-more-facts 3% → 93%.
2. ✅ **Blocking** (A4) — `blocking.py`; skips 99.80% of pairs at 15,000; 83% of true pairs meet
   (98.9% on clean specs - the gap is records missing their identity fields).
3. ✅ **Hard-negative tests** (A5) — `tests/test_hard_negatives.py`, 82 one-field veto cases across all
   14 categories; `evaluate.py` prints veto accuracy per field. The *generated* trap pairs come
   with the item factory in step 4.
4. ✅ **15,000 records, 20% duplication, real notation** (A6) — `run_all.py --run 15k
   --generate 15000`: 860 auto-merges, 0 wrong, 0 traps; dev/test reported separately.
5. **Two-person blind labels of the 417 test rows** — Claude's labels (`claude.csv`, written
   after freeze 1) give today's number; Isha and Meghna still label their own sheets, then
   `python src/labels.py compare --people isha meghna` (or against claude) and `finalise`.
   **Never tune on test rows.** Fixes for issues the test run exposed must be reproduced on dev.
6. ✅ **Review queue as candidates per record** (A10) — one record, its best candidates first.
7. ✅ **Standards equivalence** — IS 1367 (Part 3) / ISO 898-1, ASTM A325 → F3125.
8. ✅ **Numbers locked** (A11) — tag `ppt-numbers-2026-09-25`. After the tag: the deck, the
   two-person labels, a backup demo video. **Nothing new goes into the code before 27 Sept.**
