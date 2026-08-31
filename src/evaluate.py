"""
Evaluation harness - precision, recall, and the threshold sweep.

Build this early and every later change becomes a measurement instead of an
argument. Until it exists, tuning is guesswork.

    python src/evaluate.py
    python src/evaluate.py --sweep          precision/recall at each threshold

WHAT IT MEASURES

    precision   of what we merged, how much was right    <- the target metric
    recall      of the real duplicates, how many we found
    duplication N raw -> M unique, the PS's own rationalisation metric
    traps       merges across a deliberate near-miss = a safety failure

PRECISION IS THE TARGET. Recall is allowed to be lower. A missed duplicate
costs an opportunity; a false merge can put the wrong part in a refinery line.
Targets: precision > 98%, recall > 85%.

THE HONEST CAVEAT, and it must be stated wherever these numbers are:
we designed the corruption in this dataset, so a high precision here means
"we reversed the errors we introduced ourselves". That is circular. The fix is
a hand-labelled hold-out of real records reported alongside.
See docs/04-risks/honest-limits.md

data/truth/ is read HERE and nowhere else. A matcher that has seen the answer
key produces a number that means nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from itertools import combinations

import paths
from scorer import AUTO_MERGE


def load_truth() -> dict[str, str]:
    with paths.GROUND_TRUTH.open(encoding="utf-8-sig") as fh:
        return {r["record_id"]: r["true_item_id"] for r in csv.DictReader(fh)}


def load_traps() -> set[frozenset]:
    if not paths.TRAPS.exists():
        return set()
    return {frozenset((t["a"], t["b"]))
            for t in json.loads(paths.TRAPS.read_text(encoding="utf-8"))}


def pair_metrics(pairs: list[dict], truth: dict, threshold: float) -> dict:
    """Pairwise precision and recall at one threshold.

    Recall needs every truly-same pair, not just the ones the scorer emitted -
    a pair the scorer never produced is a missed duplicate, and pretending
    otherwise inflates recall.
    """
    by_item = defaultdict(list)
    for rid, item in truth.items():
        by_item[item].append(rid)
    total_true = sum(len(v) * (len(v) - 1) // 2 for v in by_item.values())

    tp = fp = 0
    false_merges = []
    for p in pairs:
        if p.get("blocked_by") or p["final"] < threshold:
            continue
        a, b = p["a"], p["b"]
        if a not in truth or b not in truth:
            continue
        if truth[a] == truth[b]:
            tp += 1
        else:
            fp += 1
            false_merges.append(p)

    fn = total_true - tp
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / total_true if total_true else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn,
            "total_true_pairs": total_true,
            "precision": precision, "recall": recall, "f1": f1,
            "false_merges": false_merges}


def cluster_metrics(clusters: list[dict], truth: dict) -> dict:
    """Cluster-level view - the number that goes on the headline slide."""
    true_items = len(set(truth.values()))
    predicted = len(clusters)

    impure, worst = 0, []
    for c in clusters:
        items = {truth[m] for m in c["members"] if m in truth}
        if len(items) > 1:
            impure += 1
            worst.append({"members": c["members"], "true_items": sorted(items),
                          "band": c.get("band")})

    # How scattered is each true item across our clusters? 1.0 means every
    # record for that item landed in one cluster.
    where = defaultdict(set)
    for i, c in enumerate(clusters):
        for m in c["members"]:
            if m in truth:
                where[truth[m]].add(i)
    fragmented = sum(1 for v in where.values() if len(v) > 1)

    return {"raw": len(truth), "predicted_clusters": predicted,
            "true_items": true_items,
            "duplication_rate": 1 - predicted / len(truth) if truth else 0.0,
            "true_duplication_rate": 1 - true_items / len(truth) if truth else 0.0,
            "impure_clusters": impure, "impure_detail": worst[:5],
            "fragmented_items": fragmented}


def trap_check(pairs: list[dict], truth: dict, traps: set, threshold: float) -> list:
    """Merges across a deliberate near-miss pair. Each one is a safety failure."""
    hits = []
    for p in pairs:
        if p.get("blocked_by") or p["final"] < threshold:
            continue
        a, b = truth.get(p["a"]), truth.get(p["b"])
        if a and b and a != b and frozenset((a, b)) in traps:
            hits.append({**p, "items": sorted((a, b))})
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    truth = load_truth()
    traps = load_traps()
    pairs = json.loads(paths.PAIR_SCORES.read_text(encoding="utf-8"))
    clusters = json.loads(paths.CLUSTERS.read_text(encoding="utf-8"))

    scored = [p for p in pairs if not p.get("blocked_by")]
    blocked = [p for p in pairs if p.get("blocked_by")]
    safety_blocks = [p for p in blocked if p["blocked_by"] != "category"]

    # Two different questions, and only the first is a safety question.
    #
    #   AUTO band   what the system merges with no human involved.
    #               A wrong merge here reaches the material master.
    #   REVIEW band what it proposes to a reviewer. A wrong pair here is a
    #               queue-quality problem, not a safety failure - the domain
    #               expert who sees it already knows 150# is not 300#.
    #
    # Reporting a single blended precision hides the distinction that matters.
    auto = pair_metrics(pairs, truth, AUTO_MERGE)
    auto_traps = trap_check(pairs, truth, traps, AUTO_MERGE)

    print("AUTO-MERGE BAND  (>= %.2f, no human involved)" % AUTO_MERGE)
    print(f"  merged without review  {auto['tp'] + auto['fp']:>7,}")
    print(f"  of those, wrong        {auto['fp']:>7,}")
    print(f"  AUTO PRECISION         {auto['precision']:>7.1%}   "
          f"<- THE SAFETY NUMBER")
    if auto_traps:
        print(f"  !! {len(auto_traps)} trap pair(s) AUTO-MERGED - safety failure")
    else:
        print(f"  trap pairs auto-merged {0:>7}   <- none, as required")

    m = pair_metrics(pairs, truth, args.threshold)
    c = cluster_metrics(clusters, truth)
    violations = trap_check(pairs, truth, traps, args.threshold)

    print(f"\nPROPOSED  (>= {args.threshold}, auto-merge + review queue)")
    print(f"  true duplicate pairs   {m['total_true_pairs']:>7,}")
    print(f"  correctly merged  TP   {m['tp']:>7,}")
    print(f"  wrongly merged    FP   {m['fp']:>7,}   <- the dangerous error")
    print(f"  missed            FN   {m['fn']:>7,}")
    print(f"\n  PRECISION              {m['precision']:>7.1%}   target > 98%")
    print(f"  RECALL                 {m['recall']:>7.1%}   target > 85%")
    print(f"  F1                     {m['f1']:>7.1%}   (not our target metric)")

    print(f"\nCLUSTERS")
    print(f"  {c['raw']} raw -> {c['predicted_clusters']} unique "
          f"({c['duplication_rate']:.1%} duplication)")
    print(f"  ground truth is {c['true_items']} items "
          f"({c['true_duplication_rate']:.1%} duplication)")
    if c["predicted_clusters"] > c["true_items"]:
        print(f"  UNDER-merging by {c['predicted_clusters'] - c['true_items']} "
              f"- {c['fragmented_items']} item(s) split across clusters")
    elif c["predicted_clusters"] < c["true_items"]:
        print(f"  OVER-merging by {c['true_items'] - c['predicted_clusters']}")
    print(f"  clusters mixing two real items: {c['impure_clusters']}")
    for bad in c["impure_detail"]:
        print(f"    {bad['true_items']} in one cluster ({bad['band']}): "
              f"{bad['members'][:4]}")

    print(f"\nSAFETY")
    print(f"  pairs blocked by a rule  {len(safety_blocks):>6,}")
    by_rule = defaultdict(int)
    for p in safety_blocks:
        by_rule[p["blocked_by"]] += 1
    for rule, n in sorted(by_rule.items(), key=lambda x: -x[1]):
        print(f"    {rule:<22} {n:>5,}")
    review_traps = [v for v in violations if v["final"] < AUTO_MERGE]
    if auto_traps:
        print(f"\n  !! {len(auto_traps)} trap pair(s) AUTO-MERGED - safety failure")
        for v in auto_traps[:5]:
            print(f"     {v['a']}/{v['b']}  {v['items']}  score {v['final']}")
    if review_traps:
        print(f"  {len(review_traps)} trap pair(s) reached the review queue")
        print(f"     not a safety failure - a reviewer catches these - but it")
        print(f"     costs queue quality, and the usual cause is a hard field")
        print(f"     that was never extracted from one side.")
    if not violations:
        print(f"  trap pairs surfaced      {0:>6}   <- none reached any band")

    if m["false_merges"]:
        print(f"\nFALSE MERGES (worst {min(5, len(m['false_merges']))})")
        for p in sorted(m["false_merges"], key=lambda x: -x["final"])[:5]:
            print(f"  {p['a']}/{p['b']}  score {p['final']}  "
                  f"specs {p['spec_sim']}  text {p['text_sim']}")

    if args.sweep:
        print(f"\nTHRESHOLD SWEEP")
        print(f"  {'thr':>5} {'precision':>10} {'recall':>8} {'F1':>7} "
              f"{'FP':>5} {'traps':>6}")
        best = None
        for t in [x / 100 for x in range(50, 100, 5)]:
            s = pair_metrics(pairs, truth, t)
            v = len(trap_check(pairs, truth, traps, t))
            flag = ""
            if s["precision"] >= 0.98 and best is None:
                best, flag = t, "  <- first to clear 98% precision"
            print(f"  {t:>5.2f} {s['precision']:>9.1%} {s['recall']:>8.1%} "
                  f"{s['f1']:>7.1%} {s['fp']:>5} {v:>6}{flag}")
        if best:
            print(f"\n  Precision-first pick: {best:.2f}")
        else:
            print(f"\n  No threshold reaches 98% precision on this run.")

    print(f"\n{'-'*66}")
    print("These numbers come from a dataset whose corruption we designed, so")
    print("they measure how well we undo our own noise. Report them with that")
    print("caveat, and alongside a hand-labelled real hold-out when it exists.")


if __name__ == "__main__":
    main()
