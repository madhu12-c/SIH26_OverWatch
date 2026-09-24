"""
Rule-based reader - the extractor that needs no model and no network.

Runs when the LLM is unavailable, and on every line in the creation gate. It
was first written against our own synthetic notation and read almost nothing
of real Indian text (3% of real material lines gave two or more facts). This
version reads the way NTPC and Oil India actually write:

    PIPE, BLK, CS, FE410, 9.5MM, 457MM, 450MM         wall, OD, NB - no labels
    Gate Valve, 2.1/16 inch x 5000 PSI, API 6A         oilfield fractions, psi
    TUBE,STRT,AS,A213-T91,54MM,4MM                      OD then wall
    CABLE, PWR, 150MM2, 1C, STRANDED, AL, 11KV

Three ideas carry it:

    1. SIZE NAMES ARE NOT MEASUREMENTS. 100 NB, DN 100 and 4" are one name;
       114.3 mm is the measured OD. Unlabelled millimetre numbers get a role by
       rule (size_roles below), and the one genuinely ambiguous value - 101.6,
       both the OD of a 3-1/2" pipe and 4 x 25.4 - is settled by the stated
       weight or left unknown. Never guessed.
    2. CLASSIFY BY THE FIRST NOUN. A master line names its item first
       ("PIPE, ...", "ELBOW, ..."). An accessory "for" something else, or a
       spare such as a bushing, is not the thing it mentions.
    3. EVERY VALUE KEEPS ITS EVIDENCE: the character span in the original text
       it was read from, so a reviewer can see exactly why.

Confidence is 0.62 for a value read by a rule - lower than a model's, on
purpose - and lower again for a value derived from a table.
"""

from __future__ import annotations

import re

import normalise as nz
import schemas

READ = 0.62          # read straight out of the text by a rule
TABLE = 0.55         # derived from a standard table, or one of two readings

NUM = r"\d+(?:\.\d+)?"
FRAC = r"\d{1,3}-\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}|\d{1,3}(?:\.\d+)?"


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

# A spare, an accessory or a drilling tool that mentions a category noun is
# not that category. Checked first, anywhere in the line.
OTHER_NOUNS = (
    r"BUSHING|INSULATOR|BOTTLE|DRILL\s?PIPE|STRAINER|SPOOL|HOSE|BATTER(?:Y|IES)|ROPE|"
    r"ELECTRODE|CEMENT(?:ING)?|STARCH|CHAIN|STABILI[SZ]ER|SWIVEL|SPINNER|MANIFOLD|"
    r"ARRESTER|TANK|TMT|ROUND\s+BAR|BELT|FAN|EXTINGUISHER|ROTOR|CLAMP|PUMPS?|"
    r"POWER\s+UNIT|HANGER|JINGLE|FENCING|WIRE|SHEET|CRIMPING|PACK\s+OFF|SLIPS?(?![- ]?ON)|CHOKE|"
    r"PLUG(?!\s*VALVE)|ENCLOSURE|RESISTOR|CONTACT\s+BLADE|GRIPS?|VENTILATOR|CLEANER|"
    r"MUD\s+MOTOR|FLOC|FRICTION\s+REDUCER|SAMPLING"
)

CATEGORY_NOUNS = (
    ("bearing",    r"BEARINGS?|BRG|BEARN?G|BER|BARNG"),
    ("gasket",     r"GASK?E?TS?"),
    ("flange",     r"FLAN[GD]E?S?|WNRF"),
    ("fitting",    r"ELBOWS?|BENDS?|TEES?|REDUCERS?|CAPS?|COUPLINGS?|UNIONS?|NIPPLES?"),
    ("pipe",       r"PIPES?|CASING|TUBING"),
    ("tube",       r"TUBES?"),
    ("plate",      r"PLATES?"),
    ("valve",      r"VALVES?|VLV"),
    ("fastener",   r"BOLTS?|STUDS?|SCREWS?|NUTS?|WASHERS?|BLT"),
    ("rotating",   r"MECH(?:ANICAL)?\.?\s*SEALS?|M/SEAL|IMPELLERS?"),
    ("instrument", r"GAUGES?|GAGES?|TRANSMITTERS?|INDICATORS?|THERMOMETERS?|THERMOCOUPLES?|PG"),
    ("cable",      r"CABLES?"),
    ("electrical", r"MOTORS?|MTR|STARTERS?|TRANSFORMERS?|SQUIRREL\s+CAGE|PANELS?|"
                   r"SWITCHGEAR|VCB|LIGHTING|BUSBAR"),
)


# Spares and tools that name the item they fit: a TRANSFORMER BUSHING is a
# bushing, a SAFETY VALVE FOR DRILL PIPE a drilling tool. These win wherever
# they appear. Every other "other" noun wins only when it comes FIRST - a
# "VALVE, PLUG" is a plug valve and a "GASKET, SHEET" a sheet gasket.
STRONG_OTHER = (r"BUSHING|INSULATOR|BOTTLE|SAMPLING|CLAMP|DRILL\s?PIPE|CLEANER|ARRESTER|"
                r"MUD\s+MOTOR|STABILI[SZ]ER|SWIVEL|SPINNER|ELECTRODE|POWER\s+UNIT")

# Head nouns a typo is allowed to reach (one slip: a dropped, added, changed
# or swapped letter). Only words of five letters or more - "BOLT" is too
# short to guess at.
FUZZY_NOUNS = {"BEARING": "bearing", "GASKET": "gasket", "FLANGE": "flange", "VALVE": "valve",
               "CABLE": "cable", "MOTOR": "electrical", "ELBOW": "fitting", "COUPLING": "fitting",
               "MECHANICAL": "rotating", "TRANSFORMER": "electrical", "GAUGE": "instrument",
               "PLATE": "plate", "NIPPLE": "fitting", "REDUCER": "fitting"}


