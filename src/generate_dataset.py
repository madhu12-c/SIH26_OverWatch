"""
Synthetic CPSE material master generator.

Builds three files that the rest of the pipeline consumes:

    materials.csv      every raw record, as a CPSE's SAP export would look
    purchases.csv      purchase order history per record
    ground_truth.csv   record_id -> true_item_id  (the answer key)

The point of generating our own data is that we know the correct answer, so the
evaluation harness can report real precision and recall instead of a demo and a
hope.

Honest caveat, stated in CLAUDE.md and worth repeating here: we design the
corruption, so "98% precision" means "we reversed 98% of the errors we ourselves
introduced". That is circular. The fix is a hand-labelled hold-out of real
records from GeM / eprocure, reported alongside this number.

Deterministic by design - the same seed always produces the same dataset, so the
demo never changes under us.

    python generate_dataset.py                      # 15 items, ~100 records
    python generate_dataset.py --items 80 --target 600
    python generate_dataset.py --seed-file seed_items.csv    # Isha's research
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import paths

# --------------------------------------------------------------------------
# CPSEs. Each writes its material codes in its own format, which is half the
# reason the same item looks like four different items.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Cpse:
    name: str
    code_fmt: str          # {n} is filled with a running number
    plants: tuple[str, ...]
    price_bias: float      # how this CPSE's negotiated prices sit vs the base


CPSES = (
    Cpse("CPCL", "1000{n:05d}",  ("Manali", "Cauvery Basin"),        1.00),
    Cpse("IOCL", "MAT-{n:05d}",  ("Panipat", "Mathura", "Barauni"),  0.87),
    Cpse("ONGC", "50{n:05d}",    ("Hazira", "Uran", "Mumbai High"),  1.09),
    Cpse("BPCL", "BR-{n:05d}",   ("Kochi", "Mumbai"),                0.96),
    Cpse("GAIL", "G/{n:06d}",    ("Vijaipur", "Hazira"),             1.14),
)

# --------------------------------------------------------------------------
# Seed items - real refinery MRO nomenclature.
#
# CPCL is a refinery, so the judging panel thinks in pipes, valves, gaskets,
# pumps, bearings and instrumentation. Not steel-plant or mining stock.
#
# `traps` records deliberate near-misses that must NEVER be merged. These are
# what the safety interlock report is built from.
# --------------------------------------------------------------------------

@dataclass
class SeedItem:
    item_id: str
    category: str
    noun: str
    modifiers: list[str]              # ordered, most-significant first
    uom: str
    base_price: float                 # INR per uom
    brands: list[str] = field(default_factory=list)
    part_numbers: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)


SEED_ITEMS: list[SeedItem] = [
    SeedItem(
        "ITM-001", "bearing", "BEARING",
        ["BALL", "DEEP GROOVE", "6205", "25X52X15 MM", "2RS SEALED"],
        "EA", 1310,
        brands=["SKF", "FAG", "NTN", "NBC"],
        part_numbers=["6205-2RS", "6205-2RSR", "6205LLU", "6205 2RS1"],
        vendors=["SKF India Ltd", "Schaeffler India", "Bearing House Chennai"],
    ),
    SeedItem(
        "ITM-002", "bearing", "BEARING",
        ["BALL", "DEEP GROOVE", "6206", "30X62X16 MM", "2RS SEALED"],
        "EA", 1580,
        brands=["SKF", "FAG", "NBC"],
        part_numbers=["6206-2RS", "6206-2RSR", "6206 2RS1"],
        vendors=["SKF India Ltd", "Schaeffler India"],
    ),
    SeedItem(
        "ITM-003", "gasket", "GASKET",
        ["SPIRAL WOUND", "SS316", "4 IN", "150#", "GRAPHITE FILLER"],
        "EA", 485,
        brands=["Champion", "Flexitallic", "IGP"],
        part_numbers=["SW-316-4-150", "FLX/SW/316/4"],
        vendors=["Flexitallic India", "Champion Seals", "IGP Engineers"],
    ),
    SeedItem(
        "ITM-004", "gasket", "GASKET",
        ["SPIRAL WOUND", "SS304", "4 IN", "150#", "GRAPHITE FILLER"],
        "EA", 392,
        brands=["Champion", "Flexitallic", "IGP"],
        part_numbers=["SW-304-4-150", "FLX/SW/304/4"],
        vendors=["Flexitallic India", "Champion Seals"],
    ),
    SeedItem(
        "ITM-005", "pipe", "PIPE",
        ["SEAMLESS", "CARBON STEEL", "ASTM A106 GR B", "4 IN", "SCH 40"],
        "MTR", 2240,
        brands=["Jindal", "MSL", "ISMT"],
        part_numbers=["A106B-4-40", "JSL/A106/4"],
        vendors=["Jindal Saw Ltd", "ISMT Ltd", "Maharashtra Seamless"],
    ),
    SeedItem(
        "ITM-006", "pipe", "PIPE",
        ["SEAMLESS", "STAINLESS STEEL", "ASTM A312 TP316", "2 IN", "SCH 40"],
        "MTR", 4870,
        brands=["Jindal", "Ratnamani"],
        part_numbers=["A312-316-2-40", "RMT/A312/2"],
        vendors=["Ratnamani Metals", "Jindal Saw Ltd"],
    ),
    SeedItem(
        "ITM-007", "valve", "VALVE",
        ["GATE", "6 IN", "150#", "CAST STEEL BODY", "FLANGED", "API 600"],
        "EA", 28400,
        brands=["Kirloskar", "Audco", "BDK"],
        part_numbers=["GV-6-150-CS", "AUD/GT/6/150"],
        vendors=["L&T Valves", "Kirloskar Brothers", "BDK Engineering"],
    ),
    SeedItem(
        "ITM-008", "valve", "VALVE",
        ["GATE", "6 IN", "300#", "CAST STEEL BODY", "FLANGED", "API 600"],
        "EA", 41200,
        brands=["Kirloskar", "Audco", "BDK"],
        part_numbers=["GV-6-300-CS", "AUD/GT/6/300"],
        vendors=["L&T Valves", "Kirloskar Brothers"],
    ),
    SeedItem(
        "ITM-009", "valve", "VALVE",
        ["BALL", "2 IN", "800#", "SS316 BODY", "SCREWED END", "FULL BORE"],
        "EA", 8950,
        brands=["Audco", "Virgo", "Microfinish"],
        part_numbers=["BV-2-800-316", "VRG/BL/2/800"],
        vendors=["Virgo Engineers", "L&T Valves", "Microfinish Valves"],
    ),
    SeedItem(
        "ITM-010", "fastener", "BOLT",
        ["HEX HEAD", "M12 X 50", "SS316", "FULL THREAD", "IS 1364"],
        "EA", 42,
        brands=["Unbrako", "TVS", "Sundram"],
        part_numbers=["HB-M12-50-316", "TVS/HX/M12/50"],
        vendors=["Sundram Fasteners", "TVS Fasteners", "Precision Bolts"],
    ),
    SeedItem(
        "ITM-011", "fastener", "STUD BOLT",
        ["FULL THREAD", "M20 X 120", "ASTM A193 B7", "WITH 2 NUTS A194 2H"],
        "EA", 186,
        brands=["Sundram", "Unbrako"],
        part_numbers=["SB-M20-120-B7", "SF/A193/M20"],
        vendors=["Sundram Fasteners", "Precision Bolts"],
    ),
    SeedItem(
        "ITM-012", "flange", "FLANGE",
        ["WELD NECK", "RAISED FACE", "4 IN", "150#", "ASTM A105", "SCH 40 BORE"],
        "EA", 1840,
        brands=["Echjay", "Citizen", "Kalikund"],
        part_numbers=["WNRF-4-150-A105", "ECH/WN/4/150"],
        vendors=["Echjay Forgings", "Citizen Metalloys", "Kalikund Steel"],
    ),
    SeedItem(
        "ITM-013", "rotating", "MECHANICAL SEAL",
        ["CARTRIDGE", "SINGLE", "45 MM SHAFT", "SIC VS CARBON", "VITON"],
        "EA", 24600,
        brands=["Burgmann", "John Crane", "Flowserve"],
        part_numbers=["MS-45-SIC-VIT", "JC/T21/45"],
        vendors=["John Crane India", "EagleBurgmann India", "Flowserve India"],
    ),
    SeedItem(
        "ITM-014", "instrument", "PRESSURE GAUGE",
        ["BOURDON", "100 MM DIAL", "0-10 BAR", "SS316 WETTED", "1/2 IN NPT BOTTOM"],
        "EA", 3250,
        brands=["Wika", "Forbes Marshall", "Baumer"],
        part_numbers=["PG-100-10-316", "WIKA/213.53/100"],
        vendors=["Wika India", "Forbes Marshall", "Baumer Technologies"],
    ),
    SeedItem(
        "ITM-015", "electrical", "MOTOR",
        ["INDUCTION", "3 PHASE", "5 HP", "1440 RPM", "FOOT MOUNTED", "IP55", "415 V"],
        "EA", 18700,
        brands=["Crompton", "ABB", "Siemens", "Kirloskar"],
        part_numbers=["MTR-5HP-1440-B3", "ABB/M2BAX/112"],
        vendors=["ABB India", "Crompton Greaves", "Siemens India"],
    ),
]

# Deliberate near-misses. A merge across any of these pairs is a safety failure,
# and the interlock report counts exactly these.
TRAPS = [
    ("ITM-003", "ITM-004", "material grade mismatch (SS316 vs SS304)"),
    ("ITM-007", "ITM-008", "pressure rating mismatch (150# vs 300#)"),
    ("ITM-001", "ITM-002", "bearing designation mismatch (6205 vs 6206)"),
    ("ITM-005", "ITM-006", "material grade mismatch (CS vs SS316)"),
]

# --------------------------------------------------------------------------
# Corruption. These patterns are modelled on how real GeM / eprocure / SAP
# descriptions actually vary - not invented for effect.
# --------------------------------------------------------------------------

ABBREVIATIONS = {
    "BEARING": ["BRG", "BEARNG", "BER"],
    "DEEP GROOVE": ["DP GRV", "DEEP GRV", "D/GROOVE"],
    "STAINLESS STEEL": ["SS", "S.S.", "STNLS STL"],
    "CARBON STEEL": ["CS", "C.S.", "CARB STL"],
    "MILD STEEL": ["MS", "M.S."],
    "CAST STEEL BODY": ["CS BODY", "C.S. BODY", "CAST STL BODY"],
    "SEAMLESS": ["SMLS", "SEAMLES"],
    "SCH 40": ["SCH40", "SCHEDULE 40", "SCH-40"],
    "HEX HEAD": ["HEX HD", "HEXAGONAL HEAD", "HH"],
    "FULL THREAD": ["FT", "F/THREAD", "FULL THRD"],
    "WELD NECK": ["WN", "W/NECK", "WELDNECK"],
    "RAISED FACE": ["RF", "R/FACE"],
    "PRESSURE GAUGE": ["PRESS GAUGE", "PG", "PR GAUGE"],
    "MECHANICAL SEAL": ["MECH SEAL", "M/SEAL", "MECH. SEAL"],
    "INDUCTION": ["IND", "INDUCTN"],
    "3 PHASE": ["3PH", "3-PH", "THREE PHASE"],
    "FOOT MOUNTED": ["FT MTD", "B3", "FOOT MTD"],
    "SCREWED END": ["SCRD END", "SCR END", "THREADED END"],
    "GRAPHITE FILLER": ["GRAPH FILLER", "GR FILLER", "GRAPHITE FILL"],
    "SPIRAL WOUND": ["SPL WOUND", "SW", "SPIRALWOUND"],
    "STUD BOLT": ["STUD BLT", "ST BOLT", "S/BOLT"],
    "WITH 2 NUTS": ["W/2 NUTS", "C/W 2 NUTS", "+ 2 NUTS"],
    "CARTRIDGE": ["CART", "CTG"],
    "BOURDON": ["BRDN", "BOURDN"],
}

UOM_VARIANTS = {
    "EA":  ["EA", "NOS", "NO", "PCS", "PC", "EACH"],
    "MTR": ["MTR", "M", "MTRS", "MTS", "METER"],
    "KG":  ["KG", "KGS", "K.G.", "KILOGRAM"],
}


def abbreviate(text: str, rng: random.Random, n: int = 2) -> str:
    """Replace some spelled-out terms with a storekeeper's shorthand."""
    hits = [k for k in ABBREVIATIONS if k in text]
    rng.shuffle(hits)
    for key in hits[:n]:
        text = text.replace(key, rng.choice(ABBREVIATIONS[key]))
    return text


