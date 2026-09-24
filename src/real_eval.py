"""
Real-text evaluation - how well the pipeline reads real Indian material lines.

    python src/real_eval.py                  extraction coverage on the DEV half
    python src/real_eval.py --show pipe      every dev pipe line with what was read
    python src/real_eval.py --misses         dev lines read as the wrong category
    python src/real_eval.py --test claude    THE REAL RESULT - frozen code, test labels
    python src/real_eval.py --test final     ...once two people have labelled and agreed

DEV ONLY. The dev half (data/real/labels/dev.csv) is what we build against;
its numbers are never reported as results. The test half is labelled blind by
two people and is read only by the final evaluation, after the code is frozen.
Dev mode refuses to open a test row: it reads split.csv and keeps "dev".
Test mode refuses to run unless the reading and scoring code still matches
data/real/labels/frozen.json - the fingerprint taken before any test row was
opened - so a test number can never come from code tuned on the test rows.

"Two or more facts" counts extracted specification fields, not brand or
part number and not fields filled from a table.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations

import paths
import schemas

sys.stdout.reconfigure(encoding="utf-8")

FROZEN = paths.REAL_LABELS / "frozen.json"


def dev_rows() -> list[dict]:
    split = {r["id"]: r["split"] for r in csv.DictReader(paths.REAL_SPLIT.open(encoding="utf-8-sig"))}
    rows = list(csv.DictReader(paths.REAL_DEV.open(encoding="utf-8-sig")))
    bad = [r["id"] for r in rows if split.get(r["id"]) != "dev"]
    if bad:
        raise SystemExit(f"refusing: {len(bad)} rows in dev.csv are not dev rows ({bad[:5]})")
    return rows


def facts(out: dict) -> int:
    ignored = set(schemas.ignored_fields(out["category"]))
    return sum(1 for k, c in out["attributes"].items()
               if k not in ignored and out["confidence"].get(k, 0) >= 0.55)


def frozen_ok() -> tuple[bool, list[str]]:
    """Does the code that reads and scores still match the freeze?"""
    if not FROZEN.exists():
        return False, ["no frozen.json - freeze the code before opening test rows"]
    manifest = json.loads(FROZEN.read_text(encoding="utf-8"))
    # Line endings don't count: git on Windows checks the same file out with
    # CRLF, and a fresh clone must still pass the freeze.
    changed = [f for f, h in manifest["files"].items()
               if hashlib.sha256((paths.ROOT / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != h]
    return not changed, changed


def test_eval(labeller: str, post_freeze: bool = False) -> None:
    """The real-data result: frozen code against blind-held-out test labels."""
    ok, changed = frozen_ok()
    if not ok and post_freeze:
        print("POST-FREEZE RUN - the code has changed since the freeze (" + ", ".join(changed) + ").")
        print("The builder has seen these test rows, so this number is NOT the result.")
        print("It shows whether later work, tuned on dev only, moved the real number.")
    elif not ok:
        raise SystemExit("refusing: code changed since the freeze - " + ", ".join(changed)
                         + "\nA post-freeze number must be labelled as such; re-freeze deliberately.")
    sheet = paths.REAL_GOLD if labeller == "final" else paths.REAL_LABELS / f"{labeller}.csv"
    rows = [r for r in csv.DictReader(sheet.open(encoding="utf-8-sig")) if r["keep"] == "y"]
    if not rows:
        raise SystemExit(f"{sheet.name} has no labelled rows yet")

    known = set(schemas.CATEGORIES) - {"unknown", "other"}
    specs, inside, right, two = {}, 0, 0, 0
    for r in rows:
        out = schemas.regex_extract(r["description"])
        out.update(record_id=r["id"], cpse=r["organization"], source_code=r["id"])
        specs[r["id"]] = out
        if r["category"] in known:
            inside += 1
            right += out["category"] == r["category"]
            two += facts(out) >= 2

    import blocking
    import scorer
    desc = {r["id"]: r["description"] for r in rows}
    group = {r["id"]: r["group"] for r in rows if r["group"]}
    candidates, stats = blocking.candidate_pairs(specs)
    scored = [scorer.score_pair(specs[a], specs[b], desc, None, {}) for a, b in candidates]
    members = defaultdict(list)
    for rid, g in group.items():
        members[g].append(rid)
    true_pairs = {frozenset(p) for v in members.values() for p in combinations(sorted(v), 2)}

    def band(lo, hi=9.9):
        got = [p for p in scored if not p["blocked_by"] and lo <= p["final"] < hi]
        tp = sum(frozenset((p["a"], p["b"])) in true_pairs for p in got)
        return got, tp

    auto, auto_tp = band(scorer.AUTO_MERGE)
    prop, prop_tp = band(scorer.REVIEW_LOW)
    wrong_auto = [p for p in auto if frozenset((p["a"], p["b"])) not in true_pairs]
    blocked_true = [p for p in scored if p["blocked_by"] and frozenset((p["a"], p["b"])) in true_pairs]
    found = {frozenset(p) for p in candidates}

    who = {"claude": "Claude - the builder - labelled AFTER the code freeze; one labeller, "
                     "not yet checked by a human",
           "final": "agreed labels of two people labelling separately"}.get(labeller, labeller)
    print(f"\nREAL TEST SET - {len(rows)} material lines ({sheet.name})")
    print(f"  labels: {who}")
    frozen_at = json.loads(FROZEN.read_text())["frozen_at"]
    print(f"  code:   frozen {frozen_at}, unchanged\n" if ok else
          f"  code:   CHANGED since the freeze of {frozen_at} - a post-freeze number\n")
    print(f"READING   inside the categories ({inside} lines)")
    print(f"  category right          {right / inside:>7.1%}")
    print(f"  two or more facts       {two / inside:>7.1%}")
    print(f"\nMATCHING  {len(true_pairs)} true same-item pairs in {len(members)} groups")
    print(f"  candidates after blocking  {len(candidates):>5}  (pair completeness "
          f"{len(true_pairs & found) / len(true_pairs):.1%})")
    print(f"  AUTO-MERGED             {len(auto):>5}   wrong {len(wrong_auto)}   "
          f"precision {auto_tp / len(auto) if auto else 1:.1%}   <- the safety number")
    print(f"  PROPOSED (auto+review)  {len(prop):>5}   right {prop_tp}   "
          f"precision {prop_tp / len(prop) if prop else 1:.1%}   "
          f"recall {prop_tp / len(true_pairs):.1%}")
    print(f"  true pairs vetoed       {len(blocked_true):>5}")
    for p in wrong_auto[:10]:
        print(f"    WRONG AUTO {p['a']}/{p['b']} {p['final']}  {desc[p['a']][:50]} | {desc[p['b']][:50]}")
    for p in blocked_true[:10]:
        print(f"    vetoed true pair {p['a']}/{p['b']} on {p['blocked_by']}: {p['reason']}")
    missed = [tuple(sorted(p)) for p in true_pairs
              if not any(frozenset((q["a"], q["b"])) == p and not q["blocked_by"]
                         and q["final"] >= scorer.REVIEW_LOW for q in scored)]
    for a, b in missed[:12]:
        print(f"    missed {a}/{b}  {desc[a][:55]} | {desc[b][:55]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", help="print every dev line of this labelled category")
    ap.add_argument("--misses", action="store_true", help="print wrong categories")
    ap.add_argument("--post-freeze", action="store_true",
                    help="with --test: run the current code anyway, labelled post-freeze (not the result)")
    ap.add_argument("--test", metavar="LABELLER",
                    help="the real result: frozen code on the TEST half, labels from "
                         "LABELLER.csv (or 'final' for the agreed two-person labels)")
    args = ap.parse_args()
    if args.test:
        test_eval(args.test, args.post_freeze)
        return

    rows = [r for r in dev_rows() if r["keep"] == "y"]
    known = set(schemas.CATEGORIES) - {"unknown"}
    per = defaultdict(lambda: Counter())
    total = Counter()
    for r in rows:
        out = schemas.regex_extract(r["description"])
        want = r["category"]
        n = facts(out)
        inside = want in known and want != "other"
        c = per[want]
        c["rows"] += 1
        c["right"] += out["category"] == want
        c["two"] += n >= 2
        if inside:
            total["rows"] += 1
            total["right"] += out["category"] == want
            total["two"] += n >= 2
        if args.show and want == args.show:
            print(f"\n{r['id']:>4} {r['description'][:110]}")
            print(f"     -> {out['category']}  {out['attributes']}")
            for note in out.get("notes", []):
                print(f"     ! {note}")
        if args.misses and out["category"] != want:
            print(f"{r['id']:>4} want {want:<10} got {out['category']:<10} {r['description'][:90]}")

    print(f"\nDEV material lines (keep = y): {len(rows)}   - never reported as results\n")
    print(f"{'category':<12}{'rows':>6}{'category right':>16}{'2+ facts':>10}")
    for cat, c in sorted(per.items(), key=lambda x: -x[1]["rows"]):
        print(f"{cat:<12}{c['rows']:>6}{c['right'] / c['rows']:>15.0%} {c['two'] / c['rows']:>9.0%}")
    if total["rows"]:
        print(f"\ninside the categories ({total['rows']} rows):  "
              f"category right {total['right'] / total['rows']:.0%}   "
              f"two or more facts {total['two'] / total['rows']:.0%}")


if __name__ == "__main__":
    main()
