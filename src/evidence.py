"""
Evidence - every headline number, from every dataset, in one stamped file.

    python src/evidence.py

Reads what the runs already wrote and copies the numbers the dashboard and
the deck quote into data/output/evidence.json, with where each came from and
when. Never computes a number of its own, and never blends two datasets:

    demo     the 100-record demo set                data/output/metrics.json
    run15k   15,000 records in real notation        data/runs/15k/output/*.json
    real     real tender lines, held-out test half  data/output/real_metrics.json

data/runs/ is not committed, so this file is how the 15,000-record numbers
travel with the repository. A dataset that has not been run is left out,
not filled in.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime

import paths


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=paths.ROOT,
                             capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=paths.ROOT,
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return out.stdout.strip() + ("+uncommitted" if dirty else "")
    except Exception:                                              # noqa: BLE001
        return "unknown"


def _stamp(path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes")


def synthetic(run: str) -> dict | None:
    out = paths.run_output(run)
    m = _load(out / "metrics.json")
    if not m:
        return None
    res = _load(out / "results.json") or {}
    meta = res.get("meta", {})
    base = _load(out / "baselines.json")
    traps = paths.run_output(run).parent / "truth" / "traps.json"
    d = {
        "source": str((out / "metrics.json").relative_to(paths.ROOT)).replace("\\", "/"),
        "measured_at": _stamp(out / "metrics.json"),
        "records": m.get("records"),
        "auto_merged": m.get("auto_merged_pairs"), "auto_wrong": m.get("auto_wrong", m.get("false_merges")),
        "auto_error_bound_95": m.get("auto_error_bound_95"),
        "recall_with_review": m.get("recall"),
        "traps_auto_merged": m.get("trap_violations_auto"),
        "traps_total": len(_load(traps) or []) if traps.exists() else None,
        "safety_blocks": m.get("safety_blocks"),
        "blocked_one_field": meta.get("blocked_one_field"),
        "true_items": m.get("true_items"), "clusters": m.get("predicted_clusters"),
        "blocking": {k: m.get("blocking", {}).get(k) for k in ("reduction_ratio", "pair_completeness")},
        "review_queue": {k: (m.get("review_queue") or {}).get(k) for k in ("true_match_first", "true_match_in_top3")},
        "by_split": m.get("by_split") or None,
    }
    if base:
        show = "test" if "test" in base["true_pairs"] else "all"
        d["baselines"] = {
            "on": show, "tuned_on": base["tuned_on"],
            "methods": {name: {k: v["best_f1"][show][k] for k in ("merged", "wrong", "traps_merged", "precision", "recall")}
                        | {"threshold": v["best_f1"]["threshold"]} for name, v in base["methods"].items()},
            "ours_auto": {k: base["ours"]["auto"][show][k] for k in ("merged", "wrong", "traps_merged", "precision", "recall")},
        }
    return d


def main() -> None:
    ev = {"built_at": datetime.now().isoformat(timespec="minutes"), "commit": _commit(),
          "caveat": ("The synthetic sets measure how well the system undoes noise we generated. "
                     "The real test is the more believable number, and it is reported beside them, never blended.")}
    demo = synthetic("")
    if demo:
        ev["demo"] = demo
    big = synthetic("15k")
    if big:
        ev["run15k"] = big
    real = _load(paths.REAL_METRICS)
    if real:
        ev["real"] = {"source": "data/output/real_metrics.json", **real}
    paths.EVIDENCE.write_text(json.dumps(ev, indent=1), encoding="utf-8")
    print(f"wrote {paths.EVIDENCE.name}: " + ", ".join(k for k in ("demo", "run15k", "real") if k in ev)
          + f"  (commit {ev['commit']})")


if __name__ == "__main__":
    main()
