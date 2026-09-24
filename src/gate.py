"""
The creation gate - the check that runs BEFORE a new material code is issued.

    python src/gate.py "GASKET SPIRAL WOUND SS321 4IN 150#"
    python src/gate.py --scenarios          rebuild the demo set into gate.json
    python src/gate.py --code NMC-31171500-000001 --explain

WHY THIS EXISTS

Everything else in this pipeline cleans up the past. Without this, the mess
regrows: tomorrow a storekeeper creates one more code for a bearing that four
other CPSEs already stock, and a batch run finds it six months later, after it
has been purchased against three times.

The honest framing - use it, it is stronger than the alternative:

    Every ERP ALREADY has a duplicate check on code creation. SAP has one.
    It fails on this data because it searches SPELLING. The existing record
    reads GSKT SPRL WND SS316 4IN and the storekeeper types "spiral wound
    gasket 316", so the search returns nothing and a new code is born.

    We are not adding a check that does not exist. We are replacing one that
    does not work, because ours compares SPECIFICATIONS.

Do not claim invention - SAP MDG and Verdantis both do duplicate-check-on-
create. Claim execution, the way CLAUDE.md section 13 does for everything else.

WHERE IT RUNS

The national registry publishes the catalogue DOWNWARD; the check runs inside
the CPSE against a local copy. Nothing sensitive leaves the company - no
prices, no vendors, no quantities - and it works with the network down. Only
the issuance of a genuinely new code travels back up. That is the same
architecture as the federated matching argument in CLAUDE.md section 10C, so
this feature strengthens that story rather than contradicting it.

COST

One incoming record is compared against the GOLDEN RECORDS, not against every
raw record - 16 comparisons here, not 100, and it stays 16 as the raw estate
grows into millions. No model call: extraction uses the offline regex path, so
this runs on a laptop with no internet. See docs/02-decisions/002-llm-once-per-record.md

WHAT IT ANSWERS

    EXISTS   >= 0.90   use this national code, N CPSEs already hold it
    REVIEW   0.70-0.90 a cataloguer looks before a code is issued
    NEW      < 0.70    genuinely new - and here is what it is NOT

The third answer is the one worth demonstrating. A gate that only says "new"
is a search box. A gate that says "new, and this is not your SS304 or SS316
gasket, the grade differs" is the safety interlock pointed forwards.

THE GATE RECOMMENDS, IT NEVER DECIDES. Above the threshold it proposes a code;
a human still accepts it. The PS asks for exactly that - recommend, propose,
review, approve - and a gate that silently refused to issue codes would be the
fastest way to have the whole system switched off. See CLAUDE.md section 9.
"""

from __future__ import annotations

import argparse
import csv
import json

import paths
import schemas
import scorer

EXISTS = scorer.AUTO_MERGE      # 0.90
REVIEW = scorer.REVIEW_LOW      # 0.70

# Below this many extracted fields there is nothing to decide with, and the
# gate must say so rather than issue a code.
#
# "BEARING" typed on its own matches nothing, so a naive gate calls it NEW and
# mints a code - which is precisely how a master fills with junk. An
# underspecified record is not a new item; it is an unfinished one. Saying
# which fields are missing is the "faster specification finalization" the PS
# Expected Impact asks for, and it costs nothing once specs are typed.
MIN_FIELDS = 2


# ---------------------------------------------------------------------------

def golden_side(nc: dict) -> dict:
    """A national code shaped like the spec dict score_pair() expects.

    No confidence map is supplied on purpose. spec_agreement() defaults every
    field to 0.8, which is the right reading: a golden record is a vote across
    a whole cluster, not a single confident extraction.
    """
    return {
        "record_id": nc["national_code"],
        "category": nc["category"],
        "attributes": nc["attributes"],
    }


