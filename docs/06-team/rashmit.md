# Rashmit — embeddings, evaluation, tuning

Two jobs. The second one is the more important of the two, and it is the one that
puts numbers on the pitch slide.

---

## Job 1 · Embeddings

### No API. None.

Everything runs on your machine. That is the reason this stage is yours.

```
❌ NVIDIA API   ❌ OpenAI   ❌ Gemini   ❌ any hosted embedding service
✅ sentence-transformers, locally, free, offline
```

There is a hard reason, not just a practical one. In our federated design the
embedding is the thing that is *allowed* to cross a company boundary, precisely
because the raw text does not. If an external service computes the embedding, the
raw text has already left — and the entire privacy argument collapses.
See [`../02-decisions/005-local-embeddings-no-api.md`](../02-decisions/005-local-embeddings-no-api.md).

### Do this first, today

```bash
python src/embed.py --check
```

Two possible outcomes:

```
CUDA available -> NVIDIA GeForce RTX ... (8.0 GB)      good
CUDA NOT available - will run on CPU                    fix it
```

If CPU: install a CUDA build of PyTorch from pytorch.org. **It is a 2 GB
download, so start it today, not Monday night.**

Not urgent for Tuesday — 100 records take about five seconds on CPU. It matters
when the dataset grows.

### Then

```bash
pip install sentence-transformers
python src/embed.py
```

Model is `BAAI/bge-small-en-v1.5` — 384 dimensions, ~130 MB, downloads once and
then works entirely offline.

### The output that actually matters

The script ends by printing real cosine similarity for both demo pairs:

```
R00001  SKF 6205-2RS DEEP GROOVE BALL BEARING
R00002  FAG 6205-2RSR BEARING, 25X52X15MM, SEALED
      cosine 0.xxx   (different words, SAME bearing, expected low)

R00003  GASKET SPIRAL WOUND SS316 4IN 150#
R00004  GASKET SPIRAL WOUND SS304 4IN 150#
      cosine 0.xxx   (same words, DIFFERENT gasket, expected high)
```

**Send Madhu those two numbers.** The deck currently says 0.31 and 0.97, which are
illustrative placeholders, not measurements. These are the real ones.

If the gap comes out small — or backwards — **the demo narrative is wrong and we
need to know today, not Tuesday.** The script flags this itself.

### Demo-day note

Run it once on the **demo laptop** before Tuesday so the 130 MB model is cached.
Or copy `~/.cache/huggingface/` across. Downloading on venue wifi is not a plan.

---

## Job 2 · Evaluation harness — the higher-value one

Build `src/evaluate.py`. One command that prints precision, recall and duplication
rate against `data/truth/ground_truth.csv`.

Build this **early**. Until it exists, every threshold change is an argument
instead of a measurement.

### The metrics

```
TP  system said same, and they are same
FP  system said same, but they are different    <- the dangerous one
FN  system said different, but they are same

precision = TP / (TP + FP)     "of what I merged, how much was right?"
recall    = TP / (TP + FN)     "of the real duplicates, how many did I find?"
```

**Precision is the target. Recall is allowed to be lower.** A missed duplicate
costs an opportunity; a false merge can put the wrong part in a refinery line.
See [`../02-decisions/003-precision-over-recall.md`](../02-decisions/003-precision-over-recall.md).

Targets: **precision > 98%**, recall > 85%.

### Also report

- **Duplication rate** — `1 - unique/raw`. This is the headline rationalisation
  number the PS asks for, in its own words.
- **False merges against `traps.json`** — any merge across a trap pair is a safety
  failure, and should be reported separately and loudly.
- **A threshold sweep** — this is what makes the harness worth building:

```
threshold   precision   recall
0.80          94.2%      91.0%
0.85          96.8%      88.3%
0.90          98.5%      82.1%    <- pick this one
0.95          99.4%      61.7%
```

### Do not let the scorer see the answer key

`data/truth/` is read by `evaluate.py` and nothing else. A matcher that has seen
`ground_truth.csv` produces a number that means nothing. The folder split exists
to make an accidental import visible.

---

## Done when

- [ ] `python src/embed.py --check` reports CUDA (or you have decided CPU is fine
      for now and said so)
- [ ] `embeddings.npz` exists, and Madhu has the two real similarity numbers
- [ ] `python src/evaluate.py` prints precision, recall, duplication rate
- [ ] A threshold sweep table exists, and the chosen threshold is justified by it
- [ ] Trap violations are reported separately from ordinary false positives

---

## Read before you argue about a number

[`../04-risks/honest-limits.md`](../04-risks/honest-limits.md) — our precision
figure is circular, because we generated the corruption we are measuring ourselves
against. Whatever number you produce carries that caveat, and the caveat goes on
the slide with it.