def vary_units(text: str, rng: random.Random) -> str:
    """The same dimension written three different ways.

    Word-bounded on purpose: an unbounded " IN" replacement turns INDUCTION into
    "DUCTION, which is not a corruption any storekeeper has ever made and reads
    as obviously fabricated data.
    """
    text = re.sub(r"(?<=\d)\s*MM\b", lambda _: rng.choice([" MM", "MM", " mm", " M.M."]), text)
    text = re.sub(r"(?<=\d)\s*IN\b", lambda _: rng.choice([" IN", '"', " INCH", "IN"]), text)
    text = re.sub(r"(?<=\d)\s*[Xx]\s*(?=\d)", lambda _: rng.choice(["X", "x", "*", " X "]), text)
    return text


def introduce_typo(text: str, rng: random.Random) -> str:
    """One realistic keyboard slip: a dropped or transposed character."""
    words = [w for w in text.split() if len(w) > 4]
    if not words:
        return text
    word = rng.choice(words)
    i = rng.randrange(1, len(word) - 1)
    if rng.random() < 0.5:
        broken = word[:i] + word[i + 1:]                              # drop
    else:
        broken = word[:i] + word[i + 1] + word[i] + word[i + 2:]      # transpose
    return text.replace(word, broken, 1)


def drop_attribute(mods: list[str], rng: random.Random) -> list[str]:
    """Storekeepers run out of characters and cut the tail off."""
    if len(mods) <= 2:
        return mods
    keep = rng.randrange(2, len(mods))
    return mods[:keep]


