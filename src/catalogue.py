"""
Item factory - thousands of VALID refinery items, built from standard tables.

The 100-record demo set has 15 hand-written items. 15,000 records at 20%
duplication needs about 12,000 distinct items, and they have to be real: a
6205 bearing is 25 x 52 x 15 mm (ISO 15), a 4" pipe is 114.3 mm OD and a
SCH 40 wall of 6.02 mm (ASME B36.10M), a 30 kW 4-pole motor sits in a 200L
frame (IEC 60072). An item a refinery storekeeper would not recognise makes
every number measured on it worthless.

Each item is a spec dict in the SAME canonical form the extractor produces,
so the truth can be compared field by field with what was read.

    family_id   all fields except the size (and, for a bearing, the
                designation). Two sizes of one pipe are one family. The
                locked test split is drawn by family, so a test record is
                never just a resized dev record.

Validity rules keep the grid honest: IS 1239 pipe is ERW; stainless is never
galvanised; small valves are forged and screwed or socket-welded, large ones
cast and flanged; a ring-joint face only from class 600; control cable is
copper; high-voltage motors only from 110 kW.

    python src/catalogue.py            prints the size of the universe
"""

from __future__ import annotations

import hashlib
import random
from itertools import product

import normalise as nz

# --------------------------------------------------------------------------
# Standard tables
# --------------------------------------------------------------------------

# The standard tables live in standards.py - the factory and derive() share them.
from standards import ISO15, WALL, IEC_FRAME, RPM, PIPE_NPS, SMALL, LARGE, CLASSES  # noqa: E402

# --------------------------------------------------------------------------
# The universe - every valid item, per category
# --------------------------------------------------------------------------

def bearings():
    for des, (bore, od, width) in ISO15.items():
        for seal in ("OPEN", "Z", "2Z", "RS", "2RS"):
            yield {"sub_type": "deep_groove_ball", "iso_designation": des, "bore_mm": float(bore),
                   "od_mm": float(od), "width_mm": float(width), "seal_type": seal}


def pipes():
    cs = (("A106 GR B", "seamless", "ASTM A106"), ("API 5L GR B", "seamless", "API 5L"),
          ("API 5L GR B", "erw", "API 5L"), ("A53 GR B", "erw", "ASTM A53"),
          ("A333 GR 6", "seamless", "ASTM A333"))
    for (grade, cons, std), nps, sch in product(cs, PIPE_NPS, ("SCH 40", "SCH 80", "SCH 160")):
        if cons == "erw" and (nps < 2 or sch == "SCH 160"):
            continue
        for end in ("plain", "bevel"):
            yield {"construction": cons, "material_grade": grade, "standard": std,
                   "nominal_size_in": nps, "schedule": sch, "wall_mm": WALL[nps][sch],
                   "od_mm": nz.od_for_nps(nps), "finish": "black", "end_type": end}
    for nps, sch, fin in product((0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0), ("SCH 40", "SCH 80"),
                                 ("black", "galvanised")):
        yield {"construction": "erw", "material_grade": "A53 GR B", "standard": "ASTM A53",
               "nominal_size_in": nps, "schedule": sch, "wall_mm": WALL[nps][sch],
               "od_mm": nz.od_for_nps(nps), "finish": fin, "end_type": "screwed"}
    for nps, wall in product((14.0, 16.0, 18.0, 20.0, 24.0), (6.35, 7.92, 9.53, 12.7)):
        yield {"construction": "erw", "material_grade": "FE410", "nominal_size_in": nps,
               "od_mm": nz.od_for_nps(nps), "wall_mm": wall, "finish": "black"}
    for grade, nps, sch in product(("SS304", "SS304L", "SS316", "SS316L"), PIPE_NPS,
                                   ("SCH 10S", "SCH 40", "SCH 80")):
        yield {"construction": "seamless", "material_grade": grade, "standard": "ASTM A312",
               "nominal_size_in": nps, "schedule": sch.replace("SCH 40", "SCH 40S").replace("SCH 80", "SCH 80S"),
               "wall_mm": WALL[nps][sch], "od_mm": nz.od_for_nps(nps)}
    for grade, nps, sch in product(("A335 P11", "A335 P22", "A335 P91"), PIPE_NPS,
                                   ("SCH 40", "SCH 80", "SCH 160")):
        for end in ("plain", "bevel"):
            yield {"construction": "seamless", "material_grade": grade, "standard": "ASTM A335",
                   "nominal_size_in": nps, "schedule": sch, "wall_mm": WALL[nps][sch],
                   "od_mm": nz.od_for_nps(nps), "end_type": end}


