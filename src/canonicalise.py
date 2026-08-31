"""
Canonicaliser - golden record, standard description, UNSPSC, national code.

Takes approved clusters and produces the actual deliverable: one national code
per unique item, with a mapping row back to every CPSE's original code.

    python src/canonicalise.py

FOUR OUTPUTS PER CLUSTER

    golden record         best value per field, taken across all members
    standard description  noun-modifier format, the way industry writes it
    UNSPSC class          the international standard, not a taxonomy we invented
    national code         NMC-<unspsc>-<serial>, with the class embedded

NOBODY CHANGES THEIR CODE. The national code sits above the existing codes and
links them - the way Aadhaar and UPI added a layer without replacing what was
underneath. CPCL's storekeeper keeps typing 100001445 forever.
See docs/02-decisions/010-append-only-reversible.md
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict

import paths
import schemas

# ---------------------------------------------------------------------------
# UNSPSC classification.
#
# We use the international standard rather than inventing a taxonomy - a
# national system must not ask every CPSE to adopt a scheme six students made
# up. Only the classes our categories touch, not the full taxonomy.
#
# Every code below was checked against the published UNSPSC class listing on
# 31 Aug 2026. Four of the original guesses were wrong and are corrected here:
#
#   fastener  31161500 -> 31161600   31161500 is Screws, not Bolts
#   flange    40171600 -> 40175000   40171600 is Industrial pipe and piping;
#                                    our flanges are weld neck
#   rotating  31401600 -> 31411700   31401600 is Die cut gaskets, not Seals
#   pipe      40171500 -> 40171600   a refinery line is industrial, not
#                                    commercial pipe
#
# GASKETS ARE CLASSIFIED AT FAMILY LEVEL, DELIBERATELY. Family 31400000
# divides gaskets by manufacturing method - molded, die cut, stamped, water
# jet cut, liquid - and spiral wound has no class at all. Forcing a spiral
# wound gasket into "molded gaskets" would be a wrong classification printed
# inside every national code we issue, so we stop at the family.
#
# The class is embedded in each national code, so an error here is visible on
# every output row. Recorded in docs/03-reference/domain-facts.md
# ---------------------------------------------------------------------------

UNSPSC = {
    "bearing":    ("31171500", "Bearings"),
    "gasket":     ("31400000", "Gaskets"),          # family - no spiral wound class
    "pipe":       ("40171600", "Industrial pipe and piping"),
    "valve":      ("40141600", "Valves"),
    "fastener":   ("31161600", "Bolts"),
    "flange":     ("40175000", "Pipe weldneck flanges"),
    "rotating":   ("31411700", "Mechanical seals"),
    "instrument": ("41111900", "Indicating and recording instruments"),
    "electrical": ("26101100", "Electric alternating current AC motors"),
    "unknown":    ("00000000", "Unclassified"),
}

# ---------------------------------------------------------------------------
# Standard description.
#
# Noun first, then modifiers in significance order. This is the format industry
# actually uses, and the PS lists "automated standardization of material
# descriptions" as its own deliverable - not a footnote of this module.
#
# Once specs are typed this is a template render, which is exactly why it makes
# the extraction work visible:
#
#   BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED
#   PIPE, SEAMLESS, CARBON STEEL, ASTM A106 GR B, 4 IN, SCH 40
# ---------------------------------------------------------------------------

NOUNS = {
    "bearing": "BEARING", "gasket": "GASKET", "pipe": "PIPE", "valve": "VALVE",
    "fastener": "FASTENER", "flange": "FLANGE", "rotating": "COMPONENT",
    "instrument": "INSTRUMENT", "electrical": "EQUIPMENT",
}


def _n(value) -> str:
    """Numbers without a trailing .0 - 25.0 reads as 25 in a description."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _clean(text) -> str:
    return str(text).replace("_", " ").upper().strip()


# For these categories the schema's type field IS the noun. "FASTENER, BOLT"
# and "EQUIPMENT, MOTOR" read like placeholders; "BOLT" and "MOTOR" read like a
# catalogue. Industry writes the specific noun first.
NOUN_FROM_FIELD = {
    "fastener": "fastener_type",
    "electrical": "equipment_type",
    "rotating": "component_type",
    "valve": None,          # noun stays VALVE, type is the first modifier
}

