# BUILD PLAN — Overwatch · SIH26099

**Written 24 Sept 2026.** `finalarchitecture.md` says **what** we build. This file says **how**:
one design card per feature, with where it goes in the code, how it works, how we know it's
done, who owns it and what it waits on.

**How to use it.**
- Work top to bottom. Phase A before 27 Sept, Phase B in October, Phase C in November,
  Phase D in December.
- Every card ends in a **Done when** test. A card is done only when that test passes on
  the owner's machine. "It works on my laptop" without the test isn't done.
- **Madhu is on the PPT from 24 Sept.** Any code card can be handed to Claude with the card
  as the brief. The owner reviews the change and runs the Done-when test.
- Every burst of work ends at a working checkpoint: demo cases pass and `run_all.py` runs
  clean. Assume a two-week gap may follow.

---

## 0. Where we stand — measured 24 Sept 2026

| What | Number | Source |
|---|---|---|
| Synthetic, 100 records | precision 1.00 · recall **1.00** (was 0.942) · 0 false merges · 181 auto-merged · 15 clusters = truth | `data/output/metrics.json` |
| Real lines mined | 902 (Oil India 546 · NTPC 351 · IOCL 5) | `data/real/candidates.csv` |
| Real split | dev 485 (labelled) · test 417 (labelled by Claude **after the code freeze**; Isha and Meghna sheets still blank) | `data/real/labels/split.csv`, `frozen.json` |
| Dev: real material lines | 308 of 485 · 110 of those (36%) fall outside our 13 categories | `labels.py report` |
| Dev: same-item groups | 32 groups, 74 rows | `labels.py report` |
| Extractor on dev material lines — before | category right 87% · two or more facts 3% · pipes 0 of 77 · valves 0 of 25 | measured against dev labels |
| **Extractor on dev — after A1/A2** | category right **99%** · two or more facts **93%** · pipes **92%** · valves **88%** | `python src/real_eval.py` |
| **Blocking at 15,000 records** | skips **99.80%** of pairs · **82%** of true pairs meet on real-notation records (98.9% on clean specs) | `run_all.py --run 15k`, `tests/test_blocking.py` |
| **Real TEST result (frozen code)** | category **97.9%** · 2+ facts **86.9%** · 4 auto-merged, **0 wrong** · recall **86.4%** · review precision **17.8%** | `python src/real_eval.py --test claude` |
| Tests | **256 pass** — real reading, real pairs, blocking at 15,000, 82 one-field veto cases | `python -m pytest tests/` |

**Done 24 Sept evening:** A1, A2, A4, A5 (tests; generated traps come with A6), and a first
A9 (`real_eval.py --test`). **Done 24 Sept late: A6** — see the A6 card's status.
**Done 24 Sept night, pulled forward from Phase B/C:** C2 error bound (auto-merge error < 0.35%
with 95% confidence at 15,000) and B2 counterfactual (stored on every blocked pair and on review
pairs held only by an unconfirmed field; shown on the Block screen). All work committed on
branch `feat/real-text-15k-run`. The one weak real number is review precision: 196 of 235 false
proposals are pairs where a safety field is stated on one side and silent on the other — see §7.

Dev numbers are **never** reported as results. They're what we build against. The
reportable real number comes from the **test** half once Isha and Meghna have labelled it.

---

## 1. Critical path

```
A1 read real text ─┬─> A6 15,000 records ──┐
A2 categories ─────┘                        │
A4 blocking ───────────> A6 ────────────────┼─> A11 numbers frozen (Thu night) ─> PPT slides 4-5
A5 traps + tests ──────> A6 ────────────────┘
A8 labelling (test) ───> A9 real evaluation ─> A11
A7 standards + derive   (optional — first to drop)
A10 UI                  (reads whatever A11 froze)
```

**Never drop:** A1, A4, A8, A6. **Drop in this order if time runs out:** A7 → UNSPSC update → A10.

---

## 2. Day by day to submission

**Revised 24 Sept night.** A1–A6 finished a day early, so the spare time goes on what the demo
and slides need, instead of leaving it for October:

| When | What | Who |
|---|---|---|
| Wed night | ✅ branch saved · ✅ C2 error bound · ✅ B2 what-if line | Claude |
| Thu 25 | C1 baselines (fuzzy, TF-IDF, embedding vs ours, same pairs) · B1 self-check · A10 "Real text" page + review queue as one record with its top 3 · B3 bolt equivalences | Claude |
| Thu 25 | Label the 417 test rows, separately | Isha, Meghna |
| Thu 25 | Slides 1, 2, 3, 6 | Madhu, Meghna |
| Fri 26 morning | B5 audit upgrade: hash-chained log, export, replay | Claude |
| **Fri 26 noon** | **A11 lock: re-freeze the code, final run, tag.** Nothing new after | Claude |
| Fri 26 afternoon | Slides 4, 5 from the tag · screenshots · backup video | Madhu, Aditya |
| Fri 26 evening | Whole team reads the deck aloud | All |
| Sat 27 morning | Export PDF, submit, touch nothing | Madhu |

Drop first if late: B3 bolts → B5 upgrade → B1 self-check. Never drop: the lock, the labels.

The original plan, for reference:

