# FINAL_ARCHITECTURE.md — Overwatch · SIH26099

**Status: FINAL — 24 September 2026.** Supersedes the 17 September freeze.
This is the single source of truth. It records every decision made up to the PPT
submission on 27 September. Anything not written here is not part of the project.

**Change rule:** nothing here changes without a row in the Change Log at the bottom.
New ideas go to `FUTURE.md`, not here.

---

## 0. The principle

> **AI reads. Engineering decides. Governance records.**

- The LLM extracts attributes. It never compares a pair and never decides a merge.
- Every decision is deterministic arithmetic over stored values — same input, same output, forever.
- Procurement data **corroborates or vetoes**. It never adds to a match score.
- No supervised model is trained. No expert-labelled CPSE pairs exist anywhere, so there
  is nothing honest to train on. Nothing is trained, so nothing needs retraining on new data.

---

## 1. What the system is

A national material-code registry for CPSEs. It ingests each company's material master,
works out which records describe the same physical item — by comparing **specifications,
not spelling** — issues one National Material Code per item, and links every original
code to it. **No company's code is changed or deleted.** The national code sits above
the existing codes, the way UPI sits above bank accounts.

It runs in two modes on one engine:

| Mode | Input | Output |
|---|---|---|
| **Harmonise** | a whole material master | national codes + mapping for every existing record |
| **Gate** | one new-code request | EXISTS · REVIEW · NEW · INCOMPLETE — before a duplicate is born |

---

## 2. Pipeline

```
00 INGEST         SAP-shaped CSV/XLSX, or one new-code request
                  append-only · versioned · source row kept verbatim
      ↓
01 NORMALISE      abbreviations — including real NTPC shorthand:
                    BLK SMLS CHQ GLV ERW SCIM PWR STRT PL 1C
                  units — 10 spellings → canonical form; pack size kept separate
                  size designations — 1/2" = DN15 = 15NB are one NAME, not a measurement;
                    the actual outside diameter (21.3 mm) comes from ASME B36.10 in 04
                  fractions (3/4" ≠ 4")
                  standard codes — ASTM-F439 = ASTM F439
                  spaced + compacted forms — C.S. / CS / C S
      ↓
02 CLASSIFY       13 categories: bearing · gasket · pipe · valve · fastener · flange ·
                  rotating · instrument · electrical · cable · fitting · plate · tube
                  confidence < 0.70 → schema bootstrap queue, never a guess
      ↓
03 EXTRACT        rules first; LLM only if a critical field is below 0.70
                  every value carries: evidence span · method · confidence
      ↓
04 DERIVE  ★      standards tables fill what the text left out
                    ISO 15 — bearing 6205 → bore 25, OD 52, width 15
                    ASME B36.10 — pipe NPS + schedule → wall thickness
                    ASME B16.5 — flange class → rating
                  cross-standard equivalence  ★
                    IS 1367 (Part 3) ≡ ISO 898-1   BIS adopted it as identical
                    IS / ISO 8.8 ≈ ASTM F3125 Gr A325   nearest only: differs in
                                               dimensions, marking, testing
                  supersession — a withdrawn standard maps to its replacement
                    ASTM A325 (withdrawn 2016) → ASTM F3125 Grade A325
                  derived values flagged, confidence 0.85
      ↓
05 SELF-CHECK ★   the record is checked against itself before anything else
                  stated vs derived · text vs extracted · impossible combinations
                  contradictory → excluded from auto, routed to a human
      ↓
06 BLOCK          only plausible pairs are ever compared
                    category · identity signature · part-number anchor ·
                    same-company internal pass
                  scope label on every pair:
                    SAME PLANT · SAME CPSE, 2+ PLANTS · ACROSS CPSEs
      ↓
07 VETO           runs BEFORE any score
                  each critical field: MATCH · MISMATCH · UNKNOWN
                    MISMATCH → blocked
                    UNKNOWN never agrees and never conflicts
                  named gates: GRADE · PRESSURE · DIMENSION · TYPE
                  service qualifiers (sour service NACE MR0175, IBR, cryogenic,
                    fire-safe, oxygen) on one side only → never IDENTICAL;
                    emitted as a directional SUBSTITUTE for a human (see 09)
                  price ratio > 10× → blocked
      ↓
08 SCORE          exact anchor on the STANDARD designation first — brand-independent;
                  then specifications (dominant) + text (weak)
                  coverage floor: too few verified fields → capped below auto
                  counterfactual stored for every blocked or near-miss pair  ★
      ↓
09 RELATE         IDENTICAL · EQUIVALENT · SUBSTITUTE · VARIANT_OF · INCOMPATIBLE
                  SUBSTITUTE only from a curated directional table, always human
      ↓
10 ROUTE          auto     ≥ 0.90 and not high-criticality
                  review   0.70–0.90, or any high-criticality item
                  blocked  a veto fired
                  queue order = uncertainty × thin evidence × value at stake
                                × safety criticality
                  plus random audit cards — some drawn from the auto-merged band,
                    giving a live, unbiased estimate of auto-merge precision
      ↓
11 CANONICALISE   golden record — conflicting values resolved in fixed order:
                    standards-confirmed → highest confidence → majority →
                    most recent purchase → most precise
                  identity-critical disagreement left unresolved → no code issued
                  noun-modifier description · UNSPSC class
                  NMC-<UNSPSC class>-<6-digit serial>
                  every source code retained and mapped
      ↓
12 GOVERN  ★      append-only audit log — who, what, when, why, reversible
                  verbs: ACCEPT · REJECT · MARK_DIFFERENT · UNMAP · DISPUTE
                  consent scales with harm (section 4)
      ↓
13 OUTPUTS        creation gate · migration pack · demand view · safety report ·
                  units report · data-quality scorecard · evidence view
```

