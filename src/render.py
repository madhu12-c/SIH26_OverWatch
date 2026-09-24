"""
Renderers - one item, written the way each company actually writes it.

Every style is copied from real text in the dev half of data/real (the row
that shows it is named), not invented:

    plain     noun-modifier, today's synthetic style, with the storekeeper
              corruptions: shorthand, reordering, dropped fields, typos, case
    comma     NTPC: "PIPE, BLK, CS, FE410, 9.5MM, 508MM, 500MM"          (dev 3)
              "TUBE,STRT,AS,A213-T91,54MM,4MM"                          (dev 156)
              "MOTOR,IND,415VAC,200L,4P,B5,30KW"                         (dev 42)
    long      Oil India: "STEEL LINE PIPE, ERW, NOMINAL BORE: 100 MM,
              O.D. 114.3 MM, WALL THICKNESS: 6.0 MM, API 5L, GRADE A"    (dev 1)
    sap40     the same, cut at 40 characters - SAP's MAKTX field

Two more are used ONLY for records of test families, so the locked test also
measures notation the reading rules were never tuned on:

    vendor    catalogue codes: "FLG WNRF 4IN CL300 A105 S40"
    sentence  tender prose: "Supply of weld neck flange, size 100 NB, ..."

Sizes are written as NPS, NB, DN, mixed, OD-only, and - rarely, on purpose -
the classic mistake: a size name multiplied by 25.4.
"""

from __future__ import annotations

import random
import re

import normalise as nz

STYLES = ("plain", "comma", "long", "sap40")
TEST_ONLY = ("vendor", "sentence")

# How each company writes. A company is mostly consistent with itself.
CPSE_STYLE = {
    "CPCL": {"plain": 0.5, "sap40": 0.3, "long": 0.2},
    "IOCL": {"comma": 0.6, "plain": 0.2, "sap40": 0.2},
    "ONGC": {"long": 0.6, "plain": 0.2, "comma": 0.2},
    "BPCL": {"sap40": 0.6, "plain": 0.3, "comma": 0.1},
    "GAIL": {"plain": 0.4, "comma": 0.3, "long": 0.3},
}

BRANDS = {
    "bearing": ["SKF", "FAG", "NTN", "NBC", "TIMKEN"], "valve": ["L&T", "AUDCO", "KSB", "BDK", "VIRGO"],
    "instrument": ["WIKA", "BAUMER", "FORBES MARSHALL"], "rotating": ["BURGMANN", "JOHN CRANE", "FLOWSERVE"],
    "electrical": ["ABB", "SIEMENS", "CROMPTON", "KIRLOSKAR", "BHARAT BIJLEE"],
    "cable": ["POLYCAB", "KEI", "HAVELLS", "FINOLEX"], "fastener": ["UNBRAKO", "TVS", "SUNDRAM"],
    "gasket": ["FLEXITALLIC", "CHAMPION", "IGP"],
}
VENDORS = {cat: [f"{b.title()} India Ltd" for b in names] + ["Refinery Stores Supplier"]
           for cat, names in BRANDS.items()}


def pick(rng, options):
    return options[rng.randrange(len(options))]


# --------------------------------------------------------------------------
# Value formatting
# --------------------------------------------------------------------------

FRACTIONS = {0.25: "1/4", 0.5: "1/2", 0.75: "3/4", 1.25: "1-1/4", 1.5: "1-1/2", 2.5: "2-1/2", 3.5: "3-1/2"}


def inch(nps: float, rng) -> str:
    whole = FRACTIONS.get(nps, f"{nps:g}")
    if "-" in whole and rng.random() < 0.3:
        whole = whole.replace("-", ".")                              # 1.1/2" - oilfield (dev 34)
    return whole + pick(rng, ['"', '"', " IN", " INCH", "IN"])


def nb(nps: float, rng) -> str:
    dn = nz.NPS_TO_DN.get(nps)
    if dn is None:
        return inch(nps, rng)
    return pick(rng, [f"{dn} NB", f"{dn}NB", f"{dn} MM NB", f"DN {dn}", f"DN{dn}", f"{dn}MM"])


def size(nps: float, rng, style: str) -> str:
    """A size NAME, in one of the notations real text uses."""
    r = rng.random()
    if style == "comma":
        return f"{nz.NPS_TO_DN.get(nps, nps):g}MM" if nps in nz.NPS_TO_DN else inch(nps, rng)
    if style == "long":
        dn = nz.NPS_TO_DN.get(nps)
        return pick(rng, [f"NOMINAL BORE: {dn} MM", f"SIZE: {dn} MM ({inch(nps, rng)})",
                          f"NB {dn} MM"]) if dn else inch(nps, rng)
    if r < 0.45:
        return inch(nps, rng)
    if r < 0.85:
        return nb(nps, rng)
    dn = nz.NPS_TO_DN.get(nps)
    return f"{dn} MM ({inch(nps, rng)})" if dn else inch(nps, rng)