def valves():
    for vt, nps, cls, body, end in product(("gate", "globe", "check", "ball", "needle"), SMALL,
                                           ("800#", "1500#"), ("ASTM_A105", "SS316"),
                                           ("screwed", "socket_weld")):
        yield {"valve_type": vt, "nominal_size_in": nps, "pressure_class": cls,
               "body_material": body, "end_connection": end, "standard": "API 602"}
    for vt, nps, cls, body, end in product(("gate", "globe", "check", "ball", "butterfly", "plug"),
                                           LARGE, CLASSES, ("A216 WCB", "SS316", "A352 LCB"),
                                           ("flanged", "butt_weld")):
        if vt == "butterfly" and (cls not in ("150#", "300#") or end != "flanged"):
            continue
        std = {"gate": "API 600", "globe": "BS 1873", "check": "BS 1868", "ball": "API 6D",
               "butterfly": "API 609", "plug": "API 599"}[vt]
        ops = ("manual", "gear") if nps >= 8 and vt != "check" else ("manual",)
        for op in ops:
            v = {"valve_type": vt, "nominal_size_in": nps, "pressure_class": cls,
                 "body_material": body, "end_connection": end, "standard": std}
            if vt != "check":
                v["operation"] = op
            yield v


def flanges():
    grades = ("ASTM_A105", "SS316", "SS304", "A350 LF2")
    for ft, nps, cls, grade, face in product(("weld_neck", "slip_on", "blind", "socket_weld", "threaded"),
                                             PIPE_NPS, CLASSES, grades,
                                             ("raised_face", "ring_joint", "flat_face")):
        if ft in ("socket_weld", "threaded") and nps > 2:
            continue
        if ft == "slip_on" and cls in ("900#", "1500#"):
            continue
        if face == "ring_joint" and cls in ("150#", "300#"):
            continue
        if face == "flat_face" and cls != "150#":
            continue
        f = {"flange_type": ft, "face_type": face, "nominal_size_in": nps, "pressure_class": cls,
             "material_grade": grade, "standard": "ASME B16.5"}
        if ft == "weld_neck":
            for bore in ("SCH 40", "SCH 80"):
                yield {**f, "bore_schedule": bore}
        else:
            yield f


def gaskets():
    for nps, cls, grade, filler, thk in product(PIPE_NPS, CLASSES, ("SS316", "SS304", "SS316L"),
                                                ("GRAPHITE", "PTFE"), (4.5, 3.2)):
        yield {"gasket_type": "spiral_wound", "nominal_size_in": nps, "pressure_class": cls,
               "material_grade": grade, "filler": filler, "thickness_mm": thk}
    for nps, cls, mat, thk in product(PIPE_NPS, ("150#", "300#"), ("CNAF", "PTFE", "GRAPHITE"), (1.5, 3.0)):
        yield {"gasket_type": "flat", "nominal_size_in": nps, "pressure_class": cls,
               "material_grade": mat, "thickness_mm": thk}
    for nps, cls, grade in product(PIPE_NPS, ("600#", "900#", "1500#"), ("SOFT_IRON", "SS316")):
        yield {"gasket_type": "ring_joint", "nominal_size_in": nps, "pressure_class": cls,
               "material_grade": grade}


def fasteners():
    lengths = {"M12": (50, 60, 70, 80, 90), "M16": (70, 80, 90, 100, 110, 120, 130),
               "M20": (90, 100, 110, 120, 130, 140, 150, 160), "M24": (110, 130, 150, 170, 190, 210),
               "M27": (130, 150, 170, 190, 210), "M30": (150, 170, 190, 220, 250),
               "M33": (170, 200, 230, 260), "M36": (200, 230, 260, 290)}
    for (thread, lens), grade in product(lengths.items(), ("A193_B7", "A193 B16", "A320 L7", "A193 B8M")):
        for ln in lens:
            yield {"fastener_type": "stud_bolt", "thread": thread, "length_mm": float(ln),
                   "material_grade": grade, "standard": "ASTM " + grade.replace("_", " ").split()[0]}
    for thread, ln, grade in product(("M6", "M8", "M10", "M12", "M16", "M20", "M24"),
                                     (20, 25, 30, 35, 40, 50, 60, 70, 80, 100, 120),
                                     ("4.6", "8.8", "10.9", "SS304", "SS316")):
        yield {"fastener_type": "bolt", "head_type": "hex", "thread": thread, "length_mm": float(ln),
               "material_grade": grade, "standard": "IS 1364"}
    for thread, grade in product(("M12", "M16", "M20", "M24", "M27", "M30", "M33", "M36"),
                                 ("A194 2H", "A194 4", "A194 8M")):
        yield {"fastener_type": "nut", "head_type": "hex", "thread": thread, "material_grade": grade,
               "standard": "ASTM A194"}


