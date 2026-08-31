# Madhu — architecture, extraction, integration

You own the critical path and the joins between everyone else's work.

---

## Priority order

**1. Real extraction, hand-checked.** This is build-order step 1 and nothing
downstream is trustworthy until it passes.

```bash
set GEMINI_API_KEY=your_key_here

python src/extractor.py --limit 10      # sanity check first
python src/extractor.py                 # full run, ~7 min at free-tier pace
python src/extractor.py --validate      # the hand-check view
```

Read 50 records against their source text. You are checking for:

- Fields invented that are not in the description (the worst failure — a
  fabricated spec that later drives a merge)
- Confidence scores that do not reflect reality — a derived value marked 0.98
- Wrong category assignment
- Anything in `dropped_fields`, which means the model returned fields outside the
  schema

Regex currently gets 2.3 fields per record. Gemini should reach 5–7. **That
difference is measurable and belongs on a slide.**

**2. Stub `results.json` to Aditya — before anything else is real.** He has the
longest job and cannot start without it. Five fake clusters is enough. Shape is
in [`aditya.md`](aditya.md).

**3. The remaining stages.**

```
src/scorer.py        signal fusion, hard blockers, union-find clustering
src/canonicalise.py  golden record, standard description, UNSPSC, national code
src/savings.py       demand aggregation from purchases.csv
src/results.py       bundle everything into results.json
```

---

## The standard description is its own deliverable

Easy to treat as a footnote of the canonicaliser. It is not — the PS lists
"automated standardization of material descriptions" as a separate bullet.

Once specs are typed it is a template render, and it makes the extraction work
*visible*:

```
BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED
PIPE, SEAMLESS, CARBON STEEL, ASTM A106 GR B, 4 IN, SCH 40
VALVE, GATE, 6 IN, 150#, CS BODY, FLANGED
```

Noun first, then modifiers in significance order. This is the format industry
actually uses, and it demos extremely well.

---

## The savings report is the highest-value hour in the project

Once clusters exist it is a `GROUP BY` over `purchases.csv`. Roughly an hour of
work, and it turns a data-cleaning project into a money project.

Current numbers from the dataset: ₹18.95 cr multi-CPSE spend, ₹3.3 cr identified
at best-observed-price.

⚠️ **Report both figures.** ₹3.3 cr is the theoretical upper bound — everyone
achieving the best price anyone got. A procurement person will know that
immediately. Give the conservative number unprompted: *"upper bound ₹3.3 cr; at a
realistic 40% capture, ₹1.3 cr."* The conservative figure is what makes the
optimistic one credible.

Also apply **k-anonymity**: suppress the benchmark when fewer than three CPSEs are
in a cluster. With only two, the minimum price *is* the other party's price.

---

## The safety interlock report — one day, most memorable slide

Everyone will show merges. Show what we **refused** to merge:

```
Merges BLOCKED by safety rules

  material grade mismatch  (SS304 vs SS316)   n
  pressure rating mismatch (150# vs 300#)     n
  price anomaly (over 10x)                    n
  bearing designation      (6205 vs 6206)     n
```

Yash's scorer already records `blocked_by` per pair. This is a count over that.

---

## Rules you are the guardian of

Everyone else can forget these. You cannot.

1. **One LLM call per record, never per pair.** If any design drifts toward
   per-pair calls, stop it. See [`../02-decisions/002-llm-once-per-record.md`](../02-decisions/002-llm-once-per-record.md).
2. **The LLM extracts; it never decides a merge.**
3. **`data/truth/` never enters the pipeline.**
4. **Nothing is destroyed.** Raw is append-only; every stage writes its own file.
5. **No live AI call in the demo path.**

---

## Known trap: the stale cache

`specs.json` is a cache keyed by `record_id`. Regenerating the dataset produces new
records; the cache still holds specs for the old ones.

**After any `generate_dataset.py` run, use `--fresh`.** This has already bitten us
once.

---

## Done when

- [ ] Extraction validated by hand on 50 records
- [ ] Stub `results.json` delivered to Aditya
- [ ] `python src/run_all.py` turns the CSVs into `results.json` in one command
- [ ] Both demo cases verified end to end — match at high confidence, block on
      grade
- [ ] Savings report producing both the upper-bound and conservative figures

---

## Open items you own

- Confirm the internal round format with the SPOC — demo allowed? time limit?
  **Still unconfirmed and everything downstream of rehearsal depends on it.**
- Fix the `MAKTX` framing in `CLAUDE.md` and `deliverables/architecture.html` —
  present tense, and one reason among several. See
  [`../03-reference/domain-facts.md`](../03-reference/domain-facts.md).
- Decide whether to drop the two low-confidence vendor names from the seed list.