★ = no other system on this problem statement has it.

---

## 3. Features

### Ours alone

| Feature | What it does |
|---|---|
| **Standards derivation** | A record that says only `6205` is matched to one that says only `25X52X15MM`. The standard supplies the dimensions nobody typed. |
| **Cross-standard equivalence** | Knows IS 1367 (Part 3) and ISO 898-1 are identical, and ASTM F3125 Grade A325 is only close. Knows when a standard was withdrawn and what replaced it — ASTM A325 was withdrawn in 2016 and now lives on as a grade of F3125, so old and new records still meet. CPSEs tender on IS and receive ASTM and DIN supply. |
| **Self-check** | A record that contradicts itself is caught before it can match anything. Bad data must not become national data. |
| **Counterfactual** | For every refused or near-miss pair: *"if the grade matched, this would score 0.94."* One field decides, and the reviewer sees which. |
| **Dispute, not veto** | The registry moves by default; any company can challenge a link at any time. |

### Built and working today

Three-signal scorer with hard vetoes · clustering with cohesion check · golden record ·
noun-modifier descriptions · UNSPSC classification · national code generation · mapping
table · savings report with k-anonymity · safety interlock report · units harmonisation ·
creation gate (four verdicts) · government-style portal (role sign-in, dashboard, analytics,
catalogue, migration export, review queue, live audit trail) · evaluation harness.

### To build — our design

Every feature below is extended with something only this system has — the standards
layer, safety criticality, direction, or the consent model.

