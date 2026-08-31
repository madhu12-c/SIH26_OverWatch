# One Nation, One Material Code

**Smart India Hackathon 2026 · Problem Statement SIH26099 · Team Overwatch**
Ministry of Petroleum & Natural Gas · Chennai Petroleum Corporation Limited (CPCL)

Ingest messy material master data from multiple CPSEs, work out which records
describe the same physical item, assign one Common National Material Code, and
keep a mapping back to every company's original code.

---

## Start here

| You are | Read |
|---|---|
| New to the project | [`docs/01-project/`](docs/01-project/) — the problem and the one idea that matters |
| Picking up your part | [`docs/06-team/`](docs/06-team/) — find your name, everything you need is in that file |
| Wondering why something is built this way | [`docs/02-decisions/`](docs/02-decisions/) — every decision with its trade-offs |
| Preparing for judges | [`docs/04-risks/`](docs/04-risks/) — what we can and cannot defend |
| Trying to run it | [`docs/05-runbook/`](docs/05-runbook/) |

Full index: [`docs/README.md`](docs/README.md)

---

## The one idea

Two records can describe the same item while sharing almost no words, and two
records can share almost every word while being different items. So text
similarity is the wrong question.

```
"SKF 6205-2RS Deep Groove Ball Bearing"
"FAG 6205-2RSR bearing, 25x52x15mm, sealed"
      text similarity LOW    ->  a fuzzy matcher MISSES it
      reality: same bearing  (6205 is an ISO designation)

"GASKET SPIRAL WOUND SS316 4IN 150#"
"GASKET SPIRAL WOUND SS304 4IN 150#"
      text similarity 0.97   ->  a fuzzy matcher WRONGLY MERGES
      reality: different items (grade matters in corrosive service)
```

We extract structured specifications first, then compare specifications.
Brand is deliberately ignored. Material grade is a veto field.

---

## Folder layout

```
├── README.md              you are here
├── CLAUDE.md              working rules, read before writing code
│
├── docs/                  all documentation
│   ├── 01-project/        what this is and why it is hard
│   ├── 02-decisions/      every decision, with what we rejected
│   ├── 03-reference/      data dictionary, schemas, domain facts
│   ├── 04-risks/          honest limits and judge preparation
│   ├── 05-runbook/        how to run everything
│   └── 06-team/           one file per person
│
├── src/                   pipeline code
│   ├── paths.py           every file path, defined once
│   ├── schemas.py         category schemas, hard blockers, regex fallback
│   ├── generate_dataset.py
│   ├── extractor.py       spec extraction (Gemini + regex fallback)
│   └── embed.py           local embeddings, no API
│
├── data/
│   ├── input/             what a CPSE hands us    (materials, purchases)
│   ├── truth/             the answer key          (evaluation ONLY)
│   └── output/            what each stage produces
│
├── ui/                    React demo frontend
└── deliverables/          architecture doc, PDF, decks
```

---

## Quick run

```bash
python src/generate_dataset.py          # build the dataset
python src/extractor.py --no-llm        # extract specs, no API needed
python src/extractor.py --validate      # hand-check the output
```

With a Gemini key set, `python src/extractor.py` runs the real extraction.
Everything works without one — the regex fallback covers both demo cases.

---

## Current state

| Stage | File | Status |
|---|---|---|
| 00 Dataset | `src/generate_dataset.py` | ✅ 100 records, 15 items, 85% duplication |
| 01 Normalise | `src/schemas.py` | ✅ canonicalisation in place |
| 02 Spec extract | `src/extractor.py` | ✅ built, needs a key for the real run |
| 03 Embeddings | `src/embed.py` | ✅ built, not yet run |
| 04 Blocking | — | ⏭️ skipped at this scale, on purpose |
| 05 Scorer | `src/scorer.py` | ⏳ next |
| 06 Clustering | `src/scorer.py` | ⏳ next |
| 07 Confidence bands | — | ⏳ |
| 08 Canonicaliser | `src/canonicalise.py` | ⏳ |
| 09 Outputs | `src/savings.py`, `src/results.py` | ⏳ |
| UI | `ui/` | ⏳ |

---

## Rules that do not bend

1. **Precision over recall.** A wrong merge can put the wrong valve in a refinery line.
2. **Nothing is destroyed.** Original codes retained, every merge reversible.
3. **Every merge is explainable.** Store which signals and which fields.
4. **The LLM extracts; it never decides a merge.**
5. **One LLM call per record, never per pair.**
6. **No company decides for another.**

The reasoning behind each is in [`docs/02-decisions/`](docs/02-decisions/).

---

## Timeline

- **1 Sept 2026 (Tue)** — college internal round
- **20 Sept 2026** — SIH idea submission (hard deadline)
- **Dec 2026** — Grand Finale, if selected
