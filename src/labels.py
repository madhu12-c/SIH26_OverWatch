"""
Real-data labelling - split the rows, label them, compare two people.

    python src/labels.py start          freeze the split, write every sheet blank
    python src/labels.py report         what the dev labels say about the data
    python src/labels.py compare        agreement numbers + a disagreements sheet
    python src/labels.py finalise       merge both test sheets into the gold file

TWO HALVES, TWO JOBS

    dev    labelled by whoever is building the extractor, and used to build it.
           Looking at these rows, tuning on them, writing patterns from them -
           all allowed. So a score on dev proves nothing, and is never reported
           as a result.
    test   held back. Nobody tunes on these rows. Two people label them
           separately; the agreed labels are the real-data number on a slide.

Why the builder cannot label the proof set: if the person (or the AI) writing
the extractor also writes its answer key, the test measures that author's
agreement with themselves - the same circularity the synthetic data has.

Rows inspected while the extractor was being designed, before this split
existed, go to dev by rule. The rest split on a hash of the text, so the split
never depends on anyone's choice and never changes.

WHY TWO TEST SHEETS

The protocol says two people label WITHOUT seeing each other's answers. One
shared file cannot honour that: whoever labels second sees the first person's
marks, and agreement between them stops meaning anything. So each labeller gets
a sheet of their own, and this script does the comparing.

WHAT GOES IN A SHEET

    keep       y   a real material line - a storekeeper could create a code from it
               n   anything else - tender wording, a service, a heading, a vendor name
               m   two or more DIFFERENT items joined in one line
               ?   unsure - say why in notes
    category   one of CATEGORIES below, for rows marked y
    group      the same tag (G1, G2, ...) on rows that are the SAME physical item.
               Leave blank if a row has no twin. Tags are private to each sheet:
               your G1 and the other person's G1 need not match - the comparison
               looks at which rows you put together, not at the tag names.
    notes      anything worth saying, especially for ?

THE LABELS ARE EVALUATION DATA. Like data/truth/, they are read by evaluation
only, never by any matching stage. See data/real/README.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations

import paths

PEOPLE = ("isha", "meghna")

# Ranks read on 24 Sept 2026 while the extractor fix was being designed: the
# first 30 in reading order, a random sample of 25, one duplicate looked up by
# hand, and 12 rows whose text a test of this script printed to the builder's
# screen. They were seen, so they can never be test rows.
SEEN_DURING_DESIGN = set(range(1, 31)) | {
    62, 114, 168, 234, 255, 297, 340, 344, 366, 479, 507, 581, 582, 586, 588,
    654, 658, 663, 665, 695, 707, 719, 721, 741, 755, 835} | {
    31, 32, 33, 34, 38, 39, 41, 44, 45, 46, 48, 49}


def split_of(rank: int, description: str) -> str:
    if rank in SEEN_DURING_DESIGN:
        return "dev"
    key = re.sub(r"[^A-Z0-9]", "", description.upper()).encode()
    return "dev" if hashlib.sha1(key).digest()[0] % 2 == 0 else "test"

KEEP = {"y", "n", "m", "?"}
CATEGORIES = {"bearing", "gasket", "pipe", "valve", "fastener", "flange", "rotating",
              "instrument", "electrical", "cable", "fitting", "plate", "tube", "other"}

SHEET = ["id", "keep", "category", "group", "description", "organization", "notes"]
DISAGREE = ["kind", "id_a", "id_b", "description_a", "description_b",
            "{a}", "{b}", "decision", "reason"]
GOLD = ["id", "keep", "category", "group", "description", "organization"]


def sheet_path(person: str):
    return paths.REAL_LABELS / f"{person}.csv"


def read_csv(path) -> list[dict]:
    """Excel may save a sheet as UTF-8 or as the Windows codepage. Accept both."""
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with path.open(encoding=enc, newline="") as fh:
                return list(csv.DictReader(fh))
        except UnicodeDecodeError:
            continue
    sys.exit(f"cannot read {path} - save it as 'CSV UTF-8' and try again")


def write_csv(path, fields, rows) -> None:
    # utf-8-sig: the byte-order mark is what makes Excel open the file as UTF-8
    # instead of mangling every non-ASCII character in the descriptions.
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def cell(row: dict, name: str) -> str:
    return (row.get(name) or "").strip().lower()


# ---------------------------------------------------------------------------

def start(args) -> None:
    targets = [paths.REAL_SPLIT, paths.REAL_DEV] + [sheet_path(p) for p in args.people]
    existing = [t for t in targets if t.exists()]
    if existing and not args.force:
        print("These files already exist, so labelling may have started:")
        for t in existing:
            print(f"  {t}")
        print("Refusing to overwrite them. Use --force only to start again from blank.")
        sys.exit(1)

    rows = read_csv(paths.REAL_CANDIDATES)
    split = {r["rank"]: split_of(int(r["rank"]), r["description"]) for r in rows}

    def blank(half):
        return [{"id": r["rank"], "description": r["description"],
                 "organization": r["organization"]} for r in rows if split[r["rank"]] == half]

    paths.REAL_LABELS.mkdir(parents=True, exist_ok=True)
    write_csv(paths.REAL_SPLIT, ["id", "split"],
              [{"id": rid, "split": s} for rid, s in split.items()])
    dev, test = blank("dev"), blank("test")
    write_csv(paths.REAL_DEV, SHEET, dev)
    print(f"wrote {paths.REAL_SPLIT}  (dev {len(dev)}, test {len(test)})")
    print(f"wrote {paths.REAL_DEV}  ({len(dev)} dev rows, blank - for the extractor's builder)")
    for person in args.people:
        write_csv(sheet_path(person), SHEET, test)
        print(f"wrote {sheet_path(person)}  ({len(test)} test rows, blank)")
    print("\nEach person opens ONLY their own sheet. Label from the top down.")


def report(args) -> None:
    """What the dev labels say about the real data. Description, not evaluation."""
    if not paths.REAL_DEV.exists():
        sys.exit("Run start first.")
    rows = [r for r in read_csv(paths.REAL_DEV) if cell(r, "keep")]
    bad = check_values("dev", {r["id"]: r for r in rows})
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    if not rows:
        sys.exit("dev.csv has no labels yet.")

    keep = Counter(cell(r, "keep") for r in rows)
    kept = [r for r in rows if cell(r, "keep") == "y"]
    cats = Counter(cell(r, "category") or "(blank)" for r in kept)
    orgs = Counter((r["organization"], cell(r, "keep")) for r in rows)
    groups = Counter(cell(r, "group") for r in kept if cell(r, "group"))
    in_groups = sum(n for n in groups.values() if n > 1)

    print(f"dev rows labelled   {len(rows)}")
    for k, name in (("y", "real material line"), ("m", "several items in one line"),
                    ("n", "not a material line"), ("?", "unsure")):
        print(f"  {k}  {name:<27} {keep[k]:>4}  ({keep[k]/len(rows):.0%})")
    print("\nby company (y / m / n / ?)")
    for org in sorted({r['organization'] for r in rows}):
        print(f"  {org:<34} " + " / ".join(str(orgs[(org, k)]) for k in "ymn?"))
    print("\ncategory of y rows")
    for c, n in cats.most_common():
        print(f"  {c:<12} {n:>4}")
    print(f"\nsame-item groups    {sum(1 for n in groups.values() if n > 1)}  "
          f"covering {in_groups} rows")


def load_sheet(person: str) -> dict[str, dict]:
    path = sheet_path(person)
    if not path.exists():
        sys.exit(f"{path} not found - run `python src/labels.py start` first")
    return {r["id"]: r for r in read_csv(path)}


def check_values(person: str, sheet: dict) -> list[str]:
    """Typos in a label column silently become disagreements. Catch them first."""
    bad = []
    for rid, r in sheet.items():
        k, c = cell(r, "keep"), cell(r, "category")
        if k and k not in KEEP:
            bad.append(f"  {person} id {rid}: keep '{r['keep']}' - use y / n / m / ?")
        if c and c not in CATEGORIES:
            bad.append(f"  {person} id {rid}: category '{r['category']}' - "
                       f"use one of {', '.join(sorted(CATEGORIES))}")
        if cell(r, "group") and k != "y":
            bad.append(f"  {person} id {rid}: has a group but keep is '{k or 'blank'}' "
                       f"- only y rows are grouped")
    return bad


def same_pairs(sheet: dict, ids: list[str]) -> set[tuple[str, str]]:
    """Every pair of rows this person put in one group, as sorted id pairs."""
    by_tag = defaultdict(list)
    for rid in ids:
        tag = cell(sheet[rid], "group")
        if tag:
            by_tag[tag].append(rid)
    out = set()
    for members in by_tag.values():
        for a, b in combinations(sorted(members, key=int), 2):
            out.add((a, b))
    return out


def kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa - agreement corrected for the agreement chance alone gives."""
    n = len(pairs)
    if not n:
        return 0.0
    observed = sum(a == b for a, b in pairs) / n
    labels = {x for p in pairs for x in p}
    expected = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n)
                   for l in labels)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def compare(args) -> None:
    a_name, b_name = args.people
    a, b = load_sheet(a_name), load_sheet(b_name)

    bad = check_values(a_name, a) + check_values(b_name, b)
    if bad:
        print("Fix these first - they would count as disagreements:\n")
        print("\n".join(bad))
        sys.exit(1)

    both = sorted((rid for rid in a if rid in b and cell(a[rid], "keep") and cell(b[rid], "keep")),
                  key=int)
    if not both:
        sys.exit("No row has a keep value in both sheets yet.")
    desc = {rid: a[rid]["description"] for rid in a}

    rows = []

    keep_pairs = [(cell(a[r], "keep"), cell(b[r], "keep")) for r in both]
    for rid, (x, y) in zip(both, keep_pairs):
        if x != y:
            rows.append({"kind": "keep", "id_a": rid, "description_a": desc[rid], a_name: x, b_name: y})

    both_y = [r for r in both if cell(a[r], "keep") == "y" and cell(b[r], "keep") == "y"]
    cat_agree = 0
    for rid in both_y:
        x, y = cell(a[rid], "category"), cell(b[rid], "category")
        if x == y:
            cat_agree += 1
        else:
            rows.append({"kind": "category", "id_a": rid, "description_a": desc[rid],
                         a_name: x or "(blank)", b_name: y or "(blank)"})

    pa, pb = same_pairs(a, both_y), same_pairs(b, both_y)
    for x, y in sorted(pa ^ pb, key=lambda p: (int(p[0]), int(p[1]))):
        rows.append({"kind": "group", "id_a": x, "id_b": y,
                     "description_a": desc[x], "description_b": desc[y],
                     a_name: "same" if (x, y) in pa else "different",
                     b_name: "same" if (x, y) in pb else "different"})

    # Keep any decision already written, so re-running after more labelling
    # never throws away a discussion that has already happened.
    decided = {}
    if paths.REAL_DISAGREEMENTS.exists():
        for r in read_csv(paths.REAL_DISAGREEMENTS):
            decided[(r["kind"], r["id_a"], r.get("id_b", ""))] = (r.get("decision", ""),
                                                                   r.get("reason", ""))
    for r in rows:
        r["decision"], r["reason"] = decided.get((r["kind"], r["id_a"], r.get("id_b", "")), ("", ""))

    fields = [f.format(a=a_name, b=b_name) for f in DISAGREE]
    write_csv(paths.REAL_DISAGREEMENTS, fields, rows)

    agree_keep = sum(x == y for x, y in keep_pairs)
    open_rows = sum(1 for r in rows if not r["decision"])
    print(f"rows labelled by both        {len(both):>5}")
    print(f"keep agrees                  {agree_keep:>5}   ({agree_keep/len(both):.0%})")
    print(f"keep agreement, Cohen kappa  {kappa(keep_pairs):>8.2f}   "
          f"(above 0.8 is strong, below 0.6 means the rules need talking through)")
    if both_y:
        print(f"category agrees on y rows    {cat_agree:>5}   ({cat_agree/len(both_y):.0%})")
    print(f"same-item pairs              {a_name} {len(pa)}, {b_name} {len(pb)}, "
          f"both {len(pa & pb)}")
    print(f"\n{len(rows)} disagreement(s), {open_rows} without a decision")
    print(f"wrote {paths.REAL_DISAGREEMENTS}")
    if open_rows:
        print("\nSit together, fill in `decision` and `reason` for every row, then run finalise.")
        print("  keep / category rows: decision is the agreed value")
        print("  group rows:           decision is same or different")


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        self.parent[self.find(y)] = self.find(x)