def mm(v: float) -> str:
    return f"{v:g}"


PRESSURE = lambda c, rng: pick(rng, [c, c, f"CLASS {c[:-1]}", f"CL{c[:-1]}", f"{c[:-1]} LB",
                                     f"ANSI {c[:-1]}", f"{c[:-1]}CL"])

# Grade spellings seen in real text. A family word alone ("CS") is written
# for a specific grade now and then - the ladder must not treat it as a match.
GRADE_TEXT = {
    "A106 GR B": ["A106 GR B", "ASTM A106 GR.B", "A106B", "A-106 GR B", "ASTM A106 GRADE B"],
    "API 5L GR B": ["API 5L GR B", "API-5L GR.B", "API 5L, GRADE B"],
    "A53 GR B": ["A53 GR B", "ASTM A53 GR.B", "A-53 GR B"],
    "A333 GR 6": ["A333 GR 6", "A333 GR.6", "ASTM A333 GRADE 6"],
    "FE410": ["FE410", "FE-410", "FE 410"],
    "SS304": ["SS304", "SS 304", "S.S.304", "304 SS", "SS-304"],
    "SS304L": ["SS304L", "SS 304L", "304L SS"],
    "SS316": ["SS316", "SS 316", "S.S.316", "316 SS", "SS-316"],
    "SS316L": ["SS316L", "SS 316L", "316L SS"],
    "A335 P11": ["A335 P11", "ASTM A335 GR.P11", "A335-P11"],
    "A335 P22": ["A335 P22", "ASTM A335 GR.P22", "A335-P22"],
    "A335 P91": ["A335 P91", "ASTM A335 GR.P91", "A335-P91"],
    "ASTM_A105": ["A105", "ASTM A105", "A-105", "ASTM A-105"],
    "A350 LF2": ["A350 LF2", "ASTM A350 LF2"],
    "A216 WCB": ["A216 WCB", "ASTM A216 WCB", "A216 GR WCB", "CAST STEEL WCB"],
    "A352 LCB": ["A352 LCB", "ASTM A352 LCB"],
    "A234 WPB": ["A234 WPB", "ASTM A234 WPB", "A234 GR WPB"],
    "A193_B7": ["A193 B7", "ASTM A193 B7", "A193 GR B7"],
    "A193 B16": ["A193 B16", "ASTM A193 B16"],
    "A320 L7": ["A320 L7", "ASTM A320 L7"],
    "A193 B8M": ["A193 B8M", "ASTM A193 B8M"],
    "A194 2H": ["A194 2H", "ASTM A194 2H"], "A194 4": ["A194 GR 4"], "A194 8M": ["A194 8M"],
    "IS2062 E250A": ["IS2062 E250A", "IS 2062 E250 A", "IS2062-A"],
    "IS2062 E250BR": ["IS2062 E250BR", "IS 2062 E250 BR"],
    "IS2062 E350": ["IS2062 E350", "IS 2062 E350"],
    "A516 GR 70": ["A516 GR 70", "ASTM A516 GR.70", "A516-70"],
    "A213 T11": ["A213 T11", "A213-T11", "ASTM A213 T11"],
    "A213 T22": ["A213 T22", "A213-T22", "ASTM A213 T22"],
    "A213 T23": ["A213 T23", "A213-T23", "A213- T23"],
    "A213 T91": ["A213 T91", "A213-T91", "ASTM A213 T91"],
}
FAMILY_WORD = {"A106 GR B": "CS", "API 5L GR B": "CS", "A53 GR B": "CS", "A333 GR 6": "CS",
               "ASTM_A105": "CS", "A216 WCB": "CS", "A234 WPB": "CS", "SS304": "SS", "SS316": "SS",
               "SS304L": "SS", "SS316L": "SS"}


def grade(g: str, rng, category: str = "") -> str:
    if g in FAMILY_WORD and rng.random() < 0.06:
        return pick(rng, [FAMILY_WORD[g], "C.S." if FAMILY_WORD[g] == "CS" else "S.S.",
                          "CARBON STEEL" if FAMILY_WORD[g] == "CS" else "STAINLESS STEEL"])
    if g.startswith("SS3") and category == "pipe" and rng.random() < 0.5:
        return f"A312 TP{g[2:]}" if rng.random() < 0.6 else f"TP{g[2:]}"       # dev 8, 40
    if g.startswith("SS3") and category in ("flange", "valve") and rng.random() < 0.4:
        return {"SS316": "A182 F316", "SS304": "A182 F304"}.get(g, g) if category == "flange" \
            else {"SS316": "CF8M", "SS304": "CF8"}.get(g, g)
    return pick(rng, GRADE_TEXT.get(g, [g.replace("_", " ")]))