| Feature | Stage | Our design |
|---|---|---|
| **Size designation vs actual dimension** | 01, 04 | NB, DN and NPS are *names*, not measurements. `1/2"` = `DN15` = `15NB`, but its outside diameter is 21.3 mm. Names map to each other; real dimensions map through ASME B36.10. So `500NB` matches `508MM` OD — a pair that appears in real NTPC tenders and that a plain unit converter misses. An Oil India tender states it outright: `NOMINAL BORE: 100 MM, O.D. 114.3 MM`. |
| **Pack size** | 01 | Same unit spelling, but a price ratio near a common pack factor (10 · 25 · 50 · 100) → flagged as a pack-size mismatch, with the likely factor named. |
| **Valve materials** | 03 | Body, trim and seat as separate fields. Trim is a hard field for control valves; seat is a hard field for soft-seated ball valves. |
| **Blocking** | 06 | Signatures are built **after** derivation, so a record that never stated its dimensions still gets them from the standard before blocking. Plus leave-one-out signatures, so one missing field never loses a true pair. Pair completeness measured and reported. |
| **Plant scope** | 06, 12 | Scope decides the route: same-plant and same-company pairs go to that company's reviewer; cross-CPSE pairs go to the registrar with a dispute window. Duplication reported separately at each scope. |
| **Coverage floor** | 07, 08 | Category-specific, not a flat count: a bearing needs its designation, or all of bore, OD and width; a valve needs size, class, body and type. UNKNOWN is resolved by derivation wherever a standard allows it, so fewer pairs stall in review. |
| **Service qualifiers** | 07, 09 | Directional. A sour-service (NACE MR0175), IBR, cryogenic or fire-safe item can typically replace one without that rating — never the reverse. Emitted as SUBSTITUTE with a direction, so procurement knows which one to stock. Always a human decision. |
| **Exact anchor** | 08 | Anchored on the **standard designation**, not the manufacturer part number. SKF `6205-2RS` and FAG `6205-2RSR` have different part numbers but meet at the anchor stage. |
| **VARIANT_OF** | 09 | Variants laid out as a size ladder — 6204 · 6205 · 6206 — and used to drive rationalisation: *"seven sizes stocked, three carry 90% of spend."* |
| **Review priority** | 10 | Uncertainty × thin evidence × value at stake × **safety criticality**. A valve in hydrocarbon service outranks a costlier item where a wrong merge harms nobody. |
| **Random audit card** | 10 | Some random cards are drawn from the **auto-merged** band, not only the review queue. That gives a continuous, unbiased estimate of auto-band precision — the safety-critical number — in live use. Agreement on random cards is tracked per reviewer. |
| **Golden-record fusion** | 11 | Standards-confirmed value → highest-confidence extraction → majority → most recent purchase → most precise. Every fused value records which source record and which rule won. |
| **MARK_DIFFERENT** | 12 | Records the field that differs. Reasons aggregate into rule proposals — *"seven pairs differed only on end_connection; make it a hard field?"* — which a human ratifies by commit. The system proposes; it never applies. |
| **Staged migration** | 13 | Plan → dry-run → impact → apply → verify → rollback. Impact shows the risk light **and** the rupee benefit the batch unlocks. Retire proposals go only to the company that owns the code. |
| **Data-quality scorecard** | 13 | Adds two rates only this system can compute — **contradiction rate** and **derivability** (records whose dimensions a standard confirms). Every rate links to the exact failing records: it says what to fix, not just a grade. |
| **Gate counters** | 13 | Two counters: duplicates prevented, **and specifications completed at creation** — the INCOMPLETE verdict made measurable, which is the PS's "specification finalisation" impact in a number. |
| **Near-miss traps** | eval | Generated from the standards tables themselves, so the trap set grows as the tables grow. Plus real near-misses from NTPC text (the 457 mm vs 508 mm pipes). Veto accuracy reported per gate. |
| **Hard-negative tests** | eval | Property test: changing any single hard field must never let a pair reach auto. Determinism test: the same input twice gives byte-identical output. |
| **Evaluation** | eval | A fourth layer for real data. Results per scope and per category. Every published number is stamped with its dataset and run time, so no figure can appear without them. |

---

## 4. Rules

**Non-negotiable.**

- **Precision over recall.** A wrong merge in a refinery master can mean the wrong valve
  installed. Uncertainty goes to a human.