| Day | Madhu | Yash | Rashmit | Isha, Meghna | Aditya |
|---|---|---|---|---|---|
| **Wed 24** | PPT slides 1, 2, 3, 6 (no numbers needed). Hands A1 + A2 to Claude, reviews them | A4 blocking | A5 traps + tests | Label test sheets separately: first ~200 rows each | A10: design screen 09 "Real text" |
| **Thu 25** | Reviews A6 item factory; A7 if A1 has landed | A4 done → helps Rashmit run A6 | A6 generate 15,000 → full run → A9 → **A11 freeze at night** | Finish all 417 → `compare` → sit together → `finalise` by 6 pm | A10 wired to the frozen results |
| **Fri 26** | Slides 4, 5 from frozen numbers only | Proof-reads numbers vs `metrics.json` | Screenshots from the frozen build | Meghna: deck story + Q&A drill | Screenshots, fallback video of the demo |
| **Sat 27** | Export PDF, submit. **Touch nothing after.** | | | | |

**The test before submitting:** run five real lines from the test half through the frozen
build. If it still reads nothing, the deck describes a system that doesn't work on the data it
claims to serve.

---

## 3. Phase A — before 27 Sept

### A1 · Read real text: normalise and extract ★ top priority

**Owner** Madhu (Claude builds) · **Hours** 6 · **Waits on** nothing

**Goal.** Take the extractor from 3% to at least 70% of dev material lines yielding two or
more facts, without breaking the synthetic demo.

**Where.** New `src/normalise.py`. Changes to `schemas.py` (`_PATTERNS`, `_GRADE_ALIASES`,
`canonical_value`, `regex_extract`) and to `extractor.py` (`PROMPT` abbreviations).

**Design.**

1. **`normalise.py` — one function, `normalise(text) -> (clean, spans)`.** It runs before
   any pattern and keeps a map back to the original characters, so evidence spans still
   point at the real text.
   - Separators: `:` `;` `_` → `, `. Collapse repeated commas and spaces.
   - Hyphenated codes: `FE-410` → `FE410`, `A-105` → `A105`, `ASTM-F439` → `ASTM F439`,
     `a213- t23` → `A213 T23`.
   - Thousands: `10, 000 PSI` / `15,000 PSI` → `10000 PSI`. Only when followed by a unit, so
     NTPC's comma-separated fields survive.
   - Oilfield fractions: `2.1/16"` → 2-1/16 in, `13.5/8"` → 13-5/8 in, `9.5/8` → 9-5/8,
     `2.7 8 inchs` → 2-7/8. Plain fractions: `1/2"`, `3/4"`, `1-1/2"`, `1 1/2"`. Parse the
     whole number **with** its fraction first, so `3/4"` never becomes `4"`.
   - Abbreviations, applied only to a **whole comma-separated field**, because NTPC writes
     `PIPE, BLK, CS, FE410` and a bare `AL` or `IND` inside a sentence is too risky:
     `BLK` black · `GLV`/`GI` galvanised · `SMLS` seamless · `CHQ` chequered · `PWR` power ·
     `STRT` straight · `SCIM` squirrel-cage induction motor · `IND` induction · `AL`/`ALU`
     aluminium · `CU` copper · `FTG` fitting · `PL`/`P/E` plain end · `B/E`/`BE` bevel end ·
     `T&C`/`S&C` threaded and coupled · `WN` weld neck · `SO` slip-on · `RTJ` ring joint ·
     `RF` raised face · `PVCA` PVC armoured · `AS` alloy steel.
   - Every expansion is listed in one table, with the dev row ids that justified it.

2. **Size: designation versus measurement.** This is the core of the fix. Fields for pipe,
   flange, valve and fitting:
   - `nominal_size_in` (**hard**): the size *name*, always stored as NPS inches.
     `DN200` / `200NB` / `200 MM NB` / `8"` / `8 inch` all become **8.0**.
     DN↔NPS table: 15↔½, 20↔¾, 25↔1, 32↔1¼, 40↔1½, 50↔2, 65↔2½, 80↔3, 90↔3½, 100↔4,
     125↔5, 150↔6, 200↔8, 250↔10, 300↔12, 350↔14, 400↔16, 450↔18, 500↔20, 600↔24,
     700↔28, 750↔30, 800↔32, 900↔36, 1000↔40, 1200↔48.
   - `od_mm` (pipe, **hard**): the real outside diameter, from `O.D. 114.3 MM` or derived
     from the size through ASME B36.10M: ½ 21.3 · ¾ 26.7 · 1 33.4 · 1½ 48.3 · 2 60.3 ·
     3 88.9 · 3½ 101.6 · 4 114.3 · 5 141.3 · 6 168.3 · 8 219.1 · 10 273.0 · 12 323.8 ·
     14 355.6 · 16 406.4 · 18 457 · 20 508 · 24 610 · 30 762. From 14 inches up, OD = size × 25.4.
   - `wall_mm` (pipe, **hard**) from `WALL THICKNESS: 6.0 MM`, or from schedule + size.
   - **Bare millimetre numbers get a role by rule.** NTPC writes wall, OD and NB with no labels:
     `PIPE, BLK, CS, FE410, 9.5MM, 508MM, 500MM`. For each bare mm value in a pipe line:
     1. It matches a B36.10M OD within 1% → `od_mm`.
     2. Otherwise it equals a DN value and another number is that DN's OD → it's the designation.
     3. Otherwise it's ≤ 60 → `wall_mm`.
     4. It equals size × 25.4 for a standard size but isn't an OD (12.7, 50.8, 152.4) → a
        **designation converted as if it were a measurement**. Store the size, confidence 0.70,
        flagged.
     5. It's **both** an OD and a converted designation (**101.6** = OD of 3½ in, or 4 × 25.4) →
        ambiguous. Settle it with the weight if one is stated: plain-end lb/ft =
        10.69 × (D − t) × t, with D and t in inches. Otherwise leave the size UNKNOWN.
        Dev row 162 (`101.60 mm … 12.66 PPF`) is exactly this case, and the weight says 4 in.
   - Then check: the OD must belong to the stated designation (`508` ↔ `500NB`). If not, it's
     a contradiction for B1. For now, log it.
   - `length_mm` (`6 M`, `5000-7000MM`) is extracted but **ignored** for matching, because
     pipe is bought by the metre.