def load_index() -> tuple[list, dict]:
    """The published catalogue: golden records plus their descriptions."""
    national = json.loads(paths.NATIONAL_CODES.read_text(encoding="utf-8"))
    descriptions = {n["national_code"]: n["std_description"] for n in national}
    # Which variants the registry holds (all fillers, all seal types ...) -
    # the same knowledge the scorer uses to decide what silence means.
    scorer.load_variants(json.loads(paths.SPECS.read_text(encoding="utf-8")))
    return national, descriptions


def check(description: str, national: list, descriptions: dict,
          vecs=None, profiles=None, spec: dict | None = None) -> dict:
    """One incoming description against the whole catalogue.

    Text similarity falls back to lexical here: a record that does not exist
    yet has no embedding. That is not a weakness in practice - the spec signal
    carries up to 0.88 of the decision once several fields are extracted, and
    embedding a single new record locally is cheap when this runs for real.
    """
    profiles = profiles if profiles is not None else {}
    incoming = dict(spec) if spec else schemas.regex_extract(description)
    incoming["record_id"] = "INCOMING"
    descriptions = dict(descriptions)
    descriptions["INCOMING"] = description

    scored, blocked = [], []
    for nc in national:
        p = scorer.score_pair(incoming, golden_side(nc), descriptions, vecs, profiles)
        row = {
            "national_code": nc["national_code"],
            "std_description": nc["std_description"],
            "category": nc["category"],
            "unspsc": nc["unspsc"],
            "cpse_count": nc["cpse_count"],
            "cpses": nc["cpses"],
            "member_count": nc["member_count"],
            "final": p["final"],
            "text_sim": p["text_sim"],
            "spec_sim": p["spec_sim"],
            "matched_fields": p.get("matched_fields", []),
            "ignored_fields": p.get("ignored_fields", []),
            "blocked_by": p.get("blocked_by"),
            "reason": p.get("reason"),
            "unverified": p.get("unverified_hard") or [],
            "attributes": nc.get("attributes") or {},
        }
        # A plain category mismatch is not an interesting refusal - a bearing
        # is not a gasket and nobody needed telling. A HARD FIELD veto is the
        # whole point: same category, nearly the same words, deliberately not
        # the same item.
        if p.get("blocked_by") and p["blocked_by"] != "category":
            blocked.append(row)
        elif not p.get("blocked_by"):
            scored.append(row)

    scored.sort(key=lambda r: -r["final"])
    blocked.sort(key=lambda r: -(r["text_sim"] or 0))

    best = scored[0] if scored else None
    top = best["final"] if best else 0.0

    category = incoming.get("category", "unknown")
    attrs = incoming.get("attributes", {})
    # What to ask for: the fields that NAME the item first; variants after.
    missing_hard = ([f for f in schemas.required_hard_fields(category) if f not in attrs]
                    + [f for f in schemas.hard_fields(category)
                       if f not in attrs and f not in schemas.required_hard_fields(category)])

    # An underspecified record is checked FIRST and never falls through to a
    # match or a new code. Deciding anything on two words would be the one
    # failure a cataloguer could not forgive.
    if category == "unknown" or len(attrs) < MIN_FIELDS:
        verdict = "INCOMPLETE"
        if category == "unknown":
            message = ("Not enough to classify this item. Name the item type - "
                       "bearing, gasket, valve, pipe, flange, fastener - and the "
                       "gate can check it against the catalogue.")
        else:
            want = ", ".join(missing_hard[:4]) or "more detail"
            message = (f"Read as a {category}, but only {len(attrs)} field"
                       f"{'' if len(attrs) == 1 else 's'} could be extracted. "
                       f"No code should be issued yet. Add: {want}.")
        return {
            "input": description,
            "extracted": {
                "category": category, "attributes": attrs,
                "confidence": incoming.get("confidence", {}),
                "method": incoming.get("method"),
            },
            "verdict": verdict, "message": message,
            "best": None, "candidates": [], "distinguished_from": [],
            "missing_hard": missing_hard,
            "compared_against": len(national),
            "thresholds": {"exists": EXISTS, "review": REVIEW},
        }

    if top >= EXISTS:
        verdict = "EXISTS"
        message = (f"Already catalogued as {best['national_code']}. "
                   f"{best['cpse_count']} CPSE"
                   f"{'s' if best['cpse_count'] != 1 else ''} already hold it. "
                   f"Do not create a new code.")
    elif top >= REVIEW:
        verdict = "REVIEW"
        # Say what could not be checked, in the catalogue's own values - the
        # requester can usually settle it by adding one word.
        gaps = []
        for f in best.get("unverified") or []:
            v = best["attributes"].get(f)
            gaps.append(f"{f.replace('_', ' ')} (the catalogue code says {schemas.canonical_value(f, v)})"
                        if v is not None else f.replace("_", " "))
        why = f" Not stated in this line: {', '.join(gaps)}." if gaps else ""
        message = (f"Possible match with {best['national_code']} at {top:.2f}.{why} "
                   f"A cataloguer decides before a code is issued.")
    else:
        verdict = "NEW"
        message = "No existing national code matches. This is a new item."
        if blocked:
            names = ", ".join(b["national_code"] for b in blocked[:2])
            message += (f" It is NOT {names} - "
                        f"{blocked[0]['blocked_by'].replace('_', ' ')} differs.")

    return {
        "input": description,
        "extracted": {
            "category": incoming.get("category"),
            "attributes": incoming.get("attributes", {}),
            "confidence": incoming.get("confidence", {}),
            "method": incoming.get("method"),
        },
        "verdict": verdict,
        "message": message,
        "best": best,
        "candidates": scored[:4],
        # The refusals are the interesting half of the answer, not a footnote.
        "distinguished_from": blocked[:4],
        # Named even on a confident match: a safety field nobody extracted is
        # a field nobody verified, and the reviewer should see which.
        "missing_hard": missing_hard,
        "compared_against": len(national),
        "thresholds": {"exists": EXISTS, "review": REVIEW},
    }


