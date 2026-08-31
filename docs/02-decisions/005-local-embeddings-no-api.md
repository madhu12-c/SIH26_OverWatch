# 005. Embeddings run locally, never through an API

**Status:** 🟢 decided
**Date:** 30 Aug 2026

## Context

Embeddings turn each description into a vector so that similarity becomes a dot
product. Hosted embedding APIs exist and are easy to call — NVIDIA, OpenAI,
Google, Cohere all offer one.

We have a GPU machine on the team, which is the reason Rashmit owns this stage.

## Decision

Run `sentence-transformers` locally with `BAAI/bge-small-en-v1.5` (384 dimensions,
~130 MB). Vectors are normalised at encode time so cosine similarity is a plain
dot product.

Ids and vectors are stored **together** in one `.npz` file. Two separate files can
drift out of order, and an off-by-one there would corrupt every score downstream
without producing any visible error.

The model downloads once and then works entirely offline.

## What we rejected

**A hosted embedding API** (NVIDIA NIM or equivalent). Would work fine. Rejected
for four reasons, in increasing order of importance:

1. Unnecessary — 100 records encode in about five seconds on CPU.
2. Adds a network dependency to a stage that has no reason to need one.
3. Rate limits and cost on re-runs, for no quality gain at our scale.
4. 🔴 **It would send raw descriptions off the machine.** In our federated design,
   the embedding is the thing that is *allowed* to cross a company boundary
   precisely because the raw text does not. If the embedding is computed by an
   external service, the raw text has already left — and the privacy argument
   collapses entirely.

Point 4 is decisive. Note that this is the same reasoning that
[004](004-gemini-for-extraction.md) currently loses on, which is why 004 is marked
as our weakest position.

**A larger model** (`bge-base`, 768 dimensions). Better on paper. At 100 records
and with text as our weakest signal anyway, the gain is invisible and the download
is four times larger.

**Training our own embeddings on the corpus.** No labels, not enough text, and
domain adaptation is a research project, not a two-day task.

## What it buys us

- Free, unlimited, offline, no rate limits — Rashmit can re-run as often as he
  wants while tuning.
- Consistent with the privacy story rather than in tension with it.
- Nothing to fail on demo day.

## What it costs us

- **Setup friction.** A CUDA build of PyTorch is a 2 GB download. Madhu's machine
  currently has `torch 2.11.0+cpu`, which is fine for 100 records but not for a
  larger dataset.
- **The model must be pre-downloaded on the demo machine.** First run pulls
  130 MB. On venue wifi that is a real risk, so the fix is to run it once on the
  demo laptop in advance — or copy `~/.cache/huggingface/` across.
- **Quality below the best hosted models.** Acceptable, because text is
  deliberately our weakest signal — it shortlists candidates, it does not decide
  merges.

## When to revisit

If the dataset grows past roughly 100k records, revisit the model size and add an
approximate-nearest-neighbour index. Not before — see
[007](007-no-infrastructure-yet.md).

## Related

- [004](004-gemini-for-extraction.md) — the same privacy question, currently
  answered differently, and knowingly so
- `src/embed.py` — includes a self-test that prints real similarity for both demo
  pairs, so the numbers in the deck are measured rather than assumed