3. **Grades — a family ladder, not a flat list.** Add `grade_family`: CS, SS, AS (alloy),
   MS, CI, CU, AL. Grades map to a family: `A106 GR B`, `A53 GR B`, `API 5L GR B / X42 / X46 /
   X52`, `A333 GR 6`, `FE410`, `IS2062 E250A` → CS · `TP304L` → SS304L (standard `ASTM A312`)
   · `A213 T91/T23/T22/T11`, `A335 P11/P22/P91` → AS · `A105`, `A182 F316`, `A234 WPB`,
   `A216 WCB`, `A351 CF8M`, `A193 B7`, `A194 2H`, `CORTEN`/`A423 GR1` · OCTG `N-80`, `P-110`,
   `K-55`, `J-55`, drill pipe `G-105`, `S-135`.
   **Compare rule** in `scorer.values_agree` for `material_grade`:
   - different families → MISMATCH (veto)
   - same family, both specific, different → MISMATCH (veto)
   - one side only states a family (`CS`) and the other a grade (`A106 GR B`) → UNKNOWN,
     which caps the pair below auto
   - MS versus CS → UNKNOWN. Indian usage mixes them; NTPC writes `CS, FE410`.
     A human decides.

4. **Pressure.** `600 Class`, `CLASS 300`, `ANSI 900 CLASS`, `CL-150`, `900#`, `300 LB` →
   `pressure_class`. API 6A `10000 PSI` / `10M` / `5000 PSI WP` → a separate field,
   `pressure_rating_psi`, because class and API ratings are different systems and never
   compared. `PN16` → `PN16`. PN versus class → UNKNOWN; there is no exact mapping.

5. **Missing patterns today.** `valve_type` (gate, globe, check/swing check, ball, butterfly,
   plug, needle, control, safety relief, dual plate check) · `flange_type` (WN, SO, blind,
   SW, threaded, LJ, companion) · `face_type` (RF, FF, RTJ) · `construction` (seamless,
   ERW, SAW, LSAW, HSAW) · new pipe `finish` (black, galvanised) **hard** · new pipe
   `end_type` (plain, bevel, threaded-and-coupled) · `standard` (`API 5L`, `API 5CT`,
   `API 6A`, `API 6D`, `API 600`, `ASME B16.5`, `IS 1239`…). Motors: `power_kw` (hp × 0.746),
   `poles` (`4P`, or `4` after the frame), `frame` (`80L`, `112M`, `DW225S`, `315SM`),
   `mounting` (B3, B5, B35, V1), `duty` (S1, S4), `insulation_class` (F), `voltage_v`
   (`415VAC`).

6. **Classify by first noun, not first pattern.** Today the first pattern in list order wins.
   Instead find every category noun and take the **earliest** in the text, because a master
   line names its noun first (`PIPE, …`, `CABLE, …`, `ELBOW, …`). A `GASKET` line with kV or
   amp ratings is a switchgear spare, so it goes to `other`, not the flange-gasket schema
   (dev 123 and 124).

7. **Evidence spans, now, for free.** Every regex match already has `m.span()`. Store
   `evidence: {field: [start, end]}` against the original text. The UI can highlight it
   later (B6).

