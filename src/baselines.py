"""
Baselines - would plain text matching have done the job?

    python src/baselines.py                 the demo set
    SIH_RUN=15k python src/baselines.py     the 15,000-record run

Three text matchers against ours, on THE SAME candidate pairs (blocking's
output), so the only difference is how a pair is judged:

    fuzzy      difflib's SequenceMatcher ratio on the lower-cased text
    tf-idf     cosine of character 2-4-gram TF-IDF vectors (scikit-learn) -
               character grams, because they survive "SS316" / "SS 316"
    embedding  cosine of the same sentence embeddings our text signal uses
    ours       the pipeline's score, with its fixed bands (0.90 auto, 0.70
               review) - never re-tuned here

Fair to the baselines. Each one gets two settings, both chosen on the DEV
families and then applied unchanged to the TEST families it never saw:

    best F1    the threshold with the best F1 on dev - its strongest setting
    zero-wrong the lowest threshold with no wrong merge on dev - what it would
               take to be as safe as a refinery needs

"Traps merged" counts merged pairs across a deliberate near-miss (SS304 vs
SS316, 150# vs 300#): a wrong merge that puts the wrong part in a line.

data/truth is read here, as in evaluate.py: this is evaluation, not matching.
"""

from __future__ import annotations

import csv
import difflib
import json
import sys
from collections import defaultdict

import paths
from scorer import AUTO_MERGE, REVIEW_LOW, load_vectors

sys.stdout.reconfigure(encoding="utf-8")


def load():
    with paths.GROUND_TRUTH.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    truth = {r["record_id"]: r["true_item_id"] for r in rows}
    split = {r["record_id"]: (r.get("split") or "all") for r in rows}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        desc = {r["record_id"]: r["description"] for r in csv.DictReader(fh)}
    traps = set()
    if paths.TRAPS.exists():
        traps = {frozenset((t["a"], t["b"])) for t in json.loads(paths.TRAPS.read_text(encoding="utf-8"))}
    cands = [tuple(p) for p in json.loads(paths.BLOCKING.read_text(encoding="utf-8"))["candidates"]]
    return truth, split, desc, traps, cands


def fuzzy_scores(cands, desc):
    low = {r: d.lower() for r, d in desc.items()}
    return [difflib.SequenceMatcher(None, low[a], low[b], autojunk=False).ratio() for a, b in cands]


def tfidf_scores(cands, desc):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    ids = sorted(desc)
    index = {r: i for i, r in enumerate(ids)}
    x = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=True).fit_transform(desc[r] for r in ids)
    a = np.fromiter((index[p[0]] for p in cands), dtype=np.int64, count=len(cands))
    b = np.fromiter((index[p[1]] for p in cands), dtype=np.int64, count=len(cands))
    out = []
    for lo in range(0, len(cands), 50_000):              # rows are L2-normalised: dot = cosine
        out.extend(np.asarray(x[a[lo:lo + 50_000]].multiply(x[b[lo:lo + 50_000]]).sum(axis=1)).ravel())
    return [float(v) for v in out]


def embedding_scores(cands):
    vecs = load_vectors()
    if vecs is None:
        return None
    v, look = vecs["vectors"], vecs["lookup"]
    return [float(v[look[a]] @ v[look[b]]) for a, b in cands]


def our_scores(cands):
    pairs = json.loads(paths.PAIR_SCORES.read_text(encoding="utf-8"))
    final = {frozenset((p["a"], p["b"])): (0.0 if p.get("blocked_by") else p["final"]) for p in pairs}
    return [final.get(frozenset(p), 0.0) for p in cands]


