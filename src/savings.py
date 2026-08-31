"""
Savings report - demand aggregation across CPSEs.

This is the module that turns a data-cleaning project into a money project.
Once clusters exist it is a GROUP BY over purchase history, roughly an hour of
work, and it produces the one number a ministry actually cares about.

    python src/savings.py

The PS Expected Impact asks for "reduced procurement cost through demand
aggregation" and "foundation for common procurement and strategic sourcing" -
but neither appears in the 8 Key Capabilities, so most teams will skip both.

TWO RULES THIS MODULE ENFORCES

  Report both figures. Best-observed-price is the theoretical maximum - every
  CPSE achieving the best price anyone in the group got. A procurement person
  knows that never happens. Giving the conservative number unprompted is what
  makes the optimistic one credible.

  k-anonymity. With fewer than three CPSEs in a group, the benchmark is
  suppressed - because with two, the minimum price IS the other party's price,
  and showing it hands one company its counterpart's negotiated rate.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict

import paths

# With fewer than this many CPSEs in a group, a "best price" statistic reveals
# an individual company's price rather than a market benchmark.
K_ANONYMITY = 3

# Fraction of the theoretical maximum a real consolidation programme captures.
# Deliberately conservative - joint tendering takes time, some CPSEs have
# contractual commitments, and the best price may reflect a volume we cannot
# replicate.
CAPTURE_RATE = 0.40


def load_purchases() -> dict:
    """Purchase rows keyed by (cpse, source_code) - the join a PO actually has."""
    rows = defaultdict(list)
    with paths.PURCHASES.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows[(r["cpse"], r["source_code"])].append({
                "vendor": r["vendor"],
                "unit_price": float(r["unit_price"]),
                "qty": int(r["qty"]),
                "po_date": r["po_date"],
                "plant": r["plant"],
            })
    return rows


def analyse(item: dict, purchases: dict) -> dict | None:
    """Spend per CPSE for one national code, and what consolidation would save."""
    per_cpse = defaultdict(lambda: {"qty": 0, "value": 0.0, "orders": 0,
                                    "vendors": set(), "prices": []})

    for member in item["members"]:
        key = (member.get("cpse"), member.get("source_code"))
        for po in purchases.get(key, []):
            bucket = per_cpse[member["cpse"]]
            bucket["qty"] += po["qty"]
            bucket["value"] += po["qty"] * po["unit_price"]
            bucket["orders"] += 1
            bucket["vendors"].add(po["vendor"])
            bucket["prices"].append(po["unit_price"])

    if not per_cpse:
        return None

    cpses = []
    for name, b in sorted(per_cpse.items(), key=lambda x: x[1]["value"], reverse=True):
        cpses.append({
            "cpse": name,
            "qty": b["qty"],
            "orders": b["orders"],
            "avg_price": round(b["value"] / b["qty"], 2) if b["qty"] else 0.0,
            "median_price": round(statistics.median(b["prices"]), 2),
            "value": round(b["value"], 2),
            "vendor_count": len(b["vendors"]),
        })

    total_qty = sum(c["qty"] for c in cpses)
    total_value = sum(c["value"] for c in cpses)
    best = min(c["avg_price"] for c in cpses)
    worst = max(c["avg_price"] for c in cpses)

    out = {
        "national_code": item["national_code"],
        "description": item["std_description"],
        "category": item["category"],
        "cpse_count": len(cpses),
        "cpses": cpses,
        "total_qty": total_qty,
        "total_value": round(total_value, 2),
        "orders": sum(c["orders"] for c in cpses),
    }

    # k-anonymity. Below the threshold we report that an overlap exists, but no
    # benchmark - the minimum price would be an individual company's rate.
    if len(cpses) < K_ANONYMITY:
        out.update({"benchmark_suppressed": True,
                    "suppression_reason":
                        f"only {len(cpses)} CPSE(s) - a benchmark here would "
                        f"reveal an individual company's price",
                    "best_price": None, "saving_upper": 0.0, "saving_realistic": 0.0})
        return out

    upper = total_value - best * total_qty
    out.update({
        "benchmark_suppressed": False,
        "best_price": best,
        "worst_price": worst,
        "price_spread_pct": round((worst - best) / best * 100, 1) if best else 0.0,
        "saving_upper": round(upper, 2),
        "saving_realistic": round(upper * CAPTURE_RATE, 2),
    })
    return out


def rupees(amount: float) -> str:
    if amount >= 1e7:
        return f"Rs {amount/1e7:,.2f} cr"
    if amount >= 1e5:
        return f"Rs {amount/1e5:,.1f} L"
    return f"Rs {amount:,.0f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=8, help="how many items to print")
    args = ap.parse_args()

    national = json.loads(paths.NATIONAL_CODES.read_text(encoding="utf-8"))
    purchases = load_purchases()

    reports = [r for r in (analyse(item, purchases) for item in national) if r]
    reports.sort(key=lambda r: r["saving_upper"], reverse=True)

    shared = [r for r in reports if r["cpse_count"] > 1]
    eligible = [r for r in reports if not r["benchmark_suppressed"]]
    suppressed = [r for r in shared if r["benchmark_suppressed"]]

    total_spend = sum(r["total_value"] for r in reports)
    shared_spend = sum(r["total_value"] for r in shared)
    upper = sum(r["saving_upper"] for r in eligible)
    realistic = sum(r["saving_realistic"] for r in eligible)

    paths.ensure_dirs()
    paths.SAVINGS.write_text(json.dumps({
        "summary": {
            "items": len(reports),
            "multi_cpse_items": len(shared),
            "benchmark_eligible": len(eligible),
            "benchmark_suppressed": len(suppressed),
            "total_spend": round(total_spend, 2),
            "shared_spend": round(shared_spend, 2),
            "saving_upper": round(upper, 2),
            "saving_realistic": round(realistic, 2),
            "capture_rate": CAPTURE_RATE,
            "k_anonymity": K_ANONYMITY,
        },
        "items": reports,
    }, indent=1), encoding="utf-8")

    print("DEMAND AGGREGATION")
    print(f"  materials analysed          {len(reports):>6}")
    print(f"  bought by 2+ CPSEs          {len(shared):>6}")
    print(f"  total spend                 {rupees(total_spend):>12}")
    print(f"  spend on shared materials   {rupees(shared_spend):>12}")
    print()
    print(f"  saving, best-observed-price {rupees(upper):>12}   <- upper bound")
    print(f"  saving at {CAPTURE_RATE:.0%} capture       {rupees(realistic):>12}   "
          f"<- quote this one")
    if suppressed:
        print(f"\n  {len(suppressed)} item(s) suppressed under k-anonymity "
              f"(fewer than {K_ANONYMITY} CPSEs)")

    print(f"\ntop {args.top} by saving")
    print("-" * 74)
    for r in reports[: args.top]:
        if r["benchmark_suppressed"]:
            continue
        print(f"\n{r['national_code']}   {r['description'][:56]}")
        for c in r["cpses"]:
            flag = "  <- best" if c["avg_price"] == r["best_price"] else ""
            print(f"    {c['cpse']:<6} {c['qty']:>6,} units  @ Rs {c['avg_price']:>9,.0f}"
                  f"   {rupees(c['value']):>11}{flag}")
        print(f"    {'TOTAL':<6} {r['total_qty']:>6,} units across {r['cpse_count']} CPSEs"
              f"   {rupees(r['total_value']):>11}")
        print(f"    spread {r['price_spread_pct']}%   "
              f"saving {rupees(r['saving_upper'])} upper / "
              f"{rupees(r['saving_realistic'])} realistic")

    print("\n" + "-" * 74)
    print("Say BOTH numbers out loud. The upper bound assumes every CPSE achieves")
    print("the best price anyone got, which never happens - and a procurement")
    print("person in the room will know that. Volunteering the conservative")
    print("figure is what makes the optimistic one believable.")


if __name__ == "__main__":
    main()