def _one_slip(a: str, b: str) -> bool:
    """True if a and b differ by one edit or one swap of neighbours."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                  and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def classify(t: str) -> tuple[str, tuple[int, int] | None]:
    """(category, span of the noun that decided it)."""
    m = re.search(rf"\b({STRONG_OTHER})\b", t)
    if m:
        return "other", m.span(1)
    best = None
    for name, pattern in CATEGORY_NOUNS:
        m = re.search(rf"\b({pattern})\b", t)
        if m and (best is None or m.start() < best[1][0]):
            best = (name, m.span(1))
    if best is None:
        for w in re.finditer(r"\b[A-Z]{5,}\b", t):
            hit = next((cat for noun, cat in FUZZY_NOUNS.items() if _one_slip(w.group(0), noun)), None)
            if hit:
                best = (hit, w.span())
                break
    weak = re.search(rf"\b({OTHER_NOUNS})\b", t)
    if weak and (best is None or weak.start() <= best[1][0]):
        return "other", weak.span(1)
    if best is None:
        return "other", None
    name, span = best
    # A "gasket" with kV and amp ratings is a switchgear spare (dev 123, 124).
    if name == "gasket" and re.search(rf"{NUM}\s*KV\b|\b{NUM}\s*A\b", t):
        return "other", span
    return name, span


# --------------------------------------------------------------------------
# The reader
# --------------------------------------------------------------------------

class Reading:
    """Collects values with confidence and evidence, first value wins."""

    def __init__(self, description: str, clean: str, idx: list[int], category: str):
        self.orig, self.t, self.idx, self.category = description, clean, idx, category
        self.valid = {f.name: f for f in schemas.fields_for(category)}
        self.attrs, self.conf, self.evidence = {}, {}, {}
        self.used: list[tuple[int, int]] = []
        self.notes: list[str] = []

    def put(self, name, value, span=None, c=READ, force=False):
        if name not in self.valid or value is None or value == "":
            return False
        if name in self.attrs and not force:
            return False
        self.attrs[name] = value
        self.conf[name] = c
        if span:
            self.evidence[name] = nz.span_of(self.idx, span[0], span[1], len(self.orig))
        return True

    def use(self, span):
        self.used.append(span)

    def free(self, span) -> bool:
        return not any(a < span[1] and span[0] < b for a, b in self.used)

    def find(self, pattern, flags=0):
        return re.search(pattern, self.t, flags)


SAP_MAKTX = 40


def extract(description: str) -> dict:
    clean, idx = nz.normalise(description)
    # SAP's short text is 40 characters. A line that stops there may have been
    # cut, and a cut NUMBER reads wrong: "SCH 8" is what is left of "SCH 80",
    # "SS31" of "SS316". So a last token that carries a digit is blanked -
    # missing is safe, wrong is not. A last word ("... GATE VALVE") is kept.
    if SAP_MAKTX - 2 <= len(description.strip()) <= SAP_MAKTX:          # exports trim trailing blanks
        cut = max(clean.rfind(","), clean.rfind(" - "), clean.rfind(" "))
        tail = clean[cut:].strip(" ,-")
        # Cut mid-number ("SCH 8", "SS31") or to a stub ("AS" of ASTM). A value
        # that ends in its unit ("900#", "600NB", "25MM") is whole - kept.
        if cut > 0 and (re.search(r"\d$", tail) or (len(tail) <= 3 and tail.isalpha())):
            clean = clean[:cut] + " " * (len(clean) - cut)
    category, noun_span = classify(clean)
    r = Reading(description, clean, idx, category)
    if noun_span:
        r.evidence["category"] = nz.span_of(idx, *noun_span, len(description))

    if category in ("pipe", "valve", "flange", "fitting", "gasket"):
        read_sizes(r)
        read_pressure(r)
    if category in ("pipe", "valve", "flange", "fitting", "gasket", "plate", "tube", "fastener"):
        read_grade(r)
    read_standard(r)

    reader = {
        "pipe": read_pipe, "valve": read_valve, "flange": read_flange,
        "fitting": read_fitting, "cable": read_cable, "plate": read_plate,
        "tube": read_tube, "electrical": read_electrical, "gasket": read_gasket,
        "fastener": read_fastener, "other": read_other, "rotating": read_rotating,
    }.get(category)
    if reader:
        reader(r)
    read_legacy(r)

    schemas.derive(category, r.attrs, r.conf)
    return {"category": category, "attributes": r.attrs, "confidence": r.conf,
            "evidence": r.evidence, "notes": r.notes, "method": "regex"}


# --------------------------------------------------------------------------
# Sizes - designation versus measurement
# --------------------------------------------------------------------------

# API 6A wellhead and valve bores, in inches. 52.38 mm is 2-1/16", not 2".
API6A_IN = (1.8125, 2.0625, 2.5625, 3.0625, 3.125, 4.0625, 5.125, 7.0625, 9.0, 11.0,
            13.625, 16.75, 18.75, 20.75, 21.25)


# API 5CT casing sizes, in inches - named by their outside diameter.
CASING_IN = (4.5, 5.0, 5.5, 6.625, 7.0, 7.625, 8.625, 9.625, 10.75, 11.75, 13.375,
             16.0, 18.625, 20.0)


def _octg(t: str) -> bool:
    return bool(re.search(r"\bAPI\s?5CT\b|\bCASING\b|\bTUBING\b", t))


def read_sizes(r: Reading) -> None:
    t = r.t
    ods, walls, desig = [], [], []

    # Measured outside diameter, labelled.
    for m in re.finditer(rf"\bO\.?\s?D\.?\s*[:=,]?\s*({NUM})\s*MM", t):
        ods.append((float(m.group(1)), m.span(1))); r.use(m.span())
    for m in re.finditer(rf"({NUM})\s*MM\s*O\.?\s?D\b", t):
        ods.append((float(m.group(1)), m.span(1))); r.use(m.span())
    for m in re.finditer(rf"({FRAC})\s*(?:\"|INCH(?:ES)?)\s*O\.?\s?D\b", t):
        v = nz.parse_inches(m.group(1))
        if v:
            ods.append((round(v * 25.4, 2), m.span(1))); r.use(m.span())

    # Wall, labelled.
    for m in re.finditer(rf"WALL\s*(?:THICKNESS|THK)?\s*[:=,]?\s*({NUM})\s*MM"
                         rf"|({NUM})\s*MM\s*(?:THICK|THK|W\.?T\.?\b)", t):
        g = 1 if m.group(1) else 2
        walls.append((float(m.group(g)), m.span(g))); r.use(m.span())

    # Weight per foot.
    m = re.search(rf"({NUM})\s*(?:PPF|LB/FT|LBS/FT|#/FT)\b", t)
    if m:
        r.put("weight_ppf", float(m.group(1)), m.span(1)); r.use(m.span())

    # Lengths - ranges and metres. Never a size.
    for m in re.finditer(rf"\b(\d{{3,5}})\s*-\s*(\d{{3,5}})\s*MM\b|\b\d{{1,2}}\s*-\s*\d{{1,2}}\s*M\b"
                         rf"|\b\d{{1,2}}(?:\.\d)?\s*M\b(?!M)", t):
        r.use(m.span())

    # Designations: DN, NB, "NOMINAL BORE", and mm with the inch in brackets.
    for pat in (rf"\bDN\s*(\d{{2,4}})\b",
                rf"(\d{{2,4}})\s*MM\s*\(\s*(?:{FRAC})\s*(?:\"|INCH(?:ES)?)?\s*\)?\s*NB\b",
                rf"(\d{{2,4}})\s*MM\s*(?:{FRAC})\s*INCH(?:ES)?\s*NB\b",
                rf"(\d{{2,4}})\s*(?:MM)?\s*NB\b",
                rf"(?:NOMINAL\s+BORE|NOM\.?\s*SIZE|\bNB)\s*[:=,]?\s*(\d{{2,4}})\s*MM",
                rf"(\d{{2,4}})\s*MM\s*\(\s*(?:{FRAC})\s*(?:\"|INCH|IN\b)"):
        for m in re.finditer(pat, t):
            if not r.free(m.span()):
                continue
            nps = nz.nps_for_dn(float(m.group(1)))
            if nps:
                desig.append((nps, m.span(1), READ)); r.use(m.span())
    for m in re.finditer(rf"({FRAC})\s*(?:\"|INCH(?:ES)?)\s*NB\b", t):
        if r.free(m.span()):
            v = nz.parse_inches(m.group(1))
            if v:
                desig.append((v, m.span(1), READ)); r.use(m.span())

    # Inch sizes. An inch value that is really the OD written in inches
    # ("O.D. 168.3 mm (6.5/8")") is the same measurement twice, not a size.
    inches = []
    for m in re.finditer(rf"(?<![\d./-])({FRAC})\s*(?:\"|INCH(?:ES|S)?\b|IN\b)", t):
        if not r.free(m.span()):
            continue
        v = nz.parse_inches(m.group(1))
        if not v or v > 60:
            continue
        if any(abs(v * 25.4 - od) <= 0.01 * od for od, _ in ods) and not _octg(t):
            r.use(m.span())
            continue
        inches.append((v, m.span(1))); r.use(m.span())

    # Unlabelled millimetre numbers.
    bare = []
    for m in re.finditer(rf"(?<![\d./X-])({NUM})\s*MM\b(?!\s*(?:2|²))", t):
        if r.free(m.span()):
            bare.append((float(m.group(1)), m.span(1)))

    size_roles(r, ods, walls, desig, inches, bare)


def size_roles(r, ods, walls, desig, inches, bare) -> None:
    """Give every size number a role, then record the result.

    Bare millimetre numbers, in the order they appear:
      1. a B36.10M outside diameter (within 0.5%)            -> OD
      2. both an OD and a standard size x 25.4 (101.6)      -> ambiguous; the
         stated weight decides, otherwise the size stays unknown
      3. a DN value, 15 mm or more, and no size named yet   -> the size name
      4. a standard size x 25.4 but not an OD (50.8, 152.4) -> the size name,
         converted as if it were a measurement; lower confidence
      5. 60 mm or less                                      -> wall
    """
    cat, t = r.category, r.t
    octg = cat == "pipe" and _octg(t)
    size = None                       # (nps, span, confidence)
    if desig:
        size = desig[0]
    elif inches:
        size = (inches[0][0], inches[0][1], READ)

    od = ods[0] if ods else None
    wall = walls[0] if walls else None
    weight = r.attrs.get("weight_ppf")

    # Pass one: settle the size NAME and the OD before any number is taken
    # as a wall. "19.05MM, 350MM" is a 14" pipe with a 19.05 mm wall - read
    # left to right, 19.05 looked like 3/4" converted to millimetres.
    if cat == "pipe" and not size:
        for v, span in bare:
            if v >= 15 and nz.nps_for_dn(v) and not (v >= 20 and nz.nps_for_od(v, tol=0.005)):
                size = (nz.nps_for_dn(v), span, READ)
                break

    if cat == "pipe" and size and not od and not octg:
        want = nz.od_for_nps(size[0])
        match = next(((v, s) for v, s in bare if want and abs(v - want) <= 0.01 * want), None)
        if match:
            od = match                       # "33.32MM, 323.8MM, 300MM": 323.8 is the OD of 300 NB

    for v, span in bare:
        if (size and span == size[1]) or (od and span == od[1]):
            continue
        is_od = cat == "pipe" and v >= 20 and nz.nps_for_od(v, tol=0.005) is not None
        converted = nz.nps_from_converted_mm(v)
        api6a = next((a for a in API6A_IN if abs(v / 25.4 - a) <= 0.004 * a), None)

        # From 14" up the OD IS the size x 25.4 - one reading, not two.
        ambiguous = is_od and converted and nz.nps_for_od(v, tol=0.005) != converted
        if cat == "pipe" and ambiguous and not octg and not od:
            # 101.6: the OD of a 3-1/2" pipe, or 4" converted by x 25.4.
            as_od = nz.wall_from_weight(v, weight) if weight else None
            real_od = nz.od_for_nps(converted)
            as_name = nz.wall_from_weight(real_od, weight) if (weight and real_od) else None
            if as_name and not as_od:
                size = size or (converted, span, TABLE)
                wall = wall or (as_name, span)
            elif as_od and not as_name:
                od = (v, span)
                wall = wall or (as_od, span)
            r.used.append(span)
            continue
        if octg and inches and abs(v - inches[0][0] * 25.4) <= 0.006 * v:
            od = od or (v, span)                    # casing: named by its OD
            continue
        casing = next((c for c in CASING_IN if abs(v / 25.4 - c) <= 0.003 * c), None)
        if octg and casing and not size:
            size, od = (casing, span, READ), (v, span)
            continue
        # Only when it is the line's one size number: "Line Pipe, 12.7mm". Next to
        # an OD and an NB, 9.5 mm is a wall, not 3/8" converted.
        if (converted and converted >= 0.5 and len(bare) == 1 and not size and not od
                and not is_od and abs(v - converted * 25.4) <= 0.05):
            size = (converted, span, TABLE)          # 12.7, 50.8, 152.4: a name x 25.4
            continue
        if is_od and not od:
            od = (v, span)
            continue
        if v < 15 or (cat == "pipe" and v <= 60 and size and not nz.nps_for_dn(v)):
            if cat in ("pipe",) and not wall:
                wall = (v, span)
            continue
        if nz.nps_for_dn(v) and not size:
            size = (nz.nps_for_dn(v), span, READ)
            continue
        if cat == "valve" and api6a and not size:
            size = (api6a, span, READ)
            continue
        if converted and not size and not is_od:
            size = (converted, span, 0.55)
            continue
        if cat == "pipe" and v <= 60 and not wall:
            wall = (v, span)

    if size:
        r.put("nominal_size_in", float(size[0]), size[1], size[2])
    if od and cat == "pipe":
        r.put("od_mm", float(od[0]), od[1])
    if wall and cat == "pipe":
        r.put("wall_mm", float(wall[0]), wall[1])
    if octg and "nominal_size_in" in r.attrs and "od_mm" not in r.attrs:
        r.put("od_mm", round(r.attrs["nominal_size_in"] * 25.4, 2), None, TABLE)

    # The OD must belong to the named size. If it does not, say so - B1's
    # self-check will act on it; for now it is recorded, not resolved.
    nps, odv = r.attrs.get("nominal_size_in"), r.attrs.get("od_mm")
    if nps and odv and not octg:
        expected = nz.od_for_nps(nps)
        if expected and abs(expected - odv) > 0.01 * expected:
            r.notes.append(f"OD {odv} mm is not the OD of a {nps:g} in pipe")


# --------------------------------------------------------------------------
# Pressure
# --------------------------------------------------------------------------

CLASSES = {125, 150, 300, 400, 600, 800, 900, 1500, 2500, 3000, 6000, 9000}
API_PSI = (2000, 3000, 5000, 10000, 15000, 20000)


def read_pressure(r: Reading) -> None:
    t = r.t
    m = (re.search(r"(?:CLASS|\bCL\.?|ANSI)\s*[:=,-]?\s*(\d{3,4})\b", t)
         or re.search(r"\b(\d{3,4})\s*(?:#|CL\b|CL\.|CLASS\b|LBS?\b)", t))
    if m and int(m.group(1)) in CLASSES:
        r.put("pressure_class", f"{int(m.group(1))}#", m.span(1))

    psi = None
    m = re.search(r"\b(\d{4,5})\s*PSI\b", t)
    if m:
        psi = (float(m.group(1)), m.span(1))
    else:
        m = re.search(r"\bX\s*(\d{1,2})M\b", t)                 # 7-1/16" x 10M
        if m:
            psi = (float(m.group(1)) * 1000, m.span(1))
        else:
            m = re.search(rf"({NUM})\s*KG\s*/?\s*(?:SQ\.?\s*CM|CM\s*2|CM2|CMSQ|SQCM|CM²)", t)
            if m:
                v = float(m.group(1)) * 14.223
                snap = next((p for p in API_PSI if abs(v - p) <= 0.03 * p), None)
                psi = (float(snap or round(v, -1)), m.span(1))
    if psi:
        if r.category == "fitting":
            # Forged fittings (ASME B16.11) are rated by class: 3000 / 6000.
            if int(psi[0]) in CLASSES:
                r.put("pressure_class", f"{int(psi[0])}#", psi[1])
        else:
            r.put("pressure_rating_psi", psi[0], psi[1])


# --------------------------------------------------------------------------
# Grades
# --------------------------------------------------------------------------

_SPECIFIC_GRADES = (
    (r"\bA\s?312\s*(?:GR\.?\s*)?TP\s?(\d{3}[LH]?)\b",  lambda m: f"SS{m.group(1)}"),
    (r"\bTP\s?(\d{3}[LH]?)\b",                       lambda m: f"SS{m.group(1)}"),
    (r"\bA\s?182\s*,?\s*F\s?(3\d{2}[LH]?)\b",         lambda m: f"SS{m.group(1)}"),
    (r"\bA\s?182\s*,?\s*(F\s?\d{1,2})\b",             lambda m: f"A182 {m.group(1).replace(' ', '')}"),
    (r"\bA\s?351\s*,?\s*CF8M\b|\bCF8M\b",             lambda m: "SS316"),
    (r"\bA\s?351\s*,?\s*CF8\b|\bCF8\b",               lambda m: "SS304"),
    (r"\bA\s?213\s*,?\s*(T\d{1,2})\b",                lambda m: f"A213 {m.group(1)}"),
    (r"\bA\s?335\s*,?\s*(P\d{1,2})\b",                lambda m: f"A335 {m.group(1)}"),
    (r"\bA\s?106\s*,?\s*(?:GR(?:ADE)?\.?\s*)?([ABC])\b", lambda m: f"A106 GR {m.group(1)}"),
    (r"\bA\s?53\s*,?\s*(?:GR(?:ADE)?\.?\s*)?([AB])\b", lambda m: f"A53 GR {m.group(1)}"),
    (r"\bA\s?333\s*,?\s*(?:GR(?:ADE)?\.?\s*)?(\d)\b",  lambda m: f"A333 GR {m.group(1)}"),
    (r"\bAPI\s?5L\b[\s,]*(?:GRADE|GR\.?)\s*(X\d{2}|[AB])\b", lambda m: _api5l(m.group(1))),
    (r"\bGRADE\s*(X\d{2})\b",                        lambda m: _api5l(m.group(1))),
    (r"\bA\s?234\s*,?\s*WPB\b",                       lambda m: "A234 WPB"),
    (r"\bA\s?216\s*,?\s*WCB\b",                       lambda m: "A216 WCB"),
    (r"\bA\s?350\s*,?\s*LF2\b",                       lambda m: "A350 LF2"),
    (r"\bA\s?193\s*,?\s*B\s?7\b|\bB7\b",              lambda m: "A193_B7"),
    (r"\bA\s?423\s*,?\s*(?:GR\.?\s*)?(\d)\b",         lambda m: f"A423 GR{m.group(1)}"),
    (r"\bCOR-?TEN\b",                                lambda m: "CORTEN"),
    (r"\bFE\s?(\d{3})\b",                            lambda m: f"FE{m.group(1)}"),
    (r"\bIS\s?2062\s*,?\s*-?\s*(E\s?\d{3}\s?(?:BR|BO|[A-D])?|[ABC])?\b",
     lambda m: "IS2062" + (f" {m.group(1).replace(' ', '')}" if m.group(1) else "")),
    (r"\bA\s?105\b",                                 lambda m: "ASTM_A105"),
    (r"\bA\s?312\b",                                 lambda m: "A312"),
    (r"\bA\s?182\b",                                 lambda m: "A182"),
    (r"\bGR\.?\s*(1\.\d{4})\b",                      lambda m: m.group(1)),
    (r"\b(?:S\.?\s?S\.?|SS|STAINLESS\s+STEEL)\s*-?\s*(30[1-9]|31[0-7]|321|347|409|410|420|430|440)\s*(L)?\b", lambda m: f"SS{m.group(1)}{m.group(2) or ''}"),
    (r"\b(30[1-9]|31[0-7]|321|347|409|410|420|430|440)\s*(L)?\s*(?:SS|S\.S\.)\b", lambda m: f"SS{m.group(1)}{m.group(2) or ''}"),
    (r"\b(?:GRADE|GR\.?)\s*([NPKJL])\s?(80|110|55)\b", lambda m: f"{m.group(1)}{m.group(2)}"),
    (r"\b([NPKJL])(80|110|55)\b",                     lambda m: f"{m.group(1)}{m.group(2)}"),
)

_FAMILY_WORDS = (
    (r"\b(?:FORGED\s+|CAST\s+)?CARBON\s+ST(?:EE)?L\b|\bC\.S\.?|(?:^|,)\s*CS\s*(?=,|$)|\bCS\b", "CARBON_STEEL"),
    (r"\bMILD\s+STEEL\b|\bM\.\s?S\.?|\bMS\b", "MILD_STEEL"),
    (r"\bALLOY\s+ST(?:EE)?L\b", "ALLOY_STEEL"),
    (r"\bSTAINLESS\s+STEEL\b|\bS\.S\.?|\bSS\b", "SS"),
    (r"\bCAST\s+STEEL\b", "CAST_STEEL"),
    (r"\bCAST\s+IRON\b|\bC\.I\.", "CAST_IRON"),
    (r"\bCOPPER\b", "COPPER"),
)


def _api5l(g: str) -> str:
    return f"API 5L {g}" if g.startswith("X") else f"API 5L GR {g}"


def read_grade(r: Reading) -> None:
    field = "body_material" if r.category == "valve" else "material_grade"
    t = r.t
    for pattern, make in _SPECIFIC_GRADES:
        m = re.search(pattern, t)
        if m:
            r.put(field, make(m), m.span())
            return
    # API 5L with no grade letter is still a carbon steel line pipe.
    for pattern, family in _FAMILY_WORDS:
        m = re.search(pattern, t)
        if m:
            r.put(field, family, m.span())
            return


def read_standard(r: Reading) -> None:
    # A product standard (API 600, ASME B16.5, BS 1873) says what the item IS;
    # an ASTM material spec says what it is MADE OF and is read as the grade.
    # Only for pipe and tube is the ASTM spec the product standard.
    product = (r"\b(API\s?(?:5L|5CT|5DP|6A|6B|6D|6FA|599|600|602|608|609|610|674|7K|7F)"
               r"|(?:ASME|ANSI|ASA)\s?,?\s?B\s?16\.\d{1,2}|B16\.\d{1,2}|BS\s?\d{3,4}"
               r"|IS\s?\d{3,5}(?:-\d)?)\b")
    material = r"\b(ASTM\s?A\s?\d{2,3})\b"
    if r.category in ("pipe", "tube"):
        m = re.search(material, r.t) or re.search(product, r.t)
    else:
        m = re.search(product, r.t)             # ASTM A105 on a flange is its grade, read there
    if m:
        s = re.sub(r"\s+", " ", m.group(1)).replace(",", "")
        s = re.sub(r"^(API|IS|ASTM|BS)\s?", r"\1 ", s)
        s = re.sub(r"^(?:ASA|ANSI)\s?", "ASME ", s)
        s = re.sub(r"\bB\s?16", "B16", s)
        if s.startswith("B16"):
            s = "ASME " + s
        r.put("standard", s.strip(), m.span(1))


# --------------------------------------------------------------------------
# Category readers
# --------------------------------------------------------------------------

def read_pipe(r: Reading) -> None:
    t = r.t
    if not re.search(r"ERW\s*/\s*[LH]?SAW|SAW\s*/\s*ERW", t):      # "either" is not a spec
        for pat, val in ((r"\bSEAMLESS\b", "seamless"), (r"\bERW\b", "erw"),
                         (r"\b[LH]?SAW\b", "saw"), (r"\bWELDED\b", "welded")):
            m = re.search(pat, t)
            if m:
                r.put("construction", val, m.span()); break
    for pat, val in ((r"\bBLACK\b", "black"), (r"\bGALVANI[SZ]ED\b|\bGALV\b|\bGI\b", "galvanised")):
        m = re.search(pat, t)
        if m:
            r.put("finish", val, m.span()); break
    for pat, val in ((r"THREADED\s+(?:AND|&)\s+COUPLED|\bBTC\b|\bT&C\b", "threaded_coupled"),
                     (r"\bBEVEL(?:LED|ED)?(?:\s*END(?:ED)?)?\b", "bevel"),
                     (r"\bPLAIN\s+END(?:ED)?\b", "plain"), (r"\bSCREWED\b", "screwed")):
        m = re.search(pat, t)
        if m:
            r.put("end_type", val, m.span()); break
    read_schedule(r)


def read_schedule(r: Reading) -> None:
    t = r.t
    m = re.search(r"\bSCH(?:EDULE)?\.?\s*[-:]?\s*(\d{1,3}S?|XXS|XS|STD)\b", t)
    if m:
        r.put("schedule", f"SCH {m.group(1)}", m.span(1)); return
    m = re.search(r"(?:^|,)\s*(\d{2,3})S\s*(?=,|$)", t)                     # 80S
    if m:
        r.put("schedule", f"SCH {m.group(1)}S", m.span(1)); return
    m = re.search(r"(?:^|[, ])(XXS|XS)(?=[,. ]|$)", t)
    if m:
        r.put("schedule", f"SCH {m.group(1)}", m.span(1)); return
    m = re.search(r"\bSTD\.?\s*W(?:EIGH)?T\.?", t)
    if m:
        r.put("schedule", "SCH STD", m.span())


VALVE_TYPES = (
    (r"DUAL\s+PLATE\s+CHECK", "dual_plate_check"), (r"(?:SWING\s+)?CHECK|NON[- ]RETURN|\bNRV\b", "check"),
    (r"\bGATE\b", "gate"), (r"\bGLOBE\b", "globe"), (r"\bBALL\b", "ball"),
    (r"\bBUTTERFLY\b", "butterfly"), (r"\bPLUG\b", "plug"), (r"\bNEEDLE\b", "needle"),
    (r"SAFETY\s+RELIEF|RELIEF|\bSAFETY\b|\bPSV\b|\bPRV\b", "safety_relief"),
    (r"\bCONTROL\b", "control"),
)


def read_valve(r: Reading) -> None:
    t = r.t
    for pat, val in VALVE_TYPES:
        m = re.search(pat, t)
        if m:
            r.put("valve_type", val, m.span()); break
    for pat, val in ((r"\bRTJ\b|RING\s+JOINT|R\.\s?J\.", "ring_joint"),
                     (r"\bFLANGED\b|\bFLNGD\b|\bFLGD?\b", "flanged"),
                     (r"\bSCREWED\b|\bSCRD\b|\bTHREADED\b|\bNPT\b", "screwed"),
                     (r"SOCKET\s*WELD|\bSWE?\b", "socket_weld"), (r"BUTT\s*WELD|\bBW\b", "butt_weld"),
                     (r"\bWAFER\b", "wafer")):
        m = re.search(pat, t)
        if m:
            r.put("end_connection", val, m.span()); break
    for pat, val in ((r"HAND\s*WHEEL|MANUAL|\bHW\b|\bLEVER", "manual"), (r"HYDRAULIC", "hydraulic"),
                     (r"PNEUMATIC", "pneumatic"), (r"GEAR|\bGO\b", "gear"),
                     (r"MOTORI[SZ]ED|ELECTRIC\s+ACTUAT", "electric")):
        m = re.search(pat, t)
        if m:
            r.put("operation", val, m.span()); break


def read_flange(r: Reading) -> None:
    t = r.t
    for pat, val in ((r"SLIP[- ]?ON|\bSO\b", "slip_on"), (r"WELD(?:ING)?\s*NECK|\bWN\b|\bWNRF\b", "weld_neck"),
                     (r"\bBLIND\b", "blind"), (r"SOCKET\s*WELD", "socket_weld"),
                     (r"\bTHREADED\b|\bSCREWED\b", "threaded"), (r"LAP\s*JOINT", "lap_joint")):
        m = re.search(pat, t)
        if m:
            r.put("flange_type", val, m.span()); break
    for pat, val in ((r"\bRTJ\b|RING\s+JOINT|R\.\s?J\.", "ring_joint"),
                     (r"RAISED\s+FACE|\bRF\b|\bWNRF\b", "raised_face"),
                     (r"FLAT\s+FACE|\bFF\b", "flat_face")):
        m = re.search(pat, t)
        if m:
            r.put("face_type", val, m.span()); break
    m = re.search(r"\bSCH(?:EDULE)?\s*(\d{1,3}S?|XXS|XS|STD)\b", t)
    if m:
        r.put("bore_schedule", f"SCH {m.group(1)}", m.span(1))


FITTINGS = (("ELBOW", "elbow"), ("BEND", "bend"), ("TEE", "tee"), ("REDUCER", "reducer"),
            ("CAP", "cap"), ("COUPLING", "coupling"), ("UNION", "union"),
            ("NIPPLE", "nipple"), ("SLEEVE", "sleeve"))


def read_fitting(r: Reading) -> None:
    t = r.t
    best = None
    for word, val in FITTINGS:
        m = re.search(rf"\b{word}S?\b", t)
        if m and (best is None or m.start() < best[1][0]):
            best = (val, m.span())
    if best:
        r.put("fitting_type", best[0], best[1])
    m = re.search(r"\b(90|45|180)\s*(?:DEG|°)", t)
    if m:
        r.put("angle", float(m.group(1)), m.span(1))
    m = re.search(r"\b(LR|SR)\b|LONG\s+RADIUS|SHORT\s+RADIUS", t)
    if m:
        r.put("radius", "LR" if "L" in m.group(0)[:1] else "SR", m.span())
    for pat, val in ((r"\bTHREAD|\bNPT\b|\bSCREWED\b", "screwed"),
                     (r"SOCKET\s*WELD|\bSW\b", "socket_weld"), (r"BUTT\s*WELD|\bBW\b", "butt_weld")):
        m = re.search(pat, t)
        if m:
            r.put("end_connection", val, m.span()); break
    read_schedule(r)


def read_cable(r: Reading) -> None:
    t = r.t
    for pat, val in ((r"\bPOWER\b", "power"), (r"\bCONTROL\b", "control"),
                     (r"\bINSTRUMENT", "instrument"), (r"FIBRE|FIBER|OPTICAL", "fibre")):
        m = re.search(pat, t)
        if m:
            r.put("cable_type", val, m.span()); break
    area = rf"(?:MM\s*2|MM²|SQ\.?\s*MM|SQMM|SQ\s+MM)"
    m = (re.search(rf"\b(\d(?:\.\d)?)\s*C?\s*X\s*({NUM})\s*{area}", t)     # 3.5 X 70 SQ MM
         or re.search(rf"\b(\d(?:\.\d)?)\s*C\s*X\s*({NUM})\b", t))         # 3C X 120 + ...
    if m:
        r.put("cores", float(m.group(1)), m.span(1))
        r.put("cross_section_mm2", float(m.group(2)), m.span(2))
    m = re.search(rf"({NUM})\s*{area}", t)
    if m:
        r.put("cross_section_mm2", float(m.group(1)), m.span(1))
    m = re.search(r"\b(\d(?:\.\d)?)\s*(?:C|CORES?)\b", t)
    if m:
        r.put("cores", float(m.group(1)), m.span(1))
    for pat, val in ((r"\bALUMINI?UM\b|\bALU\b|\bAL\b", "AL"), (r"\bCOPPER\b|\bCU\b", "CU")):
        m = re.search(pat, t)
        if m:
            r.put("conductor", val, m.span()); break
    m = re.search(rf"({NUM})\s*KV\b", t)
    if m:
        r.put("voltage_kv", float(m.group(1)), m.span(1))
    else:
        m = re.search(r"\b(\d{3,4})\s*V\b", t)
        if m:
            r.put("voltage_kv", float(m.group(1)) / 1000, m.span(1))
    for pat, val in ((r"\bXLPE\b", "XLPE"), (r"\bEPR\b|ETHYLENE\s+PROPYLENE", "EPR"), (r"\bPVC", "PVC")):
        m = re.search(pat, t)
        if m:
            r.put("insulation", val, m.span()); break
    m = re.search(r"\bUN-?ARMOU?R(?:ED)?\b|\bUNARMD\b|\bARMOU?RED\b|\bARMD\b|\bPVCA\b", t)
    if m:
        r.put("armour", "unarmoured" if m.group(0).startswith("UN") else "armoured", m.span())


def read_plate(r: Reading) -> None:
    t = r.t
    m = re.search(rf"({NUM})\s*MM\s*X\s*({NUM})\s*MM\s*X\s*({NUM})\s*MM", t)
    if m:
        r.put("thickness_mm", float(m.group(1)), m.span(1))
        big = sorted((float(m.group(2)), float(m.group(3))))
        r.put("width_mm", big[0], m.span(3))
        r.put("length_mm", big[1], m.span(2))
    m = re.search(rf"({NUM})\s*MM\b", t)
    if m:
        r.put("thickness_mm", float(m.group(1)), m.span(1))
    m = re.search(r"CHEQUERED|CHECKERED|\bCHQ\b", t)
    r.put("plate_type", "chequered" if m else None, m.span() if m else None)


def read_tube(r: Reading) -> None:
    t = r.t
    for pat, val in ((r"\bBOILER\b", "boiler"), (r"EXCHANGER", "exchanger"),
                     (r"\bINSTRUMENT", "instrument")):
        m = re.search(pat, t)
        if m:
            r.put("tube_type", val, m.span()); break
    m = re.search(rf"({FRAC})\s*(?:\"|INCH)\s*O\.?\s?D\b", t)
    if m:
        r.put("od_mm", round(nz.parse_inches(m.group(1)) * 25.4, 2), m.span(1))
    m = re.search(rf"({NUM})\s*MM\s*O\.?\s?D\b|O\.?\s?D\.?\s*({NUM})\s*MM", t)
    if m:
        g = 1 if m.group(1) else 2
        r.put("od_mm", float(m.group(g)), m.span(g))
    m = re.search(rf"({NUM})\s*MM\s*(?:THICK|THK|WALL)", t)
    if m:
        r.put("wall_mm", float(m.group(1)), m.span(1))
    nums = [(float(m.group(1)), m.span(1)) for m in re.finditer(rf"(?<![\d.-])({NUM})\s*MM\b", t)]
    nums = [n for n in nums if not (r.attrs.get("wall_mm") == n[0] or r.attrs.get("od_mm") == n[0])]
    if len(nums) == 1 and "od_mm" not in r.attrs and "wall_mm" not in r.attrs and nums[0][0] < 12:
        r.put("wall_mm", *nums[0])                  # a tube OD is never under 12 mm
        return
    for name in ("od_mm", "wall_mm"):
        if name not in r.attrs and nums:
            v, span = nums.pop(0)
            r.put(name, v, span)


def read_electrical(r: Reading) -> None:
    t = r.t
    best = None
    for pat, val in ((r"CURRENT\s+TRANSFORMER", "current_transformer"),
                     (r"TRANSFORMER", "transformer"),
                     (r"\bMOTORS?\b|\bMTR\b|SQUIRREL\s+CAGE", "motor"),
                     (r"\bSTARTER\b", "starter"), (r"\bLIGHTING\b", "lighting"),
                     (r"\bPANEL\b|\bVCB\b|\bBUSBAR\b", "panel"), (r"SWITCHGEAR", "switchgear")):
        m = re.search(pat, t)
        if m and (best is None or m.start() < best[1][0]):
            best = (val, m.span())
    if best:
        r.put("equipment_type", *best)
    kind = r.attrs.get("equipment_type")

    m = re.search(rf"\b({NUM})\s*KW\b", t)
    if m:
        r.put("power_kw", float(m.group(1)), m.span(1))
    m = re.search(rf"\b({NUM})\s*HP\b", t)
    if m:
        r.put("power_hp", float(m.group(1)), m.span(1))
    m = re.search(r"\b(\d{3,4})\s*RPM\b", t)
    if m:
        r.put("speed_rpm", float(m.group(1)), m.span(1))
    m = re.search(r"\b([2468])\s*P\b|(?:^|,)\s*([2468])\s*(?=,)", t)
    if m and (m.group(1) or re.search(r"(?:^|,)\s*(?:DW)?\d{2,3}(?:SM|MX|LX|S|M|L)\s*(?=,)", t)):
        g = 1 if m.group(1) else 2
        r.put("poles", float(m.group(g)), m.span(g))
    m = re.search(r"(?:^|,)\s*(?:DW)?(\d{2,3}(?:SM|MX|LX|MY|S|M|L))\s*(?=,|$)", t)
    if m:
        r.put("frame", m.group(1), m.span(1))
    m = re.search(r"\b(B35|B34|B3|B5|B14|V1)\b|FOOT\s+MOUNTED|FLANGE\s+MOUNTED", t)
    if m:
        code = m.group(1) or ("B3" if "FOOT" in m.group(0) else "B5")
        r.put("mounting", {"B3": "foot", "B5": "flange", "B35": "foot_flange", "B34": "foot_flange",
                           "B14": "face", "V1": "vertical"}[code], m.span())
    m = re.search(r"\b(S[1-9])\b", t)
    if m:
        r.put("duty", m.group(1), m.span(1))
    m = re.search(r"(?:^|,)\s*(?:CLASS\s+|INS\.?\s*CL\.?\s*)?([FHB])\s*(?=,|$)", t)
    if m:
        r.put("insulation_class", m.group(1), m.span(1))
    m = re.search(r"\bIP\s?(\d{2})\b", t)
    if m:
        r.put("protection_class", f"IP{m.group(1)}", m.span())
    m = re.search(r"\b3\s*-?\s*(?:PH|PHASE)\b|THREE\s+PHASE", t)
    if m:
        r.put("phases", 3.0, m.span())

    if kind in ("transformer", "current_transformer"):
        m = re.search(rf"({NUM})\s*MVA\b", t)
        if m:
            r.put("rating_kva", float(m.group(1)) * 1000, m.span(1))
        m = re.search(rf"({NUM})\s*KVA\b", t)
        if m:
            r.put("rating_kva", float(m.group(1)), m.span(1))
        kv = rf"(\d+(?:\.\d+)?|\.\d+)"
        kvs = []
        for m in re.finditer(rf"{kv}\s*(?:KV)?\s*[/ ]\s*{kv}\s*KV\b", t):
            kvs += [float(m.group(1)), float(m.group(2))]
        kvs += [float(x) for x in re.findall(rf"{kv}\s*KV\b", t)]
        if kvs:
            r.put("voltage_hv_kv", max(kvs))
    else:
        m = re.search(r"\b(\d{3,4})\s*V(?:AC|OLTS?)?\b", t)
        if m:
            r.put("voltage_v", float(m.group(1)), m.span(1))
        else:
            m = re.search(rf"\b({NUM})\s*KV\b", t)
            if m:
                r.put("voltage_v", float(m.group(1)) * 1000, m.span(1))


def read_rotating(r: Reading) -> None:
    t = r.t
    for pat, val in ((r"MECH(?:ANICAL)?\.?\s*SEAL|M/SEAL", "mechanical_seal"), (r"\bIMPELLER", "impeller"),
                     (r"\bCOUPLING", "coupling"), (r"SHAFT\s+SLEEVE", "shaft_sleeve"), (r"WEAR\s+RING", "wear_ring")):
        m = re.search(pat, t)
        if m:
            r.put("component_type", val, m.span()); break
    # Arrangement words are often misspelt ("CARRTIDGE", "DOUBEL"); one slip
    # is read through. A bare CARTRIDGE says nothing about single or double -
    # left unset rather than guessed.
    words = [(w.group(0), w.span()) for w in re.finditer(r"[A-Z]+", t)]
    like = lambda word, target: word == target or (len(word) >= 5 and _one_slip(word, target))
    cart = next((s for w, s in words if like(w, "CARTRIDGE")), None)
    kind = next(((k, s) for w, s in words for k in ("SINGLE", "DOUBLE", "TANDEM") if like(w, k)), None)
    if kind:
        v = kind[0].lower()
        r.put("arrangement", f"cartridge_{v}" if cart and v != "tandem" else v,
              (min(kind[1][0], cart[0]) if cart else kind[1][0], kind[1][1]))
    m = re.search(rf"({NUM})\s*MM\s*(?:SHAFT|SHAFT\s*DIA)|SHAFT\s*(?:DIA\.?)?\s*[:=,]?\s*({NUM})\s*MM", t)
    if m:
        g = 1 if m.group(1) else 2
        r.put("shaft_dia_mm", float(m.group(g)), m.span(g))
    m = re.search(r"\b(SIC|TC|CARBON|CERAMIC)\s*(?:VS\.?|/|AGAINST)\s*(SIC|TC|CARBON|CERAMIC)\b", t)
    if m:
        r.put("face_materials", f"{m.group(1)} VS {m.group(2)}", m.span())
    m = re.search(r"\b(VITON|FKM|EPDM|NITRILE|NBR|KALREZ|FFKM)\b", t)
    if m:
        r.put("elastomer", {"FKM": "VITON", "NBR": "NITRILE", "FFKM": "KALREZ"}.get(m.group(1), m.group(1)), m.span())


def read_gasket(r: Reading) -> None:
    m = re.search(r"\b(GRAPHITE|GRAPH|GR|PTFE|TEFLON)\b\s*(?:FILLER|FILLED|FILL)|"
                  r"(?:FILLER|FILLED)\s*[:=,]?\s*(GRAPHITE|PTFE)", r.t)
    if m:
        v = m.group(1) or m.group(2)
        r.put("filler", "PTFE" if v in ("PTFE", "TEFLON") else "GRAPHITE", m.span())
    m = re.search(rf"({NUM})\s*MM\s*(?:THK|THICK)", r.t)
    if m:
        r.put("thickness_mm", float(m.group(1)), m.span(1))
    for pat, val in ((r"SPIRAL\s*WOUND|SPIRALWOUND|SPL\s*WOUND|\bSW\b", "spiral_wound"),
                     (r"RING\s+JOINT|\bRTJ\b", "ring_joint"), (r"FULL\s+FACE", "full_face"),
                     (r"CAMPROFILE", "camprofile")):
        m = re.search(pat, r.t)
        if m:
            r.put("gasket_type", val, m.span()); break


def read_fastener(r: Reading) -> None:
    t = r.t
    m = re.search(r"\bS/BOLT\b|\bST\.?\s?BOLT\b", t)
    if m:
        r.put("fastener_type", "stud_bolt", m.span())
    for word, val in (("STUD", "stud_bolt"), ("BOLT", "bolt"), ("SCREW", "screw"),
                      ("NUT", "nut"), ("WASHER", "washer"), ("ANCHOR", "anchor")):
        m = re.search(rf"\b{word}S?\b", t)
        if m:
            r.put("fastener_type", val, m.span()); break
    m = re.search(r"\bHEX(?:AGONAL)?\b|\bHH\b", t)
    if m:
        r.put("head_type", "hex", m.span())
    m = re.search(r"\b(M\d{1,2})\b", t)
    if m:
        r.put("thread", m.group(1), m.span(1))
    m = re.search(r"\b(4\.6|5\.6|8\.8|10\.9|12\.9)\b", t)
    if m:
        r.put("material_grade", m.group(1), m.span(1))


def read_other(r: Reading) -> None:
    t = r.t
    m = re.search(rf"\b({OTHER_NOUNS})\b", t)
    if m:
        noun = re.sub(r"S$", "", re.sub(r"\s+", " ", m.group(1))) if m.group(1) not in ("GRIPS",) else "GRIP"
        r.put("noun", noun, m.span(1))
    else:
        body = re.sub(r"^(?:.*?\b(?:SUPPLY|PROCUREMENT)\s+OF\s+|BIDS\s+FOR\s+(?:THE\s+)?)", "", t)
        w = re.search(r"\b([A-Z]{3,}(?:\s+[A-Z]{3,})?)\b", body)
        if w:
            r.put("noun", w.group(1))
    # Order quantities are not specifications: "QTY: 05 NOS", "( 2 pieces )", "(Q3)".
    spec = re.sub(r"\(?\s*QTY[^)]*\)?|\(\s*[\d,.]+\s*(?:METERS?|METRES?|PIECES?|KILOGRAMS?|NOS?|SETS?|KGS?|MT|M)\s*\)"
                  r"|\(Q\d\)|\b\d+\s*(?:NOS|MT|SETS)\b", " ", t)
    found = set()
    for m in re.finditer(rf"(?<![\d./-])({FRAC})\s*(?:\"|INCH(?:ES|S)?\b)", spec):
        v = nz.parse_inches(m.group(1))
        if v:
            found.add(f"{_n(str(v))}IN")
    spec = re.sub(rf"(?<![\d./-])(?:{FRAC})\s*(?:\"|INCH(?:ES|S)?\b)", " ", spec)
    units = r"KVA|MVA|KV|MW|KW|HP|AH|PSI|SWG|MM|V|A"
    spec = re.sub(r"\bVOLTS?\b", "V", spec)
    found |= {f"{_n(m.group(1))}{m.group(2)}"
              for m in re.finditer(rf"({NUM})\s*({units})\b", spec)}
    # "29 mm (1.1/8")" states one size twice. The inch copy is not a second number.
    mms = [float(q[:-2]) for q in found if q.endswith("MM")]
    found = sorted(q for q in found
                   if not (q.endswith("IN") and any(abs(float(q[:-2]) * 25.4 - mm) <= 0.03 * mm for mm in mms)))
    if found:
        r.put("quantities", " ".join(found))


def _n(x: str) -> str:
    v = float(x)
    return str(int(v)) if v == int(v) else str(v)


# --------------------------------------------------------------------------
# Legacy patterns - the synthetic notation the demo is built on
# --------------------------------------------------------------------------

_LEGACY = {
    "iso_designation":  r"\b(6[0-3]\d{2}|2[23]\d{3})\b",
    "seal_type":        r"\b(2RSR?1?|2Z|ZZ|LLU|RS)\b",
    "thread":           r"\b(M\d{1,2})\s*[X×]",
    "length_mm":        r"M\d{1,2}\s*[X×]\s*(\d{1,3})\b",
    "power_hp":         r"(\d+(?:\.\d+)?)\s*HP\b",
    "speed_rpm":        r"(\d{3,4})\s*RPM\b",
    "voltage_v":        r"(\d{3,4})\s*V\b",
    "dial_size_mm":     r"(\d{2,3})\s*MM\s*DIAL",
    "phases":           r"\b(3)\s*[- ]?\s*(?:PH|PHASE)\b",
    "instrument_type":  r"\b(PRESSURE\s*GAUGE|TEMPERATURE\s*GAUGE|TEMP\s*GAUGE|"
                        r"PRESSURE\s*TRANSMITTER|LEVEL\s*TRANSMITTER|FLOW\s*METER|"
                        r"THERMOMETER|THERMOCOUPLE|RTD)\b",
    "wetted_material":  r"\b(S\.?\s?S\.?\s*\d{3}\s*L?|MONEL|HASTELLOY|INCONEL|"
                        r"CARBON\s*STEEL|C\.?S\.?)\b",
    "connection":       r"(\d/\d\s*(?:IN\b|INCH|\")?\s*NPT(?:\s*(?:BOTTOM|BACK|SIDE))?)",
    "shaft_dia_mm":     r"(\d{2,3})\s*MM\s*(?:SHAFT|SHAFT\s*DIA)",
    "nominal_size_in":  r'(\d+(?:\.\d+)?)\s*(?:IN\b|INCH|")',
    "schedule":         r"SCH(?:EDULE)?[\s-]*(\d{1,3}S?)",
    "pressure_class":   r"\b(\d{3,4})\s*#",
    "material_grade":   r"\b(S\.?\s?S\.?\s*\d{3}\s*L?|CARBON\s*STEEL|C\.?S\.?|"
                        r"MILD\s*STEEL|M\.?S\.?|CAST\s*STEEL|A\s*105|A193\s*B7)\b",
}

_DIMS = re.compile(r"(\d{1,4})\s*[X*×]\s*(\d{1,4})\s*[X*×]\s*(\d{1,4})")
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|TO)\s*(\d+(?:\.\d+)?)\s*"
                    r"(BAR|PSI|KPA|MPA|KG/CM2|DEG\s*C|DEGC)\b")


def read_legacy(r: Reading) -> None:
    """The original fallback patterns, for fields no reader above set.

    Size, grade, class and schedule are left alone for the categories whose
    readers handle them - the old inch pattern reads "2-1/16 INCH" as 16.
    """
    handled = r.category in ("pipe", "valve", "flange", "fitting", "gasket")
    for name, pattern in _LEGACY.items():
        if name in r.attrs or name not in r.valid:
            continue
        if handled and name in ("nominal_size_in", "schedule", "pressure_class", "material_grade"):
            continue
        m = re.search(pattern, r.t)
        if not m:
            continue
        spec = r.valid[name]
        raw = m.group(1)
        if spec.kind == "num":
            value = float(raw)
        else:
            value = schemas.canonical_value(name, raw)
            if spec.kind == "enum" and isinstance(value, str):
                value = re.sub(r"\s+", "_", value.strip())
        r.put(name, value, m.span(1))

    if r.category == "bearing" and "seal_type" not in r.attrs:
        m = re.search(r"\b(OPEN|ZZ|2Z|Z|SHIELDED|SEALED|2RS)\b", r.t)
        if m:
            r.put("seal_type", {"OPEN": "OPEN", "ZZ": "2Z", "2Z": "2Z", "Z": "Z", "SHIELDED": "2Z",
                                "SEALED": "2RS", "2RS": "2RS"}[m.group(1)], m.span(1))
    if r.category == "bearing":
        m = _DIMS.search(r.t)
        if m:
            for name, g in zip(("bore_mm", "od_mm", "width_mm"), (1, 2, 3)):
                r.put(name, float(m.group(g)), m.span(g))
        m = re.search(r"DEEP\s*(?:GROOVE|GRV)|D/GROOVE|DP\s*GRV", r.t)
        if m and re.search(r"\bBALL\b", r.t):
            r.put("sub_type", "deep_groove_ball", m.span())

    if "range_min" in r.valid:
        m = _RANGE.search(r.t)
        if m:
            r.put("range_min", float(m.group(1)), m.span(1))
            r.put("range_max", float(m.group(2)), m.span(2))
            r.put("range_unit", re.sub(r"\s+", "", m.group(3)).upper(), m.span(3))


if __name__ == "__main__":
    import json
    import sys
    for line in sys.argv[1:] or [
            "PIPE, BLK, CS, FE410, 9.5MM, 457MM, 450MM",
            "Line Pipe 101.60 mm Seamless, B/E, 12.66 PPF. Qty: 248,000 Mtr",
            "Gate Valve, 2.1/16 inch x 5000 PSI, API 6A",
            "SKF 6205-2RS DEEP GROOVE BALL BEARING"]:
        out = extract(line)
        print(line, "\n  ", out["category"], json.dumps(out["attributes"]))
