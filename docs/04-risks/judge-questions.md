# Judge questions

Prepared answers. Meghna carries the story; Madhu or Yash take deep technical
questions — **that split is normal and allowed.** Saying *"let me bring in Yash on
the scoring detail"* is stronger than guessing.

---

## Strategic

**"Informatica and SAP MDG already do this. Why do we need you?"**

> "You're right that attribute-based matching is proven — that's what commercial
> MDM does, and we're not claiming invention. The difference is architectural.
> Those tools need every company's data in one place, and no CPSE will hand over
> its prices and vendor list. That's the actual reason a national material master
> has never existed — it's a trust problem, not a technology problem. We match
> without centralising anyone's data."

**"Why should this be built in India rather than bought?"**

> "National strategic procurement data shouldn't sit on a foreign vendor's
> platform. And commercial tools need consultants building rules and dictionaries
> per client over months — we learn the abbreviation vocabulary from the corpus
> itself, so onboarding a new CPSE is days, not months."

**"What is genuinely new here?"**

Do not overclaim. The honest version:

> "The matching technique isn't new — entity resolution dates to 1969. What's new
> is the scope and the constraint: cross-CPSE rather than single-enterprise, and
> matching that works without any company exposing its raw data."

---

## Technical

**"What if it merges the wrong thing?"**

> "Grade, pressure rating and key dimensions are veto fields — a mismatch is an
> instant zero regardless of everything else. Anything uncertain goes to a human
> reviewer, which the PS asks for explicitly. And every merge is reversible;
> nothing is ever deleted."
>
> Then show the blocked list. *"Here's what we refused to merge, and why."*

**"What if the AI hallucinates a specification?"**

> "The model extracts attributes; it never decides a merge. Matching is
> deterministic arithmetic over what was extracted, so every score is reproducible
> and every merge is explainable field by field. The model is also instructed to
> return nothing rather than guess — those records route to review."

**"We have four lakh material codes. How long, and what does it cost?"**

> "One AI call per record, once, cached — never per comparison. Roughly ₹17,000 of
> inference for a million records. If we called per pair it would be lakhs of
> rupees, every single run. That constraint shaped the architecture."

**"Have you actually run it at that scale?"**

Be honest.

> "No. We've run a hundred records. The design is built for scale — blocking gives
> about 99.996% reduction at a million records — but we haven't benchmarked it.
> We built the hard part first, which is extraction."

**"Why not just use fuzzy string matching?"**

> "Because it fails in both directions." Then show both cases. This is the
> strongest moment in the whole presentation — let the data do it.

**"How do you know your accuracy numbers are real?"**

Volunteer the caveat before it is asked.

> "On our synthetic benchmark we get high precision — but we generated that
> corruption ourselves, so that number measures how well we undo our own noise.
> That's circular and we say so. The number we trust more comes from a
> hand-labelled hold-out of real records, and it's lower."

---

## Domain

**"What's the difference between SS304 and SS316, and why does it matter here?"**

> "SS316 has about 2–3% molybdenum; SS304 has none. That's what gives it chloride
> and acid corrosion resistance. In corrosive refinery service, SS304 where SS316
> is specified will pit and eventually leak. Which is why our system treats grade
> as a veto field — those two records are 97% textually identical and must never
> merge."

**"What does 150# actually mean?"**

> "It's an ANSI pressure class, not a pressure. A Class 150 A105 flange is rated
> around 285 psig at ambient and derates as temperature rises."

Getting this right signals real domain understanding. Getting it wrong — saying
"150 psi" — signals the opposite.

**"Why are the descriptions so short in the first place?"**

> "Several reasons. The standard SAP description field is still 40 characters,
> data migrated from older systems with even shorter fields, and most importantly
> there was never an enforced cataloguing standard. So every storekeeper invented
> their own shorthand."

Do **not** say it is only the 40-character limit — a CPCL person may well say the
real reason was the absence of a cataloguing policy, and they would be right.

**"Is this our actual data?"**

> "No — this is a synthetic evaluation dataset modelled on public GeM and tender
> nomenclature. We don't claim these are CPCL's codes or prices. We claim the
> variation patterns are realistic. On a real extract the pipeline runs
> identically; only the seed list changes."

---

## Commercial

**"Where does the savings number come from?"**

> "Purchase history grouped by national code. Once you know four CPSEs are buying
> the same item, you can see four different prices for it. The upper bound —
> everyone achieving the best price already observed — is ₹3.3 crore on this
> dataset. At a more realistic 40% capture it's about ₹1.3 crore. We show both."

Giving the conservative figure unprompted is what makes the optimistic one
credible.

**"Why would a CPSE agree to share price data?"**

> "They don't have to. Only encoded values cross the boundary — an embedding
> instead of the description, a price band instead of the exact price, a hash
> instead of the vendor name. Equal hashes prove 'same vendor' without naming it.
> And results show a benchmark, never who achieved it — you learn a better price
> exists and how far above it you are, not who got it."
>
> Then the limit, unprompted: *"This significantly reduces exposure. It is not
> cryptographic privacy — embeddings are partially invertible. Full secure
> multi-party computation is roadmap."*

**"Who actually uses this day to day?"**

> "The material master cataloguer at each CPSE — a domain expert who already knows
> SS304 isn't SS316. They clear the review queue. Every company has their own, and
> they only approve their own company's records. For a cross-CPSE merge, both
> sides have to approve."

**"Won't this be a huge change for the CPSEs?"**

> "No, and that's deliberate. Nobody changes their code. CPCL's storekeeper keeps
> typing 100004521. The national code sits above the existing codes and links them
> — the way Aadhaar and UPI added a layer without replacing what was underneath."

---

## Governance

**"Who's accountable if a merge is wrong?"**

> "Every merge records who approved it, when, and on what evidence — which signals
> and which fields. And it's reversible; undoing a merge deletes mapping rows, it
> never has to restore deleted data, because nothing was deleted."

**"Can you show me why these two were merged?"**

Have the review screen ready. This question is a gift — it is the thing the system
does best.

---

## If you do not know

> "I don't know — let me not guess at that."

Then follow up afterwards if you can. A judge respects this. A confident wrong
answer is the thing that loses rooms, because it puts every other answer in doubt.

---

## Related

[`honest-limits.md`](honest-limits.md) — the things to volunteer before being
asked, and the safe phrasing for each.
