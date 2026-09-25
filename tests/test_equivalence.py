"""Cross-standard equivalence (standards.EQUIVALENCE).

IDENTICAL and SUPERSEDED names are one requirement and match, with the
relation named in the evidence. NEAREST is never a match and never a veto:
it goes to a person. Different grades inside one standard still veto.
"""
import pytest

import normalise as nz
import schemas
import scorer
import standards


def pair(x, y):
    a, b = schemas.regex_extract(x), schemas.regex_extract(y)
    a["record_id"], b["record_id"] = "A", "B"
    return scorer.score_pair(a, b, {"A": x, "B": y}, None, {})


def test_is_1367_is_iso_898_1():
    p = pair("HEX BOLT M16 X 60 GR 8.8 IS 1367", "HEX BOLT M16X60 CLASS 8.8 ISO 898-1")
    assert not p["blocked_by"] and p["final"] >= scorer.AUTO_MERGE
    assert {"field": "standard", "relation": "IDENTICAL"}.items() <= p["equivalent"][0].items()


def test_a325_is_now_f3125_grade_a325():
    p = pair("HEAVY HEX BOLT 3/4 X 3 ASTM A325", "HEAVY HEX BOLT 3/4 X 3 ASTM F3125 GR A325")
    assert not p["blocked_by"] and p["final"] >= scorer.AUTO_MERGE
    assert any(e["field"] == "material_grade" and e["relation"] == "SUPERSEDED" for e in p["equivalent"])


@pytest.mark.parametrize("x,y", [
    ("HEAVY HEX BOLT 3/4 X 3 ASTM A325", "HEAVY HEX BOLT 3/4 X 3 ASTM A490"),
    ("HEAVY HEX BOLT 3/4 X 3 ASTM F3125 GR A325", "HEAVY HEX BOLT 3/4 X 3 ASTM A490"),
    ("HEX BOLT M16 X 60 GR 8.8 IS 1367", "HEX BOLT M16 X 60 GR 10.9 ISO 898-1"),
])
def test_different_grades_still_veto(x, y):
    assert pair(x, y)["blocked_by"] == "material_grade"


def test_nearest_is_a_person_not_a_match_or_a_veto():
    assert nz.compare_grades("8.8", "A325") == "unknown"
    assert nz.compare_grades("10.9", "F3125 A490") == "unknown"
    # Same everything else: the grade doubt holds the pair below auto.
    a = {"record_id": "A", "category": "fastener", "attributes": {
        "fastener_type": "bolt", "thread": "M20", "length_mm": 80.0, "material_grade": "8.8"}}
    b = {"record_id": "B", "category": "fastener", "attributes": {
        "fastener_type": "bolt", "thread": "M20", "length_mm": 80.0, "material_grade": "A325"}}
    p = scorer.score_pair(a, b, {"A": "", "B": ""}, None, {})
    assert not p["blocked_by"] and p["final"] < scorer.AUTO_MERGE


def test_nearest_never_chains():
    # 8.8 is near A325 and A325 is superseded by F3125 A325 - but 8.8 is
    # still only NEAR F3125 A325, never identical to it.
    assert standards.equivalence("8.8", "F3125 A325")[0] == "NEAREST"
    assert standards.equivalence("8.8", "10.9") is None


def test_every_row_names_its_source():
    assert all(len(row) == 4 and row[3] for row in standards.EQUIVALENCE)
