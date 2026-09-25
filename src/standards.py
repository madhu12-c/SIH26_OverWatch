"""
Standards tables - facts a record implies but does not always state.

Used twice: by the item factory (catalogue.py) to build only valid items, and
by schemas.derive() to fill what a description leaves out - a 6205 bearing
is 25 x 52 x 15 mm whether or not the storekeeper wrote it. A derived value
is marked with a lower confidence than a read one.

Sources: ISO 15 (radial bearing boundary dimensions), ASME B36.10M / B36.19M
(pipe walls), IEC 60072 (motor frames). Only the rows the catalogue uses.
"""

import normalise as nz

# ISO 15 deep groove ball bearings: designation -> (bore, OD, width) mm.
ISO15 = {
    "6000": (10, 26, 8), "6001": (12, 28, 8), "6002": (15, 32, 9), "6003": (17, 35, 10),
    "6004": (20, 42, 12), "6005": (25, 47, 12), "6006": (30, 55, 13), "6007": (35, 62, 14),
    "6008": (40, 68, 15), "6009": (45, 75, 16), "6010": (50, 80, 16), "6011": (55, 90, 18),
    "6012": (60, 95, 18), "6013": (65, 100, 18), "6014": (70, 110, 20), "6015": (75, 115, 20),
    "6016": (80, 125, 22),
    "6200": (10, 30, 9), "6201": (12, 32, 10), "6202": (15, 35, 11), "6203": (17, 40, 12),
    "6204": (20, 47, 14), "6205": (25, 52, 15), "6206": (30, 62, 16), "6207": (35, 72, 17),
    "6208": (40, 80, 18), "6209": (45, 85, 19), "6210": (50, 90, 20), "6211": (55, 100, 21),
    "6212": (60, 110, 22), "6213": (65, 120, 23), "6214": (70, 125, 24), "6215": (75, 130, 25),
    "6216": (80, 140, 26), "6217": (85, 150, 28), "6218": (90, 160, 30), "6219": (95, 170, 32),
    "6220": (100, 180, 34),
    "6300": (10, 35, 11), "6301": (12, 37, 12), "6302": (15, 42, 13), "6303": (17, 47, 14),
    "6304": (20, 52, 15), "6305": (25, 62, 17), "6306": (30, 72, 19), "6307": (35, 80, 21),
    "6308": (40, 90, 23), "6309": (45, 100, 25), "6310": (50, 110, 27), "6311": (55, 120, 29),
    "6312": (60, 130, 31), "6313": (65, 140, 33), "6314": (70, 150, 35), "6315": (75, 160, 37),
    "6316": (80, 170, 39),
}

# ASME B36.10M / B36.19M wall thickness, mm: NPS -> {schedule: wall}.
WALL = {
    0.5:  {"SCH 10S": 2.11, "SCH 40": 2.77, "SCH 80": 3.73, "SCH 160": 4.78},
    0.75: {"SCH 10S": 2.11, "SCH 40": 2.87, "SCH 80": 3.91, "SCH 160": 5.56},
    1.0:  {"SCH 10S": 2.77, "SCH 40": 3.38, "SCH 80": 4.55, "SCH 160": 6.35},
    1.5:  {"SCH 10S": 2.77, "SCH 40": 3.68, "SCH 80": 5.08, "SCH 160": 7.14},
    2.0:  {"SCH 10S": 2.77, "SCH 40": 3.91, "SCH 80": 5.54, "SCH 160": 8.74},
    3.0:  {"SCH 10S": 3.05, "SCH 40": 5.49, "SCH 80": 7.62, "SCH 160": 11.13},
    4.0:  {"SCH 10S": 3.05, "SCH 40": 6.02, "SCH 80": 8.56, "SCH 160": 13.49},
    6.0:  {"SCH 10S": 3.40, "SCH 40": 7.11, "SCH 80": 10.97, "SCH 160": 18.26},
    8.0:  {"SCH 10S": 3.76, "SCH 40": 8.18, "SCH 80": 12.70, "SCH 160": 23.01},
    10.0: {"SCH 10S": 4.19, "SCH 40": 9.27, "SCH 80": 15.09, "SCH 160": 28.58},
    12.0: {"SCH 10S": 4.57, "SCH 40": 10.31, "SCH 80": 17.48, "SCH 160": 33.32},
    14.0: {"SCH 10S": 4.78, "SCH 40": 11.13, "SCH 80": 19.05, "SCH 160": 35.71},
    16.0: {"SCH 10S": 4.78, "SCH 40": 12.70, "SCH 80": 21.44, "SCH 160": 40.49},
    18.0: {"SCH 10S": 4.78, "SCH 40": 14.27, "SCH 80": 23.83, "SCH 160": 45.24},
    20.0: {"SCH 10S": 5.54, "SCH 40": 15.09, "SCH 80": 26.19, "SCH 160": 50.01},
    24.0: {"SCH 10S": 6.35, "SCH 40": 17.48, "SCH 80": 30.96, "SCH 160": 59.54},
}
PIPE_NPS = tuple(WALL)
SMALL = (0.5, 0.75, 1.0, 1.5, 2.0)                  # forged, screwed / socket weld
LARGE = tuple(n for n in PIPE_NPS if n > 2)
CLASSES = ("150#", "300#", "600#", "900#", "1500#")

