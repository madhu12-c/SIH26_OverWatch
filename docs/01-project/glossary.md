# Glossary

Every term used in this project. Domain terms first, because they are the ones
that get asked about.

---

## The organisations

| Term | Meaning |
|---|---|
| **CPSE** | Central Public Sector Enterprise — a company majority-owned by the central government. Around 380 exist. |
| **CPCL** | Chennai Petroleum Corporation Limited. A refinery at Manali, Chennai; subsidiary of IOCL. **Our problem statement comes from here** — the judging panel thinks in refinery terms. |
| **IOCL** | Indian Oil Corporation. Refining and retail; India's largest oil company. |
| **ONGC** | Oil and Natural Gas Corporation. Upstream — extracts oil and gas. |
| **BPCL / HPCL** | Bharat / Hindustan Petroleum. Refining and marketing. |
| **GAIL** | Gas Authority of India. Gas pipelines. |
| **SAIL / NTPC / BHEL** | Steel plants / thermal power / heavy engineering. Named in the PS but not our focus. |

## Materials management

| Term | Meaning |
|---|---|
| **Material master** | The catalogue of every item a company buys. The single most important master data set in an ERP. |
| **MRO** | Maintenance, Repair and Operations — the spares and consumables that keep a plant running. |
| **Cataloguer** | The person who creates and maintains material codes. Our primary user. |
| **Indent** | A request to buy something. |
| **BOQ** | Bill of Quantities — the itemised list in a tender. A good source of real descriptions. |
| **GeM** | Government e-Marketplace, gem.gov.in. Public procurement platform with real listings and prices. |
| **UoM** | Unit of Measurement. `EA`, `NOS`, `PCS`, `MTR`, `KG`. Harmonising these is a named requirement in the PS. |

## SAP

| Term | Meaning |
|---|---|
| **SAP MM** | The Materials Management module. |
| **`MARA`** | Table holding general material data. |
| **`MATNR`** | The material number — a company's own material code. |
| **`MAKT` / `MAKTX`** | Table and field holding the material description. `MAKTX` is `CHAR(40)`. |
| **`MARC`** | Plant-specific material data. |
| **`MBEW`** | Material valuation — price and accounting. |
| **`MATKL`** | Material group — the company's own category. **We do not trust this field**; it is inconsistent in real data. |
| **`SE11`** | The transaction for viewing SAP's data dictionary. Use it to verify field lengths. |
| **IDoc / BAPI / LSMW** | SAP's mechanisms for moving data in and out. Relevant to the integration story. |

## Engineering

| Term | Meaning |
|---|---|
| **SS304 / SS316** | Stainless steel grades. SS316 contains ~2–3% molybdenum and resists chloride and acid corrosion; SS304 does not. **Never interchangeable in corrosive service.** |
| **CS** | Carbon steel. |
| **`150#` / `300#`** | ANSI/ASME pressure classes. **A class, not a pressure** — Class 150 in A105 is ~285 psig at ambient and derates with temperature. |
| **SCH 40 / SCH 80** | Pipe wall thickness schedules (ASME B36.10). |
| **NB / Nominal bore** | The designated pipe size. A designation, not a measurement. |
| **`6205`** | An ISO bearing designation. 25 mm bore, 52 mm OD, 15 mm width. **Any manufacturer's 6205 is interchangeable** — this is what makes our demo case true. |
| **`2RS` / `2RSR` / `LLU`** | Rubber sealed on both sides. Same thing, three manufacturers' notations. |
| **Spiral wound gasket** | Metal winding with a filler, the standard refinery flanged-joint gasket. |
| **WNRF** | Weld Neck Raised Face — a flange type. |
| **ASTM A106 Gr B** | Carbon steel seamless pipe specification. |
| **ASTM A193 B7** | Alloy steel stud bolt grade; pairs with A194 2H nuts. |
| **API 600** | The gate valve standard. |

## The technical problem

| Term | Meaning |
|---|---|
| **Entity resolution** | Determining which records refer to the same real-world thing. The formal name for what we do. Dates to 1969. |
| **Functional equivalence** | Two items are interchangeable in use, even if described completely differently. **The thing we are actually detecting.** |
| **Blocking** | Narrowing which pairs are worth comparing, so you never compare everything with everything. |
| **All-pairs / O(n²)** | Comparing every record with every other. 1M records → 500 billion pairs. Forbidden at scale. |
| **Reduction ratio** | How much work blocking eliminates. Target above 99.9%. |
| **Pair completeness** | How many true matches survive blocking. Target above 98%. |
| **Embedding** | Text represented as a list of numbers, positioned so similar meanings land close together. |
| **Cosine similarity** | The angle between two vectors. 1.0 identical direction, 0 unrelated. After normalisation it is just a dot product. |
| **Union-find** | The algorithm that turns matched pairs into groups. Also called disjoint-set union. |
| **Transitive closure explosion** | A~B and B~C group A and C together even when they are unrelated. One bridging record can pull hundreds of items into one blob. Our main clustering hazard. |
| **Hard blocker** | A field where a mismatch is an instant zero, regardless of everything else. Grade, pressure rating, key dimensions. |
| **Golden record** | The single best set of values assembled from a cluster. |
| **Precision** | Of what we merged, how much was correct. **Our target metric.** |
| **Recall** | Of the real duplicates, how many we found. Allowed to be lower. |
| **False merge** | Two different items merged. The dangerous error. |
| **PPRL** | Privacy-Preserving Record Linkage — matching without exchanging raw data. |
| **k-anonymity** | Suppressing a statistic when too few parties contribute. We suppress price benchmarks below three CPSEs. |

## This project

| Term | Meaning |
|---|---|
| **National code / NMC** | The Common National Material Code. `NMC-31171500-000042` — prefix, UNSPSC class, serial. |
| **UNSPSC** | United Nations Standard Products and Services Code. 8 digits, 4 levels. We use it rather than inventing a taxonomy. |
| **Mapping table** | National code ↔ every CPSE's original code. The core deliverable. |
| **Rationalisation** | Shrinking the code estate — flagging redundant, obsolete and never-procured codes. **Distinct from mapping.** |
| **Standard description** | Noun-modifier format: `BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED`. |
| **Safety interlock report** | The count of merges we refused, and why. Our most memorable slide. |
| **Confidence bands** | auto-merge above 0.90, review 0.70–0.90, leave alone below 0.70. |
| **Signal 1 / 2 / 3** | Text similarity / specification agreement / procurement behaviour. |
| **Trap pair** | A deliberate near-miss in the dataset that must never merge. |
