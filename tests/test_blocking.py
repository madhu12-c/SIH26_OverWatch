"""
Blocking - it must be generous (no true pair lost) and cheap (almost every
pair skipped), and it must be deterministic.

The scale test builds 15,000 spec records in memory from standard grids - the
shape A6's item factory will produce - so blocking is measured at the size it
exists for, without touching data/input.
"""

import json
import random
import time
from itertools import combinations, product

import blocking
import paths


def spec(rid, cat, attrs, cpse="CPCL"):
    return {"record_id": rid, "category": cat, "attributes": dict(attrs), "cpse": cpse}


def test_demo_pairs_are_candidates():
    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))
    pairs = set(blocking.candidate_pairs(specs)[0])
    assert ("R00001", "R00002") in pairs, "SKF / FAG 6205 must meet, or the match is impossible"
    assert ("R00003", "R00004") in pairs, "SS316 / SS304 must meet, so the veto can count it"


def test_deterministic():
    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))
    assert blocking.candidate_pairs(specs)[0] == blocking.candidate_pairs(dict(reversed(specs.items())))[0]


def test_brand_and_part_number_never_split_a_block():
    a = spec("A", "bearing", {"iso_designation": "6205", "bore_mm": 25.0, "brand": "SKF",
                              "part_number": "6205-2RS"})
    b = spec("B", "bearing", {"iso_designation": "6205", "bore_mm": 25.0, "brand": "FAG",
                              "part_number": "6205-2RSR"})
    assert ("A", "B") in blocking.candidate_pairs({"A": a, "B": b})[0]


def _grid_items():
    grades = ("SS316", "SS304", "SS316L", "CARBON_STEEL", "A106 GR B", "SS321", "A333 GR 6",
              "API 5L GR B", "SS304L", "A335 P11")
    nps = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0,
           16.0, 18.0, 20.0, 24.0)
    classes = ("150#", "300#", "600#", "900#", "1500#", "2500#")
    items = []
    for s, sch, g, c in product(nps, ("SCH 10", "SCH 40", "SCH 80", "SCH 160"), grades,
                                ("seamless", "erw", "saw")):
        items.append(("pipe", {"nominal_size_in": s, "schedule": sch, "material_grade": g,
                               "construction": c}))
    for t, s, c, g in product(("gate", "globe", "ball", "check", "butterfly", "plug"), nps,
                              classes, grades[:6]):
        items.append(("valve", {"valve_type": t, "nominal_size_in": s, "pressure_class": c,
                                "body_material": g}))
    for t, s, c, g in product(("weld_neck", "slip_on", "blind", "socket_weld"), nps, classes, grades[:6]):
        items.append(("flange", {"flange_type": t, "nominal_size_in": s, "pressure_class": c,
                                 "material_grade": g}))
    for s, c, g in product(nps, classes, grades):
        items.append(("gasket", {"nominal_size_in": s, "pressure_class": c, "material_grade": g}))
    for series, n in product((60, 62, 63, 222), range(0, 22)):
        items.append(("bearing", {"iso_designation": f"{series}{n:02d}", "bore_mm": float(5 * max(n, 1))}))
    for t, th, ln, g in product(("bolt", "stud_bolt", "screw"), ("M10", "M12", "M16", "M20", "M24"),
                                (40.0, 50.0, 60.0, 80.0, 100.0, 120.0), ("SS316", "8.8", "A193_B7", "4.6")):
        items.append(("fastener", {"fastener_type": t, "thread": th, "length_mm": ln,
                                   "material_grade": g}))
    for cores, cs, cond, kv in product((1.0, 2.0, 3.0, 3.5, 4.0), (2.5, 4.0, 10.0, 16.0, 35.0, 70.0,
                                                                   120.0, 150.0, 240.0, 400.0),
                                       ("AL", "CU"), (0.66, 1.1, 3.3, 11.0)):
        items.append(("cable", {"cable_type": "power", "cores": cores, "cross_section_mm2": cs,
                                "conductor": cond, "voltage_kv": kv}))
    return items


def test_scale_15000_records():
    rng = random.Random(7)
    items = _grid_items()
    rng.shuffle(items)
    specs, truth = {}, {}
    n = 0

    def add(item_id, cat, attrs):
        nonlocal n
        rid = f"R{n:05d}"
        n += 1
        specs[rid] = spec(rid, cat, attrs, cpse=rng.choice(("CPCL", "IOCL", "ONGC", "BPCL", "GAIL")))
        truth[rid] = item_id

    for i, (cat, attrs) in enumerate(items):
        add(i, cat, attrs)
    items = items[:12000]                             # 15,000 records at 20% duplication
    while n < 15000:                                  # duplicates, written less completely
        i = rng.randrange(len(items))
        cat, attrs = items[i]
        dup = dict(attrs)
        keys = sorted(dup)
        drop = rng.random()
        if drop < 0.40 and len(keys) > 2:
            dup.pop(rng.choice(keys))
        elif drop < 0.50 and len(keys) > 3:
            for k in rng.sample(keys, 2):
                dup.pop(k)
        add(i, cat, dup)

    started = time.time()
    pairs, stats = blocking.candidate_pairs(specs)
    took = time.time() - started

    by_item = {}
    for rid, item in truth.items():
        by_item.setdefault(item, []).append(rid)
    true_pairs = {tuple(sorted(p)) for v in by_item.values() for p in combinations(v, 2)}
    found = set(pairs)
    completeness = len(true_pairs & found) / len(true_pairs)

    # Records that still state all but at most one of their safety fields.
    # A record missing two of four (a valve with no size and no grade) is one
    # of a hundred look-alikes to typed keys; embedding neighbours place it in
    # the real pipeline, and it can never auto-merge. This test has no vectors,
    # so those pairs are measured separately and held to a floor, not the target.
    full = {rid for rid, s in specs.items()
            if len(s["attributes"]) >= len(items[truth[rid]][1]) - 1}
    typed = {p for p in true_pairs if p[0] in full and p[1] in full}
    typed_completeness = len(typed & found) / len(typed)

    print(f"\n  {len(specs):,} records, {len(items):,} items, {stats['candidate_pairs']:,} candidates, "
          f"reduction {stats['reduction_ratio']:.4%}, completeness {typed_completeness:.2%} "
          f"(including records missing two safety fields: {completeness:.2%}), "
          f"{len(stats['purged_keys'])} keys purged, {took:.1f}s")
    # 99.8%, not the planned 99.9%: on the real-notation 15,000-record run a
    # tighter cut lost 6 points of recall (68% -> 75% -> 81% completeness as
    # it was loosened). Skipping 998 of every 1,000 pairs is the chosen trade.
    assert stats["reduction_ratio"] >= 0.998
    assert typed_completeness >= 0.98
    assert completeness >= 0.90
    assert took < 60