def cables():
    sections = (1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400)
    for cores, cs, cond, kv, ins, arm in product((1.0, 2.0, 3.0, 3.5, 4.0), sections, ("AL", "CU"),
                                                 (1.1, 3.3, 6.6, 11.0, 22.0, 33.0), ("PVC", "XLPE"),
                                                 ("armoured", "unarmoured")):
        if cond == "AL" and cs < 10:
            continue                               # aluminium starts at 10 mm2
        if kv > 1.1 and (ins == "PVC" or cs < 25 or cores not in (1.0, 3.0)):
            continue                               # HT cable: XLPE, 1 or 3 core, 25 mm2 up
        if cores == 3.5 and cs < 25:
            continue                               # half-size neutral only on larger cables
        if cores == 1.0 and cs < 50 and kv == 1.1 and arm == "armoured":
            continue
        yield {"cable_type": "power", "cores": cores, "cross_section_mm2": float(cs),
               "conductor": cond, "voltage_kv": kv, "insulation": ins, "armour": arm,
               "standard": "IS 7098" if ins == "XLPE" else "IS 1554"}
    for cores, cs in product((2.0, 4.0, 7.0, 12.0, 19.0, 24.0), (1.5, 2.5)):
        yield {"cable_type": "control", "cores": cores, "cross_section_mm2": cs, "conductor": "CU",
               "voltage_kv": 1.1, "insulation": "PVC", "armour": "armoured", "standard": "IS 1554"}


def fittings():
    for ft, nps, sch, grade in product(("elbow", "tee", "reducer", "cap"), LARGE, ("SCH 40", "SCH 80"),
                                       ("A234 WPB", "SS316", "SS304")):
        f = {"fitting_type": ft, "nominal_size_in": nps, "schedule": sch, "material_grade": grade,
             "end_connection": "butt_weld", "standard": "ASME B16.9"}
        if ft == "elbow":
            for angle in (90.0, 45.0):
                yield {**f, "angle": angle, "radius": "LR"}
        else:
            yield f
    for ft, nps, cls, grade in product(("elbow", "tee", "coupling", "union", "cap"), SMALL,
                                       ("3000#", "6000#"), ("ASTM_A105", "SS316")):
        f = {"fitting_type": ft, "nominal_size_in": nps, "pressure_class": cls, "material_grade": grade,
             "end_connection": "socket_weld", "standard": "ASME B16.11"}
        yield {**f, "angle": 90.0} if ft == "elbow" else f


def plates():
    for grade, t in product(("IS2062 E250A", "IS2062 E250BR", "IS2062 E350", "SS304", "SS316", "A516 GR 70"),
                            (3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 32.0, 40.0)):
        yield {"material_grade": grade, "thickness_mm": t, "plate_type": "plain",
               "width_mm": 2500.0, "length_mm": 6300.0}
    for t in (5.0, 6.0, 8.0, 10.0):
        yield {"material_grade": "IS2062 E250A", "thickness_mm": t, "plate_type": "chequered",
               "width_mm": 1250.0, "length_mm": 2500.0}


def tubes():
    ods = (19.05, 25.4, 31.75, 38.1, 44.45, 50.8, 54.0, 57.0, 60.3, 63.5)
    walls = (1.65, 2.11, 2.41, 2.77, 3.05, 3.4, 4.0, 4.5, 5.6, 6.35, 7.1, 8.13)
    for grade, od, wall in product(("A213 T11", "A213 T22", "A213 T23", "A213 T91", "SS304", "SS316"),
                                   ods, walls):
        if wall > od / 6:
            continue
        kind = "boiler" if grade.startswith("A213") else "exchanger"
        yield {"material_grade": grade, "od_mm": od, "wall_mm": wall, "tube_type": kind}


def motors():
    for (kw, poles), frame in IEC_FRAME.items():
        for mount, volt in product(("foot", "flange", "foot_flange"), (415.0,)):
            if mount != "foot" and kw > 45:
                continue
            yield {"equipment_type": "motor", "phases": 3.0, "power_kw": float(kw),
                   "power_hp": round(kw / 0.746, 2), "speed_rpm": RPM[poles], "poles": float(poles),
                   "voltage_v": volt, "frame": frame, "mounting": mount, "insulation_class": "F",
                   "protection_class": "IP55"}
    for kw, poles in product((110, 132, 160, 200, 250, 315), (2, 4)):
        yield {"equipment_type": "motor", "phases": 3.0, "power_kw": float(kw),
               "power_hp": round(kw / 0.746, 2), "speed_rpm": RPM[poles], "poles": float(poles),
               "voltage_v": 3300.0, "mounting": "foot", "insulation_class": "F", "protection_class": "IP55"}