# --------------------------------------------------------------------------
# Tokens per category: [(field, text), ...] in the order a master writes them
# --------------------------------------------------------------------------

def t_bearing(a, rng, style):
    des, seal = a["iso_designation"], a["seal_type"]
    seal_txt = {"2RS": pick(rng, ["2RS", "2RS SEALED", "2RS1", "2RSR"]), "RS": "RS",
                "2Z": pick(rng, ["2Z", "ZZ"]), "Z": "Z", "OPEN": "OPEN"}[seal]
    noun = "BRG" if style in ("comma", "vendor", "sap40") else pick(rng, ["BEARING", "BRG", "BEARING BALL"])
    dims = f"{a['bore_mm']:g}X{a['od_mm']:g}X{a['width_mm']:g} MM"
    if style == "sentence":
        return [("noun", f"SUPPLY OF DEEP GROOVE BALL BEARING NO. {des}-{seal}, SIZE {dims}")]
    if style == "vendor":
        return [("noun", "BRG"), ("iso_designation", f"{des}-{seal}"), ("seal_type", "C3")]
    return [("noun", noun), ("sub_type", pick(rng, ["BALL", "DEEP GROOVE BALL", "DP GRV"])),
            ("iso_designation", des), ("dims", dims), ("seal_type", seal_txt)]


def t_pipe(a, rng, style):
    nps, g = a["nominal_size_in"], a["material_grade"]
    cons = {"seamless": pick(rng, ["SEAMLESS", "SMLS"]), "erw": "ERW"}[a["construction"]]
    toks = []
    if style == "comma":
        toks = [("noun", "PIPE")]
        if a.get("finish"):
            toks.append(("finish", "BLK" if a["finish"] == "black" else "GLV"))
        if g in FAMILY_WORD and FAMILY_WORD[g] == "CS" or g == "FE410":
            toks.append(("family", "CS"))
        toks += [("material_grade", grade(g, rng, "pipe")), ("construction", cons)]
        if "schedule" in a and rng.random() < 0.6:
            sch = a["schedule"]                                         # SCH80, or 80S for stainless
            toks.append(("schedule", sch.replace("SCH ", "") if sch.endswith("S") else sch.replace(" ", "")))
            toks.append(("size", f"{nz.NPS_TO_DN[nps]}MM"))
        else:
            toks += [("wall_mm", f"{mm(a['wall_mm'])}MM"), ("od_mm", f"{mm(a['od_mm'])}MM"),
                     ("size", f"{nz.NPS_TO_DN[nps]}MM")]                 # NTPC: wall, OD, NB
        if a.get("end_type"):
            toks.append(("end_type", {"plain": "PL", "bevel": "BE", "screwed": "SCRD"}[a["end_type"]]))
        return toks
    if style == "long":
        toks = [("noun", pick(rng, ["STEEL LINE PIPE", "LINE PIPE", "PIPE"])), ("construction", cons),
                ("size", size(nps, rng, "long"))]
        if rng.random() < 0.6:
            toks.append(("od_mm", f"O.D. {mm(a['od_mm'])} MM"))
        toks.append(("wall_mm", f"WALL THICKNESS: {mm(a['wall_mm'])} MM") if rng.random() < 0.6 or "schedule" not in a
                    else ("schedule", a["schedule"]))
        std = a.get("standard", "")
        if std.startswith("API") and "GR" in g:
            toks += [("standard", "API 5L"), ("material_grade", f"GRADE {g[-1]}")]
        else:
            toks.append(("material_grade", grade(g, rng, "pipe")))
        if a.get("finish") == "galvanised":
            toks.append(("finish", "GALVANISED"))
        if a.get("end_type"):
            toks.append(("end_type", {"plain": "PLAIN END", "bevel": "BEVEL END", "screwed": "SCREWED"}[a["end_type"]]))
        return toks
    if style == "vendor":
        return [("noun", "PIPE"), ("size", f"{inch(nps, rng).replace(' ', '')}"),
                ("schedule", a.get("schedule", "").replace("SCH ", "S")),
                ("material_grade", g.replace(" GR ", "").replace(" ", "")), ("construction", cons),
                ("end_type", {"plain": "PE", "bevel": "BE", "screwed": "SCRD"}.get(a.get("end_type", ""), ""))]
    if style == "sentence":
        sch = f", SCHEDULE {a['schedule'][4:]}" if "schedule" in a else f", {mm(a['wall_mm'])} MM WALL"
        return [("noun", f"SUPPLY OF {cons} PIPE TO {grade(g, rng, 'pipe')}, SIZE {nb(nps, rng)}{sch}")]
    toks = [("noun", "PIPE"), ("construction", cons), ("material_grade", grade(g, rng, "pipe")),
            ("size", size(nps, rng, style))]
    toks.append(("schedule", a["schedule"]) if "schedule" in a else ("wall_mm", f"{mm(a['wall_mm'])} MM WT"))
    if a.get("finish") == "galvanised":
        toks.append(("finish", pick(rng, ["GALV", "GI", "GALVANISED"])))
    elif a.get("finish") == "black" and rng.random() < 0.3:
        toks.append(("finish", "BLACK"))
    if a.get("end_type"):
        toks.append(("end_type", {"plain": pick(rng, ["PE", "PLAIN END"]), "bevel": pick(rng, ["BE", "BEVEL END"]),
                                  "screwed": pick(rng, ["SCRD", "SCREWED"])}[a["end_type"]]))
    return toks