# A model that returns "none" for an absent option is stating absence, not a
# value. It must never reach a printed description.
_EMPTY = {"", "-", "NONE", "N/A", "NA", "UNKNOWN", "NULL"}


def standard_description(category: str, attrs: dict) -> str:
    """Render the golden record as a noun-modifier description."""
    a = attrs
    parts: list[str] = []

    def add(*values):
        for v in values:
            if v is None:
                continue
            text = _clean(v)
            if text not in _EMPTY:
                parts.append(text)

    if category == "bearing":
        add(a.get("sub_type"), a.get("iso_designation"))
        if all(a.get(k) is not None for k in ("bore_mm", "od_mm", "width_mm")):
            parts.append(f"{_n(a['bore_mm'])}X{_n(a['od_mm'])}X{_n(a['width_mm'])} MM")
        if a.get("seal_type"):
            parts.append(f"{_clean(a['seal_type'])} SEALED")

    elif category == "gasket":
        add(a.get("gasket_type"), a.get("material_grade"))
        if a.get("nominal_size_in"):
            parts.append(f"{_n(a['nominal_size_in'])} IN")
        add(a.get("pressure_class"), a.get("filler"))

    elif category == "pipe":
        add(a.get("construction"), a.get("material_grade"), a.get("standard"))
        if a.get("nominal_size_in"):
            parts.append(f"{_n(a['nominal_size_in'])} IN")
        add(a.get("schedule"))

    elif category == "valve":
        add(a.get("valve_type"))
        if a.get("nominal_size_in"):
            parts.append(f"{_n(a['nominal_size_in'])} IN")
        add(a.get("pressure_class"), a.get("body_material"),
            a.get("end_connection"), a.get("standard"))

    elif category == "fastener":
        add(a.get("head_type"))
        if a.get("thread") and a.get("length_mm"):
            parts.append(f"{_clean(a['thread'])} X {_n(a['length_mm'])}")
        elif a.get("thread"):
            parts.append(_clean(a["thread"]))
        add(a.get("material_grade"), a.get("standard"))

    elif category == "flange":
        add(a.get("flange_type"), a.get("face_type"))
        if a.get("nominal_size_in"):
            parts.append(f"{_n(a['nominal_size_in'])} IN")
        add(a.get("pressure_class"), a.get("material_grade"))

    elif category == "rotating":
        add(a.get("arrangement"))
        if a.get("shaft_dia_mm"):
            parts.append(f"{_n(a['shaft_dia_mm'])} MM SHAFT")
        add(a.get("face_materials"), a.get("elastomer"))

    elif category == "instrument":
        add(a.get("instrument_type"))
        if a.get("dial_size_mm"):
            parts.append(f"{_n(a['dial_size_mm'])} MM DIAL")
        if a.get("range_min") is not None and a.get("range_max") is not None:
            unit = _clean(a.get("range_unit") or "")
            parts.append(f"{_n(a['range_min'])}-{_n(a['range_max'])} {unit}".strip())
        add(a.get("wetted_material"), a.get("connection"))

    elif category == "electrical":
        if a.get("phases"):
            parts.append(f"{_n(a['phases'])} PHASE")
        if a.get("power_hp"):
            parts.append(f"{_n(a['power_hp'])} HP")
        if a.get("speed_rpm"):
            parts.append(f"{_n(a['speed_rpm'])} RPM")
        add(a.get("mounting"), a.get("voltage_v") and f"{_n(a['voltage_v'])} V",
            a.get("protection_class"))

    else:
        add(a.get("noun"))

    # Prefer the specific noun the specs give us over the generic category name.
    noun_field = NOUN_FROM_FIELD.get(category)
    noun = None
    if noun_field and a.get(noun_field):
        candidate = _clean(a[noun_field])
        if candidate not in _EMPTY:
            noun = candidate
    noun = noun or NOUNS.get(category, "MATERIAL")

    return ", ".join([noun] + [p for p in parts if p])


# ---------------------------------------------------------------------------
# Golden record
# ---------------------------------------------------------------------------