- **Nothing is destroyed.** Materials are append-only. Original codes always retained.
  Reversing a merge deletes mapping rows only.
- **Every merge is explainable.** Which signals, what scores, which fields, what source text.
- **The LLM never decides.** One call per record, never per pair.
- **Veto before score.** UNKNOWN is never agreement and never conflict.
- **Thresholds change only by a versioned commit.** Never automatically.
- **Ground truth is read by evaluation only** — enforced with an import guard.
- **No number goes on a slide unless it came from a recorded evaluation run.**

**Consent scales with harm.**

| Action | Who decides |
|---|---|
| Link two codes under one national code | National registrar. No veto. |
| Retire or deactivate a code | **Only the company that owns it.** Nobody else, ever. |
| Show a price or vendor across companies | Never raw. Bands and hashes, suppressed below 3 CPSEs. |
| **Dispute a link** | **Any affected company, at any time.** The pair returns to review with the objection recorded. |

A national code changes nothing inside a CPSE's system, so issuing one needs no
permission. Requiring every company to sign every cross-CPSE code deadlocks the registry
— one silent company blocks a code forever. **A right to dispute, not a right to veto.**

**Rollout.**

- **Phase 1 — inside one CPSE.** Duplicates across one company's own plants. No data
  sharing, no inter-company agreement, no policy change. Value on day one.
- **Phase 2 — across CPSEs.** Price bands and vendor hashes, never raw prices or names.
  Benchmarks shown, never attribution.

---

## 5. Data

| Dataset | Size | Purpose | Rule |
|---|---|---|---|
| Synthetic dev | 15,000 records, 20% duplication, real CPSE notation | tuning | free to re-run |
| Synthetic test | family-level split made before variants; unseen corruption recipes | method check | run **once**, timestamped; re-run needs `--force` |
| Real dev — Oil India + NTPC | 485 lines, labelled by Claude while building | building the extractor | **never reported as a result** |
| **Real test — Oil India + NTPC** | 417 lines, labelled by two people independently | real-world check | nobody tunes on these rows; disagreements resolved and logged |
| Near-miss traps | several hundred, generated systematically | safety | every grade pair, every pressure-class pair, adjacent designations, bolt grades, valve types |

**Real data source:** `Prasenjeet25/sih26099-cpse-material-codes` on Hugging Face,
**CC-BY-4.0 — the licence requires attribution, so it is credited on the references slide.**
902 candidate material lines mined into `data/real/candidates.csv` — **Oil India 546, NTPC
351, IOCL 5** — every row traceable to a source document. It is real **tender text from two
CPSEs**, one of them an oil-and-gas company under the same ministry as this PS. It is not a
material master — say exactly that.

**No public real CPSE material master exists.** GeM, CPPP, data.gov.in, Kaggle and Hugging
Face were all checked. Material masters are internal ERP data; companies publish tenders,
never their master tables. Every system on this problem statement — ours included — is
evaluated on invented data. The real hold-out is what sets ours apart.

---

## 6. Evaluation

**Three datasets, reported separately, never blended into one number.**

**Three layers:**

| Layer | Question | Metric |
|---|---|---|
| A | Did the true pair reach the scorer? | Recall@K **and** reduction ratio, always together |
| B | Is the scorer good? | P / R / F1 per band, against baselines **on the same candidates** |
| C | What does a reviewer experience? | auto-band precision, review load per 1,000 records |

Precision without blocking recall beside it is meaningless — precision *improves* as
blocking throws away true pairs.

**Four baselines on the same candidates:** fuzzy string · TF-IDF cosine · pure embedding ·
ours.

**Also reported:** hard-negative veto accuracy over the full trap set · **functional-
equivalence recall on its own line** (different words, same item — the hardest case) ·
contradiction detection rate · extraction coverage on real text · LLM fallback rate per
category · a conformal bound on the auto-band error rate.

---

## 7. Coverage of the problem statement

**Key capabilities — all eight covered.**

