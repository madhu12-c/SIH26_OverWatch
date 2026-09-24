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

import blocking
import normalise as nz
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

GRADE_FIELDS = ("material_grade", "body_material", "wetted_material")

# Numbers that name or count something rather than measure it.
EXACT_NUMBERS = {"cores", "phases", "poles", "angle", "pressure_rating_psi",
                 "cross_section_mm2", "rating_kva", "range_min", "range_max"}

# Blocks that say "these are obviously different things", not "a safety rule
# stopped a near-miss". Kept out of the safety interlock report.
NOT_SAFETY = {"category", "noun", "quantities"}

# Categories with no real schema. Their pairs can reach a human, never auto.
NO_AUTO_CATEGORIES = {"other", "unknown"}


def compare(field: schemas.Field, x, y) -> str:
    """'agree' | 'mismatch' | 'unknown'.

    Grades use the family ladder (normalise.compare_grades): a bare "CS"
    against "A106 GR B" is unknown, not a match and not a veto.
    """
    if field.name in GRADE_FIELDS:
        return nz.compare_grades(x, y)
    if field.name == "connection":
        return _compare_connection(x, y)
    if field.kind != "num":
        # Specs cached by an earlier run keep older spellings ("SCH-40",
        # "GR" for graphite). A spelling must never read as a difference.
        x, y = schemas.canonical_value(field.name, x), schemas.canonical_value(field.name, y)
    return "agree" if values_agree(field, x, y) else "mismatch"


_CONN = re.compile(r"(\d/\d|\d)\s*(?:IN\b|INCH|\")?\s*(NPT|BSP)?\s*(BOTTOM|LOWER|BACK|REAR|SIDE)?")


def _compare_connection(x, y) -> str:
    """'1/2 IN NPT BOTTOM': the thread size must agree; so must the position
    where both give one. A position cut off one side is a doubt."""
    mx, my = _CONN.search(str(x).upper()), _CONN.search(str(y).upper())
    if not mx or not my:
        return "agree" if str(x).upper() == str(y).upper() else "mismatch"
    if mx.group(1) != my.group(1) or (mx.group(2) and my.group(2) and mx.group(2) != my.group(2)):
        return "mismatch"
    pos = {"LOWER": "BOTTOM", "REAR": "BACK"}
    px, py = pos.get(mx.group(3), mx.group(3)), pos.get(my.group(3), my.group(3))
    if px and py:
        return "agree" if px == py else "mismatch"
    return "unknown" if (px or py) else "agree"


def values_agree(field: schemas.Field, x, y) -> bool:
    if field.kind == "num":
        try:
            fx, fy = float(x), float(y)
        except (TypeError, ValueError):
            return False
        big = max(abs(fx), abs(fy))
        # Size names and counts are exact. 1-1/4" and 1-1/2" are different
        # pipes, 3 cores and 3.5 cores different cables - an absolute 0.5
        # tolerance here once let a 1-1/4" pipe match a 1-1/2" one.
        if field.unit == "inch" or field.name in EXACT_NUMBERS:
            return abs(fx - fy) <= 0.002 * big + 1e-6
        # Measurements get a little room: 457 and 457.2 mm are one OD, and a
        # kW rating converted to hp lands within a percent or two.
        return abs(fx - fy) <= max(0.02 * big, 0.05)
    return str(x).strip().upper() == str(y).strip().upper()


# ---------------------------------------------------------------------------
# Variant awareness.
#
# Two records can be silent on the very field that separates two products:
# "GASKET SW SS316 4IN 150#" twice, where the registry holds both a graphite-
# and a PTFE-filled 4" gasket. Silence on both sides is not evidence of
# difference - but when the registry's own records show that this item comes
# in more than one variant, it is not evidence of sameness either. Such a
# pair can reach a person, never auto-merge.
#
# The index is learned from the records themselves (never from truth): for
# each item anchor (blocking.ANCHORS - bearing|6205, gasket|4 ...), which
# values of each variant field (veto-only fields) anyone has written.
# ---------------------------------------------------------------------------

VARIANTS: dict = {}
_VARIANTS_BUILT = [False]


def load_variants(specs: dict) -> None:
    """Learn the variant index from every record. Until this runs the scorer
    stays strict: any one-sided veto field holds a pair back."""
    VARIANTS.clear()
    VARIANTS.update(build_variant_index(specs))
    _VARIANTS_BUILT[0] = True