VALVE_WORD = {"gate": "GATE", "globe": "GLOBE", "check": "CHECK", "ball": "BALL", "butterfly": "BUTTERFLY",
              "plug": "PLUG", "needle": "NEEDLE"}
END_WORD = {"flanged": ["FLANGED", "FLGD", "RF FLANGED"], "butt_weld": ["BW", "BUTT WELD", "BW ENDS"],
            "screwed": ["SCRD", "SCREWED", "NPT(F)"], "socket_weld": ["SW", "SOCKET WELD", "SWE"]}


def t_valve(a, rng, style):
    vt, nps = VALVE_WORD[a["valve_type"]], a["nominal_size_in"]
    body = a["body_material"]
    op = {"manual": pick(rng, ["HAND WHEEL OPERATED", "HW", "LEVER OPERATED" if vt in ("BALL", "PLUG") else "HAND WHEEL"]),
          "gear": pick(rng, ["GEAR OPERATED", "GEAR OPTD", "GO"])}.get(a.get("operation", ""), "")
    if style == "vendor":
        return [("noun", f"VLV {vt[:2]}"), ("size", inch(nps, rng).replace(" ", "")),
                ("pressure_class", f"CL{a['pressure_class'][:-1]}"),
                ("body_material", body.replace("A216 ", "").replace("A352 ", "").replace("ASTM_", "")),
                ("end_connection", {"flanged": "FLGD", "butt_weld": "BW", "screwed": "NPT", "socket_weld": "SW"}[a["end_connection"]])]
    if style == "sentence":
        return [("noun", f"SUPPLY OF {vt} VALVE, SIZE {nb(nps, rng)}, {PRESSURE(a['pressure_class'], rng)}, "
                         f"BODY {grade(body, rng, 'valve')}, {pick(rng, END_WORD[a['end_connection']])} ENDS "
                         f"AS PER {a['standard']}")]
    noun = pick(rng, [("noun", f"{vt} VALVE"), ("noun", f"VALVE, {vt}"), ("noun", f"VALVE {vt}")])
    toks = [noun, ("size", size(nps, rng, style)), ("pressure_class", PRESSURE(a["pressure_class"], rng)),
            ("body_material", (pick(rng, ["BODY ", ""]) + grade(body, rng, "valve"))),
            ("end_connection", pick(rng, END_WORD[a["end_connection"]])), ("standard", a["standard"])]
    if op:
        toks.append(("operation", op))
    return toks


FLANGE_WORD = {"weld_neck": ["WELD NECK", "WN", "W/NECK"], "slip_on": ["SLIP ON", "SO", "SLIP-ON"],
               "blind": ["BLIND", "BLIND FLANGE"], "socket_weld": ["SOCKET WELD", "SW"],
               "threaded": ["THREADED", "SCREWED"]}
FACE_WORD = {"raised_face": ["RF", "RAISED FACE"], "ring_joint": ["RTJ", "RING JOINT"], "flat_face": ["FF", "FLAT FACE"]}