# ---------------------------------------------------------------------------
# The demo set.
#
# Precomputed into gate.json so the browser never needs a Python process. The
# UI plays these back and can also score a typed description against the same
# shipped index. See docs/02-decisions/009-static-demo-no-backend.md
# ---------------------------------------------------------------------------

def scenarios(national, descriptions, vecs, profiles) -> list:
    """Four cases, in the order they should be shown.

    The first two are taken from records that really exist in materials.csv,
    so nothing here is a hand-tuned string that only works on stage. The last
    two are new descriptions - a grade that appears in no cluster, and an item
    from a category the catalogue has never seen.
    """
    materials = {}
    with paths.MATERIALS.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            materials[row["record_id"]] = row

    specs = json.loads(paths.SPECS.read_text(encoding="utf-8"))

    def from_record(rid):
        return materials[rid]["description"], specs.get(rid)

    plan = []

    # 1. A genuine duplicate, worded nothing like the catalogue entry.
    desc, spec = from_record("R00002")
    plan.append(("duplicate", "A duplicate arrives",
                 "IOCL types the description on a supplier quote. It shares "
                 "almost no words with the catalogue entry.", desc, spec))

    # 2. Two catalogue entries differ ONLY by grade. Picking the right one is
    #    the whole test - a text search cannot separate them at all.
    desc, spec = from_record("R00004")
    plan.append(("known-grade", "Two codes differ only by grade",
                 "The catalogue holds an SS304 and an SS316 spiral wound "
                 "gasket, identical in every other field. The gate has to "
                 "return the right one, not the nearest string.", desc, spec))

    # 3. Genuinely new, and dangerously similar to two existing codes.
    plan.append(("new-grade", "A grade the catalogue has never held",
                 "SS321 exists in no cluster. The gate must issue a new code "
                 "AND say what this is not.",
                 "GASKET SPIRAL WOUND SS321 4IN 150#", None))

    # 4. A different veto field entirely. The refusal mechanism is not a
    #    stainless-steel special case - here the grade agrees and the
    #    instrument range decides.
    plan.append(("new-range", "Same gauge, wrong range",
                 "Identical type, dial, wetted material and connection. Only "
                 "the range differs - and a 0-16 bar gauge fitted where a "
                 "0-10 bar one belongs reads wrong for the rest of its life.",
                 "PRESSURE GAUGE 100MM DIAL 0-16 BAR SS316 1/2IN NPT BOTTOM",
                 None))

    # 5. Too little to decide on. A naive gate calls this NEW and mints a code,
    #    which is how a master fills with junk in the first place.
    plan.append(("incomplete", "Not enough typed to decide",
                 "A storekeeper in a hurry types one word. The gate refuses to "
                 "issue a code and says which fields it still needs.",
                 "BEARING", None))

    out = []
    for sid, label, note, desc, spec in plan:
        result = check(desc, national, descriptions, vecs, profiles, spec=spec)
        result["id"] = sid
        result["label"] = label
        result["note"] = note
        out.append(result)
    return out


