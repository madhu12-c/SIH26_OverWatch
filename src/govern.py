"""
Governance - verify the audit log's seals and replay it into the registry.

    python src/govern.py verify nmcr_audit_2026-09-26.jsonl
    python src/govern.py replay nmcr_audit_2026-09-26.jsonl
    python src/govern.py demo          build a sample log, verify it, tamper
                                       with a copy, replay it

The portal writes the audit log in the browser and exports it one sealed
event per line (ui/src/lib/chain.js). Each event carries the SHA-256 of
itself and of the event before it, so an edit anywhere breaks every seal
after it - a hash chain, not a blockchain. This file computes the same seal
over the same canonical form; keep FIELDS in step with chain.js.

REPLAY. The registry's decisions are not stored anywhere else: they are the
log, replayed over the pipeline's proposals. Replaying the same log gives the
same state, byte for byte (the digest proves it). A decision the consent
rules would not have allowed - a company reviewer linking two companies'
codes, anyone but the owner retiring a code - is refused during replay and
listed, even if someone wrote it into the file by hand:

    link two companies' codes     the national registrar
    decide a pair in one company  that company's reviewer
    dispute a link                any company whose code is in it
    retire a code                 only the company that owns it
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import paths

FIELDS = ["id", "ts", "actor", "role", "org", "verb", "object", "pair", "note", "code", "source", "prev"]
GENESIS = "0" * 64


def canonical(e: dict) -> str:
    """The exact string that is hashed - the same as chain.js canonical()."""
    return json.dumps([None if e.get(f) is None else str(e[f]) for f in FIELDS],
                      ensure_ascii=False, separators=(",", ":"))


def seal(event: dict, prev: str) -> dict:
    e = {**event, "prev": prev}
    e["hash"] = hashlib.sha256(canonical(e).encode("utf-8")).hexdigest()
    return e


def verify(events: list[dict]) -> dict:
    """Oldest first. {ok, checked, broken_at, reason}."""
    prev = None
    for i, e in enumerate(events):
        if not e.get("hash"):
            return {"ok": False, "checked": i, "broken_at": i, "reason": "an event has no seal"}
        if prev is not None and e.get("prev") != prev:
            return {"ok": False, "checked": i, "broken_at": i, "reason": "the link to the event before is broken"}
        if hashlib.sha256(canonical(e).encode("utf-8")).hexdigest() != e["hash"]:
            return {"ok": False, "checked": i, "broken_at": i, "reason": "the event was changed after it was sealed"}
        prev = e["hash"]
    return {"ok": True, "checked": len(events), "broken_at": -1, "reason": "",
            "trimmed": bool(events) and events[0].get("prev") != GENESIS}


def read_log(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --------------------------------------------------------------------------
# Consent - the same rules as ui/src/lib/store.js can()
# --------------------------------------------------------------------------

def allowed(role: str, org: str, action: str, target: dict) -> tuple[bool, str]:
    if action == "decide_pair":
        cross = target["a_cpse"] != target["b_cpse"]
        if role == "registrar":
            return (True, "") if cross else (False, "pairs inside one company go to that company's reviewer")
        if role == "reviewer" and not cross and target["a_cpse"] == org:
            return True, ""
        return False, ("a link between two companies is the registrar's" if cross
                       else f"this pair belongs to {target['a_cpse']}'s reviewer")
    if action == "dispute":
        return (True, "") if role == "reviewer" and org in target["cpses"] else \
            (False, "only a company whose code is in the link can dispute it")
    if action == "retire":
        return (True, "") if role == "reviewer" and org == target["cpse"] else \
            (False, f"only {target['cpse']} can retire {target['cpse']}'s code")
    return False, "not permitted"


def load_proposals() -> dict:
    """What the pipeline proposed: review pairs and national codes (results.json)."""
    res = json.loads(paths.RESULTS.read_text(encoding="utf-8"))
    pairs = {}
    for p in res.get("review_queue", []):
        key = "~".join(sorted((p["a"]["record_id"], p["b"]["record_id"])))
        pairs[key] = {"a_cpse": p["a"]["cpse"], "b_cpse": p["b"]["cpse"]}
    codes = {c["national_code"]: {"cpses": c.get("cpses", []),
                                  "owners": {m["source_code"]: m["cpse"] for m in c.get("members", [])}}
             for c in res.get("clusters", [])}
    return {"pairs": pairs, "codes": codes}


def replay(events: list[dict], proposals: dict) -> dict:
    """The registry's decisions, rebuilt from the log. Latest decision wins."""
    decided, disputed, retire, refused, skipped = {}, {}, {}, [], 0
    for e in events:
        verb, role, org = e.get("verb"), e.get("role", ""), e.get("org", "")
        if verb in ("ACCEPT", "REJECT"):
            pair = proposals["pairs"].get(e.get("pair") or "")
            if pair is None:
                refused.append({"id": e.get("id"), "verb": verb, "why": "no such proposal"})
                continue
            ok, why = allowed(role, org, "decide_pair", pair)
            if not ok:
                refused.append({"id": e.get("id"), "verb": verb, "object": e.get("object"), "why": why})
                continue
            decided[e["pair"]] = {"state": "LINKED" if verb == "ACCEPT" else "APART",
                                  "by": e.get("actor"), "at": e.get("ts")}
        elif verb == "SKIP":
            skipped += 1
        elif verb == "DISPUTE":
            code = proposals["codes"].get(e.get("object") or "")
            if code is None:
                refused.append({"id": e.get("id"), "verb": verb, "why": "no such national code"})
                continue
            ok, why = allowed(role, org, "dispute", code)
            if not ok:
                refused.append({"id": e.get("id"), "verb": verb, "object": e.get("object"), "why": why})
                continue
            disputed[e["object"]] = {"by": e.get("actor"), "at": e.get("ts"), "note": e.get("note"),
                                     "state": "BACK TO REVIEW"}
        elif verb == "RETIRE_PROPOSED":
            code = proposals["codes"].get(e.get("code") or "")
            owner = code and code["owners"].get(e.get("source") or "")
            if not owner:
                refused.append({"id": e.get("id"), "verb": verb, "why": "no such company code"})
                continue
            ok, why = allowed(role, org, "retire", {"cpse": owner})
            if not ok:
                refused.append({"id": e.get("id"), "verb": verb, "object": e.get("object"), "why": why})
                continue
            retire[f"{owner} {e['source']}"] = {"code": e["code"], "by": e.get("actor"), "at": e.get("ts"),
                                                 "state": "RETIREMENT PROPOSED - stays mapped and readable"}
    state = {
        "linked": sorted(k for k, v in decided.items() if v["state"] == "LINKED"),
        "apart": sorted(k for k, v in decided.items() if v["state"] == "APART"),
        "disputed": dict(sorted(disputed.items())),
        "retirements": dict(sorted(retire.items())),
    }
    digest = hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"events": len(events), "skipped": skipped, "refused": refused, "state": state,
            "pending": len(proposals["pairs"]) - len(decided), "digest": digest}


