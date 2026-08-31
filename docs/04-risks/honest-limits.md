# Honest limits

Claims we cannot fully defend, and the safe way to phrase each one.

**The rule: volunteer the limitation before you are asked.** Stated up front, a
limitation reads as rigour. Discovered by a judge, the same limitation reads as
either sloppiness or spin, and it puts every other claim in doubt.

---

## 1. Our accuracy number is circular

**The problem.** We designed the corruption in our own dataset, so "98% precision"
means *"we reversed 98% of the errors we ourselves introduced."*

**Don't say:** "Our system achieves 98% precision."

**Say:** "On our synthetic benchmark we get 98% precision — but we generated that
corruption, so that number measures how well we undo our own noise. The number we
trust more is from a hand-labelled hold-out of real records, and it is lower."

**Fix in progress:** 200–300 real records from GeM and eprocure, labelled by the
team, reported alongside. See [`../02-decisions/006-synthetic-dataset.md`](../02-decisions/006-synthetic-dataset.md).

---

## 2. We send descriptions to a foreign API, while arguing for sovereignty

**The problem.** Our strongest strategic argument is that CPSEs will not put
procurement data on a foreign vendor's platform — and our extractor calls Gemini.

**Say, before being asked:** "The prototype uses a hosted model for extraction. In
deployment this is an on-premise model — the architecture is unchanged, only the
endpoint. Descriptions do not leave the CPSE in production. Embeddings already run
entirely locally for exactly this reason."

**Fix:** a local extraction model. Highest-value experiment after the internal
round. See [`../02-decisions/004-gemini-for-extraction.md`](../02-decisions/004-gemini-for-extraction.md).

---

## 3. "Scales to millions" is arithmetic, not a benchmark

**The problem.** We have run 100 records. We have not run a million.

**Don't say:** "It scales to millions of records."

**Say:** "The design is built for it — one AI call per record cached at ingestion,
and blocking to avoid all-pairs comparison. At a million records blocking gives
about 99.996% reduction. We have not benchmarked a million records; we built the
hard part first."

---

## 4. The privacy layer is exposure reduction, not cryptography

**The problem.** Embeddings are partially invertible. Bloom-filter encodings have
known attacks. Price bands leak magnitude.

**Never say:** "cryptographically secure", "provably private", "zero-knowledge".

**Say:** "This significantly reduces data exposure — raw descriptions, exact
prices and vendor identities stay inside the company. It is not cryptographic
privacy. Full secure multi-party computation is the roadmap; we implemented the
exposure-reduction layer."

Also state the k-anonymity rule unprompted: with fewer than three CPSEs in a
cluster, the benchmark is suppressed, because with two the minimum price *is* the
other party's price.

---

## 5. The dataset is not verified against real CPCL data

**The problem.** Standards in the seed list are correct and checkable. Vendor
lists are real companies but unconfirmed as CPCL suppliers. Prices are estimates —
the bearing at ₹1,310 is probably high.

**Say:** "This is a synthetic evaluation dataset modelled on public GeM and tender
nomenclature. We don't claim these are CPCL's actual codes or prices — we claim
the variation patterns are realistic. On a real extract only the seed list
changes."

Confidence levels per claim: [`../03-reference/domain-facts.md`](../03-reference/domain-facts.md).

---

## 6. The savings number is an upper bound

**The problem.** ₹3.3 cr assumes every CPSE gets the best price anyone achieved.
Real consolidation captures a fraction of that. A procurement person will know
this immediately.

**Don't say:** "We identified ₹3.3 crore in savings."

**Say:** "₹3.3 crore is the upper bound, if everyone achieved the best price
already observed in the group. At a more realistic 40% capture rate it is around
₹1.3 crore. We are showing both."

Giving the conservative number unprompted is what makes the optimistic one
credible.

---

## 7. The idea is not novel, and we should say so first

**The problem.** Commercial MDM exists — Informatica, SAP MDG, Verdantis, PROSOL
(which serves oil and gas in India). Entity resolution dates to 1969.
Attribute-based matching is what those tools already do.

**Don't say:** "We invented a new approach to material matching."

**Say:** "Attribute-based matching is proven — this is what commercial MDM does.
We're not claiming invention. We're claiming three things they don't do:
cross-CPSE scope rather than single-enterprise, learning the abbreviation
vocabulary from the corpus instead of consultants building it per client, and
matching without centralising anyone's data."

---

## 8. Things we have designed but not built

Say "designed, not yet built" — never imply otherwise.

| Component | State |
|---|---|
| Audit log table | Designed, data model supports it, table does not exist |
| Blocking stage | Designed and documented, deliberately skipped at this scale |
| Federated privacy layer | Architecture only |
| SAP integration | Export format and adapter interface, no live connection |
| Review UI | Specified, not built |
| Learned abbreviation vocabulary | Idea only |

---

## The general principle

> A limitation you raise yourself costs you nothing and buys you credibility for
> everything else. A limitation a judge finds costs you the room.

If a claim cannot go in [`../03-reference/domain-facts.md`](../03-reference/domain-facts.md)
with a confidence level and a way to verify it, it does not go in the deck.
