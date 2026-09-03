"""
Unit of measure harmonisation.

    python src/uom.py
    python src/uom.py --show EA        every raw spelling folded into one unit

The PS Background names units of measurement explicitly, alongside cryptic
descriptions, as a reason material masters cannot be compared across CPSEs. It
is a small feature with an outsized effect: a price comparison across two
records is meaningless until both sides agree on what one unit IS.

This data carries ten distinct spellings for two actual units. Six of them -
EACH, EA, NO, NOS, PC, PCS - mean the same thing, and four - METER, M, MTR,
MTS - mean the other. Nobody was wrong; there was simply never an enforced
cataloguing standard, so every storekeeper wrote what they were used to.

TWO RULES

    fold to the standard form, not the popular one
        The winner is the canonical abbreviation, not whichever spelling
        happens to appear most often. Standardising to a popularity contest
        means the answer changes the next time a CPSE uploads.

    never guess across families
        EA and M are different KINDS of unit, not different spellings. A code
        whose members disagree across families is a data error a human must
        look at, not something to auto-resolve.

MT AND MTS ARE GENUINELY AMBIGUOUS and are reported rather than folded. MT is
metre in one company's master and metric tonne in another's; MTS reads as
metres here only because it co-occurs with METER on pipe. Silently picking one
would put a wrong unit inside a national code, so both are surfaced for a
human. See docs/03-reference/domain-facts.md
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict

import paths

# ---------------------------------------------------------------------------
# The fold. Canonical form -> every spelling seen for it.
#
# Deliberately conservative: only spellings we have actually observed or that
# are unambiguous. A dictionary that guesses is worse than one that abstains,
# because the guess is invisible once it is inside an issued national code.
# ---------------------------------------------------------------------------

FAMILIES = {
    "EA": ("Each", {"EA", "EACH", "NO", "NOS", "NUMBER", "PC", "PCS", "PIECE",
                    "PIECES", "UNIT", "U"}),
    "M":  ("Metre", {"M", "MTR", "MTRS", "METER", "METERS", "METRE", "METRES"}),
    "KG": ("Kilogram", {"KG", "KGS", "KILOGRAM", "KILOGRAMS"}),
    "L":  ("Litre", {"L", "LTR", "LTRS", "LITRE", "LITER", "LITRES", "LITERS"}),
    "SET": ("Set", {"SET", "SETS"}),
    "BOX": ("Box", {"BOX", "BOXES", "BX"}),
    "ROLL": ("Roll", {"ROLL", "ROLLS", "RL"}),
}

# Spellings that mean different units in different companies' masters. These
# are NOT folded - they are reported, with both readings named.
AMBIGUOUS = {
    "MT":  ("M", "MT", "metre or metric tonne"),
    "MTS": ("M", "MT", "metres or metric tonnes"),
    "T":   ("MT", "M", "tonne or metre"),
}

_LOOKUP = {raw: canon for canon, (_, raws) in FAMILIES.items() for raw in raws}


def canonical(raw: str) -> tuple[str | None, bool]:
    """(canonical form, is_ambiguous). None when the spelling is unrecognised."""
    key = str(raw or "").strip().upper().replace(".", "")
    if key in AMBIGUOUS:
        return AMBIGUOUS[key][0], True
    return _LOOKUP.get(key), False


def family_label(canon: str) -> str:
    return FAMILIES.get(canon, (canon, set()))[0]


# ---------------------------------------------------------------------------

def load():
    materials = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            materials[row["record_id"]] = row
    national = json.loads(paths.NATIONAL_CODES.read_text(encoding="utf-8"))
    return materials, national


def purchase_prices() -> dict:
    """Median unit price per (cpse, source_code) - for the pack-size check."""
    rows = defaultdict(list)
    if not paths.PURCHASES.exists():
        return {}
    with paths.PURCHASES.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                rows[(r["cpse"], r["source_code"])].append(float(r["unit_price"]))
            except (KeyError, ValueError):
                continue
    return {k: statistics.median(v) for k, v in rows.items() if v}


def build() -> dict:
    materials, national = load()
    prices = purchase_prices()

    # --- what spellings exist at all -------------------------------------
    raw_counts = defaultdict(int)
    for row in materials.values():
        raw_counts[str(row.get("uom", "")).strip().upper()] += 1
    raw_counts.pop("", None)

    families = defaultdict(lambda: {"variants": defaultdict(int), "records": 0})
    unrecognised, ambiguous_seen = {}, {}
    for raw, n in raw_counts.items():
        canon, is_amb = canonical(raw)
        if is_amb:
            reading_a, reading_b, note = AMBIGUOUS[raw.replace(".", "")]
            ambiguous_seen[raw] = {"count": n, "readings": [reading_a, reading_b],
                                   "note": note}
            continue
        if canon is None:
            unrecognised[raw] = n
            continue
        families[canon]["variants"][raw] += n
        families[canon]["records"] += n

    # --- conflicts inside one national code -------------------------------
    conflicts = []
    for c in national:
        seen = defaultdict(lambda: {"count": 0, "cpses": set()})
        by_cpse = defaultdict(set)
        for m in c.get("members", []):
            row = materials.get(m["record_id"])
            if not row:
                continue
            raw = str(row.get("uom", "")).strip().upper()
            if not raw:
                continue
            seen[raw]["count"] += 1
            seen[raw]["cpses"].add(row["cpse"])
            by_cpse[row["cpse"]].add(raw)

        if len(seen) < 2:
            continue

        canons = {canonical(r)[0] for r in seen}
        canons.discard(None)
        # Members disagreeing across FAMILIES is a data error, not a spelling
        # difference - EA and M are not two ways of writing one unit.
        cross_family = len(canons) > 1
        resolved = None if cross_family else (next(iter(canons), None))

        # The most damning case: one company using several spellings for one
        # item. No inter-company coordination is needed to fix this.
        intra = sorted(cpse for cpse, raws in by_cpse.items() if len(raws) > 1)

        # Pack-size hazard. Identical unit spelling, wildly different unit
        # price, means one side is pricing a box and calling it a piece.
        # CLAUDE.md section 7: per-piece vs per-box-of-100 breaks price
        # comparison even after the spellings agree.
        member_prices = []
        for m in c.get("members", []):
            row = materials.get(m["record_id"], {})
            p = prices.get((row.get("cpse"), row.get("source_code")))
            if p:
                member_prices.append((row["cpse"], row["source_code"], p))
        pack_flag = None
        if len(member_prices) >= 2:
            lo = min(member_prices, key=lambda x: x[2])
            hi = max(member_prices, key=lambda x: x[2])
            if lo[2] > 0 and hi[2] / lo[2] >= 10:
                pack_flag = {"ratio": round(hi[2] / lo[2], 1),
                             "low": {"cpse": lo[0], "code": lo[1], "price": round(lo[2], 2)},
                             "high": {"cpse": hi[0], "code": hi[1], "price": round(hi[2], 2)}}

        conflicts.append({
            "national_code": c["national_code"],
            "description": c["std_description"],
            "category": c["category"],
            "resolved_to": resolved,
            "resolved_label": family_label(resolved) if resolved else None,
            "cross_family": cross_family,
            "variant_count": len(seen),
            "variants": sorted(
                ({"raw": r, "count": v["count"], "cpses": sorted(v["cpses"])}
                 for r, v in seen.items()),
                key=lambda x: (-x["count"], x["raw"])),
            "intra_cpse": intra,
            "pack_size_flag": pack_flag,
        })

    conflicts.sort(key=lambda c: (-c["variant_count"], c["national_code"]))

    canonical_units = sorted(families)
    return {
        "summary": {
            "records": len(materials),
            "variants_seen": len(raw_counts),
            "canonical_units": len(canonical_units),
            "units": canonical_units,
            "codes_total": len(national),
            "codes_with_conflict": len(conflicts),
            "cross_family_conflicts": sum(1 for c in conflicts if c["cross_family"]),
            "intra_cpse_conflicts": sum(1 for c in conflicts if c["intra_cpse"]),
            "pack_size_flags": sum(1 for c in conflicts if c["pack_size_flag"]),
            "ambiguous_spellings": sorted(ambiguous_seen),
            "unrecognised": sorted(unrecognised),
        },
        "families": [
            {
                "canonical": canon,
                "label": family_label(canon),
                "records": families[canon]["records"],
                "variants": sorted(
                    ({"raw": r, "count": n} for r, n in families[canon]["variants"].items()),
                    key=lambda x: (-x["count"], x["raw"])),
            }
            for canon in canonical_units
        ],
        "ambiguous": [{"raw": r, **v} for r, v in sorted(ambiguous_seen.items())],
        "unrecognised": [{"raw": r, "count": n} for r, n in sorted(unrecognised.items())],
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", metavar="UNIT",
                    help="list every raw spelling folded into one canonical unit")
    args = ap.parse_args()

    data = build()
    s = data["summary"]

    if args.show:
        want = args.show.strip().upper()
        fam = next((f for f in data["families"] if f["canonical"] == want), None)
        if not fam:
            print(f"no canonical unit '{want}'. known: "
                  f"{', '.join(f['canonical'] for f in data['families'])}")
            return
        print(f"{fam['canonical']}  {fam['label']}   {fam['records']} records")
        for v in fam["variants"]:
            print(f"    {v['raw']:<8} {v['count']:>4}")
        return

    paths.ensure_dirs()
    paths.UOM.write_text(json.dumps(data, indent=1), encoding="utf-8")

    print(f"{s['variants_seen']} spellings -> {s['canonical_units']} units "
          f"({', '.join(s['units'])})")
    for f in data["families"]:
        spellings = ", ".join(v["raw"] for v in f["variants"])
        print(f"    {f['canonical']:<4} {f['label']:<9} {f['records']:>4} records   {spellings}")

    if data["ambiguous"]:
        print("\nAMBIGUOUS - not folded, a human decides")
        for a in data["ambiguous"]:
            print(f"    {a['raw']:<6} x{a['count']:<3} {a['note']}")
    if data["unrecognised"]:
        print("\nunrecognised spellings")
        for u in data["unrecognised"]:
            print(f"    {u['raw']:<6} x{u['count']}")

    print(f"\nCONFLICTS   {s['codes_with_conflict']} of {s['codes_total']} national codes")
    print(f"    same unit, different spelling   "
          f"{s['codes_with_conflict'] - s['cross_family_conflicts']:>3}   auto-resolvable")
    print(f"    across unit families            {s['cross_family_conflicts']:>3}   "
          f"human decides")
    print(f"    one CPSE using several forms    {s['intra_cpse_conflicts']:>3}   "
          f"fixable without asking anyone")
    print(f"    possible pack-size mismatch     {s['pack_size_flags']:>3}")

    print("\nworst first")
    print("-" * 74)
    for c in data["conflicts"][:6]:
        forms = "  ".join(f"{v['raw']}x{v['count']}" for v in c["variants"])
        print(f"  {c['national_code']}  {c['variant_count']} spellings -> "
              f"{c['resolved_to'] or 'HUMAN'}")
        print(f"    {c['description'][:64]}")
        print(f"    {forms}")
        if c["intra_cpse"]:
            print(f"    within one company: {', '.join(c['intra_cpse'])}")


if __name__ == "__main__":
    main()
