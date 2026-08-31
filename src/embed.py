"""
Text embeddings - runs locally on the GPU, no API and no network.

Turns each material description into a vector of numbers, positioned so that
descriptions with similar meaning land close together. Closeness is measured by
cosine similarity, which after normalisation is just a dot product - pure
arithmetic a GPU does millions of times a second.

That speed is the whole reason this stage exists and the LLM does not run here.
Extraction is one model call per record, once. Similarity is compared across
every candidate pair, every run. Only maths survives that.

This is the WEAKEST of the three matching signals. It is useful for shortlisting
candidates, not for deciding a merge - the demo cases below show exactly why.

    pip install sentence-transformers
    python embed.py                  # encode + self-test
    python embed.py --check          # just verify the GPU, encode nothing
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

import paths

# bge-small: 384 dimensions, ~130 MB, downloads once and then works offline.
# Better on short technical text than all-MiniLM, and small enough that a demo
# laptop without a GPU can still run it on CPU.
MODEL_NAME = "BAAI/bge-small-en-v1.5"


def check_device() -> str:
    """Report what we are about to run on, and say so plainly if it is the CPU.

    Run this BEFORE Monday. `torch.cuda.is_available()` returning False on the
    day is a bad surprise, and the fix (a CUDA build of torch) is a download,
    not a five-minute change.
    """
    try:
        import torch
    except ImportError:
        print("torch not installed.")
        print("  pip install sentence-transformers")
        print("  then a CUDA build of torch from https://pytorch.org")
        return "cpu"

    print(f"torch {torch.__version__}")
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"CUDA available -> {name} ({vram:.1f} GB)")
        return "cuda"

    print("CUDA NOT available - will run on CPU.")
    print("  At 100 records this is still only a few seconds, so it is not")
    print("  urgent for Tuesday. It matters when the dataset grows.")
    print("  Fix: install the CUDA build of torch from https://pytorch.org")
    return "cpu"


def load_embeddings(path: Path = paths.EMBEDDINGS):
    """Read back what this script wrote.

    Returns (record_ids, vectors, lookup) where lookup maps a record_id to its
    row. Yash's scorer should use this rather than indexing the array by
    position - ids and rows must never drift apart.
    """
    blob = np.load(path, allow_pickle=False)
    ids = [str(x) for x in blob["ids"]]
    vectors = blob["vectors"]
    return ids, vectors, {rid: i for i, rid in enumerate(ids)}


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Vectors are stored normalised, so cosine similarity is a dot product."""
    return float(np.dot(a, b))


def self_test(ids, vectors, lookup) -> None:
    """Print the real text similarity for the two demo pairs.

    We have been quoting 0.31 and 0.97 in the deck as illustrative numbers.
    These are the actual measured ones, and they need to hold up:

      R00001 vs R00002  SHOULD BE LOW   - different words, same bearing.
                        A fuzzy matcher stops here; specs rescue the match.

      R00003 vs R00004  SHOULD BE HIGH  - near-identical words, different item.
                        A fuzzy matcher merges here; the hard blocker stops it.

    If the low one is not clearly lower than the high one, the demo narrative is
    wrong and we need to know now, not on Tuesday.
    """
    pairs = [
        ("R00001", "R00002", "different words, SAME bearing", "low"),
        ("R00003", "R00004", "same words, DIFFERENT gasket", "high"),
    ]
    descriptions = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            descriptions[row["record_id"]] = row["description"]

    print("\ntext similarity on the two demo pairs")
    print("-" * 66)
    scores = {}
    for a, b, label, expect in pairs:
        if a not in lookup or b not in lookup:
            print(f"  {a}/{b} not in this run")
            continue
        s = cosine(vectors[lookup[a]], vectors[lookup[b]])
        scores[expect] = s
        print(f"  {a}  {descriptions.get(a,'')[:44]}")
        print(f"  {b}  {descriptions.get(b,'')[:44]}")
        print(f"      cosine {s:.3f}   ({label}, expected {expect})\n")

    if "low" in scores and "high" in scores:
        gap = scores["high"] - scores["low"]
        if gap > 0.15:
            print(f"  OK - the pair that LOOKS similar scores {gap:.2f} higher.")
            print("  That gap is the argument: text alone would get both wrong.")
        else:
            print(f"  WARNING - gap is only {gap:.2f}.")
            print("  The demo narrative assumes a clear separation. Check the")
            print("  descriptions before putting these numbers on a slide.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--materials", type=Path, default=paths.MATERIALS)
    ap.add_argument("--out", type=Path, default=paths.EMBEDDINGS)
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--check", action="store_true", help="verify the GPU and exit")
    ap.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto",
                    help="auto uses the GPU when one is present; cpu forces "
                         "system RAM even if a GPU is available")
    args = ap.parse_args()

    device = check_device()
    if args.check:
        return

    if args.device == "cpu":
        device = "cpu"
        print("forced to CPU - using system RAM, not VRAM")
    elif args.device == "cuda":
        if device != "cuda":
            print("CUDA requested but not available - falling back to CPU")
        else:
            device = "cuda"

    rows = list(args.materials.open(encoding="utf-8-sig"))
    records = list(csv.DictReader(rows))
    ids = [r["record_id"] for r in records]
    texts = [r["description"] for r in records]
    print(f"\n{len(texts)} descriptions to encode")

    from sentence_transformers import SentenceTransformer

    print(f"loading {args.model} ...")
    started = time.time()
    model = SentenceTransformer(args.model, device=device)

    vectors = model.encode(
        texts,
        batch_size=args.batch_size,
        device=device,
        normalize_embeddings=True,     # so cosine similarity is a plain dot product
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # ids and vectors travel together in one file - two files can drift apart,
    # and a silent off-by-one here would corrupt every score downstream.
    np.savez_compressed(args.out, ids=np.array(ids), vectors=vectors)

    size_mb = args.out.stat().st_size / 1e6
    print(f"\nwrote {args.out.name}  {vectors.shape[0]} x {vectors.shape[1]}  "
          f"({size_mb:.1f} MB, {time.time()-started:.1f}s on {device})")

    self_test(*load_embeddings(args.out))


if __name__ == "__main__":
    main()
