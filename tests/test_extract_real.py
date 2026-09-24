"""
Real text in, correct facts out - 40 dev lines, expectations written by hand.

Each expectation was checked against the standard it rests on (ASME B36.10M
for pipe ODs, API 5CT for casing, API 6A for valve bores, IEC for motor
frames), not copied from the extractor's output. Only the fields listed are
checked; the extractor may read more.

Dev rows only - conftest refuses a test row.
"""

import pytest

import schemas

CASES = {
    # --- pipe: size name vs measurement
    1:   ("pipe", {"nominal_size_in": 4.0, "od_mm": 114.3, "wall_mm": 6.0, "construction": "erw",
                   "end_type": "threaded_coupled", "material_grade": "API 5L GR A"}),
    2:   ("pipe", {"nominal_size_in": 18.0, "od_mm": 457.0, "wall_mm": 9.5, "material_grade": "FE410",
                   "finish": "black"}),
    3:   ("pipe", {"nominal_size_in": 20.0, "od_mm": 508.0, "wall_mm": 9.5}),
    15:  ("pipe", {"nominal_size_in": 18.0, "od_mm": 457.0}),          # no NB: size from the OD
    8:   ("pipe", {"nominal_size_in": 0.75, "material_grade": "SS304L", "schedule": "SCH 80",
                   "construction": "seamless"}),                         # 20MM with a schedule is DN 20
    22:  ("pipe", {"nominal_size_in": 1.5, "wall_mm": 2.0, "material_grade": "A423 GR1",
                   "construction": "erw"}),
    28:  ("pipe", {"nominal_size_in": 5.0, "od_mm": 141.3, "wall_mm": 9.53}),
    34:  ("pipe", {"nominal_size_in": 6.0, "od_mm": 168.3}),            # 6-5/8" is the OD again
    40:  ("pipe", {"nominal_size_in": 1.0, "schedule": "SCH 80S", "material_grade": "SS304L"}),
    86:  ("pipe", {"nominal_size_in": 5.0, "finish": "galvanised", "end_type": "plain",
                   "standard": "IS 1239-1"}),
    104: ("pipe", {"nominal_size_in": 12.0, "od_mm": 323.9, "wall_mm": 12.7}),   # 12.7 here is a wall
    109: ("pipe", {"nominal_size_in": 10.0, "od_mm": 273.1, "material_grade": "API 5L X46"}),
    150: ("pipe", {"nominal_size_in": 13.375, "od_mm": 339.72, "material_grade": "N80",
                   "standard": "API 5CT"}),
    160: ("pipe", {"nominal_size_in": 5.5, "material_grade": "P110"}),
    # 101.6 mm is both the OD of 3-1/2" and 4" x 25.4. 12.66 lb/ft is a
    # standard 4" wall (0.281 in) and no 3-1/2" wall - so this is a 4" pipe.
    162: ("pipe", {"nominal_size_in": 4.0, "wall_mm": 7.14, "weight_ppf": 12.66}),
    163: ("pipe", {"nominal_size_in": 4.0, "wall_mm": 11.13}),
    173: ("pipe", {"nominal_size_in": 20.0, "wall_mm": 26.35, "material_grade": "FE410"}),
    257: ("pipe", {"nominal_size_in": 9.625, "od_mm": 244.475, "material_grade": "P110"}),
    337: ("pipe", {"nominal_size_in": 0.5}),                          # alone, 12.7 mm is 1/2" x 25.4
    338: ("pipe", {"nominal_size_in": 6.0, "construction": "erw", "end_type": "bevel"}),
    379: ("pipe", {"nominal_size_in": 9.625, "material_grade": "N80"}),

    # --- valves
    14:  ("valve", {"valve_type": "gate", "nominal_size_in": 2.0, "pressure_class": "900#",
                    "operation": "manual"}),
    116: ("valve", {"valve_type": "plug", "nominal_size_in": 4.0, "pressure_class": "900#",
                    "standard": "API 6D"}),
    174: ("valve", {"valve_type": "gate", "nominal_size_in": 2.0625, "pressure_rating_psi": 5000.0}),
    233: ("valve", {"nominal_size_in": 3.0625, "pressure_rating_psi": 10000.0}),
    363: ("valve", {"nominal_size_in": 7.0625, "pressure_rating_psi": 10000.0}),   # 10M = 10,000 psi
    421: ("valve", {"pressure_rating_psi": 5000.0}),                  # 352 kg/cm2 = 5,000 psi
    550: ("valve", {"nominal_size_in": 2.0625}),                      # 52.38 mm = 2-1/16" API 6A bore
    582: ("valve", {"valve_type": "gate", "nominal_size_in": 8.0, "pressure_class": "600#"}),
    657: ("valve", {"valve_type": "plug", "nominal_size_in": 4.0, "pressure_class": "900#"}),

    # --- flanges, fittings
    83:  ("flange", {"flange_type": "slip_on", "nominal_size_in": 1.0, "pressure_class": "150#",
                     "standard": "ASME B16.5"}),
    234: ("flange", {"flange_type": "weld_neck", "face_type": "ring_joint", "nominal_size_in": 4.0,
                     "pressure_class": "900#", "material_grade": "ASTM_A105"}),
    18:  ("fitting", {"fitting_type": "elbow", "angle": 90.0, "pressure_class": "3000#",
                      "material_grade": "ASTM_A105"}),

    # --- cable, tube, plate
    19:  ("cable", {"cable_type": "power", "cores": 1.0, "cross_section_mm2": 150.0,
                    "conductor": "AL", "voltage_kv": 11.0}),
    82:  ("cable", {"cores": 3.0, "cross_section_mm2": 120.0, "voltage_kv": 3.3}),
    356: ("cable", {"cores": 3.5, "cross_section_mm2": 70.0, "conductor": "CU", "voltage_kv": 0.66,
                    "insulation": "EPR"}),
    38:  ("tube", {"material_grade": "A213 T23", "od_mm": 38.1, "wall_mm": 11.0}),
    155: ("tube", {"tube_type": "boiler", "od_mm": 50.8, "wall_mm": 4.06}),
    29:  ("plate", {"plate_type": "chequered", "thickness_mm": 6.0, "material_grade": "IS2062 A"}),

    # --- motors and transformers
    10:  ("electrical", {"equipment_type": "motor", "frame": "315SM", "mounting": "foot_flange",
                         "speed_rpm": 2980.0, "poles": 2.0, "power_kw": 132.0}),
    23:  ("electrical", {"equipment_type": "motor", "frame": "80L", "poles": 4.0, "duty": "S4",
                         "mounting": "flange", "voltage_v": 415.0}),
    177: ("electrical", {"equipment_type": "transformer", "rating_kva": 800.0, "voltage_hv_kv": 3.3}),
    247: ("electrical", {"equipment_type": "transformer", "rating_kva": 2000.0, "voltage_hv_kv": 11.0}),
    477: ("electrical", {"equipment_type": "starter", "power_hp": 5.0}),

    # --- outside every schema
    123: ("other", {}),                                               # switchgear gasket, kV + amps
    371: ("other", {"noun": "BATTERY", "quantities": "220V 400AH"}),
}