def build_variant_index(specs: dict) -> dict:
    import blocking
    index = defaultdict(lambda: defaultdict(set))
    for s in specs.values():
        cat = s.get("category")
        key = _anchor(cat, s.get("attributes", {}), blocking)
        if key is None:
            continue
        for f in schemas.fields_for(cat):
            if f.hard and (not f.required or f.name in GRADE_FIELDS) and f.name in s["attributes"]:
                value = s["attributes"][f.name]
                value = nz.canonical_grade(value) if f.name in GRADE_FIELDS else schemas.canonical_value(f.name, value)
                index[key][f.name].add(str(value))
    return {k: {f: v for f, v in d.items() if len(v) > 1} for k, d in index.items()}


def _anchor(cat, attrs, blocking=None):
    if blocking is None:
        import blocking
    fields = blocking.ANCHORS.get(cat)
    if not fields or not all(f in attrs for f in fields):
        return None
    return cat + "|" + "|".join(blocking._v(attrs[f]) for f in fields)


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
    # Fill what each record implies but does not state (kW -> hp, OD -> size),
    # on copies - specs cached before derive() existed get the same treatment.
    attrs_a, attrs_b = dict(a["attributes"]), dict(b["attributes"])
    conf_a, conf_b = dict(a.get("confidence", {})), dict(b.get("confidence", {}))
    schemas.derive(category, attrs_a, conf_a)
    schemas.derive(category, attrs_b, conf_b)

    matched, mismatched, ignored, unverified_hard, unsure = [], [], [], [], []
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
        #
        # A veto field that is not required (a pipe's measured OD, black versus
        # galvanised) blocks on a mismatch but is not demanded: real text only
        # sometimes states it, and the synthetic set never does.
        #
        # ONE-SIDED. When one record states a veto field and the other is
        # silent, the silent one may be the other product: "GASKET SW SS316
        # 4IN 150#" against the same gasket "PTFE FILLED" - or its graphite
        # twin. Silence is not a mismatch, so no veto; but it is not a check
        # either, so the pair can reach a person, never auto-merge. On the
        # 15,000-record run this one rule was most of the difference between
        # 31% and a safe auto band.
        #
        # Tried and rejected (24 Sept): applying this only where the registry
        # has SEEN more than one value. The default variant is the one nobody
        # writes - "plain" plate, "unarmoured" cable - so the registry looks
        # single-valued exactly where it is not; 8 wrong auto-merges and 8
        # traps at 15,000 records. Silence on one side always holds a pair.
        if x is None or y is None:
            if field.hard and (field.required or (x is None) != (y is None)):
                unverified_hard.append(field.name)
            continue

        result = compare(field, x, y)
        # "SS" and "SS" agree as words, not as grades. When the registry holds
        # this item in more than one grade, two family-only records could be
        # SS304 and SS316 - a doubt, not a match.
        if result == "agree" and field.name in GRADE_FIELDS and nz.grade_family(nz.canonical_grade(x))[1]:
            key = _anchor(category, attrs_a)
            if key and len(VARIANTS.get(key, {}).get(field.name, ())) > 1:
                result = "unknown"
        if result == "unknown":
            # The two values neither agree nor contradict - "CS" against
            # "A106 GR B". Treated as a check we could not make.
            if field.hard:
                unverified_hard.append(field.name)
            unsure.append(field.name)
            continue
        agree = result == "agree"

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

    # Both silent on a variant field that the registry shows in more than
    # one value for this item: not a check - see VARIANTS above.
    if VARIANTS:
        key = _anchor(category, attrs_a)
        for fname in VARIANTS.get(key, {}) if key and key == _anchor(category, attrs_b) else ():
            if fname not in attrs_a and fname not in attrs_b:
                unverified_hard.append(fname)
                unsure.append(fname)

    # A required field checked through its alternative is checked: no
    # schedule on either side, but both walls agree, is a verified wall.
    by_name = {f.name: f for f in schemas.fields_for(category)}
    unverified_hard = [n for n in dict.fromkeys(unverified_hard)
                       if n in unsure or not any(alt in matched for alt in by_name[n].alt)]

    if weight_total == 0:
        # Same category, but nothing comparable was extracted from either side.
        # That is weak evidence of sameness, not none - and it must not look
        # like a confident match.
        return {"score": 0.25, "blocked_by": None, "reason": "no comparable fields",
                "matched": [], "ignored": ignored, "compared": 0,
                "unverified_hard": unverified_hard, "unsure": unsure}

    return {"score": weight_hit / weight_total, "blocked_by": None, "reason": None,
            "matched": matched, "mismatched": mismatched, "ignored": ignored,
            "unverified_hard": unverified_hard, "unsure": unsure,
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
            what_if = counterfactual(a, b, text, spec, proc)
            if what_if:
                out["counterfactual"] = what_if
            return out

    out.update(_fuse(a, text, spec, proc))
    return out


def _fuse(a, text, spec, proc) -> dict:
    """The three signals into one score, with the caps that keep doubt out of
    the auto band. Shared by the real score and the counterfactual."""
    w_text, w_spec, w_proc = signal_weights(spec.get("compared", 0))
    out = {"weights": {"text": round(w_text, 3), "spec": round(w_spec, 3),
                       "proc": round(w_proc, 3)}}

    # Procurement is absent for items never purchased. Redistribute its weight
    # rather than scoring the pair as if procurement disagreed.
    if proc["score"] is None:
        total = w_text + w_spec
        out["final"] = round((w_text * text + w_spec * spec["score"]) / total, 3)
    else:
        out["final"] = round(w_text * text + w_spec * spec["score"]
                             + w_proc * proc["score"], 3)
    evidence_score = out["final"]

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
    unsure = spec.get("unsure") or []
    if unsure:
        out["review_reason"] = ("could not tell " + ", ".join(unsure) + " - the family only on one side, "
                                "or neither record says which variant and the registry holds several")

    # Outside every schema: the noun and the numbers can say "possibly the
    # same", never "certainly". A person always confirms.
    if a.get("category") in NO_AUTO_CATEGORIES and out["final"] >= AUTO_MERGE:
        out["final"] = round(AUTO_MERGE - 0.01, 3)
        out["review_reason"] = "outside every schema - matched on noun and numbers only"
    elif evidence_score > out["final"]:
        # Held back only by what it could not check: tell the reviewer what
        # confirming it is worth. "Everything else agrees at 0.96."
        out["counterfactual"] = {"kind": "unverified", "fields": unverified,
                                 "score": evidence_score}
    return out


def counterfactual(a, b, text, spec, proc, max_fields: int = 3) -> dict | None:
    """What the veto cost. For a blocked pair, the score it would get if the
    blocking field agreed: "if the grade matched, this would score 0.94".

    It is the evidence that one field decided, and that the rules - not a
    threshold - refused the merge. The blocking field is set equal on both
    sides and the pair scored again; if a second field blocks, that is set
    too (up to max_fields), so the answer names every field that differs. A
    price gap is set aside the same way. Different categories have no
    counterfactual: a bearing is not one field away from a gasket.

    One extra spec comparison, only for blocked pairs. Never the LLM.
    """
    fields = []
    a2, b2 = a, b
    while spec.get("blocked_by"):
        name = spec["blocked_by"]
        if name == "category" or len(fields) == max_fields:
            return None
        value = a2["attributes"].get(name, b2["attributes"].get(name))
        if value is None:                   # both values were derived - nothing to set
            return None
        fields.append(name)
        a2 = {**a2, "attributes": {**a2["attributes"], name: value}}
        b2 = {**b2, "attributes": {**b2["attributes"], name: value}}
        spec = spec_agreement(a2, b2)
    if proc.get("blocked_by"):
        fields.append(proc["blocked_by"])
        proc = {"score": None}
    fused = _fuse(a, text, spec, proc)
    return {"kind": "blocked", "fields": fields, "score": fused["final"],
            "capped_by": fused["unverified_hard"] or None}


def review_rank(p: dict) -> tuple:
    """How to order a record's candidates in the review queue.

    Not by the final score: every pair with a field it could not check is
    capped at the same 0.89, so the final score ties exactly where a
    reviewer needs an order. What separates the right candidate is how much
    was actually confirmed. On the 15,000-record dev families this put the
    true match first for 53% of records (21.8% by final score) and in the
    top three for 81% (57%).
    """
    return (len(p.get("matched_fields") or []), p.get("spec_sim") or 0.0, p.get("text_sim") or 0.0)


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


def _split(members, lookup):
    """Re-group members by auto-band links only; each part checked again."""
    uf = UnionFind(members)
    for x, y in combinations(members, 2):
        if lookup.get((x, y), 0.0) >= AUTO_MERGE:
            uf.union(x, y)
    parts = defaultdict(list)
    for m in members:
        parts[uf.find(m)].append(m)
    out = []
    for part in parts.values():
        part.sort()
        if len(part) == 1:
            out.append({"members": part, "band": "single", "confidence": 1.0, "cohesion": 1.0})
            continue
        internal = [lookup.get((x, y), 0.0) for x, y in combinations(part, 2)]
        cohesion, weakest = sum(internal) / len(internal), min(internal)
        if weakest < AUTO_MERGE and len(part) > 2:
            # Still chained by auto links alone: keep only the strongest pair
            # structure honest - every member stands alone and the links go
            # to review.
            out.extend({"members": [m], "band": "single", "confidence": 1.0, "cohesion": 1.0} for m in part)
            continue
        out.append({"members": part, "band": "auto" if weakest >= AUTO_MERGE else "review",
                    "confidence": round(cohesion, 3), "cohesion": round(cohesion, 3),
                    "weakest_pair": round(weakest, 3)})
    return out


def build_clusters(record_ids, pairs, threshold, score_missing=None):
    """Union-find, then guard against transitive closure explosion.

    A~B and B~C group A and C together even when A and C are unrelated, and one
    bridging record can drag hundreds of items into a single blob. So after
    forming a group we check that EVERY pair inside it scores well - not just
    the connected ones - and split the group if it does not hold together.

    With blocking, many pairs inside a cluster were never generated. Reading
    those as 0.0 would send every cluster to review, so score_missing(a, b)
    scores them on demand. Clusters are capped at 25, so that is at most 300
    extra pairs each.
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

        internal = []
        for x, y in combinations(members, 2):
            if (x, y) not in lookup and score_missing and len(members) <= MAX_CLUSTER:
                lookup[(x, y)] = lookup[(y, x)] = score_missing(x, y)
            internal.append(lookup.get((x, y), 0.0))
        cohesion = sum(internal) / len(internal)
        weakest = min(internal)

        if len(members) > MAX_CLUSTER or weakest < MIN_INTRA:
            # A group that does not hold together is not one item. Union-find
            # over review-band links chains items: A~B, B~C, and C is a
            # different gasket. At 15,000 records that folded 11,815 items
            # into 1,086 groups. So the group is split back into what its
            # AUTO-band links alone support, and every remaining link waits
            # in the review queue as a pair - one code is never issued for
            # a group that contains a vetoed or weak pair.
            split_count += 1
            clusters.extend(_split(members, lookup))
            continue
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

def load_plants() -> dict:
    """record_id -> plant, from materials.csv. Older spec caches lack it."""
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        return {r["record_id"]: r.get("plant", "") for r in csv.DictReader(fh)}


def scope_of(a: dict, b: dict, plants: dict) -> str:
    """Who has to act on this pair: one plant, one company, or the registrar."""
    if a.get("cpse") != b.get("cpse"):
        return "CROSS_CPSE"
    pa = a.get("plant") or plants.get(a.get("record_id"), "")
    pb = b.get("plant") or plants.get(b.get("record_id"), "")
    return "SAME_PLANT" if pa and pa == pb else "SAME_CPSE"


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
    load_variants(specs)                     # the same knowledge the full run has
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
    print(f"  FINAL       {p['final']}")
    cf = p.get("counterfactual")
    if cf:
        verb = "matched" if cf["kind"] == "blocked" else "were confirmed"
        print(f"  WHAT IF     if {', '.join(cf['fields'])} {verb}, this pair would score {cf['score']}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=REVIEW_LOW)
    ap.add_argument("--explain", nargs=2, metavar=("A", "B"))
    ap.add_argument("--all-pairs", action="store_true",
                    help="score every pair (no blocking) - for checking blocking loses nothing")
    args = ap.parse_args()

    if args.explain:
        explain(*args.explain)
        return

    specs, descriptions = load_inputs()
    vecs = load_vectors()
    profiles = build_purchase_profiles()
    plants = load_plants()
    load_variants(specs)
    ids = sorted(specs)

    print(f"{len(ids)} records, {len(ids)*(len(ids)-1)//2:,} possible pairs")
    print(f"text signal: {'embeddings' if vecs else 'lexical fallback (run embed.py)'}")

    if args.all_pairs:
        candidates = list(combinations(ids, 2))
        stats = {"records": len(ids), "all_pairs": len(candidates),
                 "candidate_pairs": len(candidates), "reduction_ratio": 0.0, "mode": "all-pairs"}
    else:
        candidates, stats = blocking.candidate_pairs(specs, vecs)
        stats["mode"] = "blocking"
    print(f"{stats['mode']}: {stats['candidate_pairs']:,} candidate pairs "
          f"(reduction {stats['reduction_ratio']:.2%})\n")

    def scored_pair(a_id, b_id):
        p = score_pair(specs[a_id], specs[b_id], descriptions, vecs, profiles)
        p["scope"] = scope_of(specs[a_id], specs[b_id], plants)
        return p

    pairs = []
    for a_id, b_id in candidates:
        p = scored_pair(a_id, b_id)
        if p["final"] > 0 or p["blocked_by"]:
            pairs.append(p)

    scored = [p for p in pairs if not p["blocked_by"]]
    blocked = [p for p in pairs if p["blocked_by"]]
    clusters, splits = build_clusters(ids, scored, args.threshold,
                                      score_missing=lambda a, b: scored_pair(a, b)["final"])

    paths.ensure_dirs()
    stats["candidates"] = [list(p) for p in candidates]
    paths.BLOCKING.write_text(json.dumps(stats), encoding="utf-8")
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
    safety = {r: n for r, n in by_rule.items() if r not in NOT_SAFETY}

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
