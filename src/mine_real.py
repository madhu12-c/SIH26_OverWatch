"""
Mine real material-master lines out of published CPSE tender extracts.

    python src/mine_real.py              download if needed, write candidates.csv
    python src/mine_real.py --force      overwrite, even if labelling has started

WHY THIS EXISTS

No public real CPSE material master exists - GeM, CPPP, data.gov.in, Kaggle and
Hugging Face were all checked. Material masters are internal ERP data; companies
publish tenders, not master tables. So the only real material text available is
what tender documents happen to contain, and most of that is not material text
at all: of 21,513 rows in the public corpus, every one is a tender notice.

The material lines are in three small side files of the same dataset. This
script pulls them, ranks every line by how much it LOOKS like a material-master
entry, and writes a deduplicated shortlist for two people to label by hand.

IT DECIDES NOTHING. The score is a reading-order aid, built from keyword rules
written in an afternoon. It will let some junk through and miss some real lines,
which is exactly why every row it emits is checked by a human.

SOURCE AND LICENCE

Prasenjeet25/sih26099-cpse-material-codes on Hugging Face, CC-BY-4.0. The licence
requires attribution; it is credited in data/real/README.md, the top-level
README, and the references slide. See data/real/README.md.

THE LABELS ARE PRECIOUS. They live in data/real/labels/, keyed by the `rank` this
script assigns (see src/labels.py). Rebuilding candidates.csv could reorder the
ranks under them, so this script refuses once that folder holds any sheet. Use
--force only if you mean to start the labelling over.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from collections import OrderedDict

import paths

BASE = ("https://huggingface.co/datasets/Prasenjeet25/sih26099-cpse-material-codes/"
        "resolve/main/data/processed/extracted_items")

SOURCES = (
    "material_description_corpus.csv",     # 21,513 rows - all tender text, kept to show we checked
    "ntpc_material_items.csv",             # the real material lines
    "ntpc_doc_tables.csv",                 # table cells from NTPC tender PDFs
    "iocl_procurement_plan_items.csv",     # IOCL plan items, mostly equipment groups
)

# A noun that names a physical thing a refinery or power station stocks.
NOUN = re.compile(
    r"\b(pipe|tube|valve|flange|gasket|bearing|bolt|nut|stud|screw|washer|cable|"
    r"wire|pump|motor|seal|coupling|elbow|tee|reducer|nipple|union|plug|gauge|"
    r"transmitter|sensor|thermocouple|filter|strainer|belt|sheet|plate|rod|bar|"
    r"hose|switch|breaker|relay|contactor|fuse|lamp|bulb|fan|blower|compressor|"
    r"turbine|boiler|heater|cooler|exchanger|vessel|tank|drum|column|actuator|"
    r"gland|packing|ring|bush|sleeve|shaft|gear|chain|sprocket|conveyor|insulator|"
    r"transformer|panel|starter|resistor|capacitor|battery|electrode|brick|refractory)\b",
    re.I)

# A token that only appears when someone is stating a specification.
SPEC = re.compile(
    r"(\b\d+(\.\d+)?\s*(mm|cm|mtr|mts?|nb|dn|inch|in\b|\"|kg|gm|mm2|sqmm|kv|v\b|hp|kw|"
    r"bar|psi|rpm|deg|mesh|swg|awg|gauge)|"
    r"\bss\s?\d{3}l?\b|\bms\b|\bcs\b|\bwcb\b|\bcf8m?\b|"
    r"\b(astm|asme|api|ansi|din|jis|bs|is)\s?[a-z]?\s?\d{2,5}\b|"
    r"\bsch\s?\d{1,3}\b|\bcl(ass)?\s?\d{3}\b|\b\d{3,4}\s?#|"
    r"\bgr(ade)?\.?\s?[a-z0-9]{1,4}\b|\b\d{1,2}\.\d\b)", re.I)

# Words that mean this is a tender, a service, or a bidding rule - not an item.
NOISE = re.compile(
    r"\b(tender|bidder|bidding|bid\b|emd|applicant|eligibility|turnover|"
    r"contract|agreement|amc|maintenance|hiring|hire|manpower|consultancy|"
    r"survey|erection|commissioning|installation work|civil work|last date|"
    r"due date|corrigendum|annexure|clause|shall be submitted|as per|scope of work|"
    r"pre.?bid|earnest money|security deposit|experience of|should have|must have|"
    r"during last|financial year|rs\.?\s?\d|crore|lakh|per annum|validity)\b", re.I)

SEPS = re.compile(r"[,:;/]")

FIELDS = ["rank", "score", "description", "organization", "kind", "unit",
          "quantity", "source"]


def score(text: str) -> int:
    """How much does this look like a material-master line? Higher reads first."""
    t = text.strip()
    n = len(t)
    if n < 12 or n > 140 or NOISE.search(t) or not NOUN.search(t):
        return 0
    specs = len(SPEC.findall(t))
    if not specs:
        return 0

    s = min(specs, 5) * 10                       # more stated specs is better
    s += min(len(SEPS.findall(t)), 6) * 6        # comma / colon structure
    if t.isupper():
        s += 12                                  # master data is usually capitals
    if n <= 70:
        s += 8                                   # line items are short
    if re.match(r"^[A-Z][A-Z\s]{2,}[:,]", t):
        s += 15                                  # "PIPE:BLK," / "CABLE, PWR,"
    if sum(c.isalpha() for c in t) < n * 0.35:
        s -= 20                                  # mostly digits = a code, not a description
    return max(s, 0)


def fetch_sources() -> None:
    """Download any source extract not already on disk."""
    paths.REAL_SOURCE.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        target = paths.REAL_SOURCE / name
        if target.exists() and target.stat().st_size > 0:
            continue
        print(f"  downloading {name}")
        urllib.request.urlretrieve(f"{BASE}/{name}", target)


def rows_from(name, text_cols, org, kind, url_cols=()):
    path = paths.REAL_SOURCE / name
    if not path.exists():
        return
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            for col in text_cols:
                val = (r.get(col) or "").strip()
                if not val:
                    continue
                # ntpc_doc_tables packs several table cells into one field
                for part in (val.split("|") if col == "cells" else [val]):
                    part = re.sub(r"\s+", " ", part).strip(" |-\t")
                    sc = score(part)
                    if sc:
                        yield {
                            "score": sc,
                            "description": part,
                            "organization": r.get("organization") or org,
                            "kind": r.get("description_kind") or kind,
                            "unit": r.get("unit") or "",
                            "quantity": r.get("quantity") or "",
                            "source": next((r[c] for c in url_cols if r.get(c)),
                                           r.get("doc_name", "")),
                        }


def labelling_started() -> bool:
    return paths.REAL_LABELS.exists() and any(paths.REAL_LABELS.glob("*.csv"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="overwrite candidates.csv even if labelling has started")
    args = ap.parse_args()

    if labelling_started() and not args.force:
        print(f"{paths.REAL_LABELS} already holds label sheets keyed to these ranks.")
        print("Refusing to rebuild under them. Use --force only to restart labelling.")
        sys.exit(1)

    fetch_sources()

    found = []
    found += rows_from("material_description_corpus.csv", ["description"], "", "",
                       ("document_url", "source_url"))
    found += rows_from("ntpc_material_items.csv", ["item_text"],
                       "NTPC Limited", "ntpc_material_item", ("doc_name",))
    found += rows_from("iocl_procurement_plan_items.csv", ["item_description"],
                       "Indian Oil Corporation Limited", "iocl_plan_item", ("source_pdf",))
    found += rows_from("ntpc_doc_tables.csv", ["cells"],
                       "NTPC Limited", "ntpc_doc_table", ("doc_name",))

    # Keep the best-scoring instance of each distinct description.
    best = OrderedDict()
    for row in sorted(found, key=lambda r: -r["score"]):
        key = re.sub(r"[^A-Z0-9]", "", row["description"].upper())
        best.setdefault(key, row)
    out = list(best.values())

    paths.REAL.mkdir(parents=True, exist_ok=True)
    with paths.REAL_CANDIDATES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for i, r in enumerate(out, 1):
            w.writerow({"rank": i, **r})

    orgs = {}
    for r in out:
        orgs[r["organization"] or "(blank)"] = orgs.get(r["organization"] or "(blank)", 0) + 1

    print(f"{len(found):,} raw hits -> {len(out):,} distinct candidates")
    print(f"wrote {paths.REAL_CANDIDATES}")
    for org, n in sorted(orgs.items(), key=lambda x: -x[1]):
        print(f"  {org:<34} {n:>4}")
    print("\nscore bands - label from the top down")
    for lo, hi in ((60, 999), (40, 59), (25, 39), (1, 24)):
        print(f"  {lo:>3}-{hi:<3} {sum(1 for r in out if lo <= r['score'] <= hi):>5}")


if __name__ == "__main__":
    main()
