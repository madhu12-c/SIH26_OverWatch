# 008. Use UNSPSC, do not invent a taxonomy

**Status:** 🟢 decided
**Date:** 29 Aug 2026

## Context

PS Key Capability 2 is "Material Standardization & Classification". Every record
that gets a national code needs a classification, and the national code itself
embeds it:

```
NMC - 31171500 - 000042
        |
        +-- the classification code
```

We could invent a classification scheme fitted to refinery MRO. It would probably
be neater for our nine categories.

## Decision

Use **UNSPSC** — the United Nations Standard Products and Services Code. Eight
digits, four levels:

```
31 00 00 00   Segment     Manufacturing Components and Supplies
31 17 00 00   Family      Bearings and Bushings
31 17 15 00   Class       Bearings
31 17 15 07   Commodity   Ball bearings
```

Only the 20–30 classes our categories actually touch. Not the full taxonomy,
which runs to tens of thousands of codes.

## What we rejected

**Invent our own taxonomy.** Would fit our data better. Rejected on three counts:
it is exactly the kind of thing a national system must not do, since every CPSE
would then have to adopt a scheme invented by six students; it makes
interoperability with anything external impossible; and it signals to a judge
that we did not look for the existing standard.

**Use the CPSE's own `material_group` column.** Already in the data. Rejected
because in reality that column is inconsistent — it is assigned by whoever created
the record, with no enforcement. Our extractor deliberately ignores it and infers
the category from the description instead.

**eCl@ss or NATO codification (NSN).** Both real alternatives. eCl@ss is stronger
in industrial engineering than UNSPSC. Rejected on availability and familiarity:
UNSPSC is free, widely known in Indian public procurement, and its structure is
easy to explain in one slide.

**Load the full UNSPSC dataset.** Tens of thousands of codes for nine categories.
The 20–30 classes we touch are enough, and hardcoding them removes a dependency.

## What it buys us

- A credible answer to "how do you classify?" that is not "we made something up".
- The national code carries meaning — the class is readable from the code itself.
- Interoperability with GeM and other procurement systems that already use UNSPSC.
- It signals that we researched the domain rather than only the algorithm.

## What it costs us

- **Some refinery items map awkwardly.** A cartridge mechanical seal or a spiral
  wound gasket sits in a class that is broader than the item. UNSPSC was built for
  procurement categories, not engineering specification, so the fit is
  approximate.
- **We are only using a slice.** If asked "does this handle the full UNSPSC?", the
  honest answer is that we hardcoded the classes our data touches and the mapping
  would need extending for a real deployment.
- **Classification is currently rule-based**, driven off the extracted category
  rather than an independent classifier. That is sufficient and simple, but it
  means classification inherits any extraction error.

## When to revisit

If a CPSE indicates it already standardises on something else — some Indian PSUs
use their own long-established internal classification — the mapping layer changes,
not the architecture. Worth asking, if the CPCL contact is ever reachable.

## Related

- `docs/03-reference/domain-facts.md` — the UNSPSC codes we use, and confidence
- `docs/01-project/glossary.md`