def finalise(args) -> None:
    a_name, b_name = args.people
    a, b = load_sheet(a_name), load_sheet(b_name)
    if not paths.REAL_DISAGREEMENTS.exists():
        sys.exit("Run compare first.")
    disagreements = read_csv(paths.REAL_DISAGREEMENTS)
    open_rows = [r for r in disagreements if not (r.get("decision") or "").strip()]
    if open_rows:
        sys.exit(f"{len(open_rows)} disagreement(s) still have no decision - "
                 f"fill them in {paths.REAL_DISAGREEMENTS}")

    decision = {(r["kind"], r["id_a"], r.get("id_b", "")): r["decision"].strip().lower()
                for r in disagreements}

    both = sorted((rid for rid in a if rid in b and cell(a[rid], "keep") and cell(b[rid], "keep")),
                  key=int)
    gold = {}
    for rid in both:
        keep = cell(a[rid], "keep")
        if keep != cell(b[rid], "keep"):
            keep = decision[("keep", rid, "")]
        category = cell(a[rid], "category")
        if keep == "y" and category != cell(b[rid], "category"):
            category = decision.get(("category", rid, ""), category)
        gold[rid] = {"id": rid, "keep": keep, "category": category if keep == "y" else "",
                     "description": a[rid]["description"], "organization": a[rid]["organization"]}

    kept = [r for r in both if gold[r]["keep"] == "y"]
    both_y = [r for r in both if cell(a[r], "keep") == "y" and cell(b[r], "keep") == "y"]
    pa, pb = same_pairs(a, both_y), same_pairs(b, both_y)
    same = pa & pb
    same |= {(r["id_a"], r["id_b"]) for r in disagreements
             if r["kind"] == "group" and r["decision"].strip().lower() == "same"}

    uf = UnionFind()
    for x, y in same:
        if x in kept and y in kept:
            uf.union(x, y)
    groups = defaultdict(list)
    for rid in kept:
        groups[uf.find(rid)].append(rid)
    tag = 0
    for members in sorted(groups.values(), key=lambda m: int(min(m, key=int))):
        if len(members) > 1:
            tag += 1
            for rid in members:
                gold[rid]["group"] = f"G{tag:03d}"

    write_csv(paths.REAL_GOLD, GOLD, [gold[r] for r in both])
    print(f"wrote {paths.REAL_GOLD}")
    print(f"  {len(both)} rows · {len(kept)} kept · {tag} same-item group(s) "
          f"covering {sum(len(m) for m in groups.values() if len(m) > 1)} rows")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("start", "report", "compare", "finalise"))
    ap.add_argument("--people", nargs=2, default=PEOPLE, metavar=("A", "B"))
    ap.add_argument("--force", action="store_true", help="start: overwrite existing sheets")
    args = ap.parse_args()
    {"start": start, "report": report, "compare": compare,
     "finalise": finalise}[args.action](args)


if __name__ == "__main__":
    main()
