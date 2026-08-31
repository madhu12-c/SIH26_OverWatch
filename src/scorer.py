"""
Hybrid scorer and clustering - the matching engine.

Takes extracted specs, vectors and purchase history; decides which records
describe the same physical item.

    python src/scorer.py
    python src/scorer.py --explain R00001 R00002     one pair, in detail
    python src/scorer.py --threshold 0.85

THREE SIGNALS, fused:

    text          embedding cosine similarity        weakest
    specs         attribute agreement                 heaviest - the whole idea
    procurement   same vendor / price band / plant    catches what text misses

THREE RULES THAT MATTER MORE THAN THE WEIGHTS:

    hard blockers veto        a grade or rating mismatch is an instant zero,
                              however well everything else lines up
    ignored fields            brand and part number never count - this is what
                              lets SKF and FAG resolve to one item
    missing != mismatched     one record silent on a field is absent
                              information, not evidence of difference

No model call happens anywhere in this file. Scoring is pure arithmetic over
cached extraction output, which is what makes every merge reproducible and
explainable. See docs/02-decisions/002-llm-once-per-record.md
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import defaultdict
from itertools import combinations

import paths
import schemas

# --- signal weights ---------------------------------------------------------
# Adaptive, not fixed. The share given to specifications grows with how much
# spec evidence actually exists.
#
# Why: our whole thesis is that two records can be the same item while sharing
# almost no words. If a low text similarity can drag down a perfect spec match,
# we have partially reintroduced the bug we claim to fix - SKF vs FAG agree on
# every extracted field and share almost no words, and must score high.
#
# But when extraction was sparse (one or two comparable fields) that confidence
# is not earned, so text and procurement carry more of the decision.
#
# Tune the constants against evaluate.py, never by eye.
SPEC_BASE = 0.50           # spec share with a single comparable field
SPEC_PER_FIELD = 0.08      # added per further field
SPEC_MAX = 0.88            # ceiling - text and procurement always keep a say
TEXT_SHARE = 0.45          # how the remainder splits between text and procurement


def signal_weights(compared: int) -> tuple[float, float, float]:
    """(text, spec, procurement), summing to 1, given the spec evidence count."""
    spec = min(SPEC_MAX, SPEC_BASE + SPEC_PER_FIELD * max(0, compared - 1))
    rest = 1.0 - spec
    return rest * TEXT_SHARE, spec, rest * (1 - TEXT_SHARE)

# --- confidence bands ------------------------------------------------------
AUTO_MERGE = 0.90      # above: system merges, logged and reversible
REVIEW_LOW = 0.70      # 0.70-0.90 goes to a human; below, leave alone

MAX_CLUSTER = 25       # anything larger routes to review regardless of score
MIN_INTRA = 0.62       # every pair inside a cluster must clear this, or split

# A price gap this large means two records cannot be the same item, whatever
# the text and specs say. A Rs 42 bolt and a Rs 4,200 bolt are different things.
PRICE_ANOMALY_RATIO = 10.0


# ===========================================================================
# Signal 1 - text
# ===========================================================================

def load_vectors():
    """Embeddings if they exist, otherwise None and we fall back to lexical.

    embed.py needs sentence-transformers installed. The pipeline must still run
    end to end without it, so text similarity degrades rather than crashing.
    """
    if not paths.EMBEDDINGS.exists():
        return None
    try:
        import numpy as np
        blob = np.load(paths.EMBEDDINGS, allow_pickle=False)
        ids = [str(x) for x in blob["ids"]]
        return {"vectors": blob["vectors"], "lookup": {r: i for i, r in enumerate(ids)}}
    except Exception as exc:                                       # noqa: BLE001
        print(f"  ! could not read embeddings ({exc}) - using lexical fallback")
        return None


_TOKEN = re.compile(r"[a-z0-9]+")


def lexical_similarity(a: str, b: str) -> float:
    """Jaccard over tokens. A stand-in for embeddings, not a replacement.

    Deliberately crude: it exists so the pipeline runs before embeddings are
    computed, and so the fallback is visibly worse rather than quietly similar.
    """
    ta = set(_TOKEN.findall(a.lower()))
    tb = set(_TOKEN.findall(b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def text_similarity(a_id, b_id, descriptions, vecs) -> float:
    if vecs is not None:
        la, lb = vecs["lookup"].get(a_id), vecs["lookup"].get(b_id)
        if la is not None and lb is not None:
            return float(vecs["vectors"][la] @ vecs["vectors"][lb])
    return lexical_similarity(descriptions.get(a_id, ""), descriptions.get(b_id, ""))


# ===========================================================================
# Signal 2 - specifications. The heaviest signal and the core of the project.
# ===========================================================================

def values_agree(field: schemas.Field, x, y) -> bool:
    if field.kind == "num":
        try:
            fx, fy = float(x), float(y)
        except (TypeError, ValueError):
            return False
        # A little tolerance, because 25 and 25.0 and 25.4 all appear for what
        # is the same nominal dimension written from different sources.
        return abs(fx - fy) <= max(0.02 * max(abs(fx), abs(fy)), 0.5)
    return str(x).strip().upper() == str(y).strip().upper()


def spec_agreement(a: dict, b: dict) -> dict:
    """Compare two extracted spec objects.

    Returns the score plus the evidence behind it - which fields agreed, which
    were ignored, and which one (if any) vetoed the match. The review screen
    and the audit trail both read this, so a bare number is not enough.
    """
    if a["category"] != b["category"]:
        return {"score": 0.0, "blocked_by": "category",
                "reason": f"{a['category']} vs {b['category']}",
                "matched": [], "ignored": [], "compared": 0}

    category = a["category"]
    attrs_a, attrs_b = a["attributes"], b["attributes"]
    conf_a, conf_b = a.get("confidence", {}), b.get("confidence", {})

    matched, mismatched, ignored, unverified_hard = [], [], [], []
    weight_hit = weight_total = 0.0

    for field in schemas.fields_for(category):
        if field.ignore:
            if field.name in attrs_a and field.name in attrs_b:
                ignored.append(field.name)
            continue

        x, y = attrs_a.get(field.name), attrs_b.get(field.name)

        # MISSING IS NOT MISMATCHED. Silence on one side is absent information,
        # not evidence of difference. No penalty, no credit.
        #
        # But a HARD field we could not check is a different situation. We are
        # not saying the grades match - we are saying we do not know. The
        # evaluation harness caught this: 150# and 300# gate valves were
        # merging because one side never had pressure_class extracted, so the
        # veto could not fire. Absence of a safety check is not a pass.
        if x is None or y is None:
            if field.hard:
                unverified_hard.append(field.name)
            continue

        agree = values_agree(field, x, y)

        if field.hard and not agree:
            return {"score": 0.0, "blocked_by": field.name,
                    "reason": f"{x} vs {y}", "matched": matched,
                    "ignored": ignored, "compared": len(matched) + len(mismatched) + 1}

        # A field extracted with low confidence pulls less than one read
        # straight out of the text.
        confidence = min(conf_a.get(field.name, 0.8), conf_b.get(field.name, 0.8))
        w = field.weight * confidence
        weight_total += w
        if agree:
            weight_hit += w
            matched.append(field.name)
        else:
            mismatched.append(field.name)

    if weight_total == 0:
        # Same category, but nothing comparable was extracted from either side.
        # That is weak evidence of sameness, not none - and it must not look
        # like a confident match.
        return {"score": 0.25, "blocked_by": None, "reason": "no comparable fields",
                "matched": [], "ignored": ignored, "compared": 0}

    return {"score": weight_hit / weight_total, "blocked_by": None, "reason": None,
            "matched": matched, "mismatched": mismatched, "ignored": ignored,
            "unverified_hard": unverified_hard,
            "compared": len(matched) + len(mismatched)}


# ===========================================================================
# Signal 3 - procurement behaviour. Evidence for a match, and a guard against one.
# ===========================================================================

def price_band(price: float) -> int:
    """Log-scale band. Wide enough to hide a price, narrow enough to catch a
    100x gap. Also what would cross a company boundary in the federated design.
    """
    return 0 if price <= 0 else max(0, min(9, int(math.log10(price) * 2)))


def build_purchase_profiles() -> dict:
    """One profile per (cpse, source_code): vendors, median price, order sizes."""
    rows = defaultdict(list)
    with paths.PURCHASES.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows[(r["cpse"], r["source_code"])].append(r)

    profiles = {}
    for key, group in rows.items():
        prices = [float(g["unit_price"]) for g in group]
        qtys = [int(g["qty"]) for g in group]
        profiles[key] = {
            "vendors": {g["vendor"] for g in group},
            "plants": {g["plant"] for g in group},
            "median_price": statistics.median(prices),
            "band": price_band(statistics.median(prices)),
            "median_qty": statistics.median(qtys),
        }
    return profiles


def procurement_similarity(a: dict, b: dict, profiles: dict) -> dict:
    pa = profiles.get((a.get("cpse"), a.get("source_code")))
    pb = profiles.get((b.get("cpse"), b.get("source_code")))
    if not pa or not pb:
        return {"score": None, "blocked_by": None, "reason": None}

    # The guard half of this signal. Identical text and identical specs cannot
    # survive a 10x price gap - something real distinguishes them that the
    # description never captured.
    lo, hi = sorted((pa["median_price"], pb["median_price"]))
    if lo > 0 and hi / lo >= PRICE_ANOMALY_RATIO:
        return {"score": 0.0, "blocked_by": "price_anomaly",
                "reason": f"Rs {lo:,.0f} vs Rs {hi:,.0f} ({hi/lo:.0f}x)"}

    parts = []

    # Same vendor is strong evidence, and it works across companies - two CPSEs
    # both buying from SKF India is exactly the signal we want.
    parts.append(1.0 if pa["vendors"] & pb["vendors"] else 0.2)

    parts.append(max(0.0, 1.0 - abs(pa["band"] - pb["band"]) / 3.0))

    ratio = (min(pa["median_qty"], pb["median_qty"]) /
             max(pa["median_qty"], pb["median_qty"], 1))
    parts.append(ratio)

    # Plant only carries information WITHIN one company. Two CPSEs never share
    # a plant, so scoring that as disagreement would penalise exactly the
    # cross-CPSE matches this whole project exists to find.
    if a.get("cpse") == b.get("cpse"):
        parts.append(1.0 if pa["plants"] & pb["plants"] else 0.4)

    return {"score": sum(parts) / len(parts), "blocked_by": None, "reason": None}


# ===========================================================================
# Fusion
# ===========================================================================

def score_pair(a, b, descriptions, vecs, profiles) -> dict:
    text = text_similarity(a["record_id"], b["record_id"], descriptions, vecs)
    spec = spec_agreement(a, b)
    proc = procurement_similarity(a, b, profiles)

    out = {
        "a": a["record_id"], "b": b["record_id"],
        "text_sim": round(text, 3),
        "spec_sim": round(spec["score"], 3),
        "proc_sim": None if proc["score"] is None else round(proc["score"], 3),
        "matched_fields": spec.get("matched", []),
        "ignored_fields": spec.get("ignored", []),
        "blocked_by": None, "reason": None,
    }

    for signal in (spec, proc):
        if signal.get("blocked_by"):
            out["blocked_by"] = signal["blocked_by"]
            out["reason"] = signal["reason"]
            out["final"] = 0.0
            return out

    w_text, w_spec, w_proc = signal_weights(spec.get("compared", 0))
    out["weights"] = {"text": round(w_text, 3), "spec": round(w_spec, 3),
                      "proc": round(w_proc, 3)}

    # Procurement is absent for items never purchased. Redistribute its weight
    # rather than scoring the pair as if procurement disagreed.
    if proc["score"] is None:
        total = w_text + w_spec
        out["final"] = round((w_text * text + w_spec * spec["score"]) / total, 3)
    else:
        out["final"] = round(w_text * text + w_spec * spec["score"]
                             + w_proc * proc["score"], 3)

    # A safety field we could not verify caps the pair below the auto-merge
    # band. It can still be approved - by a human who can look the item up -
    # but the system will not merge it silently.
    unverified = spec.get("unverified_hard") or []
    if unverified and out["final"] >= AUTO_MERGE:
        out["final"] = round(AUTO_MERGE - 0.01, 3)
    out["unverified_hard"] = unverified
    if unverified:
        out["review_reason"] = ("could not verify " + ", ".join(unverified)
                                + " - not extracted from both records")
    return out


# ===========================================================================
# Clustering
# ===========================================================================

class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_clusters(record_ids, pairs, threshold):
    """Union-find, then guard against transitive closure explosion.

    A~B and B~C group A and C together even when A and C are unrelated, and one
    bridging record can drag hundreds of items into a single blob. So after
    forming a group we check that EVERY pair inside it scores well - not just
    the connected ones - and split the group if it does not hold together.
    """
    uf = UnionFind(record_ids)
    lookup = {}
    for p in pairs:
        lookup[(p["a"], p["b"])] = p["final"]
        lookup[(p["b"], p["a"])] = p["final"]
        if p["final"] >= threshold:
            uf.union(p["a"], p["b"])

    groups = defaultdict(list)
    for rid in record_ids:
        groups[uf.find(rid)].append(rid)

    clusters, split_count = [], 0
    for members in groups.values():
        members.sort()
        if len(members) == 1:
            clusters.append({"members": members, "band": "single",
                             "confidence": 1.0, "cohesion": 1.0})
            continue

        internal = [lookup.get((x, y), 0.0) for x, y in combinations(members, 2)]
        cohesion = sum(internal) / len(internal)
        weakest = min(internal)

        if len(members) > MAX_CLUSTER:
            band = "review"                       # too big to trust, whatever it scores
        elif weakest < MIN_INTRA:
            band = "review"                       # a member is only weakly attached
            split_count += 1
        elif cohesion >= AUTO_MERGE:
            band = "auto"
        elif cohesion >= REVIEW_LOW:
            band = "review"
        else:
            band = "review"

        clusters.append({"members": members, "band": band,
                         "confidence": round(cohesion, 3),
                         "cohesion": round(cohesion, 3),
                         "weakest_pair": round(weakest, 3)})

    return clusters, split_count


# ===========================================================================

def load_inputs():
    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))
    descriptions = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            descriptions[row["record_id"]] = row["description"]
    return specs, descriptions


def explain(a_id, b_id):
    """One pair, in full. This is what the review screen has to show a human."""
    specs, descriptions = load_inputs()
    vecs, profiles = load_vectors(), build_purchase_profiles()
    a, b = specs[a_id], specs[b_id]
    p = score_pair(a, b, descriptions, vecs, profiles)

    print(f"\n{a_id}  {descriptions.get(a_id,'')}")
    print(f"{b_id}  {descriptions.get(b_id,'')}\n")
    print(f"  category      {a['category']}  /  {b['category']}")

    names = sorted(set(a["attributes"]) | set(b["attributes"]))
    for name in names:
        x, y = a["attributes"].get(name, "-"), b["attributes"].get(name, "-")
        if name in schemas.ignored_fields(a["category"]):
            mark = "IGNORED"
        elif x == "-" or y == "-":
            mark = "missing"                 # absent information, not a mismatch
        elif name == p["blocked_by"]:
            mark = "*** BLOCK ***"
        elif name in p["matched_fields"]:
            mark = "match"
        else:
            mark = "differ"
        star = "*" if name in schemas.hard_fields(a["category"]) else " "
        print(f"  {star} {name:<18} {str(x):<16} {str(y):<16} {mark}")

    print(f"\n  text        {p['text_sim']}")
    print(f"  specs       {p['spec_sim']}")
    print(f"  procurement {p['proc_sim']}")
    if p["blocked_by"]:
        print(f"\n  BLOCKED on {p['blocked_by']}: {p['reason']}")
    print(f"  FINAL       {p['final']}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=REVIEW_LOW)
    ap.add_argument("--explain", nargs=2, metavar=("A", "B"))
    args = ap.parse_args()

    if args.explain:
        explain(*args.explain)
        return

    specs, descriptions = load_inputs()
    vecs = load_vectors()
    profiles = build_purchase_profiles()
    ids = sorted(specs)

    print(f"{len(ids)} records, {len(ids)*(len(ids)-1)//2:,} pairs")
    print(f"text signal: {'embeddings' if vecs else 'lexical fallback (run embed.py)'}\n")

    # At this scale all-pairs is the right call - 4,950 comparisons is instant.
    # Blocking is designed and documented but deliberately not built yet.
    # See docs/02-decisions/007-no-infrastructure-yet.md
    pairs = []
    for a_id, b_id in combinations(ids, 2):
        p = score_pair(specs[a_id], specs[b_id], descriptions, vecs, profiles)
        if p["final"] > 0 or p["blocked_by"]:
            pairs.append(p)

    scored = [p for p in pairs if not p["blocked_by"]]
    blocked = [p for p in pairs if p["blocked_by"]]
    clusters, splits = build_clusters(ids, scored, args.threshold)

    paths.ensure_dirs()
    paths.PAIR_SCORES.write_text(json.dumps(pairs, indent=1), encoding="utf-8")
    paths.CLUSTERS.write_text(json.dumps(clusters, indent=1), encoding="utf-8")

    multi = [c for c in clusters if len(c["members"]) > 1]
    by_band = defaultdict(int)
    for c in clusters:
        by_band[c["band"]] += 1
    by_rule = defaultdict(int)
    for p in blocked:
        by_rule[p["blocked_by"]] += 1

    # Separate "obviously unrelated" from "nearly merged, stopped by a safety
    # rule". Only the second group belongs in the safety interlock report - a
    # bearing not merging with a gasket is not an interesting refusal.
    safety = {r: n for r, n in by_rule.items() if r != "category"}

    print(f"scored pairs      {len(scored):>6,}")
    print(f"different category{by_rule.get('category', 0):>6,}   (not interesting)")
    print(f"SAFETY BLOCKS     {sum(safety.values()):>6,}   <- the interlock report")
    for rule, n in sorted(safety.items(), key=lambda x: -x[1]):
        print(f"    {rule:<22} {n:>5,}")
    print(f"\nclusters          {len(clusters):>6}   ({len(multi)} with 2+ members)")
    for band in ("auto", "review", "single"):
        print(f"    {band:<22} {by_band[band]:>5}")
    if splits:
        print(f"\n{splits} cluster(s) held back for a weakly attached member")
    print(f"\n{len(ids)} raw -> {len(clusters)} unique   "
          f"({1 - len(clusters)/len(ids):.1%} duplication)")

    # The two cases the demo depends on. Verified every run, so a regression is
    # impossible to miss.
    print("\ndemo cases")
    print("-" * 60)
    for a_id, b_id, expect in (("R00001", "R00002", "MATCH"),
                               ("R00003", "R00004", "BLOCK")):
        if a_id not in specs or b_id not in specs:
            continue
        p = score_pair(specs[a_id], specs[b_id], descriptions, vecs, profiles)
        got = "BLOCK" if p["blocked_by"] else ("MATCH" if p["final"] >= args.threshold
                                               else "no match")
        ok = "OK " if got == expect else "!! "
        detail = f"blocked on {p['blocked_by']}" if p["blocked_by"] else f"score {p['final']}"
        print(f"  {ok}{a_id}/{b_id}  expected {expect:<5} got {got:<9} {detail}")


if __name__ == "__main__":
    main()