def t_flange(a, rng, style):
    nps = a["nominal_size_in"]
    if style == "vendor":
        code = {"weld_neck": "WN", "slip_on": "SO", "blind": "BL", "socket_weld": "SW", "threaded": "THD"}[a["flange_type"]]
        face = {"raised_face": "RF", "ring_joint": "RTJ", "flat_face": "FF"}[a["face_type"]]
        return [("noun", f"FLG {code}{face}"), ("size", inch(nps, rng).replace(" ", "")),
                ("pressure_class", f"CL{a['pressure_class'][:-1]}"),
                ("material_grade", grade(a["material_grade"], rng, "flange").replace("ASTM ", "")),
                ("bore_schedule", a.get("bore_schedule", "").replace("SCH ", "S"))]
    if style == "sentence":
        return [("noun", f"SUPPLY OF {pick(rng, FLANGE_WORD[a['flange_type']])} FLANGE, "
                         f"{pick(rng, FACE_WORD[a['face_type']])}, {nb(nps, rng)}, {PRESSURE(a['pressure_class'], rng)}, "
                         f"MATERIAL {grade(a['material_grade'], rng, 'flange')} TO ASME B16.5")]
    if style == "comma":                                               # dev 83
        return [("noun", "FLANGE"), ("standard", pick(rng, ["ASA", "ANSI"]) + ",B16.5"),
                ("pressure_class", f"CL-{a['pressure_class'][:-1]}"),
                ("material_grade", grade(a["material_grade"], rng, "flange")),
                ("flange_type", pick(rng, FLANGE_WORD[a["flange_type"]])),
                ("face_type", FACE_WORD[a["face_type"]][0]),
                ("size", f"{nz.NPS_TO_DN.get(nps, nps)}MM({inch(nps, rng).replace(' ', '')})")]
    toks = [("noun", "FLANGE"), ("flange_type", pick(rng, FLANGE_WORD[a["flange_type"]])),
            ("face_type", pick(rng, FACE_WORD[a["face_type"]])), ("size", size(nps, rng, style)),
            ("pressure_class", PRESSURE(a["pressure_class"], rng)),
            ("material_grade", grade(a["material_grade"], rng, "flange")),
            ("standard", pick(rng, ["ASME B16.5", "B16.5", "ANSI B16.5"]))]
    if a.get("bore_schedule"):
        toks.append(("bore_schedule", f"{a['bore_schedule']} BORE"))
    return toks


def t_gasket(a, rng, style):
    nps, gt = a["nominal_size_in"], a["gasket_type"]
    kind = {"spiral_wound": pick(rng, ["SPIRAL WOUND", "SPL WOUND", "SPIRALWOUND"]),
            "ring_joint": pick(rng, ["RING JOINT", "RTJ", "RING TYPE JOINT"]),
            "flat": pick(rng, ["FLAT", "SHEET"])}[gt]
    mat = a["material_grade"]
    mat_txt = {"SOFT_IRON": "SOFT IRON", "CNAF": pick(rng, ["CNAF", "NON ASBESTOS"]),
               "PTFE": "PTFE", "GRAPHITE": "GRAPHITE"}.get(mat) or grade(mat, rng, "gasket")
    if style == "sentence":
        return [("noun", f"SUPPLY OF {kind} GASKET, {mat_txt}, {nb(nps, rng)}, {PRESSURE(a['pressure_class'], rng)}")]
    toks = [("noun", "GASKET"), ("gasket_type", kind), ("material_grade", mat_txt),
            ("size", size(nps, rng, style if style != "comma" else "plain")),
            ("pressure_class", PRESSURE(a["pressure_class"], rng))]
    if a.get("filler"):
        short = "GR" if a["filler"] == "GRAPHITE" else "PTFE"
        toks.append(("filler", pick(rng, [f"{a['filler']} FILLER", f"{short} FILLER",
                                          f"{a['filler']} FILLED"])))
    if a.get("thickness_mm"):
        toks.append(("thickness_mm", f"{a['thickness_mm']:g} MM THK"))
    return toks


def t_fastener(a, rng, style):
    ft, th = a["fastener_type"], a["thread"]
    noun = {"stud_bolt": pick(rng, ["STUD BOLT", "STUD", "S/BOLT"]),
            "bolt": pick(rng, ["HEX BOLT", "BOLT HEX HD", "BOLT, HEX HEAD"]),
            "nut": pick(rng, ["HEX NUT", "HEAVY HEX NUT", "NUT HEX"])}[ft]
    size_txt = th if ft == "nut" else pick(rng, [f"{th} X {a['length_mm']:g}", f"{th}X{a['length_mm']:g}",
                                                 f"{th} X {a['length_mm']:g} MM"])
    if style == "sentence":
        return [("noun", f"SUPPLY OF {noun} {size_txt} TO {grade(a['material_grade'], rng)}")]
    toks = [("noun", noun), ("thread", size_txt), ("material_grade", grade(a["material_grade"], rng))]
    if ft == "stud_bolt" and rng.random() < 0.4:
        toks.append(("nuts", pick(rng, ["WITH 2 NUTS", "C/W 2 NUTS", "W/2 NUTS"])))
    if rng.random() < 0.5:
        toks.append(("standard", a["standard"]))
    return toks


