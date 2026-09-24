"""
Hard negatives - the safety contract of the scorer, tested exhaustively.

    PROPERTY     for every category and every veto field: two records that
                 are identical except for that one field never reach
                 AUTO_MERGE, and the block names that field. Identical text
                 on both sides, so text similarity is as high as it can be -
                 the veto has to win against the strongest pull there is.
    MISSING      a required veto field silent on one side keeps the pair
                 below auto (the "unverified" cap).
    BRAND        brand and part number never change a score.
    DETERMINISM  two scorer runs give byte-identical output.
    DEMO         the two cases the demo depends on.

From now on no scorer, schema or standards change is merged unless this
suite passes: python -m pytest tests/
"""

import hashlib
import subprocess
import sys

import pytest

import paths
import schemas
import scorer

# A fully specified record per category - every field the schema has.
FULL = {
    "bearing":    {"sub_type": "deep_groove_ball", "iso_designation": "6205", "bore_mm": 25.0,
                   "od_mm": 52.0, "width_mm": 15.0, "seal_type": "2RS"},
    "gasket":     {"gasket_type": "spiral_wound", "material_grade": "SS316", "nominal_size_in": 4.0,
                   "pressure_class": "150#", "filler": "GRAPHITE", "thickness_mm": 4.5},
    "pipe":       {"construction": "seamless", "material_grade": "A106 GR B", "standard": "ASTM A106",
                   "nominal_size_in": 4.0, "od_mm": 114.3, "schedule": "SCH 40", "wall_mm": 6.02,
                   "finish": "black", "end_type": "bevel", "weight_ppf": 10.79},
    "valve":      {"valve_type": "gate", "nominal_size_in": 6.0, "pressure_class": "150#",
                   "pressure_rating_psi": 285.0, "body_material": "A216 WCB", "operation": "manual",
                   "end_connection": "flanged", "bore_type": "full", "standard": "API 600"},
    "fastener":   {"fastener_type": "bolt", "head_type": "hex", "thread": "M12", "length_mm": 50.0,
                   "material_grade": "SS316", "standard": "IS 1364"},
    "flange":     {"flange_type": "weld_neck", "face_type": "raised_face", "nominal_size_in": 4.0,
                   "pressure_class": "300#", "pressure_rating_psi": 740.0,
                   "material_grade": "ASTM_A105", "bore_schedule": "SCH 40", "standard": "ASME B16.5"},
    "rotating":   {"component_type": "mechanical_seal", "arrangement": "single", "shaft_dia_mm": 45.0,
                   "face_materials": "SIC VS CARBON", "elastomer": "VITON"},
    "instrument": {"instrument_type": "pressure_gauge", "dial_size_mm": 100.0, "range_min": 0.0,
                   "range_max": 16.0, "range_unit": "BAR", "wetted_material": "SS316",
                   "connection": "1/2 IN NPT BOTTOM"},
    "electrical": {"equipment_type": "motor", "phases": 3.0, "power_hp": 10.0, "speed_rpm": 1440.0,
                   "poles": 4.0, "voltage_v": 415.0, "frame": "132M", "mounting": "foot",
                   "duty": "S1", "insulation_class": "F", "protection_class": "IP55",
                   "rating_kva": 100.0, "voltage_hv_kv": 11.0},
    "cable":      {"cable_type": "power", "cores": 3.5, "cross_section_mm2": 240.0, "conductor": "AL",
                   "voltage_kv": 1.1, "insulation": "XLPE", "armour": "armoured", "standard": "IS 7098"},
    "fitting":    {"fitting_type": "elbow", "nominal_size_in": 2.0, "material_grade": "ASTM_A105",
                   "angle": 90.0, "schedule": "SCH 80", "pressure_class": "3000#",
                   "end_connection": "socket_weld", "radius": "LR", "standard": "ASME B16.11"},
    "plate":      {"material_grade": "IS2062 E250A", "thickness_mm": 10.0, "plate_type": "plain",
                   "width_mm": 1500.0, "length_mm": 6000.0, "standard": "IS 2062"},
    "tube":       {"material_grade": "A213 T91", "od_mm": 54.0, "wall_mm": 4.0, "tube_type": "boiler"},
    "other":      {"noun": "BATTERY", "quantities": "220V 400AH", "standard": "IS 1651"},
}

