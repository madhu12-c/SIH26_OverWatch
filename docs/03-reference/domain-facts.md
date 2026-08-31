# Domain facts register

Every domain claim we make, with how confident we are and how to verify it.

**The rule: if a claim is not in this file with a confidence level and a
verification route, it does not go in the deck.**

Confidence levels:

- 🟢 **Verifiable** — a published standard. Anyone can check it, and being right
  earns credibility.
- 🟡 **Confident, unverified** — believed correct, not personally checked. Safe to
  state, but not to build an argument on.
- 🔴 **Estimate** — made up to be plausible. Never present as fact.

---

## Bearings

| Claim | Level | How to verify |
|---|---|---|
| `6205` = 25 mm bore, 52 mm OD, 15 mm width | 🟢 | ISO 15 / any SKF or FAG catalogue |
| `6206` = 30 mm bore, 62 mm OD, 16 mm width | 🟢 | same |
| Bore code: last two digits × 5, for codes 04 and above | 🟢 | ISO 15 |
| `2RS`, `2RSR`, `2RS1`, `LLU`, `DDU` all mean rubber sealed both sides | 🟢 | Manufacturer cross-reference tables — SKF `2RS1`, FAG `2RSR`, NTN `LLU` |
| Any manufacturer's 6205 is dimensionally interchangeable | 🟢 | This is the point of an ISO designation. **This is our headline demo claim and it holds.** |

## Materials

| Claim | Level | How to verify |
|---|---|---|
| SS316 contains molybdenum (~2–3%), SS304 does not | 🟢 | ASTM A240 |
| Molybdenum gives SS316 better chloride/acid corrosion resistance | 🟢 | Any materials engineering reference |
| Using SS304 where SS316 is specified risks pitting corrosion and failure | 🟢 | Standard refinery materials practice |
| `ASTM A106 Gr B` = carbon steel seamless pipe for high-temperature service | 🟢 | ASTM A106 |
| `ASTM A312 TP316` = stainless seamless/welded pipe | 🟢 | ASTM A312 |
| `ASTM A105` = carbon steel forgings, used for flanges | 🟢 | ASTM A105 |
| `ASTM A193 B7` studs pair with `A194 2H` nuts | 🟢 | ASTM A193 / A194 |

## Dimensions and ratings

| Claim | Level | How to verify |
|---|---|---|
| `SCH 40` / `SCH 80` are wall thickness schedules | 🟢 | ASME B36.10 / B36.19 |
| `150#` / `300#` are ANSI/ASME pressure classes | 🟢 | ASME B16.5 |
| **`150#` is a class, NOT 150 psi** | 🟢 | ASME B16.5 — a Class 150 A105 flange is rated ~285 psig at ambient and derates with temperature. **Say this if asked; it demonstrates real domain understanding.** |
| Nominal pipe size is a designation, not a measurement | 🟢 | ASME B36.10 |
| `API 600` is the gate valve standard | 🟢 | API 600 |
| `IS 1364` covers hexagon head bolts and nuts in India | 🟢 | BIS |

## SAP

| Claim | Level | How to verify |
|---|---|---|
| Material descriptions live in table `MAKT`, field `MAKTX` | 🟢 | SAP `SE11` |
| `MAKTX` is **CHAR(40)** | 🟡 → make 🟢 | **Meghna: run `SE11` → table `MAKT`, screenshot it.** Widely cited in SAP MM, but verify it ourselves before saying it out loud. A CPCL judge can check instantly. |
| It is still 40 characters today, in S/4HANA — not a legacy limit | 🟡 | Same check. |
| `MARA` = general material data, `MARC` = plant data, `MBEW` = valuation | 🟢 | SAP data dictionary |

⚠️ **Careful with the framing.** The 40-character field is *one* reason
descriptions are abbreviated, not the only one. Others: no enforced cataloguing
standard, migration from older systems with shorter fields, decades of untrained
data entry, people abbreviating the way they search.

**Don't say:** "Descriptions are cryptic because SAP capped the field at 40 characters."
**Say:** "Several reasons — the standard description field is still 40 characters,
data migrated from older systems, and most importantly there was never an enforced
cataloguing standard. So every storekeeper invented their own shorthand."

The second version cannot be corrected by a judge, and invites agreement instead
of contradiction.

## Companies

| Claim | Level | Note |
|---|---|---|
| CPCL is a refinery at Manali, Chennai, a subsidiary of IOCL | 🟢 | Public |
| ONGC is upstream; IOCL, BPCL, HPCL, CPCL are refining | 🟢 | Public |
| Vendors named in the seed list are real Indian suppliers | 🟡 | SKF India, L&T Valves, Kirloskar, Jindal Saw, Ratnamani, Sundram Fasteners, Echjay, John Crane, Wika, ABB, NBC — all real companies |
| These vendors supply CPCL specifically | 🔴 | **Unverified. Never claim this.** Not public information. |
| "Audco" as a brand | 🟡 | Audco India became **L&T Valves**. Listing both separately is slightly anachronistic. |
| "Champion Seals", "IGP Engineers" | 🔴 | Low confidence these exist as named. Flexitallic definitely does. Consider removing. |

## Prices

**All 🔴 — every price in the seed list is an estimate.**

| Item | Our price | Note |
|---|---|---|
| Bearing 6205-2RS | ₹1,310 | **Probably high.** SKF retail is closer to ₹400–700. Weakest number in the dataset. |
| Gate valve 6" 150# CS | ₹28,400 | Plausible |
| Hex bolt M12×50 SS316 | ₹42 | Plausible |
| Mechanical seal, 45 mm | ₹24,600 | Plausible |
| Motor 5 HP | ₹18,700 | Plausible |

**Action for Isha:** check 15 of these against live GeM listings. Thirty minutes
of work that removes an entire category of risk.

## Economics

| Claim | Level | Note |
|---|---|---|
| Material master standardisation gives ~5–7% inventory cost reduction | 🟡 | Widely cited in MDM case studies. **Attribute it — "published case studies report" — never state it as our own finding.** |
| Our dataset shows ₹18.95 cr multi-CPSE spend, ₹3.3 cr saving | 🟢 as arithmetic | Correctly computed **from synthetic prices**. Real only as a demonstration of method. |
| That ₹3.3 cr is an upper bound | 🟢 | Assumes everyone achieves the best observed price. Always give the conservative figure too. |
| ~₹17,000 of inference to process a million records | 🟡 | Our arithmetic at current Gemini Flash pricing. **Verify at ai.google.dev/pricing before quoting.** |

## Classification

| Claim | Level | Note |
|---|---|---|
| UNSPSC is 8 digits, 4 levels: Segment / Family / Class / Commodity | 🟢 | UNSPSC documentation |
| `31171500` is the Bearings class | 🟡 | Verify before it appears on a slide — it is printed inside our national codes |
| We use 20–30 classes, not the full taxonomy | 🟢 | Our own decision, [008](../02-decisions/008-unspsc-not-custom-taxonomy.md) |

---

## Before Tuesday

- [ ] Meghna: verify `MAKTX` = CHAR(40) in `SE11`, screenshot it
- [ ] Isha: check 15 prices against GeM
- [ ] Someone: verify UNSPSC `31171500` = Bearings
- [ ] Someone: confirm Gemini pricing at ai.google.dev/pricing
- [ ] Decide whether to drop "Champion Seals" and "IGP Engineers" from the seed list
- [ ] Rename "Audco" to "L&T Valves"