| # | Capability | Covered by |
|---|---|---|
| 1 | AI matching & recommendation | stages 04–10, creation gate |
| 2 | Standardisation & classification | stages 01–02, 11 |
| 3 | Duplicate / near-duplicate detection | stages 06–10 |
| 4 | National material code generation | stage 11 |
| 5 | Mapping & migration support | mapping table + staged migration pack |
| 6 | Dashboard & analytics | overview + data-quality scorecard |
| 7 | Audit trail & governance | stage 12 |
| 8 | SAP / ERP integration | SAP-shaped export + named integration boundary |

**Expected impact.**

| Impact | Covered by |
|---|---|
| Reduced duplication | raw → unique, per company and nationally |
| Rationalisation | retire list — proposed only to the company that owns the code |
| Demand aggregation | savings view, k-anonymity 3 |
| Faster procurement and specification finalisation | creation gate; INCOMPLETE verdict names the missing fields |
| Inventory optimisation | through duplicate reduction and demand aggregation — **no stock figure; no stock data exists** |

---

## 8. Do not build

Trained matching model · embedding fine-tuning · auto-tuning thresholds · Copilot · voice ·
OCR · chatbot · blockchain audit · image recognition · privacy/PPRL implementation ·
live SAP connection · stock or inventory ledgers · prohibiting same-company matching ·
more than 13 categories before December.

---

## 9. Claims

**We can say:**
- Deterministic, reproducible, auditable matching decisions
- Standards-aware matching across manufacturers and description styles
- Knows which Indian and international standards are identical, which are only close,
  and which have been withdrawn and replaced
- Records validated against themselves before comparison
- Every extracted value traceable to its source text
- Duplicates prevented at creation, not only cleaned
- Works inside one CPSE on day one, with no inter-company agreement
- Significantly reduced data exposure for cross-CPSE analytics
- SAP-compatible export and a documented integration boundary
- Tested on real Oil India and NTPC material descriptions as well as synthetic data — both reported
- Nothing trained, so nothing needs retraining on a new company's data

**We must never say:**
- 100% precision, or any single blended precision figure
- Production or live-deployment accuracy
- A locked test result that has not actually been run
- Live SAP integration
- Secure, private, encrypted or cryptographic — about anything
- That the real set is a material master (it is tender text from two CPSEs)
- That procurement data proves technical equivalence
- That we invented entity resolution or attribute-based matching
- Any inventory or stock reduction figure

---

## 10. The PPT — six slides

**How it is scored.** SIH reviewers weigh problem understanding, novelty, feasibility,
impact and completeness; third-party guides put problem understanding near 30%. So the
deck opens on the real NTPC tender — that slide *is* the problem-understanding score — and
slide 3 shows plainly where AI is used: the LLM reads specifications, embeddings find
candidates, and a statistical bound limits the error. Nothing is left implicit.

**1 · Title.**

**2 · Proposed solution.** Open with the real NTPC tender: the same pipe written three ways
in one document, and SEAMLESS vs SMLS in another. Then the inversion — two records for one
bearing share no words; two records for different steel share almost all of them. Text
matching gets both backwards, so **we match on specifications, not spelling.** Then the
five features no one else has.

**3 · Technical approach.** The pipeline diagram — one picture covers capabilities 1, 2, 3,
4 and 7. *The AI reads; the rules decide.* One screenshot.

**4 · Feasibility and viability.** Numbers from the runs — synthetic and real, side by side.
Runs offline on a laptop. The honest line: synthetic numbers measure how well we undo
errors we created, which is why the real ones are beside them. Challenge: no CPSE will share
prices. Answer: Phase 1 needs no sharing at all.

**5 · Impact and benefits.** Savings from buying together · merges refused for safety ·
duplicates stopped at creation · a migration a CPSE's SAP team can actually load.