def t_cable(a, rng, style):
    c, cs = a["cores"], a["cross_section_mm2"]
    cond = {"AL": pick(rng, ["AL", "ALU", "ALUMINIUM"]), "CU": pick(rng, ["CU", "COPPER"])}[a["conductor"]]
    kv = a["voltage_kv"]
    volt = f"{int(kv * 1000)}V" if kv < 1.5 and rng.random() < 0.5 else f"{kv:g}KV"
    arm = {"armoured": pick(rng, ["ARMOURED", "ARMD"]), "unarmoured": pick(rng, ["UNARMOURED", "UNARMD"])}[a["armour"]]
    if style == "vendor":
        code = ("A" if a["conductor"] == "AL" else "") + ("2X" if a["insulation"] == "XLPE" else "Y") \
               + ("WY" if a["armour"] == "armoured" else "Y")                      # IS cable codes: A2XWY
        return [("noun", code), ("cores", f"{c:g}C X {cs:g} SQMM"), ("voltage_kv", f"{kv:g}KV")]
    if style == "comma":                                                  # dev 19
        return [("noun", "CABLE"), ("cable_type", "PWR" if a["cable_type"] == "power" else "CONTROL"),
                ("cross_section_mm2", f"{cs:g}MM2"), ("cores", f"{c:g}C"), ("strand", "STRANDED"),
                ("conductor", cond), ("insulation", a["insulation"]), ("armour", arm), ("voltage_kv", volt)]
    return [("noun", pick(rng, ["CABLE", "POWER CABLE" if a["cable_type"] == "power" else "CONTROL CABLE"])),
            ("cores", pick(rng, [f"{c:g}C X {cs:g} SQMM", f"{c:g} X {cs:g} SQ.MM", f"{c:g}CX{cs:g}MM2",
                                 f"{c:g} CORE {cs:g} SQ MM"])),
            ("conductor", cond), ("insulation", a["insulation"]), ("armour", arm), ("voltage_kv", volt)]


def t_fitting(a, rng, style):
    ft, nps = a["fitting_type"], a["nominal_size_in"]
    word = {"elbow": "ELBOW", "tee": pick(rng, ["TEE", "TEE EQUAL", "EQUAL TEE"]), "reducer": "REDUCER",
            "cap": "CAP", "coupling": "COUPLING", "union": "UNION"}[ft]
    toks = [("noun", word)]
    if a.get("angle"):
        toks.append(("angle", pick(rng, [f"{a['angle']:g} DEG", f"{a['angle']:g} DEG.", f"{a['angle']:g}°"])))
    if style == "sentence":
        return [("noun", f"SUPPLY OF {word} {a.get('angle', '') and str(int(a['angle'])) + ' DEG'} "
                         f"{nb(nps, rng)} {grade(a['material_grade'], rng)} TO {a['standard']}")]
    toks += [("size", size(nps, rng, style if style != "comma" else "plain"))]
    if a.get("schedule"):
        toks.append(("schedule", a["schedule"]))
    if a.get("pressure_class"):
        toks.append(("pressure_class", pick(rng, [a["pressure_class"], f"{a['pressure_class'][:-1]} LB",
                                                  f"CLASS {a['pressure_class'][:-1]}"])))
    g = a["material_grade"]
    toks.append(("material_grade", "A403 WP316" if g == "SS316" and rng.random() < 0.4 else grade(g, rng)))
    toks.append(("end_connection", pick(rng, END_WORD[a["end_connection"]])))
    if a.get("radius"):
        toks.append(("radius", pick(rng, ["LR", "LONG RADIUS"])))
    toks.append(("standard", pick(rng, [a["standard"], a["standard"].replace("ASME ", "")])))
    return toks


def t_plate(a, rng, style):
    chq = a["plate_type"] == "chequered"
    if style == "comma":                                                  # dev 29
        return [("noun", "PLATE"), ("plate_type", "CHQ" if chq else ""), ("family", "MS" if "IS2062" in a["material_grade"] else ""),
                ("material_grade", grade(a["material_grade"], rng)), ("thickness_mm", f"{a['thickness_mm']:g}MM")]
    toks = [("noun", pick(rng, ["PLATE", "MS PLATE" if "IS2062" in a["material_grade"] else "PLATE", "STEEL PLATE"]))]
    if chq:
        toks.append(("plate_type", pick(rng, ["CHEQUERED", "CHQ"])))
    toks += [("material_grade", grade(a["material_grade"], rng)),
             ("thickness_mm", pick(rng, [f"{a['thickness_mm']:g} MM THK", f"{a['thickness_mm']:g}MM",
                                          f"{a['thickness_mm']:g}MMX{a['width_mm']:g}MMX{a['length_mm']:g}MM"]))]
    return toks