# --------------------------------------------------------------------------

def sample_log(proposals: dict) -> list[dict]:
    """A short, realistic session - including two decisions the rules refuse."""
    pairs = proposals["pairs"]
    cross = next(k for k, p in pairs.items() if p["a_cpse"] != p["b_cpse"])
    inside = next((k for k, p in pairs.items() if p["a_cpse"] == p["b_cpse"]), None)
    code, info = next((c, v) for c, v in proposals["codes"].items() if len(v["cpses"]) >= 2)
    src, owner = next(iter(info["owners"].items()))
    other = next(c for c in info["cpses"] if c != owner)
    raw = [
        dict(actor="National Registrar", role="registrar", org="Registry", verb="SIGN_IN", object="National Registrar"),
        dict(actor="National Registrar", role="registrar", org="Registry", verb="ACCEPT", object=cross, pair=cross,
             note="chosen as the same item"),
        dict(actor=f"{other} Reviewer", role="reviewer", org=other, verb="DISPUTE", object=code,
             note=f"{other} says these are not all the same item."),
        dict(actor=f"{owner} Reviewer", role="reviewer", org=owner, verb="RETIRE_PROPOSED", object=f"{owner} {src}",
             code=code, source=src, note="Proposed by its owner."),
        # Written into the file by hand - the portal would have refused both.
        dict(actor=f"{other} Reviewer", role="reviewer", org=other, verb="ACCEPT", object=cross, pair=cross,
             note="forged: a company reviewer linking two companies"),
        dict(actor=f"{other} Reviewer", role="reviewer", org=other, verb="RETIRE_PROPOSED", object=f"{owner} {src}",
             code=code, source=src, note="forged: retiring another company's code"),
    ]
    if inside:
        a_cpse = pairs[inside]["a_cpse"]
        raw.insert(2, dict(actor=f"{a_cpse} Reviewer", role="reviewer", org=a_cpse, verb="REJECT",
                           object=inside, pair=inside, note="none of the candidates is the same item"))
    out, prev = [], GENESIS
    for i, e in enumerate(raw):
        s = seal({"id": f"sample-{i:02d}", "ts": f"2026-09-26T10:{i:02d}:00Z", **e}, prev)
        prev = s["hash"]
        out.append(s)
    return out


def show_verify(events, label):
    v = verify(events)
    print(f"{label}: " + (f"seal intact, {v['checked']} events verified"
                          + (" (older events trimmed from the browser copy)" if v.get("trimmed") else "")
                          if v["ok"] else f"SEAL BROKEN at event {v['broken_at'] + 1}: {v['reason']}"))
    return v


def show_replay(r):
    s = r["state"]
    print(f"replayed {r['events']} events: {len(s['linked'])} linked, {len(s['apart'])} kept apart, "
          f"{len(s['disputed'])} disputed, {len(s['retirements'])} retirement(s) proposed, "
          f"{r['pending']} proposals still pending")
    for x in r["refused"]:
        print(f"  REFUSED {x['verb']:<16} {x.get('object', '')}  - {x['why']}")
    print(f"state digest {r['digest'][:16]}  (same log, same state, every time)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("verify", "replay", "demo"))
    ap.add_argument("log", nargs="?", help="an exported audit log (.jsonl)")
    args = ap.parse_args()

    if args.command == "demo":
        proposals = load_proposals()
        events = sample_log(proposals)
        out = paths.DEMO_OUTPUT / "audit_sample.jsonl"
        out.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")
        print(f"wrote {out.name}: {len(events)} sealed events\n")
        show_verify(events, "as written")
        k = len(events) // 2
        tampered = [dict(e, note=(e.get("note") or "") + " (edited)") if i == k else e for i, e in enumerate(events)]
        show_verify(tampered, f"one word changed in event {k + 1}")
        print()
        first, second = replay(events, proposals), replay(events, proposals)
        show_replay(first)
        assert first["digest"] == second["digest"]
        return

    if not args.log:
        raise SystemExit("give the exported log: python src/govern.py verify nmcr_audit_....jsonl")
    events = read_log(Path(args.log))
    v = show_verify(events, Path(args.log).name)
    if args.command == "replay":
        if not v["ok"]:
            raise SystemExit("refusing to replay a log whose seal is broken")
        show_replay(replay(events, load_proposals()))


if __name__ == "__main__":
    main()
