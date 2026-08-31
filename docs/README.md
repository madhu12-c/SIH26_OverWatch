# Documentation index

Everything written down, so nobody has to be asked twice.

Four audiences share these files, and each section leans toward one of them:

- **01–03** — anyone joining the project
- **02, 04** — us, six weeks from now, when we have forgotten why
- **04** — judges, and any claim we might have to defend out loud
- **06** — each person's own work, self-serve

---

## 01 · Project

What this is, why it is hard, and the vocabulary.

| File | What it holds |
|---|---|
| [`problem-statement.md`](01-project/problem-statement.md) | The official PS text, and our reading of what it actually asks for |
| [`the-core-idea.md`](01-project/the-core-idea.md) | Match on specifications, not spelling — the one idea everything rests on |
| [`glossary.md`](01-project/glossary.md) | SS316, 150#, MAKTX, UNSPSC, entity resolution — every term in one place |

## 02 · Decisions

One file per decision. Each records what we chose, **what we rejected**, what it
costs us, and when to revisit it.

Index and status table: [`02-decisions/README.md`](02-decisions/README.md)

## 03 · Reference

The factual layer — no opinions, just what is true about the system.

| File | What it holds |
|---|---|
| [`data-dictionary.md`](03-reference/data-dictionary.md) | Every file, every column, where it comes from, who reads it |
| [`pipeline-stages.md`](03-reference/pipeline-stages.md) | Stage by stage: input, what happens, output |
| [`schemas-and-blockers.md`](03-reference/schemas-and-blockers.md) | Category schemas, veto fields, ignored fields, and why |
| [`domain-facts.md`](03-reference/domain-facts.md) | Every domain claim we make, with how confident we are and how to verify it |

## 04 · Risks

The uncomfortable section. Written first because it is the one that gets skipped.

| File | What it holds |
|---|---|
| [`honest-limits.md`](04-risks/honest-limits.md) | Claims we cannot fully defend, and the safe way to phrase each |
| [`technical-risks.md`](04-risks/technical-risks.md) | What breaks, how likely, what we do about it |
| [`demo-day-risks.md`](04-risks/demo-day-risks.md) | Everything that can go wrong on stage, and the fallback for each |
| [`judge-questions.md`](04-risks/judge-questions.md) | Hard questions with prepared answers |

## 05 · Runbook

| File | What it holds |
|---|---|
| [`setup.md`](05-runbook/setup.md) | Install, API keys, GPU check |
| [`run-the-pipeline.md`](05-runbook/run-the-pipeline.md) | Every command, in order |
| [`demo-day.md`](05-runbook/demo-day.md) | The checklist for Tuesday morning |

## 06 · Team

One file per person. Open yours and start — no briefing needed.

| Person | Owns |
|---|---|
| [`madhu.md`](06-team/madhu.md) | Architecture, extractor, canonicaliser, integration |
| [`yash.md`](06-team/yash.md) | Scoring, clustering, hard blockers |
| [`rashmit.md`](06-team/rashmit.md) | Embeddings, evaluation harness, tuning |
| [`aditya.md`](06-team/aditya.md) | React demo frontend |
| [`isha.md`](06-team/isha.md) | Dataset research and verification |
| [`meghna.md`](06-team/meghna.md) | Domain, narrative, presenting |

Shared contracts between people: [`06-team/README.md`](06-team/README.md)

---

## How to add to these docs

**A new decision** — copy the most recent file in `02-decisions/`, take the next
number, fill in every heading. Do not skip *"What we rejected"* — that section is
the reason the file exists.

**A new risk** — add it to the right file in `04-risks/` with a mitigation. A risk
without a mitigation is a note, not a risk entry.

**A claim you want to make in the deck** — put it in
[`domain-facts.md`](03-reference/domain-facts.md) with a confidence level and a
verification route first. If it cannot go there, it should not go in the deck.