def true_pair_counts(truth, split):
    per = defaultdict(lambda: defaultdict(int))
    for r, item in truth.items():
        per[split[r]][item] += 1
    counts = {s: sum(n * (n - 1) // 2 for n in items.values()) for s, items in per.items()}
    counts["all"] = sum(v for k, v in counts.items() if k != "all") or counts.get("all", 0)
    return counts


def measure(scores, rows, threshold, n_true):
    """Merged, wrong, precision, recall, traps at one threshold."""
    merged = wrong = traps = 0
    for s, same, trap in rows:
        if s >= threshold:
            merged += 1
            if not same:
                wrong += 1
                traps += trap
    right = merged - wrong
    return {"merged": merged, "wrong": wrong, "traps_merged": traps,
            "precision": round(right / merged, 4) if merged else None,
            "recall": round(right / n_true, 4) if n_true else None}


def pick_thresholds(rows, n_true):
    """Best-F1 and zero-wrong thresholds from (score, same, trap) rows."""
    order = sorted(rows, key=lambda r: -r[0])
    best_f1, best_t, tp, k = -1.0, 1.01, 0, 0
    i = 0
    while i < len(order):                                 # step over ties together
        t = order[i][0]
        while i < len(order) and order[i][0] == t:
            tp += order[i][1]
            k += 1
            i += 1
        f1 = 2 * tp / (k + n_true) if (k + n_true) else 0
        if f1 > best_f1:
            best_f1, best_t = f1, t
    worst_false = max((s for s, same, _ in rows if not same), default=0.0)
    return best_t, worst_false + 1e-9


def main() -> None:
    truth, split, desc, traps, cands = load()
    n_true = true_pair_counts(truth, split)
    same = [truth[a] == truth[b] for a, b in cands]
    trap = [frozenset((truth[a], truth[b])) in traps for a, b in cands]
    where = [split[a] if split[a] == split[b] else "cross" for a, b in cands]
    tuned_on = "dev" if "dev" in n_true else "all"
    report_on = [s for s in ("test", "dev") if s in n_true] + ["all"]

    print(f"run: {paths.RUN or 'demo'}   {len(truth):,} records   {len(cands):,} candidate pairs "
          f"(the same pairs for every method)")
    print(f"thresholds chosen on: {tuned_on}" + ("   (demo set: no held-out split - flattering to the baselines)"
                                                 if tuned_on == "all" else ""))

    methods = {"fuzzy": fuzzy_scores(cands, desc), "tf-idf": tfidf_scores(cands, desc)}
    emb = embedding_scores(cands)
    if emb is not None:
        methods["embedding"] = emb

    def rows_for(scores, s):
        return [(scores[i], same[i], trap[i]) for i in range(len(cands)) if s == "all" or where[i] == s]

    out = {"run": paths.RUN or "demo", "records": len(truth), "candidate_pairs": len(cands),
           "tuned_on": tuned_on, "true_pairs": dict(n_true), "methods": {}, "ours": {}}
    for name, scores in methods.items():
        best_t, safe_t = pick_thresholds(rows_for(scores, tuned_on), n_true[tuned_on])
        out["methods"][name] = {
            setting: {"threshold": round(t, 4),
                      **{s: measure(scores, rows_for(scores, s), t, n_true[s]) for s in report_on}}
            for setting, t in (("best_f1", best_t), ("zero_wrong", safe_t))}

    ours = our_scores(cands)
    for setting, t in (("auto", AUTO_MERGE), ("proposed", REVIEW_LOW)):
        out["ours"][setting] = {"threshold": t,
                                **{s: measure(ours, rows_for(ours, s), t, n_true[s]) for s in report_on}}

    show = report_on[0]
    print(f"\nON THE {show.upper()} FAMILIES  ({n_true[show]:,} true pairs)\n")
    print(f"  {'method':<11}{'setting':<22}{'thr':>6}{'merged':>9}{'wrong':>8}{'traps':>7}{'precision':>11}{'recall':>8}")

    def line(name, setting, t, m):
        p = "-" if m["precision"] is None else f"{m['precision']:.1%}"
        print(f"  {name:<11}{setting:<22}{t:>6.2f}{m['merged']:>9,}{m['wrong']:>8,}{m['traps_merged']:>7,}"
              f"{p:>11}{m['recall']:>8.1%}")

    for name, settings in out["methods"].items():
        line(name, "best F1 (tuned on dev)", settings["best_f1"]["threshold"], settings["best_f1"][show])
        line("", "zero wrong on dev", settings["zero_wrong"]["threshold"], settings["zero_wrong"][show])
    line("ours", "auto-merge (fixed)", AUTO_MERGE, out["ours"]["auto"][show])
    line("", "auto + review (human)", REVIEW_LOW, out["ours"]["proposed"][show])

    paths.BASELINES.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {paths.BASELINES.name}")
    print("Review pairs go to a person, so 'auto + review' is recall with a human, not merges.")


if __name__ == "__main__":
    main()