def transformers():
    for kva, hv in product((100, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500),
                           (3.3, 6.6, 11.0, 22.0, 33.0)):
        yield {"equipment_type": "transformer", "phases": 3.0, "rating_kva": float(kva),
               "voltage_hv_kv": hv}


def gauges():
    ranges = (1, 2.5, 4, 6, 10, 16, 25, 40, 60, 100, 160, 250)
    for dial, top, wet, conn in product((63.0, 100.0, 150.0), ranges, ("SS316", "BRASS"),
                                        ("1/2 IN NPT BOTTOM", "1/4 IN NPT BOTTOM", "1/2 IN NPT BACK")):
        if wet == "BRASS" and top > 40:
            continue
        yield {"instrument_type": "PRESSURE_GAUGE", "dial_size_mm": dial, "range_min": 0.0,
               "range_max": float(top), "range_unit": "BAR", "wetted_material": wet, "connection": conn}
    for dial, top in product((100.0, 150.0), (100, 150, 200, 300, 400, 600)):
        yield {"instrument_type": "TEMPERATURE_GAUGE", "dial_size_mm": dial, "range_min": 0.0,
               "range_max": float(top), "range_unit": "DEGC", "wetted_material": "SS316"}


def seals():
    for shaft, arr, faces, elast in product(range(25, 155, 5), ("single", "double", "cartridge_single",
                                                                "cartridge_double"),
                                            ("SIC VS CARBON", "TC VS SIC", "SIC VS SIC"),
                                            ("VITON", "EPDM", "KALREZ")):
        yield {"component_type": "mechanical_seal", "arrangement": arr, "shaft_dia_mm": float(shaft),
               "face_materials": faces, "elastomer": elast}


FACTORIES = {
    "bearing": (bearings, 1.4), "pipe": (pipes, 1.3), "valve": (valves, 1.3), "flange": (flanges, 1.0),
    "gasket": (gaskets, 1.2), "fastener": (fasteners, 1.1), "cable": (cables, 0.8),
    "fitting": (fittings, 1.0), "plate": (plates, 1.0), "tube": (tubes, 0.9),
    "electrical": (lambda: [*motors(), *transformers()], 1.0), "instrument": (gauges, 1.0),
    "rotating": (seals, 0.9),
}

# What the item is bought in. Pipe, tube and cable by the metre.
UOM = {"pipe": "MTR", "tube": "MTR", "cable": "MTR", "plate": "KG"}

SIZE_FIELDS = {"nominal_size_in", "od_mm", "wall_mm", "bore_mm", "width_mm", "iso_designation",
               "length_mm", "thickness_mm", "cross_section_mm2", "shaft_dia_mm", "power_kw",
               "power_hp", "frame", "range_max", "dial_size_mm", "rating_kva", "speed_rpm", "poles"}


def family_of(category: str, attrs: dict) -> str:
    rest = sorted((k, str(v)) for k, v in attrs.items() if k not in SIZE_FIELDS)
    return category + "|" + "|".join(f"{k}={v}" for k, v in rest)


def split_of(family_id: str, test_share: int = 5) -> str:
    """Locked test split by family: one family in five, by hash - no one chooses."""
    return "test" if hashlib.sha1(family_id.encode()).digest()[0] % test_share == 0 else "dev"