**6 · Research and references.** UNSPSC · ISO 15 · ASME B36.10, B16.5 · IS 1367 (Part 3) / ISO 898-1 · ASTM F3125 ·
the Hugging Face dataset, credited as its CC-BY-4.0 licence requires.

---

## 11. Demo — 90 seconds

| Sec | Show | Say |
|---|---|---|
| 0–15 | the real NTPC tender: one pipe, three spellings | "This is a real government document." |
| 15–30 | `6205` vs `25X52X15MM` | "No shared words. The standard says they're the same bearing." |
| 30–45 | SS316 vs SS304, text 0.989 → blocked | "Near-identical text. Grade is a veto." |
| 45–60 | counterfactual panel | "If the grade matched, this would score 0.94. One field decides." |
| 60–75 | self-contradictory record | "It contradicts itself. Caught before it can match anything." |
| 75–90 | creation gate → NEW, and not these two | "It stops the mess coming back." |

Pre-computed results. No live LLM call. Same run every time.

---

## 12. Build plan

### Before submission — 24 to 27 September

| Day | Who | Task | Hrs |
|---|---|---|---|
| **Wed 24** | Madhu | Dimensional notation; real grades (FE410, TP304L, A312, A106, IS1239, A423); SMLS / ERW / GLV / BLK; add cable, fitting, plate, tube | 6 |
| | Yash | Blocking — category + identity signature | 2 |
| | Rashmit | Systematic near-miss traps; `tests/test_hard_negatives.py` | 3 |
| | Isha, Meghna | Label the 417 real test rows separately — ~200 each | — |
| **Thu 25** | Rashmit | Regenerate 15,000 at 20% in real notation; full pipeline; **numbers frozen tonight** | — |
| | Madhu | Standards tables — ~20 bearings, ~20 bolt equivalences; derive stage | — |
| | Isha, Meghna | Finish all 417; `labels.py compare`; decide disagreements; `finalise` | — |
| | Aditya | UI shows the new numbers | — |
| | Meghna | Evidence boundary into the README | 0.5 |
| **Fri 26** | Meghna, Madhu | Write the deck. Evening: whole team reads it aloud | — |
| **Sat 27** | all | Export PDF. Submit. Touch nothing after. | — |

**The test before submitting:** run five real rows through the system. If it still
extracts nothing, the deck is describing a system that doesn't work on the data it claims
to serve. Fix that before anything else.

**If something slips, drop in this order:** standards tables → UNSPSC mapping → UI updates.
**Never drop:** the extraction fix, blocking, labelling, or the 15,000 records.

### October to December

1. Self-check engine · counterfactual panel · evidence spans
2. Relationship classes incl. VARIANT_OF · substitution table
3. Governance — audit log, five verbs, consent model, dispute flow
4. Staged migration pack · data-quality scorecard · plant scope
5. Three-layer evaluation · locked test · four baselines · conformal bound
6. Fusion order · review priority · random audit card · prevented-duplicate counter
7. Scrape more NTPC tenders → 3,000+ real lines; re-run the real evaluation
8. Transitive standards equivalence · pack-size algebra
9. December: rehearsal only. Runs identically three times in a row.

**Regression rule:** every change to the scorer, schemas or standards must pass the
hard-negative tests before it is merged.

---

## Change Log

