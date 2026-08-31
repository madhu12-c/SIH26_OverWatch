# Decision log

Every significant choice, with what we rejected and what it costs us.

The point of writing these down is not process. It is that in November someone
will ask *"why don't we just use a fuzzy matcher?"* or *"why not send everything
to one API?"* — and the answer needs to be recoverable without re-deriving it, and
without the person who decided it being in the room.

**Each file records:** context, the decision, what we rejected and why, what it
buys us, what it costs us, and the condition that would make us revisit it.

---

## Index

| # | Decision | Status | Cost we accepted |
|---|---|---|---|
| [001](001-match-on-specs-not-text.md) | Match in attribute space, not text space | 🟢 decided | Extraction becomes the critical path — if it fails, nothing works |
| [002](002-llm-once-per-record.md) | One LLM call per record, never per pair | 🟢 decided | Scoring cannot use language understanding; it is pure arithmetic |
| [003](003-precision-over-recall.md) | Precision over recall, human in the loop | 🟢 decided | We knowingly miss real duplicates |
| [004](004-gemini-for-extraction.md) | Gemini API for spec extraction | 🟡 decided, revisit | Descriptions leave the machine — contradicts our own sovereignty pitch |
| [005](005-local-embeddings-no-api.md) | Embeddings run locally, never via an API | 🟢 decided | Rashmit's machine needs a working CUDA install |
| [006](006-synthetic-dataset.md) | Generate our own dataset | 🟡 decided, weak point | Our accuracy numbers are circular until a real hold-out exists |
| [007](007-no-infrastructure-yet.md) | No Postgres, no pgvector, no blocking yet | 🟢 decided | The "scales to millions" claim is argued, not demonstrated |
| [008](008-unspsc-not-custom-taxonomy.md) | Use UNSPSC, do not invent a taxonomy | 🟢 decided | Some refinery items map awkwardly |
| [009](009-static-demo-no-backend.md) | Demo reads precomputed JSON, no backend | 🟢 decided | It is not "live", and someone may notice |
| [010](010-append-only-reversible.md) | Nothing is destroyed, every merge reversible | 🟢 decided | More storage, more tables, more code |

**Status key** — 🟢 settled, do not relitigate · 🟡 decided but known weak, revisit
after the internal round · 🔴 open

---

## Decisions we have deliberately NOT made yet

| Question | Why it is still open | When it needs answering |
|---|---|---|
| Which vector index at scale — pgvector HNSW or FAISS | At 100 records neither is needed. Choosing now would be guessing. | Before any dataset above ~50k records |
| How the federated privacy layer actually exchanges data | The architecture is clear; the implementation is not. Overcommitting now risks a claim we cannot defend. | October, before the finale |
| Whether spec extraction moves to a local model | Depends on whether the sovereignty argument gets pushed on. See [004](004-gemini-for-extraction.md). | If a judge challenges it, or before any real CPSE pilot |
| Review UI approval flow for cross-CPSE merges | Both sides must approve — the rule is settled, the interface is not. | Before the finale |
