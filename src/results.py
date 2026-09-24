"""
Bundle everything the UI reads into one file.

The demo frontend imports data/output/results.json at build time - no server,
no API, no fetch. That is deliberate: it is what makes the demo impossible to
crash on stage, and what lets the same build open from a file on a phone with
no internet. See docs/02-decisions/009-static-demo-no-backend.md

    python src/results.py
    python src/results.py --stub      five fake clusters, no pipeline needed

The stub exists so the frontend can be built before the pipeline finishes. The
SHAPE is identical to the real thing, so nothing breaks when real numbers
replace it.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date

import paths
import schemas
from scorer import AUTO_MERGE, NOT_SAFETY, REVIEW_LOW

DEMO_MATCH = ("R00001", "R00002")     # different brand, same bearing
DEMO_BLOCK = ("R00003", "R00004")     # near-identical text, different grade

REAL_SOURCE_NAME = "Prasenjeet25/sih26099-cpse-material-codes"
REAL_SOURCE_URL = f"https://huggingface.co/datasets/{REAL_SOURCE_NAME}"


def real_summary() -> dict:
    """Counts of the real tender lines, for the UI's data-source notice.

    Reads only the unlabelled candidate text. The labels under data/real/labels
    are an answer key and are never read here - the UI must not display a
    number that came from them.
    """
    if not paths.REAL_CANDIDATES.exists():
        return {}
    with paths.REAL_CANDIDATES.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    by_org = defaultdict(int)
    for r in rows:
        by_org[r["organization"]] += 1
    return {"lines": len(rows),
            "by_org": dict(sorted(by_org.items(), key=lambda x: -x[1])),
            "source": REAL_SOURCE_NAME, "url": REAL_SOURCE_URL, "licence": "CC-BY-4.0"}


def record_view(rid, materials, specs) -> dict:
    """One record as the comparison screen shows it."""
    m = materials.get(rid, {})
    s = specs.get(rid, {})
    return {
        "record_id": rid,
        "cpse": m.get("cpse"),
        "source_code": m.get("source_code"),
        "description": m.get("description"),
        "uom": m.get("uom"),
        "category": s.get("category"),
        "attributes": s.get("attributes", {}),
        "confidence": s.get("confidence", {}),
        "method": s.get("method"),
    }


def case_view(pair, pairs_index, materials, specs) -> dict | None:
    """The two demo cases, with everything screen 02 and 03 need to render."""
    a, b = pair
    p = pairs_index.get((a, b)) or pairs_index.get((b, a))
    if not p or a not in specs or b not in specs:
        return None

    category = specs[a].get("category", "unknown")
    return {
        "a": record_view(a, materials, specs),
        "b": record_view(b, materials, specs),
        "text_sim": p.get("text_sim"),
        "spec_sim": p.get("spec_sim"),
        "proc_sim": p.get("proc_sim"),
        "final": p.get("final"),
        "weights": p.get("weights"),
        "matched_fields": p.get("matched_fields", []),
        "ignored_fields": p.get("ignored_fields", []),
        "hard_fields": schemas.hard_fields(category),
        "blocked_by": p.get("blocked_by"),
        "reason": p.get("reason"),
        "unverified_hard": p.get("unverified_hard", []),
    }


# The UI bundles results.json at build time into one offline file. At
# 15,000 records the full lists would bloat it past any sensible size, so
# every list is capped - and every total the dashboard shows is computed
# here, from the FULL lists, before capping. A capped list must never be
# summed in the browser and passed off as a total.
CAPS = {"clusters": 200, "review_queue": 200, "blocked": 200, "savings": 50}


def aggregates(national: list[dict]) -> dict:
    """Per-company and per-category totals over every national code."""
    by_cpse = defaultdict(lambda: {"records": 0, "codes": 0, "inside": 0, "shared": 0})
    by_cat = defaultdict(lambda: {"records": 0, "codes": 0})
    for c in national:
        members = c.get("members") or []
        cps = [m.get("cpse") for m in members]
        by_cat[c.get("category", "unknown")]["records"] += len(members)
        by_cat[c.get("category", "unknown")]["codes"] += 1
        for cp in set(cps):
            row = by_cpse[cp]
            n = cps.count(cp)
            row["records"] += n
            row["codes"] += 1
            row["inside"] += n - 1
            row["shared"] += 1 if len(set(cps)) > 1 else 0
    return {"by_cpse": dict(sorted(by_cpse.items())), "by_category": dict(sorted(by_cat.items()))}


def cap_clusters(national: list[dict]) -> list[dict]:
    """The codes worth showing: the demo's, then the most duplicated."""
    demo = {DEMO_MATCH[0], DEMO_MATCH[1], DEMO_BLOCK[0], DEMO_BLOCK[1]}
    keep = [c for c in national if demo & {m.get("record_id") for m in c.get("members") or []}]
    rest = sorted((c for c in national if c not in keep), key=lambda c: -len(c.get("members") or []))
    return (keep + rest)[:CAPS["clusters"]]