def build() -> dict:
    national, descriptions = load_index()
    vecs = scorer.load_vectors()
    profiles = scorer.build_purchase_profiles()
    return {
        "index": {
            "codes": len(national),
            "note": ("one incoming record is compared against golden records, "
                     "not against every raw record"),
        },
        "thresholds": {"exists": EXISTS, "review": REVIEW},
        "scenarios": scenarios(national, descriptions, vecs, profiles),
    }


# ---------------------------------------------------------------------------

def show(result: dict) -> None:
    print(f"\n  in   {result['input']}")
    ex = result["extracted"]
    print(f"  as   {ex['category']}  ({ex['method']})")
    for k, v in ex["attributes"].items():
        print(f"         {k:<18} {v}")

    print(f"\n  {result['verdict']}")
    print(f"  {result['message']}")
    if result.get("missing_hard"):
        print(f"  not verified: {', '.join(result['missing_hard'])}")

    best = result["best"]
    if best and best["final"] > 0:
        print(f"\n  best candidate")
        print(f"    {best['national_code']}  {best['final']}")
        print(f"    {best['std_description']}")
        print(f"    text {best['text_sim']}   specs {best['spec_sim']}")
        if best["matched_fields"]:
            print(f"    matched  {', '.join(best['matched_fields'])}")
        if best["ignored_fields"]:
            print(f"    ignored  {', '.join(best['ignored_fields'])}")

    if result["distinguished_from"]:
        print(f"\n  NOT the same as")
        for b in result["distinguished_from"]:
            print(f"    {b['national_code']}  blocked on {b['blocked_by']}: {b['reason']}")
            print(f"      text similarity {b['text_sim']} — a fuzzy matcher merges this")
            print(f"      {b['std_description']}")

    print(f"\n  compared against {result['compared_against']} national codes\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("description", nargs="?", help="the incoming material description")
    ap.add_argument("--scenarios", action="store_true",
                    help="rebuild the demo set into gate.json")
    args = ap.parse_args()

    # `is None`, not falsiness - an empty string is a description the user
    # actually passed, and it must be answered rather than silently rebuilding
    # the scenario file.
    if args.scenarios or args.description is None:
        data = build()
        paths.ensure_dirs()
        paths.GATE.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"wrote {paths.GATE.name}   {len(data['scenarios'])} scenarios, "
              f"index of {data['index']['codes']} codes")
        for s in data["scenarios"]:
            print(f"\n  [{s['verdict']:<6}] {s['label']}")
            print(f"    {s['input'][:66]}")
            print(f"    {s['message'][:100]}")
        if not args.description:
            print("\npass a description to check one directly:")
            print('  python src/gate.py "GASKET SPIRAL WOUND SS321 4IN 150#"')
        return

    national, descriptions = load_index()
    show(check(args.description, national, descriptions,
               scorer.load_vectors(), scorer.build_purchase_profiles()))


if __name__ == "__main__":
    main()