| Date | Change | Reason |
|---|---|---|
| 17 Sept 2026 | Frozen | Final architecture agreed. |
| 24 Sept 2026 | Governance: dual approval → **consent scales with harm; dispute, not veto** | Dual approval deadlocks the registry — one silent company blocks a code forever. A national code changes nothing inside a CPSE's system, so linking needs no permission; only retiring a code does. |
| 24 Sept 2026 | Added **cross-standard equivalence** (IS ↔ ISO ↔ ASTM) to stage 04 | CPSEs tender on IS and receive ASTM/DIN supply. |
| 24 Sept 2026 | Added **dimensional notation** and real NTPC abbreviations to stage 01 | Our extractor returned nothing for 682 of 902 real rows; real Indian text writes NB and MM, not inches. |
| 24 Sept 2026 | Categories 9 → 13 (cable, fitting, plate, tube) | 39% of real rows classified as unknown. |
| 24 Sept 2026 | Blocking made explicit as stage 06 | All-pairs at 15,000 records is 112 million pairs and exhausts memory. |
| 24 Sept 2026 | Added service qualifiers → UNDETERMINED; VARIANT_OF; review priority + random card; fusion order; MARK_DIFFERENT; staged migration; scorecard; prevented-duplicate counter | Strengthens safety, review speed and governance. |
| 24 Sept 2026 | Real NTPC hold-out replaces "GeM/CPPP hold-out" | No public real material master exists; Oil India and NTPC tender extracts are the only real material text available. |
| 24 Sept 2026 | Traps 4 → several hundred, generated systematically | Four traps is not a safety claim. |
| 24 Sept 2026 | Copilot, voice, OCR, privacy implementation added to Do Not Build | They do not improve matching and break under questioning. |

| 24 Sept 2026 (late) | A6: item factory + real-notation renderers, 15,000-record run; variant fields become veto fields; one-sided silence and "several variants, both silent" hold a pair for review; non-cohesive groups split | The first 15,000 run auto-merged 2,625 wrong pairs (31%). After: 846 auto-merges, 0 wrong, 0 of 104,994 traps; test families (never tuned) match dev. |
| 24 Sept 2026 (evening) | Built A1, A2, A4, A5: real-text reader (`normalise.py`, `rules.py`), 4 new categories + "other", grade-family ladder, `blocking.py` with meta-blocking, 234 tests; code frozen, then test rows labelled | Dev 2+ facts 3% → 93%. Real test (frozen code): 0 wrong auto-merges, recall 86.4%, review precision 17.8%. Synthetic recall 0.942 → 1.0 (two false vetoes removed). |
| 24 Sept 2026 | Every mechanism in section 3 redesigned: extended with derivation, safety criticality, direction or the consent model | Each becomes this system's own design, and stronger for it. |
| 24 Sept 2026 | Size handling corrected: NB / DN / NPS treated as designations, not measurements | "15NB = 15mm" is wrong as a dimension — a 1/2" pipe is 21.3 mm OD. Real NTPC text pairs `500NB` with `508MM`; only designation-aware handling matches them. |
| 24 Sept 2026 | Service qualifiers: UNDETERMINED → directional SUBSTITUTE | "Undetermined" tells procurement nothing; a direction tells them which item to stock. |

| 24 Sept 2026 | `ASTM A325` → `ASTM F3125 Grade A325`; added **standards supersession** to stage 04 | ASTM withdrew A325 in 2016 and folded it into F3125 as a grade. Citing a withdrawn standard as current on a slide is an error a refinery engineer would catch. Old records still say A325, so the system must map old designations to new. |
| 24 Sept 2026 | `IS 1367` → `IS 1367 (Part 3)` | IS 1367 has many parts; Part 3 is the one BIS adopted as identical to ISO 898-1. |

| 24 Sept 2026 | Real data corrected: **902 lines from two CPSEs** (Oil India 546, NTPC 351, IOCL 5), not 333 from one | An earlier mining run never read the 21,513-row corpus — a file-name error — so it reported Oil India as contributing nothing. Rebuilt reproducibly with `src/mine_real.py`. Extraction coverage re-measured on the full set: 21 of 902 usable. |

| 24 Sept 2026 | Real data split into **dev** (485 lines, labelled by Claude, used only for building) and **test** (417 lines, two people, blind). `src/labels.py` gives each labeller a separate sheet. | Whoever builds the extractor can't also write the answer key it's judged by. And one shared sheet can't keep two labellers independent. Dev labelling also measured the gap: the extractor reads 2+ facts from 3% of real items, and 36% of real items fall outside the 13 categories. |

*Add a row here before changing anything above. No row, no change.*