def golden_record(members: list[str], specs: dict) -> tuple[str, dict, dict]:
    """Best value per field across a cluster.

    Values are voted on with confidence as the weight, so a field read straight
    out of the text outvotes one derived from a standard designation, which in
    turn outvotes a weak inference.

    Also returns, per field, how much of the cluster agreed - the review screen
    shows this so a human can see where members disagreed.
    """
    categories = defaultdict(float)
    for rid in members:
        s = specs[rid]
        categories[s["category"]] += 1
    category = max(categories, key=categories.get)

    votes: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    seen: dict[str, int] = defaultdict(int)

    for rid in members:
        s = specs[rid]
        if s["category"] != category:
            continue
        for name, value in s["attributes"].items():
            key = json.dumps(value, sort_keys=True)
            votes[name][key] += float(s.get("confidence", {}).get(name, 0.8))
            seen[name] += 1

    attrs, agreement = {}, {}
    for name, options in votes.items():
        best = max(options, key=options.get)
        attrs[name] = json.loads(best)
        agreement[name] = round(options[best] / sum(options.values()), 2)

    return category, attrs, agreement


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prefix", default="NMC", help="national code prefix")
    args = ap.parse_args()

    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))
    clusters = json.loads(paths.CLUSTERS.read_text(encoding="utf-8"))

    materials = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            materials[row["record_id"]] = row

    serial = defaultdict(int)
    national, mappings = [], []

    # Largest clusters first, so the lowest serial numbers land on the items
    # that matter most. Cosmetic, but it makes the demo output read better.
    for cluster in sorted(clusters, key=lambda c: -len(c["members"])):
        members = [m for m in cluster["members"] if m in specs]
        if not members:
            continue

        category, attrs, agreement = golden_record(members, specs)
        unspsc, unspsc_name = UNSPSC.get(category, UNSPSC["unknown"])
        serial[unspsc] += 1
        code = f"{args.prefix}-{unspsc}-{serial[unspsc]:06d}"

        cpses = sorted({materials[m]["cpse"] for m in members if m in materials})

        national.append({
            "national_code": code,
            "category": category,
            "unspsc": unspsc,
            "unspsc_name": unspsc_name,
            "std_description": standard_description(category, attrs),
            "attributes": attrs,
            "field_agreement": agreement,
            "confidence": cluster.get("confidence"),
            "band": cluster.get("band"),
            "member_count": len(members),
            "cpse_count": len(cpses),
            "cpses": cpses,
            "members": [
                {"record_id": m,
                 "cpse": materials.get(m, {}).get("cpse"),
                 "source_code": materials.get(m, {}).get("source_code"),
                 "description": materials.get(m, {}).get("description"),
                 "uom": materials.get(m, {}).get("uom")}
                for m in members],
        })

        for m in members:
            row = materials.get(m, {})
            mappings.append({
                "national_code": code,
                "cpse": row.get("cpse", ""),
                "source_code": row.get("source_code", ""),
                "original_description": row.get("description", ""),
                "original_uom": row.get("uom", ""),
                # Nothing is destroyed. The original code stays active and in
                # use; the national code is an additional layer above it.
                "status": "active",
                "band": cluster.get("band", ""),
            })

    paths.ensure_dirs()
    paths.NATIONAL_CODES.write_text(json.dumps(national, indent=1), encoding="utf-8")
    with paths.MAPPINGS.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(mappings[0].keys()))
        writer.writeheader()
        writer.writerows(mappings)

    raw = len(materials)
    unique = len(national)
    multi_cpse = [n for n in national if n["cpse_count"] > 1]

    print(f"national codes    {unique:>5}")
    print(f"mapping rows      {len(mappings):>5}")
    print(f"\nRATIONALISATION")
    print(f"  {raw} raw codes -> {unique} unique materials")
    print(f"  {raw - unique} redundant codes ({1 - unique/raw:.1%} duplication)")
    print(f"  {len(multi_cpse)} materials bought by 2+ CPSEs "
          f"<- these are the demand-aggregation candidates")

    print("\nstandard descriptions, largest clusters first")
    print("-" * 74)
    for n in national[:8]:
        print(f"  {n['national_code']}  x{n['member_count']:<2} {len(n['cpses'])} CPSE")
        print(f"    {n['std_description']}")


if __name__ == "__main__":
    main()
