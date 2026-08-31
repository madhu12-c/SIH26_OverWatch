# 010. Nothing is destroyed, every merge is reversible

**Status:** 🟢 decided
**Date:** 29 Aug 2026

## Context

PS Key Capability 7 is "Audit Trail & Governance", and the PS asks for migration
support with traceability back to each CPSE's existing codes.

Government master data has a requirement that ordinary software does not: someone
must be able to ask *"who approved this merge, when, on what evidence, and can it
be undone?"* — and get an answer years later.

There is also a practical reality. A CPSE will not adopt a system that rewrites
its material master. CPCL's storekeeper has typed `100004521` for fifteen years
and will keep doing so.

## Decision

**Nothing is ever deleted or overwritten.**

- `materials` is append-only. Raw descriptions are stored exactly as received and
  never modified — normalisation and extraction write to their own files
  alongside, never over.
- Original CPSE codes are always retained and mapped. The national code is an
  additional layer above existing codes, not a replacement for them.
- Every merge is reversible. Undoing a merge deletes mapping rows; it never has to
  restore deleted data, because no data was deleted.
- Every merge stores **why** — the individual signal scores and which fields
  matched — so the reasoning survives independently of the code that produced it.
- Every action is logged with actor, timestamp and reversibility.

The mental model is Aadhaar and UPI: neither replaced the identifiers underneath
them. They added a common layer above, and nothing below had to change.

## What we rejected

**Update records in place** with a `merged_into` column. Simpler and smaller.
Rejected because it loses history — after two merges and an unmerge, the original
state is unrecoverable, and "can it be reversed" becomes "partially".

**Delete duplicates after merging.** What a naive deduplication tool does. It is
exactly the behaviour that makes a CPSE refuse to adopt the system, and it makes
an error unrecoverable rather than merely wrong.

**Force a single national code as the primary key.** Cleaner data model, and a
non-starter organisationally. Every downstream system in every CPSE references the
existing code.

**Audit logging as a later feature.** Rejected because retrofitting an audit trail
means reconstructing history that was never recorded. It has to be there from the
first merge or it is incomplete forever.

## What it buys us

- A direct answer to the governance capability, which several teams will treat as
  a checkbox.
- Adoption is plausible — no CPSE has to change anything to start.
- A wrong merge is embarrassing, not catastrophic. That is what makes an
  auto-merge band defensible at all.
- The explanation stored with each merge is what the review screen displays, so
  the audit requirement and the usability requirement are served by the same data.

## What it costs us

- **More storage and more tables.** Raw, normalised, specs, scores, mappings and
  log all coexist. At our scale this is irrelevant; at a million records it is a
  real design consideration.
- **More code.** Reversibility has to be written and tested, and it is invisible
  in a demo unless we deliberately show it.
- **Queries get more complex** — "the current state" is a view over an append-only
  history rather than a table you can read directly.
- **We have not built the audit log yet.** It is designed, and the data model
  supports it, but the table does not exist. Saying "designed, not yet built" is
  fine; claiming it works would not be.

## When to revisit

Not the principle. The implementation moves to proper database transactions when
Postgres arrives — see [007](007-no-infrastructure-yet.md).

## Related

- [003](003-precision-over-recall.md) — reversibility is what makes auto-merge
  acceptable
- `docs/03-reference/data-dictionary.md` — the table layout
