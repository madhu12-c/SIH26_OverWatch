# Problem statement SIH26099

**Organisation:** Ministry of Petroleum & Natural Gas
**Department:** Chennai Petroleum Corporation Limited (CPCL)
**Category:** Software · **Theme:** Smart Automation
**Title:** AI-Driven Standardization and Harmonization of Material Codes Across CPSEs

---

## What the PS says

CPSEs across Oil & Gas, Power, Steel, Mining and Heavy Engineering procure large
numbers of similar or functionally equivalent materials. The same material is
assigned different codes, descriptions, specifications, units of measurement and
classifications across companies.

This causes duplicated material masters, inconsistent descriptions, difficulty
identifying equivalent materials, fragmented procurement data, higher inventory,
and limited collaborative procurement.

The proposed solution is an AI-powered National Unified Material Master Framework
that analyses codes, descriptions, specifications, technical parameters and
**historical procurement data** from multiple CPSEs, identifies identical,
duplicate, near-duplicate and functionally equivalent materials, recommends
standardised descriptions and a Common National Material Code, and retains mapping
to each CPSE's existing codes — with a user validation and approval workflow, and
SAP/ERP integration.

Goal: **"One Nation – One Material Code"**, with traceability to individual CPSE
codes.

---

## The 8 Key Capabilities → our components

Judges score against these.

| # | Capability | Our component | State |
|---|---|---|---|
| 1 | AI Material Matching & Recommendation | Three-signal hybrid scorer | ⏳ next |
| 2 | Material Standardization & Classification | Canonicaliser + UNSPSC mapper | ⏳ |
| 3 | Duplicate / Near-Duplicate Detection | Clustering + confidence bands | ⏳ |
| 4 | Common National Material Code Generation | Code generator | ⏳ |
| 5 | CPSE Code Mapping & Migration Support | Mapping table | ⏳ |
| 6 | Material Master Dashboard & Analytics | Dashboard | ⏳ |
| 7 | Audit Trail & Governance | Change log + approval workflow | 📐 designed |
| 8 | SAP / ERP Integration | Export API + adapter interface | 📐 designed |

---

## Four things in the PS text that are easy to under-build

Read carefully, the official text asks for more than the capability list implies.

### 1. Standardised description generation is its own deliverable

Expected Solution lists *"Automated standardization of material descriptions and
technical attributes"* as a separate bullet — not a footnote of the canonicaliser.

Industry does this with noun-modifier format. Once specs are typed it is a
template render, and it makes the extraction work visible:

```
BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED
PIPE, SEAMLESS, CARBON STEEL, ASTM A106 GR B, 4 IN, SCH 40
```

### 2. Units of measurement are named explicitly

The Background says *"different material codes, descriptions, specifications,
**units of measurement** and classification."*

UoM harmonisation (`EA`/`NOS`/`PCS`, `M`/`MTR`/`MTS`, `KG`/`KGS`) is a small named
feature with its own conflict rule. Surface it separately in the dashboard.

⚠️ Watch pack sizes — per-piece versus per-box-of-100 breaks price comparison
silently.

### 3. Rationalisation is not the same as mapping

Expected Solution says *"Legacy material code rationalization **and** migration
support"* — two things.

- **Mapping / migration** = source code ↔ national code
- **Rationalisation** = shrinking the estate: flagging redundant, obsolete and
  never-procured codes for retirement

Our headline "100 raw → 15 unique, 85% duplication" **is** the rationalisation
metric. State it in the PS's own words — Expected Impact bullet 2 is "reduction in
duplicate and redundant material codes".

### 4. Use UNSPSC, do not invent a taxonomy

Capability 2 needs a classification. Use the international standard, not something
we designed. [Decision 008](../02-decisions/008-unspsc-not-custom-taxonomy.md).

---

## What the Expected Impact list asks for that nobody will build

The Impact section — not the capability list — asks for:

- *Reduced procurement cost through demand aggregation*
- *Foundation for common procurement and strategic sourcing across CPSEs*

**Neither appears in the 8 Key Capabilities**, so most teams will skip both. And
they are exactly what a ministry cares about.

This is why the savings report is our highest-value module: once clusters exist it
is a `GROUP BY` over `purchases.csv`, roughly an hour of work, and it turns a
data-cleaning project into a money project.

---

## Human-in-the-loop is specified, not a hedge

The PS says *recommend*, *propose*, *review*, *validate* and *approve* throughout,
and lists "User validation and approval workflow for AI recommendations" as a
required capability.

So the answer to *"why not auto-merge everything?"* is not defensive — it is that
the brief asks for the workflow, and a refinery material master is not a place to
be confident. [Decision 003](../02-decisions/003-precision-over-recall.md).

---

## Two things about the department that shape everything

**CPCL is a refinery.** Manali, Chennai; an IOCL subsidiary. The panel thinks in
refinery MRO — pipes, valves, flanges, gaskets, pumps, bearings, seals, motors,
instrumentation, safety consumables. **Not** steel-plant or mining stock. Our seed
data is weighted accordingly.

**The dataset line says "to be provided by participating CPSEs."** It may arrive
late, partially, or not at all. So we generate our own, and keep the ingestion
schema loose enough that a real extract drops in without a rewrite.
[Decision 006](../02-decisions/006-synthetic-dataset.md).

---

## Timeline

| Date | Milestone |
|---|---|
| 1 Sept 2026 (Tue) | College internal round — PPT is the deliverable, demo is a large bonus |
| 20 Sept 2026 | SIH idea submission — hard deadline |
| Dec 2026 | Grand Finale, if selected |

⚠️ **The real risk is October.** After submission there is a dead zone —
submission done, finale far away, semester exams. Most teams lose there, not in
December. Keep a weekly checkpoint through Oct–Nov, however small.