def build() -> dict:
    materials = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            materials[row["record_id"]] = row

    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))
    pairs = json.loads(paths.PAIR_SCORES.read_text(encoding="utf-8"))
    national = json.loads(paths.NATIONAL_CODES.read_text(encoding="utf-8"))
    savings = json.loads(paths.SAVINGS.read_text(encoding="utf-8"))
    metrics = (json.loads(paths.METRICS.read_text(encoding="utf-8"))
               if paths.METRICS.exists() else {})

    # Optional stages. The UI hides a screen whose section is absent rather
    # than rendering an empty one, so the bundle stays valid before they run.
    uom = (json.loads(paths.UOM.read_text(encoding="utf-8"))
           if paths.UOM.exists() else {})
    gate = (json.loads(paths.GATE.read_text(encoding="utf-8"))
            if paths.GATE.exists() else {})

    pairs_index = {(p["a"], p["b"]): p for p in pairs}

    # Blocked pairs, minus plain category mismatches. A bearing not merging
    # with a gasket is not an interesting refusal; a grade mismatch is.
    blocked = []
    for p in pairs:
        if not p.get("blocked_by") or p["blocked_by"] in NOT_SAFETY:
            continue
        blocked.append({
            "a": record_view(p["a"], materials, specs),
            "b": record_view(p["b"], materials, specs),
            "rule": p["blocked_by"],
            "reason": p["reason"],
            "text_sim": p.get("text_sim"),
        })

    by_rule = defaultdict(int)
    for b in blocked:
        by_rule[b["rule"]] += 1

    # Review queue, worst-first so a reviewer sees the genuinely uncertain ones
    # rather than a wall of near-certain matches.
    review = []
    for p in pairs:
        if p.get("blocked_by"):
            continue
        if REVIEW_LOW <= p["final"] < AUTO_MERGE:
            review.append({
                "a": record_view(p["a"], materials, specs),
                "b": record_view(p["b"], materials, specs),
                "final": p["final"],
                "text_sim": p.get("text_sim"),
                "spec_sim": p.get("spec_sim"),
                "proc_sim": p.get("proc_sim"),
                "matched_fields": p.get("matched_fields", []),
                "ignored_fields": p.get("ignored_fields", []),
                "review_reason": p.get("review_reason"),
            })
    review.sort(key=lambda r: r["final"])

    auto = sum(1 for n in national if n.get("band") == "auto")
    summary = savings.get("summary", {})
    items = savings.get("items", [])

    return {
        "meta": {
            "generated": date.today().isoformat(),
            "records": len(materials),
            "extracted": len(specs),
            "unique_items": len(national),
            "duplication": round(1 - len(national) / len(materials), 3) if materials else 0,
            "cpses": sorted({m["cpse"] for m in materials.values()}),
            "auto_merged": auto,
            "review_pending": len(review),
            "blocked": len(blocked),
            "savings_upper": summary.get("saving_upper", 0),
            "savings_realistic": summary.get("saving_realistic", 0),
            "uom_variants": uom.get("summary", {}).get("variants_seen"),
            "uom_units": uom.get("summary", {}).get("canonical_units"),
            # Straight from evaluate.py. Null when it has not been run -
            # a number nobody measured must not reach a slide, and the UI
            # says "run evaluate.py" rather than inventing one.
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "auto_precision": metrics.get("auto_precision"),
            "safety_blocks": metrics.get("safety_blocks"),
            "trap_violations": metrics.get("trap_violations_auto"),
            "run": paths.RUN or "demo",
            "totals": {"codes": len(national), "review_pairs": len(review), "blocked": len(blocked),
                       "savings_items": len(items)},
            "shown": {"codes": min(len(national), CAPS["clusters"]),
                      "review_pairs": min(len(review), CAPS["review_queue"]),
                      "blocked": min(len(blocked), CAPS["blocked"]),
                      "savings_items": min(len(items), CAPS["savings"])},
            **aggregates(national),
            "review_queue_quality": metrics.get("review_queue"),
            "by_split": metrics.get("by_split"),
        },
        "cases": {
            "match": case_view(DEMO_MATCH, pairs_index, materials, specs),
            "block": case_view(DEMO_BLOCK, pairs_index, materials, specs),
        },
        "clusters": national if len(national) <= CAPS["clusters"] else cap_clusters(national),
        "review_queue": review[:CAPS["review_queue"]],
        "blocked": blocked[:CAPS["blocked"]],
        "blocked_by_rule": dict(sorted(by_rule.items(), key=lambda x: -x[1])),
        "savings": items[:CAPS["savings"]],
        "savings_summary": summary,
        "uom": uom,
        "gate": gate,
        "real": real_summary(),
    }


