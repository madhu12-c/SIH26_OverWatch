"""
Real duplicates are found, real near-misses are refused - on dev rows.

The groups are the ones labelled in data/real/labels/dev.csv: the same item
written again, often by a different tender. A group must reach at least the
review band. A group outside every schema ("other") must never auto-merge.
Each near-miss is two real lines that look alike and are different items; the
pair must be blocked, and blocked by the field that differs.
"""

import csv
from itertools import combinations

import pytest

import paths
import schemas
import scorer


@pytest.fixture(scope="module")
def score(dev):
    cache = {}

    def spec(i):
        if i not in cache:
            row = dev(i)
            out = schemas.regex_extract(row["description"])
            out.update(record_id=str(i), cpse=row["organization"], source_code=str(i))
            cache[i] = out
        return cache[i]

    def run(a, b):
        desc = {str(a): dev(a)["description"], str(b): dev(b)["description"]}
        return scorer.score_pair(spec(a), spec(b), desc, None, {})
    return run


def dev_groups():
    groups = {}
    for r in csv.DictReader(paths.REAL_DEV.open(encoding="utf-8-sig")):
        if r["group"]:
            groups.setdefault(r["group"], []).append((int(r["id"]), r["category"]))
    return groups


@pytest.mark.parametrize("group", sorted(dev_groups(), key=lambda g: int(g[1:])))
def test_real_duplicates_reach_review(score, group):
    members = dev_groups()[group]
    for (a, cat), (b, _) in combinations(members, 2):
        p = score(a, b)
        assert not p["blocked_by"], f"{group} {a}/{b} blocked on {p['blocked_by']}: {p['reason']}"
        assert p["final"] >= scorer.REVIEW_LOW, f"{group} {a}/{b} scored {p['final']}"
        if cat == "other":
            assert p["final"] < scorer.AUTO_MERGE, f"{group} {a}/{b} auto-merged outside a schema"


NEAR_MISSES = [
    (2, 3, "nominal_size_in"),         # 450 NB vs 500 NB black pipe
    (162, 163, "wall_mm"),             # 12.66 vs 19 lb/ft: same OD, different wall
    (251, 252, "nominal_size_in"),     # 1-1/4" vs 1-1/2" - once passed on a loose tolerance
    (19, 21, "cross_section_mm2"),     # 150 vs 240 mm2 cable
    (279, 283, "cross_section_mm2"),   # 10 vs 16 mm2
    (42, 44, "power_hp"),              # 30 kW vs 55 kW motor
    (156, 189, "od_mm"),               # T91 tube 54 vs 51 mm
    (675, 610, "rating_kva"),          # 250 vs 50 MVA transformer
    (765, 755, "quantities"),          # 20 HP vs 5 HP pump
    (237, 470, "quantities"),          # 29 vs 25 mm wire rope
    (86, 220, "nominal_size_in"),      # galvanised 125 vs 100 NB
]


@pytest.mark.parametrize("a,b,field", NEAR_MISSES)
def test_real_near_misses_are_blocked(score, a, b, field):
    p = score(a, b)
    assert p["blocked_by"] == field, f"{a}/{b}: blocked_by={p['blocked_by']} final={p['final']}"
