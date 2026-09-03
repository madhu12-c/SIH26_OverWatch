# CLAUDE.md — One Nation, One Material Code

> Working instructions for this repo. Read fully before writing code.
> Companion document: `architecture.html` / `Architecture.pdf` — the full stage-by-stage
> flow, written in plain English for the whole team. This file is the decision record.

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
docs/                     full documentation, indexed at docs/README.md
  01-project/             problem, core idea, glossary
  02-decisions/           every decision with what we rejected  <- read before changing anything
  03-reference/           data dictionary, pipeline stages, schemas, domain facts
  04-risks/               honest limits, technical + demo risks, judge Q&A
  05-runbook/             setup, running, demo day
  06-team/                one self-serve file per person
src/                      paths.py, schemas.py, generate_dataset.py, extractor.py, embed.py,
                          scorer.py, evaluate.py, canonicalise.py, savings.py, uom.py,
                          gate.py, results.py
data/input/               materials.csv, purchases.csv        (what a CPSE gives us)
data/truth/               ground_truth.csv, traps.json        (evaluation ONLY, never the pipeline)
data/output/              specs.json, embeddings.npz, uom.json, gate.json, ... (regenerable)
ui/                       React demo frontend — eight screens
deliverables/             architecture doc, PDF, decks
```

**Built and working — the pipeline runs end to end.** Dataset generator (100 records, 15 items,
84% duplication, 245 POs), category schemas with hard blockers, spec extractor (Gemini + regex
fallback, cached, resumable), local embeddings, hybrid scorer, clustering, evaluation harness,
canonicaliser, savings report, UoM harmonisation, creation gate, and an eight-screen React UI.
Both demo cases pass on the regex fallback alone — no API, no internet.

Current measured numbers (`data/output/metrics.json`): precision 1.0, recall 0.942, 177 auto-merged
pairs, 0 false merges, 0 trap violations, 282 safety blocks, 100 raw → 16 unique (84% duplication).
Savings: ₹22.6 cr total spend, ₹1.79 cr upper / ₹0.72 cr realistic, k-anonymity 3.

**Not yet built:** `run_all.py`; the audit trail and cross-CPSE dual approval (PS Capability 7 —
the only genuine zero); the migration pack and ERP export (Capabilities 5 and 8); learned
abbreviation vocabulary (differentiator D).

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
- **No company decides for another.** Within one CPSE, that company's reviewer decides alone.
  Across two CPSEs, both sides must approve before a national code is issued.

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
- **1 Sept 2026 (Tue)** — college internal round. Deliverable is a **PPT**; a working demo is a
  large bonus. **Still unconfirmed: is a live demo allowed, and what is the time limit?** Confirm
  with the SPOC.
- **20 Sept 2026** — SIH idea submission deadline (hard)
- **Dec 2026** — Grand Finale (if selected)

**The real risk is October.** After the 20 Sept submission there is a dead zone — submission done,
finale far away, semester exams. Most SIH teams lose there, not in December. Keep a weekly
checkpoint through Oct–Nov, however small.

Post-internal priority: **savings report → real hold-out labelling → federated layer → review UI
polish.** December is for rehearsal only, not new features.

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

1. Two records sharing almost no words (`SKF 6205-2RS...` vs `FAG 6205-2RSR...`).
2. Plain text similarity scores 0.31 — a fuzzy matcher stops here.
3. Extracted specs align field by field; brand deliberately ignored.
4. System matches at 0.94.
5. **Reverse it:** SS304 vs SS316 — 0.97 text similarity, blocked on grade mismatch.
6. *"A conventional fuzzy-matching tool misses the first and wrongly merges the second. We match
   on specifications, not spelling."*
7. Headline numbers: N raw → M unique, X% duplication, precision/recall, and rupees saved.

**Never make a live LLM call during a demo.** Pre-extract specs to JSON and have the script read
from it. Venue internet fails; a broken demo erases everything.

---

## 15. Immediate next steps

1. **Confirm internal round format with the SPOC** — demo allowed? time limit?
2. Rebuild `generate_dataset.py` + the three CSVs, with `SEED_ITEMS` expanded to real
   refinery-weighted nomenclature.
3. Build the spec extractor and validate on 50 records by hand.
4. Build the evaluation harness against `ground_truth.csv`.
5. Savings report from `purchases.csv` — one day, highest payoff.
6. Then proceed down the build order in section 6.
