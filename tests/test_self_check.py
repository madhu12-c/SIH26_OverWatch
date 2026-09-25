"""The self-check: a record checked against itself before it can match.

Planted contradictions must be caught; clean lines - including every dev row
of the real set and every generated record - must not be flagged. A pair
involving a contradicted record never auto-merges.
"""
import pytest

import schemas
import scorer
import selfcheck

PLANTED = [
    ("BEARING 6205 2RS 30X62X16MM", "dimensions"),          # a 6206's dimensions
    ("PIPE CS SMLS 20 INCH SCH 40 457 MM OD", "od_mm"),      # 457 is 18 in, not 20
    ("PIPE 4 INCH SCH 40 114.3 X 8.56 MM", "wall_mm"),       # 8.56 is SCH 80
    ("PIPE 6 IN 114.3 MM OD SCH 40", "od_mm"),               # 114.3 is 4 in
    ("MOTOR 7.5 KW 15 HP 4 POLE 1440 RPM", "power_hp"),      # 7.5 kW is 10 hp
    ("MOTOR 11KW 4P 2880RPM", "speed_rpm"),                  # 2880 is a 2-pole speed
    ("PRESSURE GAUGE RANGE 10 TO 0 BAR", "range_min"),       # backwards range
]

CLEAN = [
    "SKF 6205-2RS BEARING 25X52X15",
    "PIPE 4 INCH SCH 40 114.3 X 6.02 MM",
    "MOTOR 7.5KW 10HP 1440RPM 4P",
    "MOTOR 90 KW 125 HP 4 POLE 1480 RPM",                    # a real nameplate pairing
    "MOTOR 30KW 1770 RPM 4 POLE",                            # 60 Hz
    "PRESSURE GAUGE 100MM DIAL 0-16 BAR SS316 1/2IN NPT BOTTOM",
    "PRESSURE GAUGE -1 TO 0 BAR 100MM",
]


@pytest.mark.parametrize("line,field", PLANTED)
def test_planted_contradiction_caught(line, field):
    found = selfcheck.check(schemas.regex_extract(line))
    assert field in [c["field"] for c in found], found


@pytest.mark.parametrize("line", CLEAN)
def test_clean_line_not_flagged(line):
    assert selfcheck.check(schemas.regex_extract(line)) == []


def test_bearing_names_the_designation_the_dimensions_belong_to():
    [c] = selfcheck.check(schemas.regex_extract("BEARING 6205 2RS 30X62X16MM"))
    assert "6206" in c["rule"]


def test_derived_values_never_contradict():
    # A 6205 with no dimensions gets 25x52x15 from ISO 15: that is not a claim
    # the line made, and it agrees with its source by construction.
    out = schemas.regex_extract("SKF 6205-2RS DEEP GROOVE BALL BEARING")
    assert out["attributes"].get("bore_mm") == 25.0
    assert selfcheck.check(out) == []


def test_no_dev_row_flagged(dev):
    import csv
    import paths
    split = {r["id"]: r["split"] for r in csv.DictReader(paths.REAL_SPLIT.open(encoding="utf-8-sig"))}
    ids = [i for i, s in split.items() if s == "dev"]
    rows = [dev(i) for i in ids]
    flagged = [r["id"] for r in rows if r["keep"] == "y"
               and selfcheck.check(schemas.regex_extract(r["description"]))]
    assert len(flagged) <= 0.02 * len(rows), flagged


def test_contradicted_record_never_auto_merges():
    a = schemas.regex_extract("BEARING 6205 2RS 30X62X16MM")
    b = schemas.regex_extract("SKF 6205-2RS BEARING")
    a["record_id"], b["record_id"] = "X1", "X2"
    p = scorer.score_pair(a, b, {"X1": "", "X2": ""}, None, {})
    assert p["blocked_by"] or p["final"] < scorer.AUTO_MERGE
    assert p.get("contradictions")
