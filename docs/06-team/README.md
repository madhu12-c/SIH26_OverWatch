# Team

Open your own file. Everything you need is in it — inputs, outputs, commands,
and what "done" means. Nobody should have to ask Madhu to explain their part.

| Person | Owns | File |
|---|---|---|
| Madhu | Architecture, extractor, canonicaliser, integration | [`madhu.md`](madhu.md) |
| Yash | Scoring, clustering, hard blockers | [`yash.md`](yash.md) |
| Rashmit | Embeddings, evaluation harness, tuning | [`rashmit.md`](rashmit.md) |
| Aditya | React demo frontend | [`aditya.md`](aditya.md) |
| Isha | Dataset research and verification | [`isha.md`](isha.md) |
| Meghna | Domain, narrative, presenting | [`meghna.md`](meghna.md) |

---

## The contracts

Every stage reads a file and writes a file. **That is the only coupling.** If you
know the shape of your input, you can start now — even if the person producing it
has not finished.

```
Isha      data/input/seed_items.csv       researched items + real specs
             |
Madhu     data/input/materials.csv        raw records, 5 CPSEs
          data/input/purchases.csv        purchase orders
          data/truth/ground_truth.csv     answer key
             |
Madhu     data/output/specs.json          record_id -> attributes + confidence
Rashmit   data/output/embeddings.npz      record_id -> 384-dim vector
             |
Yash      data/output/pair_scores.json    every scored pair, and why
          data/output/clusters.json       records grouped into one item
             |
Madhu     data/output/national_codes.json golden record, std description, UNSPSC
          data/output/mappings.csv        national code -> every source code
             |
Madhu     data/output/results.json        everything the UI needs
             |
Aditya    ui/                             React app reading results.json
```

Paths are defined once in [`src/paths.py`](../../src/paths.py). Import from
there — do not build paths out of strings.

---

## Work against stubs, not finished data

**Nobody waits.** Madhu ships a stub version of each output file with a few fake
rows in it. Build against the stub; it keeps working when the real data replaces
it, because the shape does not change.

This is the single thing that makes six people possible in two days.

---

## Rules that apply to everyone

1. **Precision over recall.** A wrong merge can put the wrong part in a refinery
   line. When unsure, route to a human.
2. **Nothing is destroyed.** Never overwrite raw data. Write to your own file.
3. **`data/truth/` is off limits** to anything except evaluation. A matcher that
   has seen the answer key produces a worthless number.
4. **No live AI call in the demo path.** Ever.
5. **Every burst ends at a working checkpoint.** Assume the next person to touch
   this is you, two weeks from now, having forgotten everything.

---

## When you finish something

Drop it in the group with one line: what you produced, where it is, and anything
that surprised you. Do not wait to be asked.

## When you are stuck

Say so within 20 minutes, not two hours. Include what you ran and what it printed.
