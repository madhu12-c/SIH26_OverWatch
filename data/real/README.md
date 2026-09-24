# data/real — the real CPSE hold-out

## Source and licence

Derived from **[`Prasenjeet25/sih26099-cpse-material-codes`](https://huggingface.co/datasets/Prasenjeet25/sih26099-cpse-material-codes)**
on Hugging Face, published by Prasenjeet25, collected 8 September 2026, licensed
**[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)**.

**Changes made:** material-like lines were extracted from four of the dataset's CSV files,
ranked by `src/mine_real.py`, deduplicated, and given two new columns, `rank` and `score`.
The source text itself is unchanged.

## What is here

| File | What |
|---|---|
| `candidates.csv` | 902 distinct real material lines, ranked for reading order. No labels |
| `labels/split.csv` | which rows are **dev** (485) and which are **test** (417). Frozen |
| `labels/dev.csv` | dev rows, labelled on 24 Sept 2026 by Claude while building the extractor fix |
| `labels/isha.csv`, `labels/meghna.csv` | test rows, blank. One sheet each; never open the other's |
| `labels/disagreements.csv` | written by `labels.py compare`; decisions filled in together |
| `labels/final.csv` | written by `labels.py finalise` — **the real-data answer key** |
| `source/` | the downloaded source extracts — not committed; re-fetched by the script |

| Company | Rows | Character |
|---|---|---|
| Oil India | 546 | oil & gas — line pipe, casing, valves, flanges, wellhead. Same ministry as this PS |
| NTPC | 351 | power — cable, motors, pipe, structural |
| IOCL | 5 | procurement-plan equipment groups |

This is **real tender text from two CPSEs**. It is **not** a material master, and must never
be described as one.

Most of the 21,513-row `material_description_corpus.csv` is tender notices and service
contracts. A few hundred of its Oil India lines are genuine item descriptions — those are the
Oil India rows here.

**Expect cleaning.** Many rows are several items joined into one tender line
(`FLANGE SLIP ON SIZE: 10" , FLANGE SLIP ON SIZE: 8" , …`) or begin with tender phrasing
(`Supply of …`, `Bids for the supply of …`). Don't edit the text. Label the row as it is:
`m` for several items, `y` if tender wording wraps a single item. The item text inside is real.

Every row carries a `source` file name. The original documents are in the Hugging Face
dataset, so any line can be checked against the tender it came from.

## How it was built

```bash
python src/mine_real.py
```

The ranking is a keyword heuristic, not a classifier. It lets some junk through and misses
some real lines. **Nothing it emits is trusted until a person has read it.**

## Two halves, two jobs

| Half | Rows | Labelled by | Used for | Reported as a result? |
|---|---|---|---|---|
| **dev** | 485 | Claude, while building | fixing the extractor — patterns may be written from these rows | **Never** |
| **test** | 417 | Isha and Meghna, separately | the real-data number on the slide | **Yes** |

**Why the builder can't label the proof set.** If whoever writes the extractor also writes
its answer key, the test only measures that author agreeing with themselves. That's the
same circularity the synthetic data has. Rows read during the design work (the first 30, a
random 25, one lookup, and 12 that a tool test printed) were put in dev by rule. The rest were split on a hash of their
text. `src/labels.py` holds the rule.

**Nobody tunes on test rows.** Don't open a test row to see why the extractor missed it.
Find the same pattern in dev instead.

## Labelling protocol (test half)

```bash
python src/labels.py start      # already run on 24 Sept 2026 - sheets exist
python src/labels.py compare    # after both have labelled
python src/labels.py finalise   # after every disagreement has a decision
```

1. **Two people, working separately.** Each opens only their own sheet. No discussion
   until both have finished.
2. Work from the top down. Fill four columns:

   | Column | Write |
   |---|---|
   | `keep` | `y` names one specific item a storekeeper could stock, even if under-specified · `n` not an item: tender wording, works, a service, a clause, a heading, a vendor name, or a **class or range** ("up to 1.1 kV", "> 200 KVA") · `m` two or more **different** items in one line · `?` unsure, and say why in `notes` |
   | `category` | for `y` rows: bearing · gasket · pipe · valve · fastener · flange · rotating · instrument · electrical · cable · fitting · plate · tube · other |
   | `group` | the same tag (`G1`, `G2`, …) on `y` rows that are the **same physical item**. Leave it blank if a row has no twin. Your tags don't need to match the other person's |
   | `notes` | anything worth saying |

3. **Grouping rule.** Rows are the same item when every stated fact agrees and the main
   size is stated. A line that only adds a quantity, an internal code or a stray fragment
   is still the same item. Two rows with **no size at all** ("TMT steel bar") are never
   grouped, because nobody can say they're the same.
4. **Tip:** once `keep` is done, sort the sheet by `description` so near-identical lines sit
   together, then assign groups. Sorting is fine because `id` travels with each row.
5. Save as **CSV UTF-8**. The script also accepts a plain Excel CSV.
6. Run `compare`. It checks for typos, prints agreement (Cohen's kappa), and writes
   `disagreements.csv`. Sit together, fill in `decision` and `reason` for every row,
   then run `finalise`. The disagreement log is part of the result.
7. Target: all 417 test rows. About a third are quick `n` rows.

## Worked examples (from dev rows)

| Line | keep | category | Why |
|---|---|---|---|
| `PIPE, BLK, CS, FE410, 9.5MM, 508MM, 500MM` | y | pipe | one pipe: wall 9.5, OD 508, 500 NB |
| `M1613517861_ PIPE, BLK, CS, FE410, 9.5MM, 508MM, 500MM` | y | pipe | the same pipe with an NTPC code in front → **same group** |
| `PIPE, BLK, CS, FE410, 9.5MM, 457MM, 450MM` | y | pipe | 457 not 508: a **different** pipe, and a perfect near-miss |
| `Line Pipe, 4", Seamless, B/E, 12.66 PPF` and `Line Pipe 101.60 mm Seamless, B/E, 12.66 PPF` | y | pipe | **same group**, but only the weight proves it. 101.6 mm is either "4 inch" converted as a measurement or the real outside diameter of a 3½-inch pipe. 12.66 lb/ft fits only the 4-inch one |
| `FLANGE SLIP ON SIZE: 10" , FLANGE SLIP ON SIZE: 8" , …` | m | — | several different flanges |
| `PIPE,TP304L,SMLS,SCH80,5000-7000MM,20MM , PIPE` | y | pipe | one item plus a stray fragment of the next row |
| `Distribution Transformer, 3 Phase, 11 kV > 200 KVA up to and Including 2500 KVA` | n | — | a class of transformers, not one |
| `Providing fencing at Executive Bungalows area …` | n | — | works contract |
| `API 6A Gate Valve, 352 Kg/Sq.cm. W.P.` | y | valve | a real item, under-specified (no size) |

## What the dev half shows (24 Sept 2026)

These describe the data. They aren't results.

- **64%** of dev rows are real material lines (`y`), **14%** join several items (`m`), and **22%**
  aren't material lines at all.
- Oil India gives 190 `y` rows, NTPC 117 and IOCL 1.
- **36% of real material lines (110 of 308) fall outside all 13 categories** (drilling equipment,
  batteries, bushings, wire rope, pumps). The "other" path needs to be useful, not a dead end.
- **32 same-item groups**, 74 rows in all. Several are one item repeated across tenders.
  Others are one NTPC code appearing in several documents.
- The extractor as it was found the category for 87% of in-scope rows but got **two or more
  facts from only 3%**. Pipes: 0 of 77. Valves: 0 of 25. After A1/A2 (24 Sept evening):
  category 99%, two or more facts **93%**, pipes 92%, valves 88% — dev numbers, built against,
  never reported as results.

## The code freeze and the test result (24 Sept 2026, evening)

Before any test row was opened, the code that reads and scores real text was fingerprinted
in `labels/frozen.json` (SHA-256 of `normalise.py`, `rules.py`, `schemas.py`, `scorer.py`,
`blocking.py`, `extractor.py`). `python src/real_eval.py --test <labeller>` refuses to run if
any of those files has changed since, so a test number can never come from code tuned on test
rows.

The test rows were then labelled by Claude into `labels/claude.csv` (252 `y`, 96 `n`, 68 `m`,
1 `?`; 38 same-item groups, 86 rows). **Caveat:** Claude also wrote the extractor, so this is
one labeller, the builder — better than nothing, weaker than the protocol. `isha.csv` and
`meghna.csv` are untouched; their blind labels replace these when done.

| Frozen code on 252 test material lines | Result |
|---|---|
| category right (145 lines inside the categories) | **97.9%** |
| two or more facts read | **86.9%** |
| auto-merged pairs | **4 — 0 wrong** |
| true same-item pairs found (auto + review) | **51 of 59 — recall 86.4%** |
| review-queue precision | **17.8%** — 196 of 235 false proposals have a safety field silent on one side |
| true pairs wrongly vetoed | 6 (reading slips: `(1.6X 2500X 1250MM)`, `1.13 16 inchs`, a bracketed inch restating an OD, a truncated fragment) |

These issues are recorded, not fixed: fixing them now would be tuning on the test rows.
Each must be reproduced on a dev row first; the fixed code gets a new freeze and its test
number is reported as post-freeze.

## Rule

Everything in `labels/` is an **answer key**. Like `data/truth/`, it is read by evaluation
only, never by any matching stage. A matcher that has seen the answers has a worthless
score.

`src/mine_real.py` refuses to rebuild `candidates.csv` once `labels/` holds a sheet,
because the sheets are keyed to its ranks.
