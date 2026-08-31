# Isha — dataset research and verification

Your output goes straight into the code, so the format matters. And you own the
fix to one of our two biggest weaknesses.

---

## Why this job matters more than it sounds

Our biggest demo risk is a judge from CPCL looking at our data and thinking *"that
does not look like a real material master."* If that happens, they stop believing
everything else — the accuracy numbers, the savings, all of it.

Right now the seed items were written from general knowledge. The engineering
standards are correct and checkable. **The item names, vendor lists and prices are
not verified.** You are what turns that from a weakness into a strength.

---

## Job 1 · Find real refinery items

### Where to look

| Source | What you get |
|---|---|
| **GeM catalogue** (gem.gov.in) | Real product listings with real descriptions and live prices |
| **eprocure.gov.in** | Tender BOQs — line items exactly as a PSU writes them |
| Manufacturer catalogues | SKF, FAG, L&T Valves, Jindal Saw, Flexitallic, Wika |

### What to look for

CPCL is a **refinery**, so weight the list that way:

```
pipes, valves, flanges, gaskets, pumps, bearings, mechanical seals,
motors, instrumentation, safety consumables
```

**Not** steel-plant or mining stock. A judge from a refinery notices immediately.

### The format

Save as `data/input/seed_items.csv`. Pipe-separate anything with multiple values.

```
item_id | category | noun | modifiers | uom | base_price | brands | part_numbers | vendors | source_url | verified_by | verified_on
```

Example row:

```
ITM-016 | valve | VALVE | GLOBE|2 IN|300#|CS BODY|FLANGED | EA | 16400 | Audco|BDK | GL-2-300 | L&T Valves | gem.gov.in/product/... | Isha | 2026-08-31
```

Categories must be one of: `bearing` `gasket` `pipe` `valve` `fastener` `flange`
`rotating` `instrument` `electrical`.

The generator picks it up automatically — `python src/generate_dataset.py` uses
`seed_items.csv` if the file exists.

**Target 200–300 items. Fifty good ones beat three hundred guessed ones.**

---

## Job 2 · Screenshots — the most valuable thing you produce

**Screenshot every real description you find.** Save them in
`docs/03-reference/evidence/`.

This is our proof that the corruption patterns in our synthetic data were
*observed*, not invented. When a judge asks whether the data is realistic, we open
the folder.

Look for and capture:

- Abbreviated descriptions (`BRG`, `M.S.`, `SS316`, `SCH40`)
- Descriptions that are obviously truncated
- The same item written differently in two tenders
- Inconsistent units (`NOS` vs `EA` vs `PCS` for the same kind of item)

---

## Job 3 · Price check — 30 minutes, removes a whole category of risk

Every price in the current seed list is an estimate. One is probably wrong:

| Item | Our price | Concern |
|---|---|---|
| Bearing 6205-2RS | ₹1,310 | **Likely too high.** SKF retail is closer to ₹400–700. |
| Gate valve 6" 150# CS | ₹28,400 | Probably fine |
| Hex bolt M12×50 SS316 | ₹42 | Probably fine |
| Motor 5 HP | ₹18,700 | Probably fine |

Check 15 of these against live GeM listings and correct them. A CPCL judge buys
bearings; they will know the price.

---

## Also worth flagging

Two vendor names in the current seed list are low confidence — **"Champion Seals"**
and **"IGP Engineers"**. If you cannot confirm they exist, tell Madhu and we drop
them. Flexitallic is definitely real.

Also: **"Audco"** became **L&T Valves**. Listing both as separate brands is
slightly out of date.

---

## Job 4 · The real hold-out — the highest-value thing after Tuesday

This is the fix to our most serious credibility problem.

Because we generated our own dataset, "98% precision" really means *"we reversed
98% of the errors we introduced ourselves."* A sharp judge can puncture that.

The fix: **200–300 real records from public sources, hand-labelled by the team** —
which of them refer to the same item. Then we report both numbers:

```
Synthetic (100 records)    P = 98%   R = 87%
Real hold-out (300)        P = 94%   R = 79%   <- the believable one
```

The smaller, weaker number is worth more than the larger one.

Not needed for Tuesday. It is the first thing after.

---

## Done when

- [ ] `data/input/seed_items.csv` with 50+ verified items (200–300 eventually)
- [ ] Screenshots saved in `docs/03-reference/evidence/`
- [ ] 15 prices checked against GeM and corrected
- [ ] The two doubtful vendor names resolved

---

## Read this

[`../03-reference/domain-facts.md`](../03-reference/domain-facts.md) — every claim
we make, with how confident we are. Your work moves rows in that file from 🔴 and
🟡 up to 🟢, and that is exactly the point.