# The value one field changes to. Every change is to a VALID, plausible
# neighbour - the near-miss a real catalogue contains, not noise.
ALT = {
    "iso_designation": "6206", "bore_mm": 30.0, "material_grade": "SS304",
    "nominal_size_in": 6.0, "pressure_class": "600#", "construction": "erw",
    "od_mm": 168.3, "schedule": "SCH 80", "wall_mm": 8.56, "finish": "galvanised",
    "valve_type": "globe", "pressure_rating_psi": 5000.0, "body_material": "SS316",
    "fastener_type": "stud_bolt", "thread": "M16", "length_mm": 60.0,
    "flange_type": "slip_on", "component_type": "impeller", "shaft_dia_mm": 50.0,
    "instrument_type": "temperature_gauge", "range_min": 1.0, "range_max": 25.0,
    "wetted_material": "MONEL", "equipment_type": "starter", "phases": 1.0,
    "power_hp": 15.0, "speed_rpm": 2880.0, "poles": 2.0, "voltage_v": 230.0,
    "frame": "160M", "rating_kva": 250.0, "voltage_hv_kv": 33.0,
    "cable_type": "control", "cores": 4.0, "cross_section_mm2": 300.0, "conductor": "CU",
    "voltage_kv": 11.0, "fitting_type": "tee", "angle": 45.0, "thickness_mm": 12.0,
    "plate_type": "chequered", "noun": "INSULATOR", "quantities": "110V 400AH",
    # Variant fields - veto-only since the 15,000-record run.
    "sub_type": "angular_contact", "seal_type": "2Z", "gasket_type": "ring_joint", "filler": "PTFE",
    "end_type": "plain", "operation": "gear", "end_connection": "butt_weld", "bore_type": "reduced",
    "head_type": "socket", "face_type": "ring_joint", "bore_schedule": "SCH 80",
    "arrangement": "double", "elastomer": "EPDM", "dial_size_mm": 150.0, "mounting": "flange",
    "insulation": "PVC", "armour": "unarmoured", "radius": "SR", "connection": "1/4 IN NPT BACK",
    "face_materials": "TC VS SIC",
}
# Where a changed grade must stay in the same family for the test to mean
# anything (a tube's alloy against another alloy, not against stainless).
ALT_BY_CATEGORY = {("tube", "material_grade"): "A213 T23", ("plate", "material_grade"): "IS2062 E350",
                   ("pipe", "material_grade"): "API 5L GR B", ("valve", "nominal_size_in"): 8.0,
                   ("fitting", "schedule"): "SCH 160"}

# A motor's speed and pole count are two readings of one fact; so are an OD
# and a size. Change one and the other must follow, or the test would be
# checking a record that contradicts itself.
COUPLED = {("electrical", "speed_rpm"): {"poles": 2.0}, ("electrical", "poles"): {"speed_rpm": 2880.0},
           ("pipe", "nominal_size_in"): {"od_mm": 168.3}, ("pipe", "od_mm"): {"nominal_size_in": 6.0}}


def record(rid, category, attrs):
    return {"record_id": rid, "category": category, "attributes": dict(attrs),
            "confidence": {k: 0.95 for k in attrs}, "cpse": "CPCL", "source_code": rid}


def score(a, b):
    text = "IDENTICAL DESCRIPTION ON BOTH SIDES"
    return scorer.score_pair(a, b, {a["record_id"]: text, b["record_id"]: text}, None, {})


VETO_CASES = [(cat, f) for cat in FULL for f in schemas.hard_fields(cat) if f in FULL[cat]]


@pytest.mark.parametrize("category,field", VETO_CASES)
def test_one_changed_veto_field_blocks(category, field):
    base = FULL[category]
    changed = dict(base)
    changed[field] = ALT_BY_CATEGORY.get((category, field), ALT[field])
    changed.update(COUPLED.get((category, field), {}))
    assert changed[field] != base[field]
    p = score(record("A", category, base), record("B", category, changed))
    assert p["final"] < scorer.AUTO_MERGE, f"{category}.{field} changed and still auto-merged"
    assert p["blocked_by"] in {field, *COUPLED.get((category, field), {})}, (
        f"{category}.{field}: blocked_by={p['blocked_by']} reason={p.get('reason')}")


