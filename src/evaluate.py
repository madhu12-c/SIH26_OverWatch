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
import math
from collections import defaultdict
from itertools import combinations

import paths
from scorer import AUTO_MERGE, NOT_SAFETY, review_rank


def error_bound(wrong: int, n: int, confidence: float = 0.95) -> float | None:
    """Upper bound on the true error rate, given `wrong` of `n` observed.

    Clopper-Pearson, one-sided: the largest rate p for which seeing `wrong` or
    fewer errors in `n` tries still has at least a 5% chance. "0 wrong of 846"
    does not mean the error rate is 0 - it means that, with 95% confidence, it
    is below this number. It treats pairs as independent tries; pairs from one
    cluster are not quite, so read it as an estimate, not a guarantee.
    """
    if n == 0:
        return None
    alpha = 1 - confidence
    if wrong >= n:
        return 1.0
    if wrong == 0:
        return 1 - alpha ** (1 / n)

    def cdf(p: float) -> float:                        # P(X <= wrong | n, p)
        return sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                            + i * math.log(p) + (n - i) * math.log1p(-p)) for i in range(wrong + 1))

    lo, hi = wrong / n, 1.0
    for _ in range(60):                                # cdf falls as p rises
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > alpha else (lo, mid)
    return hi


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


def load_splits() -> dict[str, str]:
    """record_id -> dev / test, for factory runs. Empty for the demo set."""
    with paths.GROUND_TRUTH.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {r["record_id"]: r["split"] for r in rows if r.get("split")}


def split_metrics(pairs: list[dict], truth: dict, splits: dict) -> dict:
    """Auto precision and proposed recall per split. A pair counts for a
    split only when both records belong to it; the test families were never
    looked at while the rules were tuned."""
    out = {}
    for name in ("dev", "test"):
        keep = {r for r, s in splits.items() if s == name}
        sub_truth = {r: i for r, i in truth.items() if r in keep}
        sub_pairs = [p for p in pairs if p["a"] in keep and p["b"] in keep]
        auto, prop = pair_metrics(sub_pairs, sub_truth, AUTO_MERGE), pair_metrics(sub_pairs, sub_truth, 0.70)
        out[name] = {"records": len(keep), "auto_merged": auto["tp"] + auto["fp"], "auto_wrong": auto["fp"],
                     "auto_precision": auto["precision"], "recall": prop["recall"],
                     "true_pairs": prop["total_true_pairs"]}
    return out