def t_tube(a, rng, style):
    kind = {"boiler": "BOILER", "exchanger": pick(rng, ["HEAT EXCHANGER", "EXCHANGER"])}[a["tube_type"]]
    if style == "comma":                                                  # dev 156
        return [("noun", "TUBE"), ("tube_type", "STRT"), ("family", "AS" if a["material_grade"].startswith("A213") else "SS"),
                ("material_grade", grade(a["material_grade"], rng)), ("od_mm", f"{a['od_mm']:g}MM"),
                ("wall_mm", f"{a['wall_mm']:g}MM")]
    return [("noun", f"{kind} TUBE"), ("material_grade", grade(a["material_grade"], rng)),
            ("od_mm", pick(rng, [f"OD {a['od_mm']:g} MM", f"{a['od_mm']:g} MM OD"])),
            ("wall_mm", pick(rng, [f"X {a['wall_mm']:g} MM THK", f"{a['wall_mm']:g} MM WALL"]))]


def t_electrical(a, rng, style):
    if a["equipment_type"] == "transformer":
        hv = a["voltage_hv_kv"]
        ratio = pick(rng, [f"{hv:g}/0.433 KV", f"{hv:g}KV/433V", f"{hv:g} KV / 0.433 KV"])
        return [("noun", pick(rng, ["TRANSFORMER", "DISTRIBUTION TRANSFORMER"])),
                ("rating_kva", f"{a['rating_kva']:g} KVA"), ("voltage_hv_kv", ratio)]
    kw, poles = a["power_kw"], int(a["poles"])
    mount = {"foot": "B3", "flange": "B5", "foot_flange": "B35"}[a["mounting"]]
    if style == "comma":                                                  # dev 41
        toks = [("noun", "MOTOR"), ("kind", "IND"), ("voltage_v", f"{a['voltage_v']:g}VAC"),
                ("phases", "3PH")]
        if a.get("frame"):
            toks.append(("frame", a["frame"]))
        return toks + [("poles", f"{poles}P"), ("mounting", mount), ("power_kw", f"{kw:g}KW")]
    hp = a["power_hp"]
    power = pick(rng, [f"{kw:g} KW", f"{kw:g}KW", f"{hp:.1f} HP" if hp < 10 else f"{hp:.0f} HP"])
    toks = [("noun", pick(rng, ["MOTOR", "INDUCTION MOTOR", "MOTOR, INDUCTION"])), ("power", power),
            ("speed", pick(rng, [f"{a['speed_rpm']:g} RPM", f"{poles} POLE", f"{poles}P"])),
            ("voltage_v", f"{a['voltage_v']:g} V"), ("phases", pick(rng, ["3 PHASE", "3PH"])),
            ("mounting", pick(rng, [mount, {"B3": "FOOT MOUNTED", "B5": "FLANGE MOUNTED", "B35": "B35"}[mount]])),
            ("protection_class", a["protection_class"])]
    if a.get("frame") and rng.random() < 0.5:
        toks.append(("frame", f"FRAME {a['frame']}"))
    return toks


def t_instrument(a, rng, style):
    temp = a["instrument_type"] == "TEMPERATURE_GAUGE"
    rng_txt = f"0-{a['range_max']:g} {'DEG C' if temp else pick(rng, ['BAR', 'BAR G'])}"
    toks = [("noun", "TEMPERATURE GAUGE" if temp else pick(rng, ["PRESSURE GAUGE", "PR GAUGE", "PRESS GAUGE"])),
            ("dial_size_mm", pick(rng, [f"{a['dial_size_mm']:g} MM DIAL", f"{a['dial_size_mm']:g}MM DIAL"])),
            ("range", pick(rng, [rng_txt, f"RANGE {rng_txt}"])),
            ("wetted_material", f"{a['wetted_material']} WETTED" if a["wetted_material"] != "BRASS" else "BRASS")]
    if a.get("connection"):
        toks.append(("connection", a["connection"]))
    return toks


