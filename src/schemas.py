"""
Material category schemas - the shared contract between extraction and matching.

Both sides read this file, and neither should hard-code field names of its own:

    extractor.py   uses it to build the prompt and validate what comes back
    scorer.py      uses it to know which fields veto a match and which are ignored

Three field properties carry the matching rules that matter more than the weights:

    hard=True      a veto field. Mismatch is an instant zero, however well
                   everything else lines up. Grade, pressure rating, key
                   dimensions - the fields where being wrong is a safety failure.

    ignore=True    never counts toward a match. Brand and vendor part number
                   live here, and that is exactly what lets SKF and FAG resolve
                   to one item.

    weight         relative pull of a normal field when both records state it.

One rule is not expressible as a flag and must be honoured by the scorer:
MISSING IS NOT MISMATCHED. If one record states a field and the other is silent,
that is absent information, not evidence of difference. No penalty either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    name: str
    kind: str                     # "str" | "num" | "enum"
    hard: bool = False
    ignore: bool = False
    weight: float = 1.0
    enum: tuple[str, ...] = ()
    unit: str | None = None
    note: str = ""

    def describe(self) -> str:
        bits = [f'"{self.name}"', f"({self.kind}"]
        if self.unit:
            bits.append(f" in {self.unit}")
        bits.append(")")
        line = "".join(bits)
        if self.enum:
            line += "  one of: " + " | ".join(self.enum)
        if self.note:
            line += f"  - {self.note}"
        return line


# Present on every category. Brand and part number are extracted because the
# review screen shows them to a human, never because they influence a match.
COMMON = (
    Field("brand", "str", ignore=True, note="manufacturer, if named"),
    Field("part_number", "str", ignore=True, note="vendor part number, if present"),
)


CATEGORIES: dict[str, tuple[Field, ...]] = {
    "bearing": (
        Field("sub_type", "enum", weight=1.5,
              enum=("deep_groove_ball", "angular_contact", "cylindrical_roller",
                    "tapered_roller", "spherical_roller", "thrust", "needle")),
        Field("iso_designation", "str", hard=True, weight=3.0,
              note="e.g. 6205, 6206, 22215 - the ISO bearing number"),
        Field("bore_mm", "num", hard=True, weight=2.0, unit="mm"),
        Field("od_mm", "num", weight=1.5, unit="mm"),
        Field("width_mm", "num", weight=1.5, unit="mm"),
        Field("seal_type", "enum", weight=1.2,
              enum=("2RS", "RS", "2Z", "Z", "OPEN"),
              note="2RS and 2RSR and 2RS1 and LLU all mean rubber sealed both sides"),
        *COMMON,
    ),
    "gasket": (
        Field("gasket_type", "enum", weight=1.5,
              enum=("spiral_wound", "ring_joint", "full_face", "flat", "camprofile")),
        Field("material_grade", "str", hard=True, weight=3.0,
              note="SS316 / SS304 / SS316L / CS - NEVER treat these as equivalent"),
        Field("nominal_size_in", "num", hard=True, weight=2.0, unit="inch"),
        Field("pressure_class", "str", hard=True, weight=2.0,
              note='ANSI class such as 150# or 300# or 600#'),
        Field("filler", "str", weight=0.8),
        Field("thickness_mm", "num", weight=0.8, unit="mm"),
        *COMMON,
    ),
    "pipe": (
        Field("construction", "enum", hard=True, weight=2.0,
              enum=("seamless", "welded", "erw", "saw")),
        Field("material_grade", "str", hard=True, weight=3.0,
              note="carbon_steel / SS316 / SS304 - grade is a safety field"),
        Field("standard", "str", weight=1.5, note="e.g. ASTM A106 GR B, ASTM A312 TP316"),
        Field("nominal_size_in", "num", hard=True, weight=2.0, unit="inch"),
        Field("schedule", "str", hard=True, weight=2.0, note="SCH 40, SCH 80, SCH 10"),
        *COMMON,
    ),
    "valve": (
        Field("valve_type", "enum", hard=True, weight=2.5,
              enum=("gate", "globe", "ball", "check", "butterfly", "plug",
                    "needle", "safety_relief")),
        Field("nominal_size_in", "num", hard=True, weight=2.0, unit="inch"),
        Field("pressure_class", "str", hard=True, weight=2.5,
              note="150# / 300# / 600# / 800# - a rating mismatch can burst a line"),
        Field("body_material", "str", hard=True, weight=2.0,
              note="cast_steel / SS316 / carbon_steel"),
        Field("end_connection", "enum", weight=1.2,
              enum=("flanged", "screwed", "socket_weld", "butt_weld", "wafer")),
        Field("bore_type", "enum", weight=0.8, enum=("full", "reduced")),
        Field("standard", "str", weight=0.8, note="e.g. API 600, API 6D"),
        *COMMON,
    ),
    "fastener": (
        Field("fastener_type", "enum", hard=True, weight=2.0,
              enum=("bolt", "stud_bolt", "screw", "nut", "washer", "anchor")),
        Field("head_type", "enum", weight=1.0,
              enum=("hex", "socket", "csk", "pan", "none")),
        Field("thread", "str", hard=True, weight=2.5, note="e.g. M12, M20, 1/2-13 UNC"),
        Field("length_mm", "num", hard=True, weight=2.0, unit="mm"),
        Field("material_grade", "str", hard=True, weight=2.5,
              note="SS316 / A193 B7 / 8.8 / 4.6 - grade governs load capacity"),
        Field("standard", "str", weight=0.8, note="e.g. IS 1364, ASTM A193"),
        *COMMON,
    ),
    "flange": (
        Field("flange_type", "enum", hard=True, weight=2.0,
              enum=("weld_neck", "slip_on", "blind", "socket_weld", "threaded", "lap_joint")),
        Field("face_type", "enum", weight=1.2, enum=("raised_face", "flat_face", "ring_joint")),
        Field("nominal_size_in", "num", hard=True, weight=2.0, unit="inch"),
        Field("pressure_class", "str", hard=True, weight=2.5),
        Field("material_grade", "str", hard=True, weight=2.5, note="e.g. ASTM A105, F316"),
        Field("bore_schedule", "str", weight=0.8),
        *COMMON,
    ),
    "rotating": (
        Field("component_type", "enum", hard=True, weight=2.0,
              enum=("mechanical_seal", "impeller", "coupling", "shaft_sleeve", "wear_ring")),
        Field("arrangement", "enum", weight=1.2,
              enum=("single", "double", "tandem", "cartridge_single", "cartridge_double")),
        Field("shaft_dia_mm", "num", hard=True, weight=2.5, unit="mm"),
        Field("face_materials", "str", weight=1.5, note="e.g. SIC vs carbon"),
        Field("elastomer", "str", weight=1.0, note="e.g. viton, nitrile, EPDM"),
        *COMMON,
    ),
    "instrument": (
        Field("instrument_type", "enum", hard=True, weight=2.5,
              enum=("pressure_gauge", "temperature_gauge", "transmitter",
                    "flow_meter", "level_gauge", "switch")),
        Field("dial_size_mm", "num", weight=1.2, unit="mm"),
        Field("range_min", "num", hard=True, weight=2.0),
        Field("range_max", "num", hard=True, weight=2.0),
        Field("range_unit", "str", weight=1.0, note="bar / kg/cm2 / psi / degC"),
        Field("wetted_material", "str", hard=True, weight=2.0, note="e.g. SS316"),
        Field("connection", "str", weight=1.0, note='e.g. 1/2 IN NPT bottom'),
        *COMMON,
    ),
    "electrical": (
        Field("equipment_type", "enum", hard=True, weight=2.5,
              enum=("motor", "cable", "switchgear", "transformer", "lighting", "starter")),
        Field("phases", "num", hard=True, weight=1.5),
        Field("power_hp", "num", hard=True, weight=2.5, unit="hp"),
        Field("speed_rpm", "num", hard=True, weight=2.0, unit="rpm"),
        Field("voltage_v", "num", hard=True, weight=2.0, unit="volt"),
        Field("mounting", "enum", weight=1.0, enum=("foot", "flange", "face", "vertical")),
        Field("protection_class", "str", weight=1.0, note="e.g. IP55"),
        *COMMON,
    ),
    "unknown": (
        Field("noun", "str", weight=1.0, note="the head noun, if identifiable"),
        *COMMON,
    ),
}


def fields_for(category: str) -> tuple[Field, ...]:
    return CATEGORIES.get(category, CATEGORIES["unknown"])


def hard_fields(category: str) -> list[str]:
    """Veto fields. A mismatch on any of these is an instant zero."""
    return [f.name for f in fields_for(category) if f.hard]


def scoring_fields(category: str) -> list[Field]:
    """Fields that contribute to a match score - everything not ignored."""
    return [f for f in fields_for(category) if not f.ignore]


def ignored_fields(category: str) -> list[str]:
    return [f.name for f in fields_for(category) if f.ignore]


def schema_block(category: str) -> str:
    """Human-readable schema, embedded in the extraction prompt."""
    lines = [f"  {f.describe()}" for f in fields_for(category)]
    return f'"{category}":\n' + "\n".join(lines)


def all_schemas_block() -> str:
    return "\n\n".join(schema_block(c) for c in CATEGORIES if c != "unknown")


# --------------------------------------------------------------------------
# Normalisation of extracted values.
#
# The model returns "SS 316", "ss316" and "316 SS" for the same thing. Matching
# compares these directly, so they have to converge before they are stored.
# --------------------------------------------------------------------------

_GRADE_ALIASES = {
    r"^ss\s*316\s*l$": "SS316L",
    r"^(ss|sst|stainless(\s+steel)?)\s*316$": "SS316",
    r"^(ss|sst|stainless(\s+steel)?)\s*304\s*l$": "SS304L",
    r"^(ss|sst|stainless(\s+steel)?)\s*304$": "SS304",
    r"^(cs|carbon(\s+steel)?|carb\s*stl)$": "CARBON_STEEL",
    r"^(ms|mild(\s+steel)?)$": "MILD_STEEL",
    r"^cast\s*steel(\s*body)?$": "CAST_STEEL",
    r"^a\s*105$": "ASTM_A105",
    r"^a\s*193\s*b\s*7$": "A193_B7",
}

_SEAL_ALIASES = {
    r"^2\s*rs(r|1)?$": "2RS", r"^ll[ub]$": "2RS", r"^dd?u$": "2RS",
    r"^rs\d?$": "RS", r"^2\s*z$": "2Z", r"^zz$": "2Z", r"^z$": "Z",
}


def canonical_value(field_name: str, value):
    """Collapse spelling variants so two records can actually compare equal."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    low = re.sub(r"[\s._-]+", " ", text.lower()).strip()

    table = None
    if field_name in ("material_grade", "body_material", "wetted_material", "face_materials"):
        table = _GRADE_ALIASES
    elif field_name == "seal_type":
        table = _SEAL_ALIASES

    if table:
        # "C.S." arrives as "c s" once punctuation is stripped, so try the
        # compacted form too - otherwise every dotted abbreviation slips past.
        compact = low.replace(" ", "")
        for pattern, canon in table.items():
            if re.fullmatch(pattern, low) or re.fullmatch(pattern, compact):
                return canon

        # Any stainless grade, listed or not. The alias table above exists to
        # collapse SPELLINGS ("stainless steel 316", "S.S.316", "316 SS");
        # this rule exists so a grade nobody enumerated still resolves to a
        # comparable value instead of being dropped. Dropping it would be the
        # dangerous outcome: a field that is silent cannot veto a merge.
        if table is _GRADE_ALIASES:
            stainless = (re.fullmatch(r"(?:ss|sst|s s|stainless(?: steel)?)\s*(\d{3})\s*(l?)", low)
                         or re.fullmatch(r"(?:ss|sst|stainless(?:steel)?)(\d{3})(l?)", compact))
            if stainless:
                return f"SS{stainless.group(1)}{stainless.group(2).upper()}"

    if field_name == "pressure_class":
        m = re.search(r"(\d{3,4})", low)
        if m:
            return f"{m.group(1)}#"

    if field_name == "schedule":
        m = re.search(r"(\d{1,3}\s*s?)$", low.replace("sch", "").replace("schedule", ""))
        if m:
            return "SCH " + m.group(1).replace(" ", "").upper()

    return re.sub(r"\s+", " ", text.upper())