def review_metrics(pairs: list[dict], truth: dict) -> dict:
    """The review queue as a reviewer meets it: one record, its candidates.

    Pairwise precision punishes a terse record for being compatible with
    several items. The questions that matter to the person clearing the
    queue are: is the right match at the top, is it in the first three, and
    how many candidates does a record bring?
    """
    cands = defaultdict(list)
    for p in pairs:
        if p.get("blocked_by") or not (0.70 <= p["final"] < AUTO_MERGE):
            continue
        cands[p["a"]].append((review_rank(p), p["b"]))
        cands[p["b"]].append((review_rank(p), p["a"]))
    with_true = hit1 = hit3 = 0
    sizes = []
    for rid, lst in cands.items():
        lst.sort(reverse=True)
        sizes.append(len(lst))
        right = [truth.get(o) == truth.get(rid) for _, o in lst]
        if any(right):
            with_true += 1
            hit1 += right[0]
            hit3 += any(right[:3])
    n = len(cands)
    sizes.sort()
    return {"records_in_queue": n, "with_a_true_match": with_true,
            "true_match_first": hit1 / with_true if with_true else 0.0,
            "true_match_in_top3": hit3 / with_true if with_true else 0.0,
            "median_candidates": sizes[len(sizes) // 2] if sizes else 0}


def blocking_metrics(truth: dict) -> dict | None:
    """Reduction ratio and pair completeness of the candidate set.

    Completeness is the share of truly-same pairs that blocking let through
    to the scorer. A pair it drops can never be matched, whatever the scorer
    would have said - so this is a ceiling on recall.
    """
    if not paths.BLOCKING.exists():
        return None
    stats = json.loads(paths.BLOCKING.read_text(encoding="utf-8"))
    cand = {frozenset(p) for p in stats.get("candidates", [])}
    by_item = defaultdict(list)
    for rid, item in truth.items():
        by_item[item].append(rid)
    true_pairs = [frozenset(p) for v in by_item.values() for p in combinations(sorted(v), 2)]
    found = sum(1 for p in true_pairs if p in cand)
    return {"mode": stats.get("mode"), "candidate_pairs": stats.get("candidate_pairs"),
            "all_pairs": stats.get("all_pairs"),
            "reduction_ratio": stats.get("reduction_ratio", 0.0),
            "pair_completeness": found / len(true_pairs) if true_pairs else 1.0,
            "true_pairs_missed": len(true_pairs) - found}


# Which field should stop a trap, read from its reason when the trap does not
# say. Traps written by the item factory carry "field" directly.
_TRAP_FIELDS = (("grade", ("material_grade", "body_material", "wetted_material")),
                ("pressure", ("pressure_class", "pressure_rating_psi")),
                ("rating", ("pressure_class", "pressure_rating_psi")),
                ("designation", ("iso_designation",)), ("size", ("nominal_size_in",)),
                ("range", ("range_max", "range_min")), ("type", ("valve_type", "fastener_type")))


def veto_accuracy(pairs: list[dict], truth: dict) -> dict:
    """For each safety field: of the record pairs across a trap, how many were
    blocked by the right field, reached review, auto-merged (must be 0), or
    never met at all (fine - never compared is never merged)."""
    if not paths.TRAPS.exists():
        return {}
    traps = json.loads(paths.TRAPS.read_text(encoding="utf-8"))
    by_item = defaultdict(list)
    for rid, item in truth.items():
        by_item[item].append(rid)
    index = {frozenset((p["a"], p["b"])): p for p in pairs}
    out = {}
    for t in traps:
        fields = (t["field"],) if t.get("field") else next(
            (f for word, f in _TRAP_FIELDS if word in t.get("reason", "").lower()), ("?",))
        key = fields[0]
        row = out.setdefault(key, {"pairs": 0, "blocked_right": 0, "blocked_other": 0,
                                   "review": 0, "auto": 0, "never_met": 0})
        for a in by_item.get(t["a"], []):
            for b in by_item.get(t["b"], []):
                row["pairs"] += 1
                p = index.get(frozenset((a, b)))
                if p is None:
                    row["never_met"] += 1
                elif p.get("blocked_by"):
                    row["blocked_right" if p["blocked_by"] in fields else "blocked_other"] += 1
                elif p["final"] >= AUTO_MERGE:
                    row["auto"] += 1
                elif p["final"] >= 0.70:
                    row["review"] += 1
                else:
                    row["never_met"] += 1
    return out


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
    safety_blocks = [p for p in blocked if p["blocked_by"] not in NOT_SAFETY]

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
    bound = error_bound(auto["fp"], auto["tp"] + auto["fp"])
    if bound is not None:
        print(f"  error rate, 95% sure   {'< ' + format(bound, '.2%'):>7}   "
              f"(Clopper-Pearson upper bound on {auto['tp'] + auto['fp']:,} merges)")
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

    rq = review_metrics(pairs, truth)
    print(f"\nREVIEW QUEUE  (as a reviewer meets it: one record, its candidates)")
    print(f"  records waiting          {rq['records_in_queue']:>7,}   median {rq['median_candidates']} candidates each")
    print(f"  true match ranked first  {rq['true_match_first']:>7.1%}   of records that have one")
    print(f"  true match in top three  {rq['true_match_in_top3']:>7.1%}")

    splits = load_splits()
    by_split = split_metrics(pairs, truth, splits) if splits else {}
    if by_split:
        print("\nBY SPLIT  (test = families locked before tuning; two notations only they use)")
        for name, s in by_split.items():
            s["auto_error_bound"] = error_bound(s["auto_wrong"], s["auto_merged"])
            print(f"  {name:<5} {s['records']:>6,} records   auto-merged {s['auto_merged']:>5,}  wrong {s['auto_wrong']:>3}"
                  f"  (precision {s['auto_precision']:.1%})   recall {s['recall']:.1%} of {s['true_pairs']:,} true pairs")
            if s["auto_error_bound"] is not None:
                print(f"  {'':<5} {'':>6}           error rate, 95% sure < {s['auto_error_bound']:.2%}")

    blk = blocking_metrics(truth)
    if blk:
        print(f"\nBLOCKING  ({blk['mode']})")
        print(f"  candidate pairs     {blk['candidate_pairs']:>9,} of {blk['all_pairs']:,}")
        print(f"  reduction ratio     {blk['reduction_ratio']:>9.2%}   target >= 99.9% at 15,000 records")
        print(f"  pair completeness   {blk['pair_completeness']:>9.2%}   target >= 98%")
        if blk["true_pairs_missed"]:
            print(f"  true pairs never compared: {blk['true_pairs_missed']}")

    vetoes = veto_accuracy(pairs, truth)
    if vetoes:
        print("\nVETO ACCURACY  (record pairs across each trap)")
        print(f"  {'field':<18}{'pairs':>6}{'right':>7}{'other':>7}{'review':>8}{'AUTO':>6}{'apart':>7}")
        for f, v in sorted(vetoes.items()):
            flag = "   <- SAFETY FAILURE" if v["auto"] else ""
            print(f"  {f:<18}{v['pairs']:>6}{v['blocked_right']:>7}{v['blocked_other']:>7}"
                  f"{v['review']:>8}{v['auto']:>6}{v['never_met']:>7}{flag}")

    # Write the measured figures so results.py carries them into the UI.
    # A number nobody measured must never reach a slide - and a number typed
    # in by hand is a number nobody measured.
    paths.METRICS.write_text(json.dumps({
        "threshold": args.threshold,
        "auto_merge_threshold": AUTO_MERGE,
        "precision": round(m["precision"], 4),
        "recall": round(m["recall"], 4),
        "f1": round(m["f1"], 4),
        "auto_precision": round(auto["precision"], 4),
        "auto_merged_pairs": auto["tp"] + auto["fp"],
        "auto_wrong": auto["fp"],
        "auto_error_bound_95": round(bound, 5) if bound is not None else None,
        "false_merges": m["fp"],
        "trap_violations_auto": len(auto_traps),
        "trap_violations_review": len(review_traps),
        "true_items": c["true_items"],
        "predicted_clusters": c["predicted_clusters"],
        "duplication_rate": round(c["duplication_rate"], 4),
        "safety_blocks": len(safety_blocks),
        "blocking": {k: (round(v, 4) if isinstance(v, float) else v)
                     for k, v in (blk or {}).items()},
        "veto_accuracy": vetoes,
        "review_queue": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rq.items()},
        "by_split": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                     for k, v in by_split.items()},
        "records": len(truth),
        "run": paths.RUN or "demo",
    }, indent=1), encoding="utf-8")
    print(f"\nwrote {paths.METRICS.name}")

    print(f"\n{'-'*66}")
    print("These numbers come from a dataset whose corruption we designed, so")
    print("they measure how well we undo our own noise. Report them with that")
    print("caveat, and alongside a hand-labelled real hold-out when it exists.")


if __name__ == "__main__":
    main()
