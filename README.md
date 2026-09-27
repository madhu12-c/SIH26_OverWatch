# One Nation, One Material Code

**Smart India Hackathon 2026 · Problem Statement SIH26099 · Team Overwatch**
Ministry of Petroleum & Natural Gas · Chennai Petroleum Corporation Limited (CPCL)

A national material-code registry for CPSEs. It reads each company's material master,
works out which records describe the same physical item — by comparing **specifications,
not spelling** — issues one National Material Code per item, and links every original
code to it. No company's code is changed or deleted.

---

## What the numbers in this repository mean

Every figure here is measured on data we generated, unless it is marked **real**.
Synthetic numbers measure how well the system undoes errors we introduced ourselves, so
they are always reported beside the real ones and never alone.

No figure in this repository is a production accuracy claim. The system has not been
connected to a live SAP instance, and no real multi-company material master was available
to test on — none is public.

---

## Start here

| You are | Read |
|---|---|
| **Anyone** | [`finalarchitecture.md`](finalarchitecture.md) — the final design: pipeline, features, rules, data, evaluation, PPT |
| **Building something** | [`buildplan.md`](buildplan.md) — one design card per feature: where it goes, how it works, when it's done, who owns it |
| Writing code | [`CLAUDE.md`](CLAUDE.md) — working rules and the decision record |
| Trying to run it | [Run it](#run-it), below |

---

## The one idea

Two records can describe the same item while sharing almost no words, and two records can
share almost every word while being different items. Measured on this system's own
embeddings:

```
SKF 6205-2RS DEEP GROOVE BALL BEARING
FAG 6205-2RSR BEARING, 25X52X15MM, SEALED
      text similarity 0.833     reality: SAME bearing — 6205 is an ISO designation

GASKET SPIRAL WOUND SS316 4IN 150#
GASKET SPIRAL WOUND SS304 4IN 150#
      text similarity 0.989     reality: DIFFERENT items — grade matters in corrosive service
```

The pair that must never merge scores *higher* than the pair that should. No threshold can
fix an inverted ordering. So we extract structured specifications first and compare those.
Brand is deliberately ignored. Material grade is a veto.

---

## Folder layout

```
├── README.md              you are here
├── finalarchitecture.md   the final design — start here
├── buildplan.md           how each feature gets built, card by card
├── CLAUDE.md              working rules and decision record
│
├── src/                   pipeline
│   ├── paths.py           every file path, defined once
│   ├── schemas.py         category schemas, hard blockers, derive()
│   ├── normalise.py       real-text cleanup, size tables (DN/NPS/OD), grade-family ladder
│   ├── rules.py           rule reader for real text — sizes, grades, pressure, evidence spans
│   ├── generate_dataset.py
│   ├── extractor.py       spec extraction — Gemini, with an offline regex fallback
│   ├── embed.py           local embeddings, no API
│   ├── blocking.py        candidate pairs: signature keys + meta-blocking, no all-pairs
│   ├── scorer.py          veto-first hybrid scorer and clustering
│   ├── evaluate.py        precision / recall against the answer key, 95% error bound
│   ├── baselines.py       fuzzy, TF-IDF and embedding matchers vs ours, same pairs
│   ├── selfcheck.py       a record checked against itself (6205 with a 6206's size)
│   ├── canonicalise.py    golden record, description, UNSPSC, national code
│   ├── savings.py         demand aggregation with k-anonymity
│   ├── uom.py             unit-of-measure harmonisation
│   ├── gate.py            the creation gate
│   ├── mine_real.py       builds the real hold-out candidates
│   ├── standards.py       ISO 15 bearings, B36.10 pipe walls, IEC motor frames
│   ├── catalogue.py       item factory - 11,815 valid refinery items for big runs
│   ├── render.py          writes an item the way NTPC / Oil India / SAP write it
│   ├── run_all.py         the whole chain, one command, per run
│   ├── labels.py          dev/test split, one sheet per labeller, agreement
│   ├── real_eval.py       real-text coverage (dev), the frozen-code test result, --freeze
│   ├── real_view.py       the "Real tender text" page, from dev rows only
│   ├── govern.py          verify the sealed audit log and replay it under the consent rules
│   ├── evidence.py        every headline number from every dataset, stamped
│   └── results.py         bundles everything the UI reads
│
├── tests/                 python -m pytest tests/ — must pass before any scorer or schema change
├── data/
│   ├── input/             what a CPSE hands us       (materials, purchases)
│   ├── truth/             the answer key             (evaluation ONLY)
│   ├── real/              real CPSE tender text      (Oil India, NTPC — CC-BY-4.0)
│   └── output/            what each stage produces
│
└── ui/                    React portal — role sign-in, dashboard, analytics, catalogue, audit; offline, one file
```

---

## Run it

One command runs everything:

```bash
python src/run_all.py --tests                               # the 100-record demo set
python src/run_all.py --run 15k --generate 15000 --tests    # 15,000 records (data/runs/15k, ~4 min)
```

Step by step (the demo set):

```bash
python src/generate_dataset.py
python src/extractor.py --no-llm --fresh   # --fresh after every regeneration: specs.json is a cache
python src/embed.py                        # optional — a lexical fallback is used without it
python src/scorer.py                       # blocking on by default; --all-pairs to compare
python src/canonicalise.py
python src/savings.py
python src/evaluate.py
python src/uom.py
python src/gate.py --scenarios
python src/results.py                      # writes data/output/results.json and ui/src/results.json
python src/real_eval.py                    # real-text coverage on the dev half
python -m pytest tests/                    # the safety suite

cd ui && npm install && npm run build      # then open ui/dist/index.html — no server, no internet
```

With a Gemini key set, drop `--no-llm` for the full extraction. Nothing on the demo path
makes a live model call.

---

## Current state

| Stage | File | Status |
|---|---|---|
| Dataset | `generate_dataset.py`, `catalogue.py`, `render.py` | ✅ 100-record demo · 15,000-record run in real notation (`SIH_RUN=15k`) |
| Normalise + extract | `normalise.py`, `rules.py`, `extractor.py` | ✅ reads real CPSE text — dev 2+ facts 96%, real test 90% |
| Embeddings | `embed.py` | ✅ |
| Blocking | `blocking.py` | ✅ identity keys + meta-blocking: skips 99.8% of pairs at 15,000 |
| Veto-first scorer + clustering | `scorer.py` | ✅ with a "what if" score on every refused pair |
| Self-check | `selfcheck.py` | ✅ a line that contradicts itself never auto-merges; 0 false alarms on 308 real dev lines |
| Cross-standard equivalence | `standards.py` | ✅ IS 1367 = ISO 898-1; A325 → F3125 (superseded); 8.8 ≈ A325 goes to a person |
| Canonicaliser, UNSPSC, national codes | `canonicalise.py` | ✅ |
| Savings with k-anonymity | `savings.py` | ✅ |
| Units harmonisation | `uom.py` | ✅ |
| Creation gate | `gate.py` | ✅ five verdicts, including CONTRADICTS |
| Evaluation | `evaluate.py`, `baselines.py`, `real_eval.py` | ✅ 15,000 run: 860 auto-merges, **0 wrong** (< 0.35% at 95%), 0 of 104,994 traps · text matchers 6–8% right at their best · real test (freeze 2): 0 wrong, 83% found |
| Safety tests | `tests/` | ✅ 292 pass — veto cases, self-check, equivalence, sealed audit log |
| Portal UI | `ui/` | ✅ role sign-in + 12 pages: evidence panel, review queue by record, real tender text, sealed audit trail, SAP-shaped export |
| Governance | `govern.py` | ✅ hash-chained log, tamper test, replay refuses what the consent rules forbid |
| Five relationships · staged migration pack · data-quality scorecard | — | ⏳ see `finalarchitecture.md` §12 |

---

## Rules that do not bend

1. **Precision over recall.** A wrong merge can put the wrong valve in a refinery line.
2. **Nothing is destroyed.** Original codes retained; every merge reversible.
3. **Every merge is explainable.** Which signals, which fields, which source text.
4. **The AI reads; it never decides a merge.** One model call per record, never per pair.
5. **Veto before score.** A missing value is unknown — never agreement, never conflict.
6. **Consent scales with harm.** Linking codes needs no permission; retiring a code is only
   ever its owner's decision; any company can dispute a link at any time.

---

## Data credit

The real hold-out in `data/real/` is derived from
[`Prasenjeet25/sih26099-cpse-material-codes`](https://huggingface.co/datasets/Prasenjeet25/sih26099-cpse-material-codes)
on Hugging Face, licensed **CC-BY-4.0**. See [`data/real/README.md`](data/real/README.md).

---

## Timeline

- **27 Sept 2026** — SIH idea submission
- **Dec 2026** — Grand Finale, if selected
