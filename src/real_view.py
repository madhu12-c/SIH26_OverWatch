"""
The "Real text" page: real Oil India and NTPC tender lines, read by the rules.

    python src/real_view.py          print what the page will show

Built from the DEV half only (data/real/labels/dev.csv). These are examples
of the reader at work, never a result - the result is the frozen-code test
run in real_eval.py. Test rows are never opened here.

Three parts, all computed, nothing typed in by hand:

    groups      one item written differently in different documents - dev
                groups whose lines share the fewest words, and what the
                scorer makes of each pair
    near_misses two lines that read almost alike and are different items,
                refused on a safety field
    lines       real lines with every value the reader took and the words it
                took it from (the evidence span), plus what a standard filled in
"""

from __future__ import annotations

import sys
from collections import defaultdict
from itertools import combinations

import real_eval
import schemas
import scorer

PER_CATEGORY = 10
SHOW_GROUPS = 5
SHOW_NEAR = 4


def _read(row: dict) -> dict:
    out = schemas.regex_extract(row["description"])
    out.update(record_id=row["id"], cpse=row["organization"], source_code=row["id"])
    return out


# What schemas.derive() can fill in from a standard. A value with no evidence
# span is "from the standard" only if it is one of these; anything else was
# read (an "other" line's quantities carry no span of their own).
DERIVABLE = {"od_mm", "wall_mm", "nominal_size_in", "bore_mm", "width_mm", "sub_type", "power_hp", "poles"}
NOT_MATCHED = {"brand", "part_number", "manufacturer"}


def _fields(out: dict) -> tuple[list, list]:
    """(read from the text, filled from a standard) - each [{name, value, span}]."""
    spans = out.get("evidence") or {}
    read, filled = [], []
    for name, value in out["attributes"].items():
        item = {"name": name, "value": schemas.canonical_value(name, value) if isinstance(value, str) else value,
                "ignored": name in NOT_MATCHED}
        if name in spans:
            read.append({**item, "span": spans[name]})
        elif name in DERIVABLE:
            filled.append(item)
        else:
            read.append(item)
    return read, filled


def _line(row: dict, out: dict) -> dict:
    read, filled = _fields(out)
    return {"id": row["id"], "org": row["organization"], "text": row["description"],
            "category": out["category"], "category_span": (out.get("evidence") or {}).get("category"),
            "read": read, "filled": filled, "notes": out.get("notes", [])}


def _pair(a_out: dict, b_out: dict, desc: dict) -> dict:
    p = scorer.score_pair(a_out, b_out, desc, None, {})
    band = ("blocked" if p["blocked_by"] else "auto" if p["final"] >= scorer.AUTO_MERGE
            else "review" if p["final"] >= scorer.REVIEW_LOW else "apart")
    return {"a": a_out["record_id"], "b": b_out["record_id"], "final": p["final"], "band": band,
            "text_sim": round(scorer.lexical_similarity(desc[a_out["record_id"]], desc[b_out["record_id"]]), 3),
            "matched": p.get("matched_fields", []), "blocked_by": p.get("blocked_by"),
            "reason": p.get("reason"), "review_reason": p.get("review_reason")}


def build() -> dict:
    rows = [r for r in real_eval.dev_rows() if r["keep"] == "y"]
    outs = {r["id"]: _read(r) for r in rows}
    by_id = {r["id"]: r for r in rows}
    desc = {r["id"]: r["description"] for r in rows}

    # One item, several spellings: each dev group's least-alike pair.
    members = defaultdict(list)
    for r in rows:
        if r["group"]:
            members[r["group"]].append(r["id"])
    groups, found = [], 0
    for g, ids in members.items():
        if len(ids) < 2:
            continue
        pairs = [_pair(outs[a], outs[b], desc) for a, b in combinations(ids, 2)]
        found += any(p["band"] in ("auto", "review") for p in pairs)
        worst = min(pairs, key=lambda p: p["text_sim"])
        groups.append({"group": g, "lines": [_line(by_id[i], outs[i]) for i in ids[:4]], "pair": worst})
    n_groups = len(groups)
    shown = sorted((g for g in groups if g["pair"]["band"] in ("auto", "review")),
                   key=lambda g: (g["lines"][0]["category"] in ("other", "unknown"),
                                  g["pair"]["text_sim"], -g["pair"]["final"]))[:SHOW_GROUPS]

    # Near misses: alike on paper, different items, refused on a safety field.
    group_of = {i: r["group"] for i, r in by_id.items() if r["group"]}
    by_cat = defaultdict(list)
    for i, o in outs.items():
        by_cat[o["category"]].append(i)
    near = []
    for cat, ids in by_cat.items():
        if cat in ("other", "unknown"):
            continue
        for a, b in combinations(ids, 2):
            if group_of.get(a) and group_of.get(a) == group_of.get(b):
                continue
            if scorer.lexical_similarity(desc[a], desc[b]) < 0.6:
                continue
            p = _pair(outs[a], outs[b], desc)
            if p["blocked_by"] and p["blocked_by"] not in scorer.NOT_SAFETY:
                near.append(p)
    near.sort(key=lambda p: -p["text_sim"])
    seen, near_shown = set(), []
    for p in near:                       # one per safety field, so the page shows range
        if p["blocked_by"] in seen:
            continue
        seen.add(p["blocked_by"])
        near_shown.append({**p, "lines": [_line(by_id[p["a"]], outs[p["a"]]), _line(by_id[p["b"]], outs[p["b"]])]})
        if len(near_shown) == SHOW_NEAR:
            break

    # A browsable sample: the lines with the most read facts, per category.
    per = defaultdict(list)
    for i, o in outs.items():
        per[o["category"]].append(i)
    lines = []
    for cat, ids in sorted(per.items(), key=lambda x: -len(x[1])):
        ids.sort(key=lambda i: (-len(_fields(outs[i])[0]), by_id[i]["organization"], i))
        lines += [_line(by_id[i], outs[i]) for i in ids[:PER_CATEGORY]]

    return {
        "half": "dev",
        "note": "Development half of the real set - examples of the reader at work, not a result.",
        "lines_total": len(rows),
        "by_org": {o: sum(1 for r in rows if r["organization"] == o) for o in sorted({r["organization"] for r in rows})},
        "groups_total": n_groups, "groups_found": found,
        "groups": shown, "near_misses": near_shown, "lines": lines,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    v = build()
    print(f"dev lines {v['lines_total']}  {v['by_org']}  groups found {v['groups_found']} of {v['groups_total']}")
    print("\nONE ITEM, DIFFERENT WORDS")
    for g in v["groups"]:
        p = g["pair"]
        print(f"  {g['group']}  text {p['text_sim']}  -> {p['band']} {p['final']}  matched {p['matched']}")
        for ln in g["lines"]:
            print(f"      {ln['org']:<10} {ln['text'][:90]}")
    print("\nNEAR MISSES")
    for p in v["near_misses"]:
        print(f"  text {p['text_sim']}  blocked on {p['blocked_by']}: {p['reason']}")
        for ln in p["lines"]:
            print(f"      {ln['text'][:90]}")
    print(f"\n{len(v['lines'])} lines in the browsable sample")


if __name__ == "__main__":
    main()