@pytest.mark.parametrize("row", sorted(CASES))
def test_reads_real_line(dev, row):
    category, expected = CASES[row]
    out = schemas.regex_extract(dev(row)["description"])
    assert out["category"] == category, dev(row)["description"]
    wrong = {k: (out["attributes"].get(k), v) for k, v in expected.items()
             if out["attributes"].get(k) != v}
    assert not wrong, f"{dev(row)['description']}\n  got / want: {wrong}"


def test_evidence_points_at_the_original_text(dev):
    """Every read value keeps the span it came from, in the ORIGINAL text."""
    text = dev(2)["description"]
    out = schemas.regex_extract(text)
    a, b = out["evidence"]["od_mm"]
    assert text[a:b] == "457"
    a, b = out["evidence"]["material_grade"]
    assert "FE410" in text[a:b].upper()


def test_synthetic_demo_lines_still_read():
    out = schemas.regex_extract("SKF 6205-2RS DEEP GROOVE BALL BEARING")
    assert out["category"] == "bearing" and out["attributes"]["iso_designation"] == "6205"
    out = schemas.regex_extract("GASKET SPIRAL WOUND SS316 4IN 150#")
    assert out["attributes"] == {**out["attributes"], "material_grade": "SS316",
                                 "nominal_size_in": 4.0, "pressure_class": "150#"}
