# Technical risks

What breaks, how likely, and what we do about it. A risk without a mitigation is a
note, not a risk entry.

Ordered by expected damage, not probability.

---

## 🔴 1. Spec extraction is unreliable

**The single biggest technical risk.** Everything downstream consumes extraction
output, so a failure here propagates everywhere.

| | |
|---|---|
| Looks like | Wrong values, invented fields, wrong category, confidence that does not reflect reality |
| Damage | Total — matching, clustering, national codes and the demo all inherit it |
| Likelihood | Medium |

**Mitigations in place**

- Strict per-category schema; anything the model returns outside it is discarded
  as hallucination rather than trusted
- Per-field confidence; anything below 0.4 is dropped entirely
- Prompt instructs "omit rather than guess" — the worst outcome is a fabricated
  spec that later drives a merge
- Regex fallback that gets **both demo cases right** with no model at all
- `--validate` prints a hand-checkable view

**Still to do:** hand-check 50 records against source text. This is build-order
step 1 and it has not been done on real Gemini output yet.

---

## 🔴 2. The dataset looks fake

Our biggest **demo** risk lives here too, because it is a data problem.

| | |
|---|---|
| Looks like | A CPCL judge reads a description and it does not resemble their master |
| Damage | Severe — they stop believing the accuracy numbers, the savings, everything |
| Likelihood | Medium |

**Already happened once:** an unbounded string replacement turned `MOTOR INDUCTION`
into `MOTOR"DUCTION`. Fixed with word boundaries; the check is
`grep -cE '[A-Z]"[A-Z]'` over `materials.csv`, currently 0.

**Mitigations**

- Corruption patterns modelled on observed variation, not invented
- Engineering standards in the seed list are correct and verifiable
- Isha's screenshots of real GeM/eprocure descriptions are the evidence

**Open:** vendor lists and prices are unverified. The bearing at ₹1,310 is
probably high. See [`../03-reference/domain-facts.md`](../03-reference/domain-facts.md).

---

## 🟠 3. Transitive closure explosion in clustering

| | |
|---|---|
| Looks like | One cluster containing 200 unrelated records |
| Damage | High — a single blob destroys precision and is visible in a demo |
| Likelihood | Medium, and it rises as the dataset grows |

A matches B, B matches C, A does not match C — connected components groups all
three anyway. One bridging record can chain hundreds together.

**Mitigations** — high threshold; validate that *every* intra-cluster pair scores
well, not just the connected ones, and split if not; cap cluster size and route
oversized clusters to review.

**Not yet built** — the scorer does not exist yet. This must be in it from the
start, not added later.

---

## 🟠 4. Stale cache after a dataset regeneration

| | |
|---|---|
| Looks like | Pipeline runs on specs for records that no longer exist |
| Damage | Silent wrong numbers — the worst kind |
| Likelihood | High. **It has already bitten us once.** |

`specs.json` is keyed by `record_id`. Regenerating the dataset produces new
records; the cache still holds the old ones.

**Mitigation** — always `python src/extractor.py --fresh` after
`generate_dataset.py`.

**Better fix, not yet built** — store a dataset hash in `specs.json` and refuse to
use a cache that does not match.

---

## 🟠 5. Gemini unavailable or rate-limited

| | |
|---|---|
| Looks like | Extraction fails partway, or free-tier quota is exhausted |
| Damage | Low, because of the fallback |
| Likelihood | Medium |

**Mitigations** — retry with exponential backoff on transient errors; pacing at 14
requests/minute; per-record cache so a partial run resumes; regex fallback so no
record is ever left empty; **no live call in the demo path at all.**

---

## 🟡 6. CUDA not available on the demo machine

| | |
|---|---|
| Damage | Low for Tuesday, real later |
| Likelihood | Confirmed — Madhu's machine has `torch 2.11.0+cpu` |

100 records encode in about five seconds on CPU. It matters when the dataset
grows.

**Mitigation** — `python src/embed.py --check` reports this explicitly rather than
failing silently. Rashmit installs the CUDA build; the 2 GB download is why it has
to start today, not Monday night.

---

## 🟡 7. Embedding model not cached on the demo machine

| | |
|---|---|
| Looks like | First run tries to download 130 MB over venue wifi |
| Damage | Demo delay or failure |
| Likelihood | High if not prepared |

**Mitigation** — run `embed.py` once on the demo laptop before Tuesday, or copy
`~/.cache/huggingface/` across. Verify with `HF_HUB_OFFLINE=1`.

---

## 🟡 8. Sparse descriptions extract almost nothing

`GASKET SW SS316` yields three fields; the same item written fully yields six.

**Damage** — a rich record matched against a sparse one leans entirely on the
"missing is not mismatched" rule. If that rule is implemented wrongly, these pairs
break.

**Mitigation** — the rule is documented in three places and is a Done-when
criterion for Yash. Records extracting zero fields land in `unknown` and route to
review — currently 5 of 100 on the regex fallback.

---

## 🟡 9. `results.json` goes stale

The UI reads a precomputed bundle. If anything upstream changes and it is not
regenerated, the demo silently shows old numbers.

**Mitigation** — `run_all.py` regenerates it as the last step. **Not yet built.**
Until it exists, this is a manual discipline and therefore a real risk.

---

## ⚪ 10. Scale is argued, not demonstrated

We have run 100 records, not a million. Blocking is designed and documented but
not implemented.

**Mitigation** — the honest answer, prepared:
[`honest-limits.md`](honest-limits.md) §3. Never claim a benchmark we have not run.

---

## Summary

| # | Risk | Damage | Mitigated? |
|---|---|---|---|
| 1 | Extraction unreliable | 🔴 total | Partly — hand-check still pending |
| 2 | Dataset looks fake | 🔴 severe | Partly — verification pending |
| 3 | Cluster explosion | 🟠 high | Designed, not built |
| 4 | Stale cache | 🟠 silent | Manual discipline only |
| 5 | Gemini unavailable | 🟠 low | ✅ fully |
| 6 | No CUDA | 🟡 low now | ✅ detected explicitly |
| 7 | Model not cached | 🟡 medium | Needs doing before Tuesday |
| 8 | Sparse descriptions | 🟡 medium | ✅ by design rule |
| 9 | Stale `results.json` | 🟡 medium | Needs `run_all.py` |
| 10 | Scale unproven | ⚪ reputational | ✅ honest answer prepared |