8. **LLM prompt.** Add the NTPC and Oil India shorthand to `PROMPT`, plus the size rule
   ("NB, DN and inch sizes are names; report the name as nominal_size_in and any stated
   outside diameter as od_mm").

**Done when.**
- `tests/test_extract_real.py`: 40 dev lines with their expected fields written by hand,
  including dev rows 1, 2, 3, 8, 14, 18, 19, 22, 23, 28, 29, 34, 83, 104, 162, 234, 582.
  All pass.
- On dev material lines inside the 13 categories: **two or more facts ≥ 70%** (from 3%),
  pipes ≥ 80%, valves ≥ 70%, and category accuracy stays ≥ 87%.
- `python src/scorer.py` still prints `OK R00001/R00002 MATCH` and `OK R00003/R00004 BLOCK`.
- **No test row was opened.** If dev coverage looks good but a pattern is missing, find it in dev.

---

### A2 · Four new categories and a useful "other" path

**Owner** Madhu (Claude builds) · **Hours** 2 · **Waits on** A1 (same files)

**New schemas in `schemas.CATEGORIES`.**

| Category | Hard fields | Other fields |
|---|---|---|
| `cable` | `cable_type` (power/control/instrument/fibre) · `cores` (1, 2, 3, 3.5, 4) · `cross_section_mm2` · `conductor` (AL/CU) · `voltage_kv` | `insulation` (XLPE/PVC/EPR) · `armour` · `standard` |
| `fitting` | `fitting_type` (elbow/bend/tee/reducer/cap/coupling/union/nipple/sleeve) · `nominal_size_in` · `material_grade` · `angle` (for elbow, bend) · `schedule` **or** `pressure_class` (3000#/6000# forged) | `end_connection` · `radius` (LR/SR) · `standard` (B16.9, B16.11) |
| `plate` | `material_grade` · `thickness_mm` | `plate_type` (plain/chequered) · `width_mm` · `length_mm` · `standard` (IS 2062) |
| `tube` | `material_grade` · `od_mm` · `wall_mm` | `tube_type` (boiler/exchanger/instrument/straight) · `length_mm` |

`electrical.equipment_type` loses `cable`, since cable now has its own schema, and gains
`current_transformer` and `panel`.

**The "other" path.** 36% of real material lines are drilling equipment, batteries,
bushings, wire rope, pumps and so on. They get a generic extraction: the head noun phrase,
every number with its unit (`29 MM`, `220V`, `400AH`, `10000 PSI`, `1150 HP`), and any
standard code. Two "other" records can **only ever reach review, never auto**, and only when
the noun phrase and every stated number agree. This still finds the real dev duplicates (the
bushing in three tenders, the 250 MVA transformer in three, the rotor in two) without
pretending we know the schema.

**Done when.** Dev tube, fitting and plate rows are classified right (0% today → ≥ 90%). The
dev groups G19, G23, G27 and G28 reach **review**, and none reaches auto.

---

### A4 · Blocking, and a scope label on every pair

**Owner** Yash · **Hours** 3 · **Waits on** nothing (uses whatever `specs.json` holds)

**Where.** New `src/blocking.py` with `candidate_pairs(specs, vecs) -> list[(a, b)]`.
`scorer.main` calls it instead of `combinations(ids, 2)`.

**Design.** A record joins a block through any of these keys. Two records sharing any key
become a candidate pair.
1. **Anchor key** — category + the standard designation: `bearing|6205`,
   `fastener|M12|50`, `pipe|4.0|SCH40`, `cable|3.5|240|AL`. It uses the standard number,
   never the maker's part number, so SKF `6205-2RS` and FAG `6205-2RSR` share `bearing|6205`.
2. **Leave-one-out signatures** — take the category's hard fields the record actually has.
   Emit one key with all of them, plus one key per field left out. A record missing one field
   still meets its twin. Near-miss pairs (SS316 against SS304) still meet on the key without
   grade, which is what we want: the veto then refuses them, and the safety report can count
   the refusal.
3. **Embedding neighbours** — the top 10 by cosine within the same category, computed in
   chunks of 1,000 rows (a 1,000 × 15,000 block is 60 MB). This catches records whose
   extraction is thin. No FAISS needed at 15,000.
4. **Block purging** — any key holding more than 200 records is too generic (`pipe|` with
   nothing else). It emits no pairs and gets logged.

**Scope.** Carry `plant` from `materials.csv` into each spec record: add it in `extractor.run`
next to `cpse`. Label each pair `SAME_PLANT` / `SAME_CPSE` / `CROSS_CPSE` and store it in
`pair_scores.json`.

**Cohesion fix, needed because of blocking.** `build_clusters` looks up every pair inside a
cluster and treats a missing pair as 0.0. With blocking, many pairs inside a cluster were
never generated, so every cluster would fail cohesion and go to review. Fix: score the missing
pairs inside a cluster on demand. Clusters are capped at 25, so that's at most 300 extra pairs
each.

**Rule.** `blocking.py` never reads `data/truth`. Pair completeness is computed in
`evaluate.py`, which is allowed to read truth.

**Done when.** `tests/test_blocking.py` passes: the SKF/FAG pair is a candidate; the
SS316/SS304 pair is a candidate (so the veto can count it); two runs give identical pairs. On
the 15,000-record set, the **reduction ratio is ≥ 99.9%** and **pair completeness is ≥ 98%**,
both printed by `evaluate.py`. The demo cases still pass.

---

### A5 · Hundreds of near-miss traps, and the hard-negative tests

**Owner** Rashmit · **Hours** 3 · **Waits on** nothing. It plugs into A6 when that lands.

**Traps, generated not hand-written.** In the A6 item factory, any two items in the same
category that differ in **exactly one hard field** form a trap pair. Adjacent grid cells give
this for free: every grade pair (304/316/316L/321; CS/SS), every pressure pair
(150/300/600/900), adjacent designations (6204/6205/6206, 6205/6305), bolt grades
(8.8/10.9), threads (M12/M16), valve types (gate/globe), cable cores (3C/3.5C/4C), cable
sections (150/240), pipe sizes (450/500 NB, the real NTPC pair), schedules (40/80),
construction (SMLS/ERW) and finish (black/galvanised, the real Oil India pair). Write them all
to `traps.json` with the field that differs.

`evaluate.py` gains **veto accuracy per gate**: for each trap field, the share blocked by the
right field, the share that reached review, and the share auto-merged (which must be 0).

**`tests/test_hard_negatives.py`** (pytest is installed):
- **Property test.** For every category, take one fully specified record. For every hard
  field, change only that field to another valid value. Assert the pair never reaches
  `AUTO_MERGE`, and that `blocked_by` names that field.
- **Missing-field test.** Remove one hard field from one side. Assert the pair stays below
  auto (the unverified cap).
- **Brand test.** Change the brand and part number. Assert the score doesn't change.
- **Determinism test.** Run the scorer twice on the same input. Assert byte-identical
  `pair_scores.json` and `clusters.json`.
- **Demo test.** R00001/R00002 MATCH ≥ 0.90, and R00003/R00004 blocked on `material_grade`.

**Done when.** `python -m pytest tests/` is green, and the 15,000-record run reports 0 traps
auto-merged. **From now on no scorer, schema or standards change is merged unless this
suite passes.**

---

### A6 · 15,000 records at 20% duplication, written the way real companies write

**Status, 24 Sept late — done.** `catalogue.py` (11,815 valid items; tables in `standards.py`),
`render.py` (4 styles + 2 test-only), factory mode in `generate_dataset.py` (2 s), run folders
(`SIH_RUN`), `run_all.py` (whole chain, 4.4 min at 15,000, 3.6 of it CPU embeddings),
`results.py` caps with totals computed before capping, `evaluate.py` by split + review-queue
view. 15,000 records on 11,815 items (21.2%), 104,994 generated traps.

| 15,000-record run | first run | now |
|---|---|---|
| auto-merged / wrong | 3,811 / **2,625** (31%) | 846 / **0** (100%) |
| traps auto-merged | 55 | **0** |
| recall (auto + review) | 70.6% | 82.0% (dev 82.2%, test 81.4%) |
| blocking | 99.87% skipped, 68% of true pairs meet | 99.80% skipped, 82% meet |

What fixed it (all from dev families; test families untouched): variant fields became veto
fields; **one-sided silence on a veto field holds a pair**; **variant awareness** (both silent,
registry holds several values); family-only grades are a doubt; non-cohesive groups are split;
identity keys for blocking; reader fixes for seals, typo'd nouns, SAP truncation, stainless
numbers, NTPC OD-before-wall. Blocking target moved to 99.8% — the tighter cut cost recall.
Review queue: pairwise precision ~7%; ranked by confirmed fields the true match is first for 50%
of records, top three for 78% → the UI shows candidates per record (A10).

**Owner** Rashmit (runs) with Madhu (item factory; Claude builds) · **Hours** 5 · **Waits on** A1, A2, A4

**Why the current generator can't just be scaled.** It has 15 hand-written items. 15,000
records at 20% duplication needs about 12,000 distinct items.

**Item factory — new `src/catalogue.py`.** Build valid items from spec grids that follow
real standards:
- bearings: 60xx/62xx/63xx series × seal (open, Z, 2Z, RS, 2RS), with dimensions from the
  ISO 15 table (the same table A7 uses)
- pipe: size ½–24 × schedule × grade × construction × finish, with validity rules (IS 1239
  is ERW; stainless is never galvanised)
- flange: type × face × size × class × grade
- valve: type × size × class × body × end
- gasket: type × size × class × winding grade × filler
- fastener: type × thread × length × grade
- cable: type × cores × section × conductor × voltage × insulation × armour
- fitting, plate, tube, motor (kW × poles × voltage × mounting × frame), gauge, seal

Sample about 12,000 valid items with a fixed seed, weighted towards refinery stock. Each
item gets a `family_id`: all fields except size (and, for bearings, the designation).

**Real-notation renderers.** Each company writes in its own observed style, copied from the
dev rows rather than invented:
- **NTPC style:** comma fields, `PIPE, BLK, CS, FE410, 9.5MM, 508MM, 500MM`
- **Oil India style:** long form, `STEEL LINE PIPE, SEAMLESS, NOMINAL BORE: 100 MM, O.D. 114.3 MM, …`
- **SAP style:** truncated to 40 characters (`MAKTX`)
- **Noun-modifier style:** today's style

Size notation (NPS / NB / DN / OD mm / the converted-designation mistake), grade notation
(`A106 GR B` / `A106B` / `CS`) and abbreviations are all drawn from tables built from dev.
The existing corruptions stay: typos, reordering, dropped fields, case.

**Duplication.** 15,000 records on about 12,000 items, lumpy rather than even: most items
appear once, some 2–5 times, spread across companies and plants.

**Family-level split for the locked test (C3).** Before any variants are made, 20% of
**families** are marked `test` by a hash. The split lives in `data/truth/ground_truth.csv`
only, so the pipeline can't see it. Two renderer styles are used **only** for test records,
so test also measures notation the rules were never tuned on.

**Keep.** `GUARANTEED` stays as R00001–R00004, so the demo cases never move. Purchases get
regenerated with price bands per item, plus a few pack-size cases (box of 100 against each)
for C13.

**Also.** `results.py` must cap every list it embeds: review queue 200, codes 200, blocked
200, savings 50. The UI bundles `results.json` at build time, and 15,000 full records would
bloat the single-file demo.

**Done when.** `generate_dataset.py --target 15000 --dup 0.20` runs in under a minute.
`run_all.py` runs the whole chain. Evaluation prints dev and test separately. Trap count is
≥ 300. Demo cases pass.

---

### A7 · Standards tables and the derive stage — optional, first to drop

**Owner** Madhu (Claude builds) · **Hours** 4 · **Waits on** A1

**Tables in `data/standards/`, each row with its source.**
- `bearings_iso15.csv`: designation, type, bore, od, width (6000–6012, 6200–6215, 6300–6312)
- `pipe_b36_10.csv`: nps, dn, od_mm, schedule, wall_mm
- `designations.csv`: the DN↔NPS table
- `equivalence.csv`: standard_a, grade_a, relation, standard_b, grade_b, source. Relation is
  one of `IDENTICAL` / `NEAREST` / `SUPERSEDED_BY`. Starter rows:
  IS 1367 (Part 3) 8.8 IDENTICAL ISO 898-1 8.8 · same for 10.9 ·
  ASTM A325 SUPERSEDED_BY ASTM F3125 Gr A325 · ASTM A490 SUPERSEDED_BY ASTM F3125 Gr A490 ·
  ISO 898-1 8.8 NEAREST ASTM F3125 Gr A325 · ISO 898-1 10.9 NEAREST ASTM F3125 Gr A490 ·
  IS 2062 Fe 410 W SUPERSEDED_BY IS 2062 E250 (**check against the standard before it goes on
  a slide**).

**`src/derive.py`.** Reads `specs.json` and writes `specs_enriched.json`. The scorer reads the
enriched file. `specs.json` stays a pure extraction cache, never polluted with derived values.
- A bearing with a designation but no dimensions gets bore, OD and width from ISO 15.
- A pipe with a size gets `od_mm`; a pipe with size + schedule gets `wall_mm`.
- A pipe with only an OD gets its size by reverse lookup.
- Every derived value: confidence 0.85, `method: derived`, and
  `derived_from: "ISO 15: 6205"`.
- Grades are resolved through `equivalence.csv`. Chain IDENTICAL links only; NEAREST never
  chains. A superseded grade maps to its replacement and is marked `superseded`.

**Done when.** The demo can show `6205` matched to `25X52X15MM` with no shared words: a record
that states only the designation meets one that states only the dimensions. Dev row 162
(101.6 mm, 12.66 lb/ft) resolves to 4 in. A test row for each equivalence relation passes.

---

### A8 · Real-data labelling — dev done, test labelled by Claude after the freeze, humans pending

**Owner** Isha, Meghna · **Hours** about 3 each

**Status, 24 Sept evening.** Dev 485 rows labelled by Claude. At Madhu's request Claude also
labelled the 417 test rows — into `labels/claude.csv`, **after** fingerprinting the reading and
scoring code in `labels/frozen.json`, so no test row influenced the code that is scored. That
gives today's number, with the caveat "one labeller, the builder". `isha.csv` and `meghna.csv`
are untouched and still blank: two people labelling blind remains the proper result, and can be
compared against Claude's sheet with `labels.py compare --people isha claude`.

**Steps.** Each opens **only** their own sheet (`data/real/labels/isha.csv` or
`meghna.csv`) and fills in `keep`, `category`, `group` and `notes` from the top down. Then:
`python src/labels.py compare` → sit together → fill in `decision` and `reason` →
`python src/labels.py finalise`.

**Done when.** `data/real/labels/final.csv` exists, with a kappa above 0.6 printed by
`compare`, and the disagreement log is filled in.

---

### A9 · Real evaluation

**Owner** Rashmit · **Hours** 2 · **Waits on** A1, A8

**New `src/real_eval.py`.** Two reports, never blended:

| Report | Labels | Measures |
|---|---|---|
| **dev** (for building) | `labels/dev.csv` | same metrics, printed with a "DEV — not a result" banner |
| **test** (the result) | `labels/final.csv` | category accuracy on `y` rows · rows with ≥ 2 facts · pairs: precision and recall of the matcher against the groups · real near-misses auto-merged (must be 0) |

**How matching runs on real rows.** Write the test `y` rows as a small materials file
(`cpse` = organization, `source_code` = id) into `data/output/real/`. Run the same pipeline on
it. Compare the pairs with the gold groups. Report the counts plainly too: the result may be
something like "11 true duplicate pairs among 190 rows", and that sentence belongs beside the
percentage.

Every output carries its dataset name, row count, timestamp and git commit, in
`data/output/real_metrics.json`.

**Done when.** `real_eval.py --split test` runs after `finalise` and writes
`real_metrics.json`. The UI and the deck read it from there, never typed in by hand.

---

### A10 · UI updates

**Owner** Aditya · **Hours** 4 · **Waits on** A11 for the final numbers

- **Overview:** three datasets side by side (synthetic 15,000 · real test · traps), each
  stamped with its dataset and date. Never one blended number.
- **New screen 09, "Real text":** the real NTPC and Oil India lines. On the left, the original
  line. On the right, the extracted fields with evidence highlighting from A1's spans. Then
  the three spellings of one pipe next to each other. This is demo scene 1 and a slide 2
  screenshot.
- The Block screen gains the counterfactual line when B2 lands (not before 27 Sept).
- `verify.py` gets updated with the new screen.

**Done when.** `npm run build` produces one file that opens offline and shows the frozen
numbers.

---

### A11 · One command, and the numbers freeze

**Owner** Rashmit · **Hours** 1

**`run_all.py`** runs the whole chain: generate → extract `--no-llm --fresh` → derive →
embed → score → canonicalise → savings → uom → gate → evaluate → real_eval → results →
`npm run build`. It stops at the first failure. It stamps `run_id` = date + git short hash +
hash of `materials.csv` into every metrics file.

**Freeze, Thursday night.** Commit the outputs and tag them `ppt-numbers-2026-09-25`. Every
number in the deck must match a file at that tag. If it doesn't, it doesn't go on a slide.

---

### A12 · What the PPT needs from engineering

| Slide | Needs | From | By |
|---|---|---|---|
| 2 | Real NTPC and Oil India lines: one pipe three ways; `101.60 mm` vs `4"`; `500NB` vs `508MM` | dev examples in `data/real/README.md` | now |
| 3 | Pipeline picture with 14 stages; one screenshot | update `deliverables/slides/slide3-architecture.html` | Thu |
| 4 | Synthetic numbers + real test numbers + trap numbers, side by side | `metrics.json`, `real_metrics.json` at the freeze tag | Thu night |
| 5 | Savings, safety blocks, gate verdicts | `savings.json`, `metrics.json`, `gate.json` | Thu night |
| 6 | References + Hugging Face credit (CC-BY-4.0) | `finalarchitecture.md` §10 | now |

---

## 4. Phase B — October: the five ★ features and governance

### B1 · Self-check ★

**Where:** `derive.py`, after derivation. **Design:** check each record against itself. Stated
against derived (a bearing says 6205 but also 30×62×16) · OD against designation (500NB with
457 mm) · wall against schedule · category against fields (a valve with a cross-section in
mm²) · impossible values (bore ≥ OD, range min ≥ max, a negative number). Output
`contradictions: [{field, stated, derived, rule}]`. Any pair involving a contradicted record is
capped below auto, with the contradiction shown. **Done when:** five planted contradictions are
caught, no clean dev row is flagged by more than 2% false alarms, and the contradiction rate
per company appears on the scorecard (C9).

### B2 · Counterfactual ★

**Where:** `scorer.score_pair`. **Design:** for a blocked pair, re-score with the blocking
field set equal on both sides: "if `material_grade` matched, this would score 0.94". For a
near-miss (0.70–0.90), find the single non-hard field whose agreement would lift it over 0.90.
Each costs one extra `spec_agreement` call, only on blocked or review pairs. Store
`counterfactual: {field, score_if_equal}`. The UI shows it on the Block screen and the review
card. **Done when:** every blocked pair in `pair_scores.json` has a counterfactual, and the
SS316/SS304 demo shows it.

### B3 · Cross-standard equivalence and supersession ★

**Where:** `data/standards/equivalence.csv`, `src/standards.py`, and
`scorer.values_agree`. **Design:** `resolve(standard, grade)` returns a canonical key through
IDENTICAL links (transitive closure over IDENTICAL only) and follows SUPERSEDED_BY to the
current designation. Comparison: IDENTICAL → MATCH; NEAREST → UNKNOWN with relation
`EQUIVALENT?` for a human; a superseded designation → MATCH with its current name, marked
`superseded` in the evidence. **Done when:** an IS 1367 (Part 3) 8.8 bolt matches its
ISO 898-1 twin; an A325 record meets an F3125 Gr A325 one; ISO 8.8 against F3125 A325 goes to
review, never auto.

### B4 · Five relationships

**Where:** a new function in `scorer.py`. **Design:** IDENTICAL (all hard fields match, and none
match only by derivation) · EQUIVALENT (match only through the equivalence table or
derivation) · SUBSTITUTE (from the directional service table, B-C11; always human) ·
VARIANT_OF (same `family_id` signature, differs only in size or designation) · INCOMPATIBLE
(hard mismatch). Clusters form only from IDENTICAL and EQUIVALENT. VARIANT_OF feeds the size
ladder (C14). **Done when:** every scored pair carries a `relation`, and 6204/6205/6206 show
up as variants, not duplicates.

### B5 · Governance: audit log, five verbs, consent, dispute ★

**Where:** new `src/govern.py`, `data/output/audit.jsonl`. **Design:**
- The log can only be added to. Each event: `event_id, ts, actor, org, verb, national_code,
  source_codes, pair, field, note, prev_hash`. `prev_hash` is the SHA-256 of the previous line,
  so tampering shows. It's a hash chain, not a blockchain.
- Verbs: ACCEPT · REJECT · MARK_DIFFERENT (field required) · UNMAP · DISPUTE.
- Mapping state is a **replay** of events over the pipeline's proposals. Nothing is ever
  overwritten; undoing is another event.
- Consent in code: `allowed(actor_org, verb, target)`. Linking needs the registrar role.
  **Retiring is only allowed to the company that owns the code.** Any affected company can
  DISPUTE.
- Lifecycle of a cross-company link: PROPOSED → LINKED (provisional, 30-day dispute window)
  → LINKED (settled). DISPUTED → back to REVIEW, with the objection logged.
- The static demo records decisions in the browser and exports `audit.jsonl`. `govern.py`
  replays it.

**Done when:** the demo shows a dispute sending a pair back to review with the reason recorded;
a retire attempt by a non-owner is refused and logged; replaying the log rebuilds the mapping
exactly. This closes capability 7, the only capability with nothing built today.

### B6 · Evidence everywhere

**Design:** the UI highlights the source words behind every field (spans from A1). **The LLM
must quote the words it read.** A value whose quote isn't found in the description is
dropped. That's a hallucination guard that costs one string search. **Done when:** every field
on the Match screen is highlighted in its source line.

---

## 5. Phase C — November

| Card | Design in one paragraph | Done when |
|---|---|---|
| **C1 Three-layer evaluation + 4 baselines** | Layer A: pair completeness and reduction ratio from blocking. Layer B: P/R/F1 per band. Layer C: auto-band precision and review load per 1,000 records. Baselines on **the same candidate pairs**: fuzzy string (stdlib `difflib`), TF-IDF cosine (scikit-learn, installed), pure embedding cosine, ours. Each baseline gets its best-F1 threshold on dev, which is fair to them. | One table, four methods, three datasets, printed by `evaluate.py --baselines` |
| **C2 Error bound** | Clopper–Pearson upper bound on the auto-band false-merge rate: "with 95% confidence, auto-merge error ≤ X%". Named honestly, not "guaranteed". | The bound prints next to auto precision |
| **C3 Locked test** | `evaluate.py --split test --lock` runs once and writes a timestamped file. A second run needs `--force`, and the force is logged. | One locked result exists before December |
| **C4 Review priority** | Priority = uncertainty (closeness to 0.80) × thin evidence (1 − compared/total fields) × value (spend band) × criticality (valve/flange/gasket in hydrocarbon service 3, bearing 1.5, plate 1) | The queue is sorted, and the top 10 make sense to a refinery person |
| **C5 Random audit cards** | 5% of queue slots show a random **auto-merged** pair, unmarked. Agreement gives a live estimate of auto precision with an interval, tracked per reviewer. | The estimate shows on the Overview |
| **C6 Fusion order** | In `canonicalise.golden_record`: standard-confirmed → highest confidence → majority → latest purchase → most precise. Record `provenance` per field. If a hard field is still split after the first two rules → no code, cluster goes to review. | Every golden field shows which record and which rule won |
| **C7 MARK_DIFFERENT → rule proposals** | Count MARK_DIFFERENT reasons by (category, field). Five or more on a non-hard field → a proposal in `rule_proposals.json`. A human makes it hard by commit. The system never changes itself. | Proposals appear after simulated reviews |
| **C8 Staged migration + SAP-shaped export** | `migrate.py --company NTPC --batch 1`: plan → dry-run (every code exists, no conflicts, no retiring someone else's code) → impact (rows, risk colour, ₹ unlocked) → apply (flat file: MATNR, MAKTX ≤ 40, MEINS, MATKL, ZZNMC) → verify → rollback file. Never claim a live SAP link. | A dry-run and a rollback round-trip leave the data identical |
| **C9 Data-quality scorecard** | Per company: records meeting the category minimum, contradiction rate, derivability, duplicates by scope, unit conflicts, unknown-category rate. Every rate links to the record ids. | A scorecard page per company |
| **C10 Plant scope routing** | SAME_PLANT and SAME_CPSE pairs go to that company's reviewer; CROSS_CPSE to the registrar with the dispute window. Duplication reported per scope. | The Overview shows three duplication rates |
| **C11 Service qualifiers** | Extract NACE MR0175/sour, IBR, cryogenic, fire-safe (API 607/6FA), oxygen-clean. Only one side has it → SUBSTITUTE with a direction (qualified can replace unqualified), never auto. Both have it → must match. | Dev 116 (fire safe) and 155 (IBR) carry the flag |
| **C12 Valve materials** | Body, trim and seat as separate fields. Trim is hard for control valves; seat is hard for soft-seated ball valves. | Property tests extended |
| **C13 Pack size** | Same unit, price ratio within ±15% of 10/12/25/50/100 → flagged, with the likely factor named | The planted box-of-100 case is flagged |
| **C14 Variant ladder** | From VARIANT_OF: sizes per family with spend share. "Seven sizes stocked, three carry 90% of spend." | One ladder view in the UI |
| **C15 Gate counters** | `gate.py` logs verdicts. Counters: duplicates stopped, and specs completed at creation (INCOMPLETE → resubmitted complete). | The counters show on the Gate screen |
| **C16 More real data** | Collect more public NTPC and Oil India tender extracts, respecting each site's terms, to reach 3,000+ lines. Same split rule; new test rows labelled by two people. | Real test set ≥ 800 rows |
| **C17 Coverage floor per category** | A bearing needs its designation or all three dimensions; a valve needs size, class, body and type. Below that → no auto. Derivation fills gaps first. | Encoded in `schemas.py`, tested |
| **C18 Classification queue** | Category confidence < 0.70 → a bootstrap queue for a human, never a guess | Queue count on the Overview |
| **C19 Same-code anchor** | Two lines carrying the same company material code (NTPC `M1613517861`) are the same record. Anchor before scoring. | Dev groups G11, G12, G19, G20 and G24 resolve by anchor |

---

## 6. December — rehearsal only

- The demo runs identically three times in a row from a clean clone.
- A fallback video of the 90-second demo, in case the laptop fails.
- Meghna answers 30 hostile domain questions without slides (`docs/04-risks/judge-questions.md`).
- Every number spoken matches a file at a tag.
- No new features.

---

## 7. Defects to fix along the way

| Where | Problem | Fix |
|---|---|---|
| `scorer.build_clusters` | The docstring says a weak cluster is split; the code sends it to review | Keep routing to review (safer). Fix the docstring and anything that says "split". **Done in the progress PDF on 24 Sept.** |
| `scorer.build_clusters` | With blocking, missing intra-cluster pairs count as 0.0 | Score them on demand (A4). **Done** |
| `results.py` | Embeds lists uncapped relative to 15,000 records | Cap every list (A6) |
| `extractor.run` | Spec records don't carry `plant` | Add it (A4). **Done**; scope SAME_PLANT / SAME_CPSE / CROSS_CPSE on every pair |
| `generate_dataset.py` docstring | Says the hold-out comes from GeM/eprocure | Point to `data/real` |
| `schemas._CATEGORY_HINTS` | First pattern wins; switchgear gaskets land in the flange-gasket schema | First noun wins; kV/A context → other (A1). **Done** (`rules.classify`) |
| `values_agree` | Grade compared as flat strings; `CS` against `A106 GR B` would veto a true pair | Family ladder (A1). **Done** |
| `values_agree` | A flat ±0.5 tolerance let a 1-1/4" pipe match a 1-1/2" one, and a 1.6 mm plate a 2.0 mm one | Exact for size names and counts, 2% for measurements. **Done 24 Sept** |
| grade spellings | `A193_B7` vs `ASTM A193 B7` (synthetic, from the model) vetoed 7 true pairs; cast vs carbon steel vetoed 14 | `normalise.canonical_grade` + family ladder. **Done — recall 0.942 → 1.0** |
| **review band on real text** | Real test: 196 of 235 false proposals have a safety field silent on one side | Propose only when at least N hard fields actually agree; design and check on **dev** |
| `rules.read_plate` | `(1.6X 2500X 1250MM)` reads thickness 1250 (seen in the test run) | Reproduce on dev, then fix — post-freeze |
| `normalise` | `1.13 16 inchs` (two-digit numerator, slash dropped) reads 16 (test run) | Same |
| `rules.read_sizes` | `114.3 mm (4.1/2")`: the bracketed inch restates the bare OD but is read as the size (test run) | Same |

---

## 8. Submission checklist — Saturday morning

- [ ] `python -m pytest tests/` green at the freeze tag
- [ ] `run_all.py` from a clean clone reproduces every number in the deck
- [ ] Real **test** numbers come from `labels/final.csv`, not from dev
- [ ] Five real test lines run through the frozen build and yield fields
- [ ] Every slide number traced to a file at `ppt-numbers-2026-09-25`
- [ ] Hugging Face dataset credited on slide 6 (CC-BY-4.0)
- [ ] No slide says 100%, production, live SAP, secure or encrypted
- [ ] The real data is called "tender text from two CPSEs", never a material master
- [ ] PDF, six slides maximum, submitted
