# Meghna — domain, narrative, presenting

Your deliverable is not a document. It is your own understanding.

On the day, the deck is not what convinces anyone — the answer to the follow-up
question is. Finale judges are ministry and PSU people who will cross-question,
and a presenter reciting slides falls apart in one exchange.

---

## The story, in the order it should be told

**1. The scene.**
Ravi runs the material catalogue at CPCL Manali. An engineer asks for a 6205
bearing. Ravi searches "BEARING 6205" — nothing. So he creates a new code. But it
was already there, written `BRG BALL DP GRV 6205` by someone years ago. **Now one
bearing has two codes, inside one company.**

**2. Multiply by five companies.**

```
CPCL   100004521   BRG BALL DP GRV 6205 2RS SKF
IOCL   MAT-88213   BEARING,BALL,6205-2RS,SKF
ONGC   5000123     BALL BRG SKF 6205 2RS
BPCL   BRG-4471    DEEP GROOVE BALL BEARING 6205
GAIL   G/001290    BER BALL D/GROOVE 6205
```

One bearing. Five companies. Five codes. Five different prices — ₹1,205 to ₹1,495
— and nobody can see anyone else's.

**3. The twist — why it is hard.**
People assume text matching solves this. It fails both ways:

- SKF vs FAG: no shared words, same bearing → a matcher **misses** it
- SS316 vs SS304: 97% identical text, different item → a matcher **wrongly merges**
  it, and in a refinery that is a leak

**4. Our answer.**
*"We don't match on spelling. We match on specification."* Extract structured
specs first, ignore brand, veto on grade.

**5. The number.**
100 records → 15 items, 85% duplication. ₹18.95 cr multi-CPSE spend, ₹3.3 cr
identified.

**6. Close.**
*"We're not cleaning a catalogue. We're finding the money companies lose because
they can't see each other's data — and doing it without showing anyone anyone
else's data."*

---

## Learn these cold

Not to recite — so you can answer sideways questions.

| Topic | What you need to know |
|---|---|
| Material master | The catalogue of everything a company buys. Lives in SAP tables `MARA` (general), `MAKT` (descriptions), `MARC` (plant). |
| Why descriptions are cryptic | The standard description field `MAKTX` is 40 characters — **still, today, not just legacy**. Plus: migration from older systems, and no enforced cataloguing standard. |
| SS316 vs SS304 | SS316 has ~2–3% molybdenum; SS304 has none. That gives chloride and acid corrosion resistance. Wrong one in corrosive service → pitting → leak. |
| 150# vs 300# | ANSI pressure classes. **`150#` is a class, not 150 psi** — a Class 150 A105 flange is ~285 psig at ambient and derates with temperature. Saying this correctly signals real domain knowledge. |
| 6205 | ISO bearing designation. 25 mm bore, 52 OD, 15 wide. Any manufacturer's 6205 is interchangeable — that is what makes our demo case true. |
| The competitors | Informatica, SAP MDG, Verdantis, PROSOL (this one serves oil & gas in India). |

Everything with a confidence level and a verification route:
[`../03-reference/domain-facts.md`](../03-reference/domain-facts.md)

---

## ⚠️ One thing to verify yourself

Open SAP `SE11` → table `MAKT` → field `MAKTX`. Confirm it is `CHAR 40`.
**Screenshot it.**

A CPCL judge can check this in seconds. A fact you have verified yourself is
spoken with confidence; a fact you were told collapses under one follow-up.

**And be careful with the framing.** The 40-character field is one reason
descriptions are abbreviated, not the only one.

❌ "Descriptions are cryptic because SAP limited the field to 40 characters."
✅ "Several reasons — the description field is still 40 characters, data migrated
from older systems, and most importantly there was never an enforced cataloguing
standard. So every storekeeper invented their own shorthand."

The second cannot be corrected by a judge, and invites agreement rather than
contradiction.

---

## Five questions you will be asked

**1. "Informatica already does this. Why you?"**
> "You're right that attribute-based matching is proven — that's what commercial
> MDM does. We're not claiming invention. The difference is architectural: those
> tools need every company's data in one place, and no CPSE will hand over its
> prices and vendor list. That's the actual reason a national material master has
> never existed. We match without centralising anyone's data."

**2. "What if it merges the wrong thing?"**
> "Grade, pressure rating and key dimensions are veto fields — a mismatch is an
> instant zero regardless of everything else. Anything uncertain goes to a human
> reviewer, and the PS asks for that workflow explicitly. And every merge is
> reversible; nothing is ever deleted."
> Then show the blocked list.

**3. "We have four lakh codes. How long, and what does it cost?"**
> "One AI call per record, once, cached — never per comparison. About ₹17,000 of
> inference for a million records. If we called per pair it would be lakhs, every
> single run."

**4. "What if the AI hallucinates a specification?"**
> "The model extracts attributes; it never decides a merge. Matching is
> deterministic arithmetic over what was extracted, so every score is reproducible
> and every merge is explainable. And the model is instructed to return nothing
> rather than guess — those records route to review."

**5. "Why would CPSEs share their data?"**
> "They don't have to. Only encoded values cross the boundary — an embedding
> instead of the description, a price band instead of the price, a hash instead of
> the vendor name. Equal hashes prove 'same vendor' without naming it. And we show
> a benchmark, never who achieved it."
> Then add the honest limit: *"this significantly reduces exposure — it is not
> cryptographic privacy. Full MPC is roadmap."*

---

## What to volunteer before being asked

Read [`../04-risks/honest-limits.md`](../04-risks/honest-limits.md) fully.

A limitation you raise yourself costs nothing and buys credibility for everything
else. The same limitation found by a judge costs you the room.

The three to get ahead of:

1. **Our accuracy number is circular** — we generated the corruption we measure
   against.
2. **The savings figure is an upper bound** — give the conservative number too.
3. **The idea is not novel** — claim execution and scope, never invention.

---

## Presenting

You carry the story. Madhu or Yash take deep technical questions. **That split is
normal and allowed** — say "let me bring in Yash on the scoring detail" rather than
guessing.

Start domain prep now, not in December. The finale is decided by the Q&A, not the
slides.