def stub() -> dict:
    """Same shape, invented numbers. Lets the UI be built before the data exists."""
    def rec(rid, cpse, code, desc, attrs):
        return {"record_id": rid, "cpse": cpse, "source_code": code,
                "description": desc, "uom": "EA", "category": "bearing",
                "attributes": attrs,
                "confidence": {k: 0.95 for k in attrs}, "method": "llm"}

    a = rec("R00001", "CPCL", "100001445", "SKF 6205-2RS DEEP GROOVE BALL BEARING",
            {"iso_designation": "6205", "bore_mm": 25, "od_mm": 52,
             "width_mm": 15, "seal_type": "2RS", "brand": "SKF"})
    b = rec("R00002", "IOCL", "MAT-01248", "FAG 6205-2RSR BEARING, 25X52X15MM, SEALED",
            {"iso_designation": "6205", "bore_mm": 25, "od_mm": 52,
             "width_mm": 15, "seal_type": "2RS", "brand": "FAG"})
    g1 = rec("R00003", "ONGC", "5001035", "GASKET SPIRAL WOUND SS316 4IN 150#",
             {"material_grade": "SS316", "nominal_size_in": 4, "pressure_class": "150#"})
    g2 = rec("R00004", "BPCL", "BR-01454", "GASKET SPIRAL WOUND SS304 4IN 150#",
             {"material_grade": "SS304", "nominal_size_in": 4, "pressure_class": "150#"})
    g1["category"] = g2["category"] = "gasket"

    return {
        "meta": {"generated": date.today().isoformat(), "records": 100,
                 "extracted": 100, "unique_items": 15, "duplication": 0.85,
                 "cpses": ["BPCL", "CPCL", "GAIL", "IOCL", "ONGC"],
                 "auto_merged": 9, "review_pending": 6, "blocked": 222,
                 "savings_upper": 330000000, "savings_realistic": 132000000,
                 "precision": None, "recall": None},
        "cases": {
            "match": {"a": a, "b": b, "text_sim": 0.31, "spec_sim": 0.97,
                      "proc_sim": 0.88, "final": 0.94,
                      "weights": {"text": 0.06, "spec": 0.88, "proc": 0.06},
                      "matched_fields": ["iso_designation", "bore_mm", "od_mm",
                                         "width_mm", "seal_type"],
                      "ignored_fields": ["brand"],
                      "hard_fields": ["iso_designation", "bore_mm"],
                      "blocked_by": None, "reason": None, "unverified_hard": []},
            "block": {"a": g1, "b": g2, "text_sim": 0.97, "spec_sim": 0.0,
                      "proc_sim": 0.7, "final": 0.0, "weights": None,
                      "matched_fields": ["nominal_size_in", "pressure_class"],
                      "ignored_fields": [],
                      "hard_fields": ["material_grade", "nominal_size_in",
                                      "pressure_class"],
                      "blocked_by": "material_grade",
                      "reason": "SS316 vs SS304", "unverified_hard": []},
        },
        "clusters": [{
            "national_code": "NMC-31171500-000001", "category": "bearing",
            "unspsc": "31171500", "unspsc_name": "Bearings",
            "std_description": "BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED",
            "attributes": a["attributes"], "field_agreement": {},
            "confidence": 0.94, "band": "auto", "member_count": 10,
            "cpse_count": 5, "cpses": ["BPCL", "CPCL", "GAIL", "IOCL", "ONGC"],
            "members": [{"record_id": a["record_id"], "cpse": a["cpse"],
                         "source_code": a["source_code"],
                         "description": a["description"], "uom": "EA"}],
        }],
        "review_queue": [{"a": a, "b": b, "final": 0.82, "text_sim": 0.31,
                          "spec_sim": 0.80, "proc_sim": 0.7,
                          "matched_fields": ["iso_designation"],
                          "ignored_fields": ["brand"],
                          "review_reason": "could not verify bore_mm"}],
        "blocked": [{"a": g1, "b": g2, "rule": "material_grade",
                     "reason": "SS316 vs SS304", "text_sim": 0.97}],
        "blocked_by_rule": {"nominal_size_in": 64, "material_grade": 60,
                            "iso_designation": 48, "thread": 28,
                            "pressure_class": 18, "price_anomaly": 4},
        "savings": [{
            "national_code": "NMC-31171500-000001",
            "description": "BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED",
            "category": "bearing", "cpse_count": 5,
            "cpses": [{"cpse": "BPCL", "qty": 910, "orders": 4, "avg_price": 1264,
                       "median_price": 1264, "value": 1150240, "vendor_count": 2},
                      {"cpse": "IOCL", "qty": 230, "orders": 2, "avg_price": 1205,
                       "median_price": 1205, "value": 277150, "vendor_count": 1}],
            "total_qty": 2125, "total_value": 2830000, "orders": 12,
            "benchmark_suppressed": False, "best_price": 1205, "worst_price": 1501,
            "price_spread_pct": 24.5, "saving_upper": 270000,
            "saving_realistic": 108000}],
        "savings_summary": {"items": 15, "multi_cpse_items": 9,
                            "saving_upper": 330000000,
                            "saving_realistic": 132000000,
                            "capture_rate": 0.40, "k_anonymity": 3},
        "uom": {
            "summary": {"records": 100, "variants_seen": 10, "canonical_units": 2,
                        "units": ["EA", "M"], "codes_total": 15,
                        "codes_with_conflict": 14, "cross_family_conflicts": 0,
                        "intra_cpse_conflicts": 11, "pack_size_flags": 0,
                        "ambiguous_spellings": ["MTS"], "unrecognised": []},
            "families": [
                {"canonical": "EA", "label": "Each", "records": 90,
                 "variants": [{"raw": "EACH", "count": 21}, {"raw": "NO", "count": 16}]},
                {"canonical": "M", "label": "Metre", "records": 8,
                 "variants": [{"raw": "METER", "count": 4}, {"raw": "M", "count": 3}]},
            ],
            "ambiguous": [{"raw": "MTS", "count": 2, "readings": ["M", "MT"],
                           "note": "metres or metric tonnes"}],
            "unrecognised": [],
            "conflicts": [{
                "national_code": "NMC-31171500-000001",
                "description": "BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED",
                "category": "bearing", "resolved_to": "EA", "resolved_label": "Each",
                "cross_family": False, "variant_count": 5,
                "variants": [{"raw": "NO", "count": 3, "cpses": ["CPCL", "GAIL"]},
                             {"raw": "EACH", "count": 2, "cpses": ["BPCL"]}],
                "intra_cpse": ["BPCL", "CPCL"], "pack_size_flag": None,
            }],
        },
        "gate": {
            "index": {"codes": 15, "note": "compared against golden records"},
            "thresholds": {"exists": 0.90, "review": 0.70},
            "scenarios": [{
                "id": "duplicate", "label": "A duplicate arrives",
                "note": "Shares almost no words with the catalogue entry.",
                "input": "FAG 6205-2RSR BEARING, 25X52X15MM, SEALED",
                "extracted": {"category": "bearing",
                              "attributes": b["attributes"],
                              "confidence": {}, "method": "regex"},
                "verdict": "EXISTS",
                "message": "Already catalogued as NMC-31171500-000001.",
                "best": {"national_code": "NMC-31171500-000001",
                         "std_description": "BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED",
                         "category": "bearing", "unspsc": "31171500",
                         "cpse_count": 5, "cpses": ["BPCL", "CPCL", "GAIL", "IOCL", "ONGC"],
                         "member_count": 10, "final": 0.95, "text_sim": 0.25,
                         "spec_sim": 1.0,
                         "matched_fields": ["iso_designation", "bore_mm"],
                         "ignored_fields": ["brand"], "blocked_by": None, "reason": None},
                "candidates": [], "distinguished_from": [], "compared_against": 15,
                "thresholds": {"exists": 0.90, "review": 0.70},
            }],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stub", action="store_true",
                    help="write fake data with the real shape, for the frontend")
    ap.add_argument("--ui", action="store_true",
                    help="also write ui/src/results.json from a non-demo run (e.g. SIH_RUN=15k)")
    args = ap.parse_args()

    data = stub() if args.stub else build()
    paths.ensure_dirs()
    blob = json.dumps(data, indent=1)
    paths.RESULTS.write_text(blob, encoding="utf-8")
    # Written in the same breath as the canonical copy. The frontend imports
    # its own file at build time, and letting the two drift is how a demo ends
    # up presenting numbers nobody generated.
    # A bigger run writes its own results.json and leaves the UI alone unless
    # asked - the demo must not change because someone ran the 15,000 set.
    to_ui = paths.UI_RESULTS.parent.exists() and (not paths.RUN or args.ui)
    if to_ui:
        paths.UI_RESULTS.write_text(blob, encoding="utf-8")

    m = data["meta"]
    kind = "STUB" if args.stub else "real"
    print(f"wrote {paths.RESULTS.name}  ({kind}, "
          f"{paths.RESULTS.stat().st_size/1024:.0f} KB)" + ("  + ui/src/results.json" if to_ui else "  (UI untouched)"))
    print(f"  records         {m['records']}   extracted {m['extracted']}")
    print(f"  unique items    {m['unique_items']}   "
          f"({m['duplication']:.1%} duplication)")
    print(f"  review queue    {m['review_pending']}")
    print(f"  blocked         {m['blocked']}")
    for case in ("match", "block"):
        c = data["cases"].get(case)
        if not c:
            print(f"  !! demo case '{case}' missing - the UI needs it")
        elif case == "match":
            print(f"  demo match      {c['final']}  "
                  f"(text {c['text_sim']}, specs {c['spec_sim']})")
        else:
            print(f"  demo block      {c['blocked_by']}  "
                  f"(text {c['text_sim']})")
    if m["precision"] is None:
        print("\n  precision/recall left null - run evaluate.py and fill them in")
        print("  rather than putting an unmeasured number in front of a judge")


if __name__ == "__main__":
    main()