# --------------------------------------------------------------------------
# Regex fallback.
#
# Runs when the LLM is unavailable, rate-limited, or returns nothing usable.
# It catches roughly two thirds of fields, which is enough to keep the pipeline
# moving and enough to keep a demo alive when the venue wifi dies.
# --------------------------------------------------------------------------

_CATEGORY_HINTS = (
    ("bearing",    r"\b(bearing|brg|bearn?g|ber)\b"),
    ("gasket",     r"\bgask?et\b"),
    ("flange",     r"\bflan[gd]e?\b|\bwnrf\b"),
    ("pipe",       r"\bpipe\b|\belbow\b|\btee\b|\breducer\b"),
    ("valve",      r"\bvalve\b|\bvlv\b"),
    ("fastener",   r"\b(bolt|stud|screw|nut|washer|blt)\b"),
    ("rotating",   r"\b(mech(anical)?\.?\s*seal|m/seal|impeller|coupling)\b"),
    ("instrument", r"\b(gauge|gage|transmitter|indicator)\b"),
    ("electrical", r"\b(motor|mtr|cable|starter|transformer)\b"),
)

_PATTERNS = {
    "iso_designation":  r"\b(6[0-3]\d{2}|2[23]\d{3})\b",
    "nominal_size_in":  r'(\d+(?:\.\d+)?)\s*(?:in\b|inch|")',
    "schedule":         r"sch(?:edule)?[\s-]*(\d{1,3}s?)",
    "pressure_class":   r"\b(\d{3,4})\s*#",
    # Austenitic stainless is a NUMBERED FAMILY - 304, 316, 321, 347, 310 -
    # not a list of two. Hardcoding 316 and 304 meant SS321 extracted as
    # nothing at all, so the grade veto could not fire on a grade we had
    # simply never listed, and a 321 gasket scored as a possible match
    # against a 304 one. An unlisted grade must still block.
    "material_grade":   r"\b(s\.?\s?s\.?\s*\d{3}\s*l?|carbon\s*steel|c\.?s\.?|"
                        r"mild\s*steel|m\.?s\.?|cast\s*steel|a\s*105|a193\s*b7)\b",
    "seal_type":        r"\b(2rsr?1?|2z|zz|llu|rs)\b",
    "thread":           r"\b(m\d{1,2})\s*[x×]",
    "length_mm":        r"m\d{1,2}\s*[x×]\s*(\d{1,3})\b",
    "power_hp":         r"(\d+(?:\.\d+)?)\s*hp\b",
    "speed_rpm":        r"(\d{3,4})\s*rpm\b",
    "voltage_v":        r"(\d{3,4})\s*v\b",
    "dial_size_mm":     r"(\d{2,3})\s*mm\s*dial",
    "phases":           r"\b(3)\s*[- ]?\s*(?:ph|phase)\b",
    # An instrument was reachable by dial size alone - one field, below the
    # creation gate's floor, so a fully specified gauge read as "not enough
    # information". Type, wetted material and range are what actually separate
    # two instruments, and range_max is a veto field: a 0-16 bar gauge fitted
    # where a 0-10 bar one belongs reads wrong for the whole of its life.
    "instrument_type":  r"\b(pressure\s*gauge|temperature\s*gauge|temp\s*gauge|"
                        r"pressure\s*transmitter|level\s*transmitter|flow\s*meter|"
                        r"thermometer|thermocouple|rtd)\b",
    "wetted_material":  r"\b(s\.?\s?s\.?\s*\d{3}\s*l?|monel|hastelloy|inconel|"
                        r"carbon\s*steel|c\.?s\.?)\b",
    "connection":       r"(\d/\d\s*(?:in\b|inch|\")?\s*npt(?:\s*(?:bottom|back|side))?)",
}

