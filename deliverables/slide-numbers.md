# Slide numbers — locked at tag `ppt-numbers-2026-09-25`

For slides 4 and 5. **Use only numbers from this sheet.** Each one comes from a file at the tag;
if a number is not here, it does not go on a slide. The portal's dashboard shows the same
numbers ("How we know it is safe"), read from `data/output/evidence.json`.

To check any number yourself: `git checkout ppt-numbers-2026-09-25`, then open the file named
beside it.

---

## Slide 4 — Feasibility: does it work?

### The headline: it never merged anything wrong

| Say this | Number | Source |
|---|---|---|
| "On 15,000 material records written the way NTPC, Oil India and SAP write, the system merged **860 pairs on its own, and none were wrong**." | 860 auto-merged, 0 wrong | `evidence.json` → `run15k` |
| "With 95% confidence, the wrong-merge rate is **below 0.35%**." | < 0.35% | `run15k.auto_error_bound_95` |
| "One in five item families was locked away before tuning and only scored at the end. There it merged **217 pairs, 0 wrong**." | 217 / 0 | `run15k.by_split.test` |
| "We planted **104,994 near-miss traps** — SS304 against SS316, 150# against 300#, a 6205 bearing against a 6305. It merged **none** of them." | 0 of 104,994 | `run15k.traps_*` |
| "With a reviewer, it finds **82%** of the duplicates." | 82% | `run15k.recall_with_review` |
| "For a reviewer, the right match is in the **top three for 78%** of records." | 78% | `run15k.review_queue` |

### Why not just match the text? (the comparison slide)

Same 15,000 records, same candidate pairs, each text method at its best setting (tuned on one
half, scored on the half it never saw). Source: `evidence.json` → `run15k.baselines`.

| Method | Merged | Wrong | Traps merged | Right |
|---|---|---|---|---|
| Fuzzy string match | 3,334 | 3,120 | 1,468 | 6% |
| TF-IDF | 2,112 | 1,953 | 1,121 | 8% |
| Sentence embeddings | 4,068 | 3,783 | 1,697 | 7% |
| **Ours — specifications** | **217** | **0** | **0** | all of what it merged |

Say: "At their best setting, text matchers are right less than one time in ten. No setting gets
them to zero wrong — two different items can have identical text once SAP's 40-character field
cuts them. We find about as many duplicates with no human, with **none** of the wrong merges."

### On real tender text (the honest number — put it beside the others)

252 real material lines from Oil India and NTPC tenders, held back while building.
Source: `data/output/real_metrics.json`.

| Say this | Number |
|---|---|
| "It read the item type right for **98%** of real lines." | 97.9% |
| "It read two or more facts from **90%**." | 90.3% |
| "It merged **4 pairs on its own — 0 wrong**." | 4 / 0 |
| "With a reviewer, it found **49 of 59** real duplicate pairs (83%)." | 83.1% |
| "Its weak point: only **18%** of what it sends a reviewer is a true duplicate — a short line fits several items. So the reviewer sees one record with its best three candidates, not a list of pairs." | 17.9% |

**Always say with the real number:** the labels are one person's so far (the builder's);
two team members are labelling separately, and their labels replace these.

### Reading real text (slide 2 or 4)

"`Line Pipe 101.60 mm Seamless, B/E, 12.66 PPF` and `Line Pipe, 4", Seamless, B/E, 12.66 PPF`
are the same pipe — only the weight proves it. Two lines that say `101.60 mm` with 12.66 and 19
lb/ft are **different** pipes: the weight means a different wall." (Portal page *Real Tender
Text*.)

---

## Slide 5 — Impact

| Say this | Number | Source |
|---|---|---|
| "**13,128** refused merges were one field away from happening — everything else agreed. **13,127** of them really were different items." | 13,128 / 13,127 | `run15k.blocked_one_field`; the check is in CLAUDE.md |
| Demo: "If the material grade matched, this pair would score **0.956**. One field decided — not a threshold." | 0.956 | portal page *Case: The Block* |
| Demo set savings: "**₹2.31 crore** upper bound, **₹0.92 crore** realistic, on ₹22.6 crore of spend, from buying together." | ₹2.31 cr / ₹0.92 cr | `data/output/savings.json` |
| "A new request is checked before a code is issued. It says what an item is **not**, and stops a line that **contradicts itself**." | gate verdicts | `data/output/gate.json` |
| "Every decision is sealed to the one before it. Change one word and the check fails." | — | portal page *Audit Trail* |

---

## Do not say

- "100% accurate" or "100% precision". Say **"0 wrong out of 860"** and **"below 0.35%"**.
- "Production-ready", "live SAP integration", "secure", "encrypted". Say *prototype*,
  *SAP-shaped export file*, *reduces data exposure*.
- "Material master" about the real data. It is **tender text from two CPSEs**.
- Any synthetic number without the real one beside it.
- The 86.4% from the first freeze on its own. The locked number is **83.1%**; the first freeze
  is kept in `data/real/labels/frozen.json` history.