# IEC 60072 frame for a TEFC motor: (kW, poles) -> frame. Common sizes only.
IEC_FRAME = {
    (0.37, 4): "71", (0.55, 4): "80", (0.75, 4): "80", (1.1, 4): "90S", (1.5, 4): "90L",
    (2.2, 4): "100L", (3.7, 4): "112M", (5.5, 4): "132S", (7.5, 4): "132M", (11, 4): "160M",
    (15, 4): "160L", (18.5, 4): "180M", (22, 4): "180L", (30, 4): "200L", (37, 4): "225S",
    (45, 4): "225M", (55, 4): "250M", (75, 4): "280S", (90, 4): "280M", (110, 4): "315S",
    (132, 4): "315M", (160, 4): "315L",
    (0.75, 2): "80", (1.1, 2): "80", (1.5, 2): "90S", (2.2, 2): "90L", (3.7, 2): "100L",
    (5.5, 2): "132S", (7.5, 2): "132S", (11, 2): "160M", (15, 2): "160M", (18.5, 2): "160L",
    (22, 2): "180M", (30, 2): "200L", (37, 2): "200L", (45, 2): "225M", (55, 2): "250M",
    (75, 2): "280S", (90, 2): "280M", (110, 2): "315S", (132, 2): "315M",
    (0.75, 6): "90S", (1.1, 6): "90L", (1.5, 6): "100L", (2.2, 6): "112M", (3.7, 6): "132M",
    (5.5, 6): "132M", (7.5, 6): "160M", (11, 6): "160L", (15, 6): "180L", (18.5, 6): "200L",
    (22, 6): "200L", (30, 6): "225M", (37, 6): "250M", (45, 6): "280S", (55, 6): "280M",
    (75, 6): "315S", (90, 6): "315M", (110, 6): "315L",
}
RPM = {2: 2880.0, 4: 1440.0, 6: 960.0}




def bearing_dims(designation: str):
    """(bore, OD, width) mm for an ISO 15 deep groove ball bearing, or None."""
    d = ISO15.get(str(designation).strip())
    return tuple(float(x) for x in d) if d else None


def pipe_wall(nps: float, schedule: str):
    """B36.10M / B36.19M wall in mm. 'SCH 40S' reads as SCH 40 for the sizes listed."""
    row = WALL.get(float(nps))
    if not row or not schedule:
        return None
    s = str(schedule).upper().replace("SCH ", "SCH ").strip()
    if s in row:
        return row[s]
    base = s[:-1] if s.endswith("S") and s != "SCH 10S" else s
    return row.get(base)


