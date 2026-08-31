# Demo day

Tuesday 1 September 2026 — college internal round.

---

## ⚠️ Still unconfirmed

**Is a live demo allowed, and how many minutes?**

Open since the start. Everything about rehearsal depends on it. Madhu to confirm
with the SPOC.

Prepare both: a **3-minute** version (screens 01, 02, 03) and a **6-minute**
version (all five). If time is cut, drop 04 and 05. **Never cut 02.**

---

## The night before

```
[ ] python src/generate_dataset.py
[ ] python src/extractor.py --fresh          (real extraction, with key)
[ ] python src/embed.py                      (caches the model)
[ ] full pipeline -> results.json regenerated
[ ] cd ui && npm run build
[ ] numbers in the deck match numbers in results.json
[ ] copy dist/ to the phone, open it, check it works offline
[ ] three full rehearsals with a timer
[ ] laptop charged, charger packed
```

---

## The morning of — run with wifi OFF

```
[ ] wifi OFF
[ ] double-click ui/dist/index.html          -> loads, not blank
[ ] all five screens render
[ ] screen 02 animation plays; replay button works
[ ] screen numbers == deck numbers
[ ] phone copy opens, comparison readable stacked
[ ] projector tested at venue resolution
[ ] deck PDF on a phone as final backup
```

If any line fails, fix it before leaving.

---

## The demo sequence

**Do not open with two obviously similar records merging.** It looks like string
matching and invites the wrong question.

### 1 · Headline (20s)
100 records → 15 items. 85% duplication. ₹18.95 cr multi-CPSE spend.

### 2 · The Match (90s) — the whole argument

```
"SKF 6205-2RS DEEP GROOVE BALL BEARING"
"FAG 6205-2RSR BEARING, 25X52X15MM, SEALED"
```

> "Two records. Different companies. Almost no words in common."

Text similarity fills to 0.31, red.

> "A conventional fuzzy matcher stops here. It would miss this."

**Pause.** Let it sit.

Specs slide in, ticking one by one. Brand row lands last, greyed out.

> "6205 is an ISO designation — any manufacturer's 6205 is the same bearing.
> We ignore brand entirely. That's what lets SKF and FAG resolve to one item."

Score counts to 0.94.

### 3 · The Block (60s) — the reverse

```
"GASKET SPIRAL WOUND SS316 4IN 150#"
"GASKET SPIRAL WOUND SS304 4IN 150#"
```

> "Now the opposite. One character different. 97% textually identical — a fuzzy
> matcher merges these."

Show the block.

> "SS316 has molybdenum; SS304 doesn't. In corrosive service the wrong one leaks.
> Grade is a veto field — no text similarity can override it."

**The line:**

> "A conventional tool misses the first and wrongly merges the second. We match on
> specifications, not spelling."

### 4 · Review queue (45s)
> "Anything uncertain goes to a cataloguer who already knows SS304 isn't SS316.
> The PS asks for this workflow explicitly. Five seconds a decision, keyboard
> only."

### 5 · Savings (45s)
One bearing, five CPSEs, five prices, ₹1,205 to ₹1,495.

> "Upper bound across the dataset is ₹3.3 crore, if everyone got the best price
> already observed. At a realistic 40% capture, about ₹1.3 crore. We show both."

### Close (20s)
> "We're not cleaning a catalogue. We're finding money companies lose because they
> can't see each other's data — and doing it without showing anyone anyone else's
> data."

---

## If it breaks

**Do not debug on stage.** It looks worse than the failure.

1. Phone copy — *"Let me show you this on the phone."*
2. Deck screenshots — the argument does not need the software.
3. Keep talking. The two cases can be explained from a slide.

Screenshots of all five screens belong in the deck for exactly this reason.

---

## Who says what

**Meghna** carries the story and the demo.
**Madhu or Yash** take deep technical questions.

The handover is normal and allowed — *"let me bring in Yash on the scoring
detail"* reads as a real team, not a gap.

Prepared answers: [`../04-risks/judge-questions.md`](../04-risks/judge-questions.md)

---

## Three things to volunteer before being asked

1. **The accuracy number is circular** — we generated the corruption we measure
   against.
2. **The savings figure is an upper bound** — give the conservative one too.
3. **The idea is not novel** — claim execution and scope, never invention.

A limitation you raise yourself costs nothing. The same limitation found by a
judge costs you the room.

[`../04-risks/honest-limits.md`](../04-risks/honest-limits.md)