def reorder(mods: list[str], rng: random.Random) -> list[str]:
    """Nothing forces modifier order, so nobody agrees on one."""
    mods = list(mods)
    if len(mods) > 2:
        i, j = rng.sample(range(len(mods)), 2)
        mods[i], mods[j] = mods[j], mods[i]
    return mods


def apply_case(text: str, rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.70:
        return text.upper()
    if roll < 0.88:
        return text.title()
    return text.lower()


def join_tokens(noun: str, mods: list[str], rng: random.Random) -> str:
    sep = rng.choice([" ", " ", " ", ", ", ",", " - "])
    return noun + (sep if sep != " " else " ") + sep.join(mods)


# --------------------------------------------------------------------------
# Record construction
# --------------------------------------------------------------------------

def make_description(item: SeedItem, rng: random.Random) -> tuple[str, str | None, str | None]:
    """One corrupted description, plus the brand and part number used (if any)."""
    mods = list(item.modifiers)

    if rng.random() < 0.45:
        mods = drop_attribute(mods, rng)
    if rng.random() < 0.40:
        mods = reorder(mods, rng)

    brand = rng.choice(item.brands) if item.brands and rng.random() < 0.65 else None
    part_no = rng.choice(item.part_numbers) if item.part_numbers and rng.random() < 0.45 else None

    tail = [t for t in (brand, part_no) if t]
    text = join_tokens(item.noun, mods + tail, rng)

    if rng.random() < 0.55:
        text = abbreviate(text, rng)
    if rng.random() < 0.60:
        text = vary_units(text, rng)
    if rng.random() < 0.22:
        text = introduce_typo(text, rng)

    text = apply_case(text, rng)
    return " ".join(text.split()), brand, part_no


# Two records the demo depends on. They are injected verbatim so that no random
# corruption can ever break the story on stage.
GUARANTEED = [
    # Functional equivalence: different brand, different part number, same bearing.
    dict(item_id="ITM-001", cpse="CPCL",
         desc="SKF 6205-2RS DEEP GROOVE BALL BEARING", uom="EA"),
    dict(item_id="ITM-001", cpse="IOCL",
         desc="FAG 6205-2RSR BEARING, 25X52X15MM, SEALED", uom="NOS"),
    # Grade trap: near-identical text, must never merge.
    dict(item_id="ITM-003", cpse="ONGC",
         desc="GASKET SPIRAL WOUND SS316 4IN 150#", uom="EA"),
    dict(item_id="ITM-004", cpse="BPCL",
         desc="GASKET SPIRAL WOUND SS304 4IN 150#", uom="EA"),
]


def build(items: list[SeedItem], target_records: int, rng: random.Random):
    materials, truth, purchases = [], [], []
    counters = {c.name: 1000 + rng.randrange(500) for c in CPSES}
    by_name = {c.name: c for c in CPSES}
    rec_n = 0

    def emit(item: SeedItem, cpse: Cpse, desc: str, uom: str,
             brand: str | None = None, part_no: str | None = None) -> str:
        nonlocal rec_n
        rec_n += 1
        rid = f"R{rec_n:05d}"
        counters[cpse.name] += rng.randrange(1, 40)
        source_code = cpse.code_fmt.format(n=counters[cpse.name])
        plant = rng.choice(cpse.plants)

        materials.append(dict(
            record_id=rid, cpse=cpse.name, source_code=source_code,
            description=desc, uom=uom, material_group=item.category.upper()[:8],
            plant=plant,
        ))
        truth.append(dict(record_id=rid, true_item_id=item.item_id))

        # Purchase history. Price spread across CPSEs is what the savings
        # report is built on, so it has to be real and not noise.
        for _ in range(rng.randrange(1, 5)):
            price = item.base_price * cpse.price_bias * rng.uniform(0.94, 1.07)
            purchases.append(dict(
                cpse=cpse.name, source_code=source_code,
                vendor=rng.choice(item.vendors) if item.vendors else "UNKNOWN",
                unit_price=round(price, 2),
                qty=rng.choice([5, 10, 20, 25, 50, 100, 200, 400]),
                po_date=(date(2025, 4, 1) + timedelta(days=rng.randrange(0, 500))).isoformat(),
                plant=plant,
            ))
        return rid

    for g in GUARANTEED:
        item = next(i for i in items if i.item_id == g["item_id"])
        emit(item, by_name[g["cpse"]], g["desc"], g["uom"])

    # Spread the remaining records over the seed items, with an uneven number of
    # variants each - real masters are lumpy, not uniform.
    remaining = max(0, target_records - len(materials))
    weights = [rng.uniform(0.5, 2.0) for _ in items]
    total_w = sum(weights)
    for item, w in zip(items, weights):
        n_var = max(1, round(remaining * w / total_w))
        chosen = rng.sample(CPSES, k=min(len(CPSES), max(2, rng.randrange(2, 6))))
        for k in range(n_var):
            cpse = chosen[k % len(chosen)]
            desc, brand, part_no = make_description(item, rng)
            uom = rng.choice(UOM_VARIANTS.get(item.uom, [item.uom]))
            emit(item, cpse, desc, uom, brand, part_no)

    return materials, truth, purchases


# --------------------------------------------------------------------------
# Factory mode - thousands of valid items (catalogue.py), written in the
# notations real companies use (render.py). Used when --dup is given.
# --------------------------------------------------------------------------

DEMO_ITEMS = [
    ("bearing", {"iso_designation": "6205", "seal_type": "2RS"}),
    ("gasket", {"gasket_type": "spiral_wound", "material_grade": "SS316", "nominal_size_in": 4.0,
                "pressure_class": "150#", "filler": "GRAPHITE", "thickness_mm": 4.5}),
    ("gasket", {"gasket_type": "spiral_wound", "material_grade": "SS304", "nominal_size_in": 4.0,
                "pressure_class": "150#", "filler": "GRAPHITE", "thickness_mm": 4.5}),
]
# How many EXTRA records a duplicated item gets. Lumpy, like a real master:
# most duplicated items appear twice, a few five times.
EXTRA_COPIES = ((1, 0.60), (2, 0.25), (3, 0.10), (4, 0.05))


def build_factory(target: int, dup: float, rng: random.Random):
    import catalogue
    import render
    import schemas

    n_items = min(round(target * (1 - dup)), len(catalogue.universe()))
    items = catalogue.sample(n_items, rng, must_have=DEMO_ITEMS)
    by_id = {it["item_id"]: it for it in items}
    demo_ids = [items[0]["item_id"], items[0]["item_id"], items[1]["item_id"], items[2]["item_id"]]

    copies = {it["item_id"]: 1 for it in items}
    copies[demo_ids[0]] -= 1                         # the guaranteed records count as its copies
    copies[items[1]["item_id"]] -= 1
    copies[items[2]["item_id"]] -= 1
    extra = target - sum(copies.values()) - len(GUARANTEED)
    order = [it["item_id"] for it in items]
    while extra > 0:
        iid = order[rng.randrange(len(order))]
        r, acc = rng.random(), 0.0
        for k, w in EXTRA_COPIES:
            acc += w
            if r < acc:
                break
        k = min(k, extra)
        copies[iid] += k
        extra -= k

    materials, truth, purchases = [], [], []
    counters = {c.name: 1000 + rng.randrange(500) for c in CPSES}
    by_name = {c.name: c for c in CPSES}

    def emit(item, cpse, desc, uom, style, pack=1, plant=None):
        rid = f"R{len(materials) + 1:05d}"
        counters[cpse.name] += rng.randrange(1, 9)
        source_code = cpse.code_fmt.format(n=counters[cpse.name])
        plant = plant or rng.choice(cpse.plants)
        materials.append(dict(record_id=rid, cpse=cpse.name, source_code=source_code, description=desc,
                              uom=uom, material_group=item["category"].upper()[:8], plant=plant))
        truth.append(dict(record_id=rid, true_item_id=item["item_id"], family_id=item["family_id"],
                          split=item["split"], style=style, pack=pack))
        vendors = render.VENDORS.get(item["category"], ["Refinery Stores Supplier"])
        for _ in range(rng.randrange(1, 5)):
            price = item["base_price"] * pack * cpse.price_bias * rng.uniform(0.94, 1.07)
            purchases.append(dict(cpse=cpse.name, source_code=source_code, vendor=rng.choice(vendors),
                                  unit_price=round(price, 2),
                                  qty=rng.choice([1, 2, 5, 10, 20, 25, 50, 100]) if pack == 1 else rng.choice([1, 2, 5]),
                                  po_date=(date(2025, 4, 1) + timedelta(days=rng.randrange(0, 500))).isoformat(),
                                  plant=plant))
        return rid

    for g, iid in zip(GUARANTEED, demo_ids):
        emit(by_id[iid], by_name[g["cpse"]], g["desc"], g["uom"], "guaranteed")

    for it in items:
        n = copies[it["item_id"]]
        if n <= 0:
            continue
        # Mostly different companies; now and then a second plant of the same
        # one - the within-company duplicate that needs no data sharing to fix.
        cps = rng.sample(CPSES, k=min(n, len(CPSES)))
        while len(cps) < n:
            cps.append(rng.choice(CPSES))
        for cpse in cps:
            style = render.style_for(cpse.name, it["split"], rng)
            desc, _, _ = render.describe(it, style, rng)
            uom = rng.choice(UOM_VARIANTS.get(it["uom"], [it["uom"]]))
            pack = 1
            # Pack sizes: a box of 100 against each. The price guard sees a
            # 100x gap on the same item - the case C13 exists to handle.
            if it["category"] == "fastener" and rng.random() < 0.02:
                pack, uom = 100, rng.choice(["BOX", "BOX OF 100", "PKT"])
            emit(it, cpse, desc, uom, style, pack)

    trap_list = catalogue.traps(items, schemas.hard_fields)
    return materials, truth, purchases, items, trap_list


def load_seed_file(path: Path) -> list[SeedItem]:
    """Swap in a researched seed list (Isha's GeM / eprocure spreadsheet).

    Expected columns: item_id, category, noun, modifiers (| separated), uom,
    base_price, brands, part_numbers, vendors (all | separated).
    """
    out = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            split = lambda k: [s.strip() for s in (row.get(k) or "").split("|") if s.strip()]
            out.append(SeedItem(
                item_id=row["item_id"].strip(),
                category=row["category"].strip(),
                noun=row["noun"].strip().upper(),
                modifiers=[m.upper() for m in split("modifiers")],
                uom=(row.get("uom") or "EA").strip().upper(),
                base_price=float(row.get("base_price") or 100),
                brands=split("brands"), part_numbers=split("part_numbers"),
                vendors=split("vendors"),
            ))
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=100, help="approximate record count")
    ap.add_argument("--seed", type=int, default=20260901, help="RNG seed - keep fixed for demos")
    ap.add_argument("--seed-file", type=Path, default=None,
                    help=f"CSV of researched seed items (default: {paths.SEED_ITEMS} if it exists)")
    ap.add_argument("--dup", type=float, default=None,
                    help="factory mode: duplication rate, e.g. 0.20 with --target 15000 "
                         "(run under SIH_RUN=15k so the demo set is untouched)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.dup is not None:
        if not paths.RUN:
            raise SystemExit("factory mode writes a whole new dataset - set SIH_RUN (e.g. SIH_RUN=15k) "
                             "so the 100-record demo set in data/input is not overwritten")
        import time
        started = time.time()
        materials, truth, purchases, items, trap_list = build_factory(args.target, args.dup, rng)
        paths.ensure_dirs()
        write_csv(paths.MATERIALS, materials)
        write_csv(paths.PURCHASES, purchases)
        write_csv(paths.GROUND_TRUTH, truth)
        paths.TRAPS.write_text(json.dumps(trap_list), encoding="utf-8")
        paths.ITEMS.write_text(json.dumps({it["item_id"]: it for it in items}), encoding="utf-8")
        per_item = {}
        for t in truth:
            per_item[t["true_item_id"]] = per_item.get(t["true_item_id"], 0) + 1
        test = sum(1 for t in truth if t["split"] == "test")
        from collections import Counter
        print(f"run '{paths.RUN}': {paths.INPUT.parent}")
        print(f"materials.csv     {len(materials):>6,} records on {len(per_item):,} items "
              f"({1 - len(per_item) / len(materials):.1%} duplication)")
        print(f"                  test families {test:,} records - locked, never tuned on")
        print(f"purchases.csv     {len(purchases):>6,} purchase orders")
        print(f"traps.json        {len(trap_list):>6,} near-miss pairs, one hard field apart")
        print("styles            " + "  ".join(f"{k} {v}" for k, v in Counter(t["style"] for t in truth).most_common()))
        print(f"done in {time.time() - started:.1f}s")
        return

    seed_file = args.seed_file or (paths.SEED_ITEMS if paths.SEED_ITEMS.exists() else None)
    items = load_seed_file(seed_file) if seed_file else SEED_ITEMS
    if seed_file:
        print(f"using researched seed list: {seed_file.name} ({len(items)} items)\n")

    materials, truth, purchases = build(items, args.target, rng)

    paths.ensure_dirs()
    write_csv(paths.MATERIALS, materials)
    write_csv(paths.PURCHASES, purchases)
    write_csv(paths.GROUND_TRUTH, truth)

    # The trap list drives the safety interlock report, so ship it as data
    # rather than hard-coding it again downstream.
    paths.TRAPS.write_text(json.dumps(
        [dict(a=a, b=b, reason=r) for a, b, r in TRAPS], indent=2), encoding="utf-8")

    per_item: dict[str, int] = {}
    for t in truth:
        per_item[t["true_item_id"]] = per_item.get(t["true_item_id"], 0) + 1

    print(f"materials.csv     {len(materials):>5} records")
    print(f"ground_truth.csv  {len(truth):>5} rows, {len(per_item)} true items")
    print(f"purchases.csv     {len(purchases):>5} purchase orders")
    print(f"traps.json        {len(TRAPS):>5} deliberate near-miss pairs")
    print(f"\nduplication rate  {1 - len(per_item) / len(materials):.1%}"
          f"   ({len(materials)} raw -> {len(per_item)} unique)")
    print(f"variants per item  min {min(per_item.values())}, max {max(per_item.values())}")


if __name__ == "__main__":
    main()