# Cross-standard equivalence - when two names are one requirement.
#
#   IDENTICAL      the same requirements under another body's number (an IS
#                  adopted identically from an ISO). Matches.
#   SUPERSEDED_BY  withdrawn; the replacement carries the grade forward
#                  unchanged. Matches, and the evidence says "superseded".
#   NEAREST        close but not interchangeable - different test regimes,
#                  different units. Never a match and never a veto: a person
#                  decides. Only IDENTICAL links chain; NEAREST never does.
#
# Each row names its source. Check a row against the standard itself before
# it goes on a slide.
EQUIVALENCE = [
    # ISO 898-1 property classes, adopted identically as IS 1367 (Part 3).
    ("IS 1367", "IDENTICAL", "ISO 898-1", "IS 1367 (Part 3) is an identical adoption of ISO 898-1"),
    ("IS 1367-3", "IDENTICAL", "ISO 898-1", "IS 1367 (Part 3) is an identical adoption of ISO 898-1"),
    ("IS 1364", "IDENTICAL", "ISO 4014", "IS 1364 (Part 1) hexagon head bolts is an identical adoption of ISO 4014"),
    ("IS 1364-1", "IDENTICAL", "ISO 4014", "IS 1364 (Part 1) hexagon head bolts is an identical adoption of ISO 4014"),
    # ASTM withdrew A325 and A490 in 2016; F3125 carries both as grades.
    ("A325", "SUPERSEDED_BY", "F3125 A325", "ASTM A325 withdrawn 2016, now ASTM F3125 Grade A325"),
    ("A490", "SUPERSEDED_BY", "F3125 A490", "ASTM A490 withdrawn 2016, now ASTM F3125 Grade A490"),
    ("ASTM A325", "SUPERSEDED_BY", "ASTM F3125", "ASTM A325 withdrawn 2016, now ASTM F3125"),
    ("ASTM A490", "SUPERSEDED_BY", "ASTM F3125", "ASTM A490 withdrawn 2016, now ASTM F3125"),
    # Close in strength, not interchangeable: metric class against inch grade.
    ("8.8", "NEAREST", "F3125 A325", "ISO 898-1 class 8.8 is close to A325 in strength; different standard, sizes and tests"),
    ("10.9", "NEAREST", "F3125 A490", "ISO 898-1 class 10.9 is close to A490 in strength; different standard, sizes and tests"),
]


def _key(value) -> str:
    import re
    v = re.sub(r"[\s_]+", " ", str(value).strip().upper())
    v = re.sub(r"\bGR(?:ADE)?\.?\s*", "", v)
    return re.sub(r"\s*\(PART\s*(\d)\)", r"-\1", v).strip()


def _current(value: str) -> str:
    """Follow SUPERSEDED_BY to the name in force today."""
    seen = set()
    while value not in seen:
        seen.add(value)
        nxt = next((b for a, rel, b, _ in EQUIVALENCE if rel == "SUPERSEDED_BY" and _key(a) == value), None)
        if nxt is None:
            return value
        value = _key(nxt)
    return value


def _identical_class(value: str) -> set:
    """Everything linked to value by IDENTICAL, transitively (IDENTICAL only)."""
    group, todo = {value}, [value]
    while todo:
        v = todo.pop()
        for a, rel, b, _ in EQUIVALENCE:
            if rel != "IDENTICAL":
                continue
            for x, y in ((_key(a), _key(b)), (_key(b), _key(a))):
                if x == v and y not in group:
                    group.add(y)
                    todo.append(y)
    return group


def equivalence(x, y):
    """How two grade or standard names relate: (relation, source) or None.

    relation is IDENTICAL, SUPERSEDED or NEAREST. Two spellings of one name
    are not an equivalence - that is canonical_grade's job - so equal keys
    return None.
    """
    a, b = _key(x), _key(y)
    if a == b:
        return None
    ca, cb = _current(a), _current(b)
    if ca == cb or cb in _identical_class(ca):
        rel = "SUPERSEDED" if (ca, cb) != (a, b) else "IDENTICAL"
        src = next((s for p, r, q, s in EQUIVALENCE if {_key(p), _key(q)} & {a, b}), "")
        return rel, src
    for p, rel, q, src in EQUIVALENCE:
        if rel == "NEAREST" and {_key(p), _key(q)} == {ca, cb}:
            return "NEAREST", src
    return None