def test_every_category_is_covered():
    missing = {c for c in schemas.CATEGORIES if c != "unknown"} - set(FULL)
    assert not missing, f"no hard-negative case for {missing}"
    for cat, attrs in FULL.items():
        absent = set(schemas.hard_fields(cat)) - set(attrs)
        assert not absent, f"{cat}: FULL record lacks veto fields {absent}"


@pytest.mark.parametrize("category", sorted(FULL))
def test_identical_records_match(category):
    """The positive control: without it, 'never auto-merges' could pass by
    never merging anything."""
    p = score(record("A", category, FULL[category]), record("B", category, FULL[category]))
    if category in scorer.NO_AUTO_CATEGORIES:
        assert scorer.REVIEW_LOW <= p["final"] < scorer.AUTO_MERGE
    else:
        assert p["final"] >= scorer.AUTO_MERGE and not p["blocked_by"]


REQUIRED = [(cat, f) for cat in FULL for f in schemas.required_hard_fields(cat)]


@pytest.mark.parametrize("category,field", REQUIRED)
def test_missing_required_veto_field_caps_below_auto(category, field):
    sparse = {k: v for k, v in FULL[category].items() if k != field}
    # Remove its alternatives too, and what derives them - a stated weight
    # and OD rebuild the wall, which genuinely verifies a missing schedule.
    alts = next(f.alt for f in schemas.fields_for(category) if f.name == field)
    derives = {"wall_mm": ("weight_ppf",), "od_mm": (), "poles": ("speed_rpm",),
               "bore_mm": ("iso_designation",)}          # ISO 15 gives a bearing's bore
    gone = set(alts) | {d for a in (*alts, field) for d in derives.get(a, ())}
    sparse = {k: v for k, v in sparse.items() if k not in gone}
    p = score(record("A", category, FULL[category]), record("B", category, sparse))
    assert p["final"] < scorer.AUTO_MERGE, f"{category} without {field} auto-merged"


@pytest.mark.parametrize("category", sorted(FULL))
def test_brand_and_part_number_never_count(category):
    a = record("A", category, {**FULL[category], "brand": "SKF", "part_number": "6205-2RS"})
    b = record("B", category, {**FULL[category], "brand": "FAG", "part_number": "6205-2RSR"})
    c = record("C", category, {**FULL[category], "brand": "SKF", "part_number": "6205-2RS"})
    assert score(a, b)["final"] == score(a, c)["final"]


def test_grade_ladder():
    """Family only against a specific grade is a doubt, not a match or a veto."""
    a = record("A", "pipe", {**FULL["pipe"], "material_grade": "CARBON_STEEL"})
    b = record("B", "pipe", FULL["pipe"])                          # A106 GR B, carbon steel
    p = score(a, b)
    assert not p["blocked_by"] and p["final"] < scorer.AUTO_MERGE
    c = record("C", "pipe", {**FULL["pipe"], "material_grade": "SS316"})
    assert score(a, c)["blocked_by"] == "material_grade"          # different family: veto


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_scorer_is_deterministic():
    runs = []
    for _ in range(2):
        subprocess.run([sys.executable, str(paths.SRC / "scorer.py")], check=True,
                       capture_output=True, cwd=paths.ROOT)
        runs.append((_digest(paths.PAIR_SCORES), _digest(paths.CLUSTERS)))
    assert runs[0] == runs[1]


def test_demo_cases():
    specs, descriptions = scorer.load_inputs()
    vecs, profiles = scorer.load_vectors(), scorer.build_purchase_profiles()
    match = scorer.score_pair(specs["R00001"], specs["R00002"], descriptions, vecs, profiles)
    assert match["final"] >= scorer.AUTO_MERGE and not match["blocked_by"]
    block = scorer.score_pair(specs["R00003"], specs["R00004"], descriptions, vecs, profiles)
    assert block["blocked_by"] == "material_grade"
