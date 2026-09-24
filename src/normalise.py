"""
Normaliser - real material text in, cleaned text and standard tables out.

Runs before any pattern in rules.py. It fixes how Indian material masters
actually write things - NTPC's comma-separated fields, Oil India's tender
sentences, "2.1/16"" for 2-1/16 inch, "FE-410" for FE410 - and it keeps a map
from every character of the cleaned text back to the original, so an
extracted value can point at the exact words it came from (evidence spans).

It also holds the tables that turn a size NAME into a size MEASUREMENT:

    NB / DN / NPS are designations. 100 NB, DN 100 and 4" are the same name.
    The pipe's real outside diameter is 114.3 mm (ASME B36.10M). Treating the
    name as a measurement - 4 x 25.4 = 101.6 mm - is the classic mistake, and
    101.6 mm happens to be the real OD of a 3-1/2" pipe. See size_from_mm().

Every abbreviation below was seen in the dev half of data/real/labels; the
comment names a dev row that needed it. Test rows were never opened.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Size tables
# --------------------------------------------------------------------------

# DN (mm name) -> NPS (inch name). ASME B36.10M / ISO 6708.
DN_TO_NPS = {
    6: 0.125, 8: 0.25, 10: 0.375, 15: 0.5, 20: 0.75, 25: 1.0, 32: 1.25, 40: 1.5,
    50: 2.0, 65: 2.5, 80: 3.0, 90: 3.5, 100: 4.0, 125: 5.0, 150: 6.0, 200: 8.0,
    250: 10.0, 300: 12.0, 350: 14.0, 400: 16.0, 450: 18.0, 500: 20.0, 550: 22.0,
    600: 24.0, 650: 26.0, 700: 28.0, 750: 30.0, 800: 32.0, 850: 34.0, 900: 36.0,
    1000: 40.0, 1050: 42.0, 1200: 48.0,
}
NPS_TO_DN = {v: k for k, v in DN_TO_NPS.items()}

# NPS -> real outside diameter in mm, ASME B36.10M. From 14" up, OD = NPS x 25.4.
NPS_OD_MM = {
    0.125: 10.3, 0.25: 13.7, 0.375: 17.1, 0.5: 21.3, 0.75: 26.7, 1.0: 33.4,
    1.25: 42.2, 1.5: 48.3, 2.0: 60.3, 2.5: 73.0, 3.0: 88.9, 3.5: 101.6,
    4.0: 114.3, 5.0: 141.3, 6.0: 168.3, 8.0: 219.1, 10.0: 273.0, 12.0: 323.8,
}
for _nps in (14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 40, 42, 48):
    NPS_OD_MM[float(_nps)] = round(_nps * 25.4, 1)

# Standard wall thicknesses in inches (ASME B36.10M and API 5L), used only to
# settle a size that is ambiguous between two ODs by the stated weight.
STD_WALLS_IN = (
    0.083, 0.109, 0.120, 0.125, 0.141, 0.154, 0.156, 0.172, 0.188, 0.203, 0.216,
    0.219, 0.226, 0.237, 0.250, 0.258, 0.276, 0.280, 0.281, 0.300, 0.312, 0.318,
    0.337, 0.344, 0.375, 0.400, 0.432, 0.438, 0.500, 0.531, 0.562, 0.600, 0.625,
    0.636, 0.674, 0.688, 0.719, 0.750, 0.864, 0.875,
)


def od_for_nps(nps: float) -> float | None:
    return NPS_OD_MM.get(float(nps))


def nps_for_od(od_mm: float, tol: float = 0.01) -> float | None:
    """The NPS whose B36.10M outside diameter this is, within 1%."""
    best = None
    for nps, od in NPS_OD_MM.items():
        if abs(od - od_mm) <= tol * od and (best is None or abs(od - od_mm) < abs(NPS_OD_MM[best] - od_mm)):
            best = nps
    return best


def nps_for_dn(dn: float) -> float | None:
    return DN_TO_NPS.get(int(round(dn))) if abs(dn - round(dn)) < 1e-6 else None


def nps_from_converted_mm(mm: float) -> float | None:
    """A standard NPS that someone converted to mm as if it were a measurement.

    12.7 (1/2"), 50.8 (2"), 101.6 (4"), 152.4 (6"). Only exact-ish multiples.
    """
    inches = mm / 25.4
    for nps in NPS_OD_MM:
        if abs(nps - inches) <= 0.004 * nps + 0.002:
            return nps
    return None


def pipe_weight_lb_ft(od_in: float, wall_in: float) -> float:
    """Plain-end weight, ASME B36.10M: lb/ft = 10.69 (D - t) t, D and t in inches."""
    return 10.69 * (od_in - wall_in) * wall_in


def wall_from_weight(od_mm: float, lb_ft: float, tol: float = 0.006) -> float | None:
    """The standard wall (mm) that gives this weight on this OD, if any does."""
    d = od_mm / 25.4
    best = None
    for t in STD_WALLS_IN:
        if t >= d / 2:
            break
        w = pipe_weight_lb_ft(d, t)
        err = abs(w - lb_ft) / lb_ft
        if err <= tol and (best is None or err < best[0]):
            best = (err, t)
    return None if best is None else round(best[1] * 25.4, 2)


def parse_inches(text: str) -> float | None:
    """'2-1/16', '1/2', '13-5/8', '4', '6.5' -> inches as a float."""
    text = text.strip()
    m = re.fullmatch(r"(\d{1,3})-(\d{1,2})/(\d{1,2})", text)
    if m:
        whole, num, den = (int(g) for g in m.groups())
        return round(whole + num / den, 4) if den else None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", text)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return round(num / den, 4) if den and num < den else None
    try:
        return float(text)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Grade families - a ladder, not a flat list.
#
# Two grades in different families never match. Two different specific grades
# in one family never match. A bare family ("CS") against a specific grade
# ("A106 GR B") is UNKNOWN - the text does not say, so a human decides.
# --------------------------------------------------------------------------

_FAMILY_RULES = (
    # (family, pattern on the canonical value, is_bare_family)
    ("CS", r"CARBON_STEEL|CS|CARBON STEEL", True),
    ("MS", r"MILD_STEEL|MS|MILD STEEL", True),
    ("SS", r"SS|STAINLESS_STEEL|STAINLESS STEEL", True),
    ("AS", r"ALLOY_STEEL|AS|ALLOY STEEL", True),
    ("CS", r"CAST_STEEL|CAST STEEL", True),
    ("CI", r"CAST_IRON|CI|CAST IRON", True),
    ("CU", r"COPPER|CU", True),
    ("AL", r"ALUMINIUM|AL", True),
    ("SS", r"A312|A182|A240|A213 TP", True),      # a stainless spec with no grade
    ("SS", r"SS\d{3}[LH]?", False),
    ("AS", r"A213 T\d+|A335 P\d+|A182 F(11|22|5|9|91)|A193[ _]B7|A387.*|1\.7\d{3}", False),
    ("CS", r"A106 GR [ABC]|A53 GR [AB]|API 5L GR [AB]|API 5L X\d{2}|A333 GR \d|"
           r"FE\s?\d{3}|IS2062.*|E\d{3}[A-D]?|ASTM_A105|A105|A234 WPB|A216 WCB|A350 LF2", False),
    ("WS", r"CORTEN.*|A423.*", False),
    ("OCTG", r"[NPKJL]\d{2,3}|C\d{2,3}|Q125", False),
    ("DP", r"[EGXS]\d{2,3}(?:\s*DP)?|G105|S135", False),
)


def grade_family(value) -> tuple[str | None, bool]:
    """(family, is_bare) for a canonical grade value. (None, False) if unknown."""
    if value is None:
        return None, False
    v = str(value).strip().upper()
    for fam, pattern, bare in _FAMILY_RULES:
        if re.fullmatch(pattern, v):
            return fam, bare
    return None, False


def canonical_grade(value) -> str:
    """One spelling per grade: 'ASTM A193 B7', 'A193_B7' and 'A193 B7' are one.

    The extractor already canonicalises, but specs cached by an earlier run -
    or by the model - carry older spellings, and a spelling difference must
    never read as a grade difference. That exact bug vetoed seven true stud
    bolt pairs in the synthetic set.
    """
    v = re.sub(r"[\s_]+", " ", str(value).strip().upper())
    v = re.sub(r"^ASTM\s?", "", v)
    # IS 2062:2011 renamed grade A to E250A. The old name is the same steel.
    v = {"IS2062 A": "IS2062 E250A"}.get(v, v)
    return {"A105": "ASTM_A105", "CARBON STEEL": "CARBON_STEEL", "MILD STEEL": "MILD_STEEL",
            "CAST STEEL": "CAST_STEEL", "STAINLESS STEEL": "SS", "ALLOY STEEL": "ALLOY_STEEL",
            "CAST IRON": "CAST_IRON"}.get(v, v)


def compare_grades(x, y) -> str:
    """'agree' | 'mismatch' | 'unknown' for two canonical grade values."""
    a, b = canonical_grade(x), canonical_grade(y)
    if a == b:
        return "agree"
    fa, bare_a = grade_family(a)
    fb, bare_b = grade_family(b)
    if fa is None or fb is None:
        return "mismatch"                   # unrecognised and different: veto
    if {fa, fb} == {"CS", "MS"}:
        return "unknown"                    # Indian usage mixes them; a human decides
    if fa != fb:
        return "mismatch"
    if bare_a or bare_b:
        return "unknown"                    # one side names only the family
    return "mismatch"                       # two different specific grades


# --------------------------------------------------------------------------
# Text cleanup with a character map back to the original
# --------------------------------------------------------------------------

def _sub(pattern, repl, text: str, idx: list[int], flags=0):
    """re.sub that keeps idx (clean char -> original char) in step."""
    out, out_idx, pos = [], [], 0
    for m in re.finditer(pattern, text, flags):
        out.append(text[pos:m.start()])
        out_idx.extend(idx[pos:m.start()])
        new = m.expand(repl) if isinstance(repl, str) else repl(m)
        out.append(new)
        span = max(1, m.end() - m.start())
        out_idx.extend(idx[min(m.start() + min(k, span - 1), len(idx) - 1)] if idx else 0
                       for k in range(len(new)))
        pos = m.end()
    out.append(text[pos:])
    out_idx.extend(idx[pos:])
    return "".join(out), out_idx


# Whole comma-separated fields only. NTPC writes "PIPE, BLK, CS, FE410", and a
# bare AL or IND inside a sentence is too risky to expand.
FIELD_ABBREVIATIONS = {
    "BLK": "BLACK",                      # dev 2
    "GLV": "GALVANISED", "GALV": "GALVANISED", "GI": "GALVANISED",   # dev 86
    "SMLS": "SEAMLESS",                  # dev 8
    "CHQ": "CHEQUERED",                  # dev 29
    "PWR": "POWER",                      # dev 19
    "STRT": "STRAIGHT",                  # dev 38
    "SCIM": "SQUIRREL CAGE INDUCTION MOTOR",   # dev 10
    "IND": "INDUCTION",                  # dev 25
    "AL": "ALUMINIUM", "ALU": "ALUMINIUM",     # dev 19, 279
    "CU": "COPPER",                      # dev 406
    "FTG": "FITTING",
    "PL": "PLAIN END", "P/E": "PLAIN END",     # dev 86
    "B/E": "BEVEL END", "BE": "BEVEL END",     # dev 162
    "T&C": "THREADED AND COUPLED", "S&C": "THREADED AND COUPLED",
    "WN": "WELD NECK", "SO": "SLIP ON",
    "RF": "RAISED FACE",
    "PVCA": "PVC ARMOURED",              # dev 279
    "AS": "ALLOY STEEL",                 # dev 38
    "SQ": "SQUIRREL CAGE", "SQL": "SQUIRREL CAGE", "SQL CAGE": "SQUIRREL CAGE",
    "MTR": "MOTOR",
}

# Hyphenated or spaced grade codes that must read as one token.
_JOIN_GRADES = re.compile(
    r"\b(N|P|K|J|L|C|G|S|E|X)[- ]{0,2}(80|110|55|105|135|95|75|42|46|52|56|60|65|70)\b"
    r"(?![./]\d)")


def normalise(text: str) -> tuple[str, list[int]]:
    """Clean real material text. Returns (clean_uppercase_text, index_map)."""
    s = (text or "").upper()
    idx = list(range(len(s)))

    s, idx = _sub(r"[–—]", "-", s, idx)
    s, idx = _sub(r"[�]", " ", s, idx)
    s, idx = _sub(r"''|”|“|″", '"', s, idx)

    # Oilfield fractions: 2.1/16" -> 2-1/16", 13.5/8 -> 13-5/8, 5. 1/2 -> 5-1/2,
    # and the slash-dropped forms 9.5 8 INCH / 2.7 8 INCHS / 4.1 2 INCHES.
    # An inch fraction's denominator is a power of two - "3.3/0.415 KV" is a
    # voltage ratio, not 3-3/0.
    s, idx = _sub(r"\b(\d{1,2})\.\s?(\d{1,2})/(2|4|8|16|32|64)\b(?!\.\d)", r"\1-\2/\3", s, idx)
    s, idx = _sub(r"\b(\d{1,2})\.(\d) (2|4|8|16)(?=\s*(?:INCH|IN\b|\"))", r"\1-\2/\3", s, idx)
    s, idx = _sub(r"(?<!SCH )(?<!SCH)(?<!GRADE )(?<!GR )(?<!GR\.)\b(\d{1,2}) (\d{1,2})/(\d{1,2})"
                  r"(?=\s*(?:INCH|IN\b|\"|$|[ ,)]))", r"\1-\2/\3", s, idx)

    # Thousands separators before a unit: "10, 000 PSI", "27,000MTR".
    s, idx = _sub(r"\b(\d{1,3}),\s?(\d{3})(?=\s*(?:PSI|KG|MT|MTR|M\b|KM|NOS|LB))", r"\1\2", s, idx)

    # Separators NTPC and SAP exports use between fields.
    s, idx = _sub(r"\s*[:;_]\s*", ", ", s, idx)

    # Hyphenated standards and grades: FE-410, A-105, ASTM-F439, A213- T23, API-5L.
    s, idx = _sub(r"\b(ASTM|API|IS|ASME|ANSI|ASA)[- ]+(?=[A-Z]?\d)", r"\1 ", s, idx)
    s, idx = _sub(r"\b(FE|CL|SA|DN)-\s?(\d)", r"\1\2", s, idx)
    s, idx = _sub(r"\b(A\d{3})[- ]+(?=(TP|T|P|F|GR|WP|CF|B)\s?\d)", r"\1 ", s, idx)
    s, idx = _sub(r"\bA-(\d{3})\b", r"A\1", s, idx)
    s, idx = _sub(r"\bA (\d{3})\b(?=\s*(GR|TP|,|$| ))", r"A\1", s, idx)
    s, idx = _join_grades(s, idx)

    # Whole-field abbreviations.
    def expand(m):
        key = m.group(2).strip()
        return m.group(1) + FIELD_ABBREVIATIONS.get(key, key) + m.group(3)
    keys = "|".join(re.escape(k) for k in sorted(FIELD_ABBREVIATIONS, key=len, reverse=True))
    for _ in range(2):          # adjacent fields share a comma; a second pass catches them
        s, idx = _sub(rf"((?:^|,)\s*)({keys})(\s*(?:,|$))", expand, s, idx)

    s, idx = _sub(r"\s{2,}", " ", s, idx)
    s, idx = _sub(r"(,\s*){2,}", ", ", s, idx)
    s, idx = _sub(r"^[\s,]+", "", s, idx)
    return s, idx


def _join_grades(s, idx):
    # Only where the letter is a grade, not "X 10000" in "2-1/16 X 10000 PSI":
    # the number list is the OCTG / drill pipe / line pipe grade list.
    return _sub(_JOIN_GRADES, lambda m: m.group(1) + m.group(2), s, idx)


def span_of(idx: list[int], start: int, end: int, original_len: int) -> list[int]:
    """Clean-text span -> original-text span."""
    if not idx or start >= len(idx):
        return [0, 0]
    a = idx[start]
    b = idx[min(end, len(idx)) - 1] + 1 if end > start else a
    return [a, min(b, original_len)]


if __name__ == "__main__":
    for t in ("PIPE, BLK, CS, FE410, 9.5MM, 457MM, 450MM",
              "Tube,strt,as,a213- t23,63.5mm,12.7mm",
              "Gate Valve, 2.1/16 inch x 5000 PSI, API 6A",
              "3.1/16\" X 10, 000 PSI API 6A Gate Valve",
              "Bids for the supply of 9.5 8 inch 244.475 mm , API 5CT, P 110, CASING PIPE",
              "M1616254395-PIPE: IS1239-1 MEDIUM,GLV,ERW,PL,125MM"):
        print(normalise(t)[0])
