# Data dictionary

Every file, every column, where it comes from, and who is allowed to read it.

Paths are defined once in [`src/paths.py`](../../src/paths.py). No other module
builds a path from string pieces.

---

## The three data folders, and the rule they encode

```
data/input/    what a CPSE hands us.  Read-only to the pipeline.
data/truth/    the answer key.        Read ONLY by evaluation.
data/output/   what each stage makes. Safe to delete and regenerate.
```

The separation exists to make one rule hard to break by accident: **a matcher
that has seen `ground_truth.csv` is cheating, and its precision number is
worthless.** Keeping truth in its own folder means an accidental import is
visible in code review.

---

## `data/input/materials.csv` — 100 rows

What a CPSE gives us. In reality this is a SAP export: a store manager runs a
report and gets a CSV.

| Column | Type | Meaning | SAP source |
|---|---|---|---|
| `record_id` | `R00001` | **Our** internal id | — does not exist in SAP, we assign it |
| `cpse` | `CPCL` | Which company | the file's origin |
| `source_code` | `100001445` | **The CPSE's own material code** | `MARA-MATNR` |
| `description` | free text | The messy one-line description | `MAKT-MAKTX` |
| `uom` | `EA` `NOS` `MTR` | Unit of measurement | `MARA-MEINS` |
| `material_group` | `BEARING` | The CPSE's own category | `MARA-MATKL` |
| `plant` | `Manali` | Which plant | `MARC-WERKS` |

**Two things to know:**

`source_code` format differs per CPSE, deliberately — this is half the real
problem:

```
CPCL   100001445    9-digit numeric
IOCL   MAT-01248    prefix + number
ONGC   5001035      7-digit numeric
BPCL   BR-01454     different prefix
GAIL   G/001290     slash format
```

**`material_group` is not trusted.** In real masters this column is inconsistent —
assigned by whoever created the record, with no enforcement. The extractor infers
the category from the description instead and ignores this column entirely.

---

## `data/input/purchases.csv` — 245 rows

Purchase order history. Multiple rows per material — a material is bought many
times, from different vendors, at different prices.

| Column | Type | Meaning | Used by |
|---|---|---|---|
| `cpse` | `CPCL` | Which company | join key |
| `source_code` | `100001445` | The material code | join key |
| `vendor` | `SKF India Ltd` | Supplier name | signal 3 |
| `unit_price` | `1332.76` | Price per UoM, INR | signal 3 **and** false-merge guard |
| `qty` | `200` | Order quantity | order-size band, savings |
| `po_date` | `2025-09-18` | Purchase order date | trend, dead-stock flag |
| `plant` | `Cauvery Basin` | Delivery plant | signal 3 |

**The join is `(cpse, source_code)`, not `record_id`.** In reality a purchase
order references the CPSE's material code, not our internal id — so the join key
has to be the thing that exists in both systems.

**`unit_price` does two jobs.** It is evidence *for* a match (similar prices,
same vendor) and evidence *against* one — a ₹42 bolt and a ₹4,200 bolt with
identical text and identical specs cannot be the same item.

---

## `data/truth/ground_truth.csv` — 100 rows

The answer key. Exists **only** because we generated the data.

| Column | Meaning |
|---|---|
| `record_id` | `R00001` |
| `true_item_id` | `ITM-001` — which real item this record came from |

```
✅ evaluate.py       reads it, to measure accuracy
❌ extractor.py      never
❌ scorer.py         never
❌ clustering        never
```

A real CPSE extract has no equivalent file. That is exactly why most teams can
only show a demo, and we can report numbers — and also why our numbers carry the
caveat in [`../04-risks/honest-limits.md`](../04-risks/honest-limits.md).

---

## `data/truth/traps.json` — 4 pairs

Deliberate near-misses. Pairs that must **never** merge.

```json
{ "a": "ITM-003", "b": "ITM-004",
  "reason": "material grade mismatch (SS316 vs SS304)" }
```

| Pair | Difference | Consequence if merged |
|---|---|---|
| ITM-003 / ITM-004 | SS316 vs SS304 | Corrosion, leak |
| ITM-007 / ITM-008 | 150# vs 300# | Joint failure |
| ITM-001 / ITM-002 | 6205 vs 6206 | Bearing does not fit |
| ITM-005 / ITM-006 | Carbon steel vs SS316 pipe | Corrosion |

Two uses: as a **test** — any merge across these is a false merge and should raise
an alarm — and as the source of the **safety interlock report**.

---

## `data/output/specs.json` — extractor output

Keyed by `record_id`. JSON rather than CSV because each category has different
fields.

```json
"R00003": {
  "category": "gasket",
  "attributes":  { "material_grade": "SS316",
                   "nominal_size_in": 4.0,
                   "pressure_class": "150#" },
  "confidence":  { "material_grade": 0.62, ... },
  "method": "regex",
  "dropped_fields": [],
  "record_id": "R00003", "cpse": "ONGC", "source_code": "5001035"
}
```

| Key | Meaning |
|---|---|
| `category` | Inferred from the description, not from `material_group` |
| `attributes` | Only fields valid for that category — anything else is discarded as hallucination |
| `confidence` | Per field. 0.95+ stated, 0.75–0.94 derived from a standard, below 0.4 dropped |
| `method` | `llm` or `regex` — which path produced this |
| `dropped_fields` | Fields the model returned that are not in the schema |

**This file is also the LLM cache.** A record already present is never re-extracted.
Use `--fresh` after regenerating the dataset, or the specs will describe records
that no longer exist.

---

## `data/output/embeddings.npz`

| Array | Shape | Contents |
|---|---|---|
| `ids` | (100,) | record ids, in row order |
| `vectors` | (100, 384) | normalised embedding per record |

Ids and vectors are in **one file** on purpose. Two files can drift out of order,
and an off-by-one there corrupts every score downstream with no visible error.

Read it with `embed.load_embeddings()`, which returns a lookup — never index by
position.

---

## Files not yet produced

| File | Stage | Produced by |
|---|---|---|
| `pair_scores.json` | 05 scorer | every scored pair, plus the signal values behind it |
| `clusters.json` | 06 clustering | groups of records that are one item |
| `national_codes.json` | 08 canonicaliser | golden record, standard description, UNSPSC |
| `mappings.csv` | 08 canonicaliser | national code ↔ every CPSE source code |
| `savings.json` | 09 savings | per-item multi-CPSE spend analysis |
| `results.json` | 09 | everything the UI reads, in one bundle |

---

## How it all joins

```
materials.csv ──┐
  (cpse, source_code) ──── purchases.csv
  record_id ────┐
                ↓ extractor.py
          specs.json  (record_id -> attributes)
                ↓ embed.py
          embeddings.npz  (record_id -> vector)
                ↓ scorer.py
          pair_scores.json -> clusters.json
                ↓ canonicalise.py
          national_codes.json + mappings.csv
                ↓
          results.json  ->  ui/

ground_truth.csv ──→ evaluate.py ONLY
traps.json       ──→ evaluate.py + safety report
```