_DIMS = re.compile(r"(\d{1,4})\s*[x*×]\s*(\d{1,4})\s*[x*×]\s*(\d{1,4})")

# "0-16 BAR", "0 TO 160 KG/CM2". Two numbers and a unit in one shape, which is
# why it cannot live in _PATTERNS - that captures a single group per field.
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*"
                    r"(bar|psi|kpa|mpa|kg/cm2|deg\s*c|degc)\b")


def regex_extract(description: str) -> dict:
    """Best-effort extraction with no model call. Confidence is deliberately low."""
    text = description.lower()

    category = "unknown"
    for name, pattern in _CATEGORY_HINTS:
        if re.search(pattern, text):
            category = name
            break

    attrs, conf = {}, {}
    valid = {f.name for f in fields_for(category)}

    for name, pattern in _PATTERNS.items():
        if name not in valid:
            continue
        m = re.search(pattern, text)
        if not m:
            continue
        raw = m.group(1)
        spec = next(f for f in fields_for(category) if f.name == name)
        if spec.kind == "num":
            attrs[name] = float(raw)
        else:
            value = canonical_value(name, raw)
            # Enum values are written with underscores everywhere else
            # (SPIRAL_WOUND, DEEP_GROOVE_BALL), so "pressure gauge" read out of
            # free text has to arrive in that shape or it compares unequal to
            # the identical value the model extracted.
            if spec.kind == "enum" and isinstance(value, str):
                value = re.sub(r"\s+", "_", value.strip())
            attrs[name] = value
        conf[name] = 0.62

    dims = _DIMS.search(text)
    if dims and category == "bearing":
        for name, value in zip(("bore_mm", "od_mm", "width_mm"), dims.groups()):
            attrs.setdefault(name, float(value))
            conf.setdefault(name, 0.62)

    span = _RANGE.search(text)
    if span and "range_min" in valid:
        lo, hi, unit = span.groups()
        attrs.setdefault("range_min", float(lo))
        attrs.setdefault("range_max", float(hi))
        attrs.setdefault("range_unit", re.sub(r"\s+", "", unit).upper())
        for name in ("range_min", "range_max", "range_unit"):
            conf.setdefault(name, 0.62)

    return {"category": category, "attributes": attrs,
            "confidence": conf, "method": "regex"}


if __name__ == "__main__":
    for sample in ("SKF 6205-2RS DEEP GROOVE BALL BEARING",
                   "GASKET SPIRAL WOUND SS316 4IN 150#",
                   "PIPE SMLS C.S. ASTM A106 GR B 4\" SCH40",
                   "BOLT HEX HD M12 X 50 SS316"):
        out = regex_extract(sample)
        print(f"{sample}\n  -> {out['category']}: {out['attributes']}\n")