def t_rotating(a, rng, style):
    arr = a["arrangement"].replace("_", " ").upper()
    return [("noun", pick(rng, ["MECHANICAL SEAL", "MECH SEAL", "M/SEAL"])), ("arrangement", arr),
            ("shaft_dia_mm", pick(rng, [f"{a['shaft_dia_mm']:g} MM SHAFT", f"{a['shaft_dia_mm']:g}MM SHAFT"])),
            ("face_materials", a["face_materials"]), ("elastomer", a["elastomer"])]


TOKENS = {"bearing": t_bearing, "pipe": t_pipe, "valve": t_valve, "flange": t_flange, "gasket": t_gasket,
          "fastener": t_fastener, "cable": t_cable, "fitting": t_fitting, "plate": t_plate, "tube": t_tube,
          "electrical": t_electrical, "instrument": t_instrument, "rotating": t_rotating}


# --------------------------------------------------------------------------
# Corruption - storekeeper habits, as in the original generator
# --------------------------------------------------------------------------

SHORTHAND = {"BEARING": ["BRG", "BEARNG", "BER"], "SEAMLESS": ["SMLS"], "STAINLESS STEEL": ["SS", "S.S."],
             "CARBON STEEL": ["CS", "C.S."], "WELD NECK": ["WN", "W/NECK"], "RAISED FACE": ["RF"],
             "SPIRAL WOUND": ["SPL WOUND", "SW"], "MECHANICAL SEAL": ["MECH SEAL", "M/SEAL"],
             "PRESSURE GAUGE": ["PR GAUGE", "PG"], "GRAPHITE FILLER": ["GR FILLER", "GRAPH FILLER"],
             "HAND WHEEL OPERATED": ["HW OPTD"], "GEAR OPERATED": ["GEAR OPTD"]}


def typo(text: str, rng) -> str:
    words = [w for w in text.split() if len(w) > 5 and w.isalpha()]
    if not words:
        return text
    w = pick(rng, words)
    i = rng.randrange(1, len(w) - 1)
    broken = w[:i] + w[i + 1:] if rng.random() < 0.5 else w[:i] + w[i + 1] + w[i] + w[i + 2:]
    return text.replace(w, broken, 1)


def describe(item: dict, style: str, rng: random.Random) -> tuple[str, str | None, str | None]:
    """One description of one item, in one style. Returns (text, brand, part_number)."""
    cat, a = item["category"], item["attributes"]
    toks = [(f, t) for f, t in TOKENS[cat](a, rng, style) if t]
    head, rest = toks[:1], toks[1:]

    if style in ("plain", "sap40"):
        rest = [x for x in rest if rng.random() > 0.12]                 # dropped fields
        if len(rest) > 2 and rng.random() < 0.35:                       # nobody agrees on order
            i, j = rng.sample(range(len(rest)), 2)
            rest[i], rest[j] = rest[j], rest[i]
    elif style in ("comma", "long"):
        rest = [x for x in rest if rng.random() > 0.06]

    brand = part = None
    if cat in BRANDS and rng.random() < (0.5 if style in ("plain", "vendor") else 0.2):
        brand = pick(rng, BRANDS[cat])
        if cat == "bearing":
            part = f"{a['iso_designation']}-{a['seal_type'].replace('OPEN', '')}".rstrip("-")
            part = part.replace("2RS", pick(rng, ["2RS", "2RS1", "2RSR"]))
        elif rng.random() < 0.5:
            part = f"{brand[:3]}/{rng.randrange(100, 999)}/{rng.randrange(10, 99)}"
    tail = [t for t in (brand, part) if t]

    parts = [t for _, t in head + rest] + tail
    if style == "comma":
        text = pick(rng, [", ", ","]).join(parts)
    elif style == "long":
        text = ", ".join(parts)
    elif style in ("vendor", "sentence"):
        text = " ".join(parts)
    else:
        sep = pick(rng, [" ", " ", ", ", ",", " - "])
        text = sep.join(parts)
        for k, v in SHORTHAND.items():
            if k in text and rng.random() < 0.4:
                text = text.replace(k, pick(rng, v))
        if rng.random() < 0.18:
            text = typo(text, rng)
        roll = rng.random()
        text = text.upper() if roll < 0.72 else text.title() if roll < 0.9 else text.lower()
    if style == "sap40":
        text = text.upper()[:40].rstrip(" ,-")
    return re.sub(r"\s+", " ", text).strip(), brand, part


def style_for(cpse: str, split: str, rng: random.Random) -> str:
    if split == "test" and rng.random() < 0.35:
        return pick(rng, TEST_ONLY)
    weights = CPSE_STYLE[cpse]
    r, acc = rng.random(), 0.0
    for style, w in weights.items():
        acc += w
        if r < acc:
            return style
    return "plain"
