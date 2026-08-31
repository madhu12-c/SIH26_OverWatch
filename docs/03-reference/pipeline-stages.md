# Pipeline stages

What each stage takes in, does, and hands on. Stages marked ⏭️ are designed and
documented but deliberately not implemented — see
[decision 007](../02-decisions/007-no-infrastructure-yet.md).

```
raw CSV → [01] normalise → [02] extract specs → [03] embed → [04] block
        → [05] score → [06] cluster → [07] route → [08] canonicalise → [09] output
```

---

## 00 · Ingestion

**In** — `materials.csv` and `purchases.csv` per CPSE. In reality a SAP export.
**Does** — validates columns, tags each row with its source CPSE, stores raw text
exactly as received.
**Out** — `data/input/`
**Rule** — raw is append-only. Nothing after this point modifies it.

---

## 01 · Normaliser

**In** — raw description, raw UoM
**Does** — three rule-based passes, no AI:

- Expand abbreviations: `BRG` → `BEARING`, `M.S.` → `MILD STEEL`, `DP GRV` → `DEEP GROOVE`
- Canonicalise units: `EA`/`NOS`/`NO`/`PCS` → `EACH`, `M`/`MTR`/`MTS` → `METRE`
- Clean text: casing, punctuation, repeated spaces, `Ø` → `DIA`

**Out** — `clean_description`, `canonical_uom`, stored beside the raw values
**Where** — value canonicalisation lives in `src/schemas.py` (`canonical_value`)

⚠️ **Pack sizes.** If one CPSE prices per piece and another per box of 100,
comparing unit prices is wrong. Not yet handled.

---

## 02 · Spec extractor — the critical path

**In** — one cleaned description
**Does** — Gemini call with a per-category schema; returns typed attributes plus
per-field confidence. Falls back to regex on any failure.
**Out** — `data/output/specs.json`
**Where** — `src/extractor.py`

```
"BRG BALL DP GRV 6205 2RS SKF"
  -> { category: "bearing", iso_designation: "6205",
       bore_mm: 25, od_mm: 52, width_mm: 15,
       seal_type: "2RS", brand: "SKF" }
```

Three properties that matter:

- **A separate schema per category.** A pipe schema and a valve schema share
  almost nothing.
- **Per-field confidence.** Stated 0.95+, derived from a standard 0.75–0.94,
  below 0.4 dropped entirely.
- **Never guess.** A fabricated spec that later drives a merge is the worst
  failure this system can produce. Unknown routes to review.

**The rule this stage enforces:** one call per record, at ingestion, cached.
Never per pair. [Decision 002](../02-decisions/002-llm-once-per-record.md).

---

## 03 · Embeddings

**In** — cleaned description
**Does** — `sentence-transformers` with `BAAI/bge-small-en-v1.5`, locally on GPU
or CPU. Vectors normalised so cosine similarity is a dot product.
**Out** — `data/output/embeddings.npz` (ids and vectors together in one file)
**Where** — `src/embed.py`

No API, ever. [Decision 005](../02-decisions/005-local-embeddings-no-api.md).

---

## 04 · Blocking ⏭️ *designed, not built*

**In** — all records with categories and vectors
**Does** — decides which pairs are worth scoring at all.

```
1,000,000 records -> 500,000,000,000 pairs   ~6 days
   group by category            bearings: 12,000
   group by key attribute       bearings, 25mm bore: 300
   plus top-50 nearest vectors
                             -> ~20,000,000 pairs
```

**Two numbers to measure when it is built:**

- **Reduction ratio** — work eliminated. Target above 99.9%.
- **Pair completeness** — true matches surviving. Target above 98%.

Blocking too tightly loses real matches; too loosely wastes time without improving
accuracy. Both numbers move together and must be reported together.

**Why not now:** at 100 records all-pairs is 4,950 comparisons — instant. Build it
past ~5,000 records.

---

## 05 · Hybrid scorer

**In** — candidate pairs, with both records' specs, vectors and purchase history
**Does** — fuses three independent signals into one number.

```
score = w1 * text_sim          weakest  — shortlisting, not deciding
      + w2 * spec_agreement    heaviest — this is the whole idea
      + w3 * procurement_sim   same vendor, price band, order size, plant

any hard blocker -> score = 0
```

**Three rules that matter more than the weights:**

| Rule | Meaning |
|---|---|
| Hard blockers veto | Grade, pressure rating, key dimensions. Instant zero. |
| Ignored fields never count | Brand, part number. This is what lets SKF and FAG match. |
| Missing ≠ mismatched | Silence is absent information, not evidence of difference. |

**Price does double duty** — evidence *for* a match, and a guard *against* one. A
₹42 bolt and a ₹4,200 bolt with identical text and specs are not the same item.

Pure arithmetic. No model call. That is what makes every score reproducible.

**Out** — `pair_scores.json`, each entry carrying its signal breakdown so the
review screen can show *why*.

---

## 06 · Clustering

**In** — pairs above threshold
**Does** — union-find. Each connected group becomes one proposed item.

**The hazard:** A~B, B~C, but A≁C. Connected components groups all three, and one
bridging record can drag hundreds of unrelated items into a blob.

Three defences:

1. High threshold.
2. After forming a group, verify *every* internal pair scores well — not just the
   connected ones. Split if not.
3. Cap cluster size; oversized clusters route to review.

**Out** — `clusters.json`

---

## 07 · Confidence routing

```
above 0.90    auto-merge      logged, reversible
0.70 – 0.90   review queue    a human approves or rejects
below 0.70    leave alone     kept separate
```

Not a workaround for imperfect AI — the PS requires a validation workflow.
Cross-CPSE merges need approval from **both** sides.

The reviewer is a domain expert who already knows SS304 ≠ SS316. The screen must
show all evidence at once and take five seconds per decision, not two minutes.

---

## 08 · Canonicaliser

**In** — an approved cluster
**Does** — four things:

1. **Golden record** — best value per field, by confidence or majority.
2. **Standard description** — noun-modifier template render:
   `BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED`
3. **UNSPSC classification** — `31171500` for bearings. The 20–30 classes we
   touch, not the full taxonomy.
4. **National code** — `NMC-31171500-000042`, with the class embedded.

**Out** — `national_codes.json`, `mappings.csv`

```
national_code          cpse   original_code   status
NMC-31171500-000042    CPCL   100001445       active
NMC-31171500-000042    IOCL   MAT-01248       active
```

Nobody changes their code. The national code sits above the existing ones and
links them — the way Aadhaar and UPI added a layer without replacing what was
underneath.

---

## 09 · Outputs

| Output | What it is |
|---|---|
| **Savings report** | Purchase history grouped by national code. Turns data cleaning into a money project. Give the upper bound *and* a conservative figure. |
| **Safety interlock report** | Count of merges refused, by rule. Everyone shows merges; nobody shows refusals. |
| **Audit log** | Who, when, what, reversible. Not optional for government data. Designed, not yet built. |
| **Dashboard** | Duplication rate, queue depth, savings. One slide. |
| **Export API** | Mapping file loadable through SAP migration tooling, plus an adapter interface. |
| **`results.json`** | Everything the UI reads, in one bundle. |