def base_price(category: str, a: dict, rng: random.Random) -> float:
    """A plausible INR price. Only its spread matters - savings and the price guard."""
    size = a.get("nominal_size_in") or 1.0
    grade = str(a.get("material_grade") or a.get("body_material") or "")
    alloy = 3.2 if grade.startswith(("SS", "A312", "A182 F3")) else 2.6 if grade.startswith(("A335", "A213")) else 1.0
    p = {
        "bearing": lambda: 90 * (a["bore_mm"] ** 0.9) * (1.25 if "RS" in a["seal_type"] else 1.0),
        "pipe": lambda: 180 * size ** 1.35 * alloy * (1 + a.get("wall_mm", 5) / 20),
        "valve": lambda: 2600 * size ** 1.45 * alloy * (1 + CLASSES.index(a["pressure_class"]) * 0.35
                                                        if a["pressure_class"] in CLASSES else 1.3),
        "flange": lambda: 420 * size ** 1.3 * alloy * (1 + (CLASSES.index(a["pressure_class"]) * 0.4)),
        "gasket": lambda: 95 * size ** 1.1 * (1.3 if a.get("filler") == "PTFE" else 1.0),
        "fastener": lambda: (a.get("length_mm", 30) / 10) * int(a["thread"][1:]) * (2.5 if "SS" in grade or "8M" in grade else 1.0),
        "cable": lambda: 6 * a["cross_section_mm2"] * a["cores"] * (3.1 if a["conductor"] == "CU" else 1.0)
                         * (1 + a["voltage_kv"] / 11),
        "fitting": lambda: 260 * size ** 1.3 * alloy,
        "plate": lambda: 72 * alloy,
        "tube": lambda: 55 * a["od_mm"] * a["wall_mm"] / 10 * alloy,
        "electrical": lambda: (9000 + 5200 * a["power_kw"] ** 0.92 * (1.6 if a["voltage_v"] > 1000 else 1.0)
                               if "power_kw" in a else 1800 * a["rating_kva"] * (1 + a["voltage_hv_kv"] / 33)),
        "instrument": lambda: 900 + 12 * a["dial_size_mm"] * (1.8 if a["wetted_material"] == "SS316" else 1.0),
        "rotating": lambda: 180 * a["shaft_dia_mm"] * (1.9 if "double" in a["arrangement"] else 1.0)
                            * (1.4 if a["elastomer"] == "KALREZ" else 1.0),
    }[category]()
    return round(p * rng.uniform(0.85, 1.2), 2)


def universe() -> list[tuple[str, dict]]:
    out = []
    for cat, (make, _) in FACTORIES.items():
        out.extend((cat, a) for a in make())
    return out


def sample(n_items: int, rng: random.Random, must_have: list[tuple[str, dict]] = ()) -> list[dict]:
    """About n_items valid items, weighted towards refinery stock, fixed by the seed.

    must_have items (the demo's bearing and gaskets) are always included.
    """
    pool = universe()
    weights = [FACTORIES[cat][1] for cat, _ in pool]
    chosen, seen = [], set()

    def key(cat, a):
        return cat + repr(sorted(a.items()))

    for cat, a in must_have:
        match = next((x for x in pool if x[0] == cat and all(x[1].get(k) == v for k, v in a.items())), None)
        assert match, f"demo item not in the universe: {cat} {a}"
        seen.add(key(*match))
        chosen.append(match)
    order = sorted(range(len(pool)), key=lambda i: rng.random() ** (1 / weights[i]), reverse=True)
    for i in order:
        if len(chosen) >= n_items:
            break
        k = key(*pool[i])
        if k not in seen:
            seen.add(k)
            chosen.append(pool[i])
    items = []
    for n, (cat, a) in enumerate(chosen, 1):
        fam = family_of(cat, a)
        items.append({"item_id": f"ITM-{n:05d}", "category": cat, "attributes": dict(a),
                      "family_id": fam, "split": split_of(fam), "uom": UOM.get(cat, "EA"),
                      "base_price": base_price(cat, a, rng)})
    return items


def traps(items: list[dict], hard_fields) -> list[dict]:
    """Every pair of items that differ in EXACTLY ONE hard field.

    These are the near-misses a real catalogue is full of - SS316 against
    SS304, 150# against 300#, 6205 against 6206 - and a merge across any of
    them is a safety failure. Derived from the sample, not hand-written.
    """
    out = []
    by_cat = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)
    for cat, group in by_cat.items():
        hard = [f for f in hard_fields(cat)]
        for f in hard:
            buckets = {}
            for it in group:
                a = it["attributes"]
                if f not in a:
                    continue
                sig = (tuple((h, str(a.get(h))) for h in hard if h != f),
                       tuple(sorted((k, str(v)) for k, v in a.items() if k not in hard and k not in SIZE_FIELDS)))
                buckets.setdefault(sig, []).append(it)
            for members in buckets.values():
                members.sort(key=lambda x: x["item_id"])
                for i, x in enumerate(members):
                    for y in members[i + 1:]:
                        if str(x["attributes"][f]) != str(y["attributes"][f]):
                            out.append({"a": x["item_id"], "b": y["item_id"], "field": f,
                                        "reason": f"{f}: {x['attributes'][f]} vs {y['attributes'][f]}"})
    return out


if __name__ == "__main__":
    from collections import Counter
    u = universe()
    print(f"{len(u):,} valid items in the universe")
    for cat, n in Counter(c for c, _ in u).most_common():
        print(f"  {cat:<11} {n:>6,}")
