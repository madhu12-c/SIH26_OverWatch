# Running the pipeline

Every command, in order. Run from the **project root**, not from inside `src/`.

---

## The whole thing

```bash
python src/generate_dataset.py          # 00  dataset
python src/extractor.py --fresh         # 02  specs      (needs GEMINI_API_KEY)
python src/embed.py                     # 03  vectors
python src/scorer.py                    # 05  scores + clusters      [not built]
python src/evaluate.py                  # --  precision / recall     [not built]
python src/canonicalise.py              # 08  national codes         [not built]
python src/savings.py                   # 09  savings report         [not built]
python src/results.py                   # 09  bundle for the UI      [not built]
```

Eventually `python src/run_all.py` does all of it.

---

## 00 · Dataset

```bash
python src/generate_dataset.py
```

```
materials.csv       100 records
ground_truth.csv    100 rows, 15 true items
purchases.csv       245 purchase orders
traps.json            4 deliberate near-miss pairs
duplication rate  85.0%   (100 raw -> 15 unique)
```

| Flag | Effect |
|---|---|
| `--target 600` | More records |
| `--seed 12345` | Different dataset. **Keep the default for demos** — determinism is why the demo never changes. |
| `--seed-file path.csv` | Use a researched item list. Picks up `data/input/seed_items.csv` automatically if present. |

⚠️ **After this, always re-extract with `--fresh`.** `specs.json` is keyed by
`record_id`, and regenerating produces new ids. Running on a stale cache gives
silently wrong numbers, and it has already happened once.

---

## 02 · Spec extraction

```bash
set GEMINI_API_KEY=your_key_here
python src/extractor.py --limit 10       # always sanity-check first
python src/extractor.py                  # full run, ~7 min at free-tier pace
```

| Flag | Effect |
|---|---|
| `--limit N` | First N records only |
| `--no-llm` | Regex only. No network, no key. |
| `--fresh` | Ignore the cache and re-extract |
| `--validate` | Print the hand-checkable view |
| `--model X` | Override the model |

**Resumable.** Interrupt it and re-run; records already in `specs.json` are
skipped. Costs nothing to resume.

### Hand-check before trusting anything downstream

```bash
python src/extractor.py --validate
```

```
R00003  [gasket]  via llm
  GASKET SPIRAL WOUND SS316 4IN 150#
    * material_grade     SS316         0.98 #########
    * nominal_size_in    4.0           0.97 #########
    * pressure_class     150#          0.96 #########
      gasket_type        spiral_wound  0.95 #########

  * = hard blocker
```

Read 50 records against their source text. Look for:

- Fields present that are **not** in the description — the worst failure
- Confidence that does not match reality (a derived value marked 0.98)
- Wrong category
- Anything in `dropped_fields`

This is build-order step 1. Nothing downstream is trustworthy until it passes.

---

## 03 · Embeddings

```bash
python src/embed.py --check     # verify GPU first
python src/embed.py
```

Ends by printing real cosine similarity for both demo pairs. **Those two numbers
go in the deck** — the 0.31 and 0.97 currently quoted are placeholders.

If the gap comes out small, or backwards, the demo narrative is wrong. The script
says so explicitly.

---

## 05–09 · Not yet built

| Stage | File | Produces |
|---|---|---|
| Scorer + clustering | `src/scorer.py` | `pair_scores.json`, `clusters.json` |
| Evaluation | `src/evaluate.py` | precision, recall, duplication, trap violations |
| Canonicaliser | `src/canonicalise.py` | `national_codes.json`, `mappings.csv` |
| Savings | `src/savings.py` | `savings.json` |
| Bundle | `src/results.py` | `results.json` for the UI |

Contracts for each: [`../06-team/README.md`](../06-team/README.md)

---

## UI

```bash
cd ui
npm run build
```

Then **double-click `ui/dist/index.html`** — do not only test `npm run dev`.

---

## Quick checks

**Both demo cases still work:**
```bash
python src/extractor.py --validate --limit 4
```
R00001 and R00002 should both show `iso_designation 6205`.
R00003 and R00004 should show `SS316` and `SS304`.

**Dataset does not look fake:**
```bash
grep -cE '[A-Z]"[A-Z]' data/input/materials.csv     # expect 0
```

**Full reset:**
```bash
rm -rf data/output/*
python src/generate_dataset.py
python src/extractor.py --no-llm --fresh
```

---

## Where things live

```
data/input/    materials.csv, purchases.csv, seed_items.csv
data/truth/    ground_truth.csv, traps.json      <- evaluation ONLY
data/output/   specs.json, embeddings.npz, ...   <- safe to delete
```

Paths are defined once in [`src/paths.py`](../../src/paths.py).
