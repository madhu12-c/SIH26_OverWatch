"""
One command, the whole chain - so every number in the deck can be reproduced.

    python src/run_all.py                                   the demo set (100 records)
    python src/run_all.py --run 15k --generate 15000        the 15,000-record run
    python src/run_all.py --run 15k --tests                 ...and the safety suite after

The demo set's specs were read by the model and are cached; it is never
re-extracted here unless --extract is given, because the demo plays those
exact specs. A factory run is regenerated (--generate), read by the rules,
embedded (skipped when embeddings exist, unless --embed), scored,
evaluated and bundled.

Each step runs as its own process with SIH_RUN set, stops the chain on the
first failure, and is timed. The last lines say where the numbers are.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="", help="run name, e.g. 15k (data/runs/<run>); empty = the demo set")
    ap.add_argument("--generate", type=int, metavar="N", help="regenerate N records with the item factory")
    ap.add_argument("--dup", type=float, default=0.20, help="duplication rate for --generate")
    ap.add_argument("--extract", action="store_true", help="re-read every record (always on with --generate)")
    ap.add_argument("--embed", action="store_true", help="recompute embeddings even if they exist")
    ap.add_argument("--tests", action="store_true", help="run python -m pytest tests/ at the end")
    ap.add_argument("--ui", action="store_true", help="write ui/src/results.json from this run")
    args = ap.parse_args()

    env = dict(os.environ, SIH_RUN=args.run, PYTHONIOENCODING="utf-8")
    sys.path.insert(0, str(SRC))
    os.environ["SIH_RUN"] = args.run
    import paths                                                   # after SIH_RUN is set

    steps = []
    if args.generate:
        if not args.run:
            raise SystemExit("--generate needs --run: the demo set in data/input is never regenerated here")
        steps.append(("generate", ["generate_dataset.py", "--target", str(args.generate), "--dup", str(args.dup)]))
    if args.generate or args.extract:
        steps.append(("extract", ["extractor.py", "--no-llm", "--fresh"]))
    if args.generate or args.embed or not paths.EMBEDDINGS.exists():
        steps.append(("embed", ["embed.py"]))
    steps += [("score", ["scorer.py"]), ("evaluate", ["evaluate.py"]), ("baselines", ["baselines.py"]),
              ("canonicalise", ["canonicalise.py"]),
              ("savings", ["savings.py"]), ("units", ["uom.py"]), ("gate", ["gate.py", "--scenarios"]),
              ("evidence", ["evidence.py"]),
              ("results", ["results.py"] + (["--ui"] if args.ui else []))]

    print(f"run: {args.run or 'demo'}   ({paths.OUTPUT})\n")
    total = time.time()
    for name, cmd in steps:
        started = time.time()
        res = subprocess.run([sys.executable, str(SRC / cmd[0]), *cmd[1:]], cwd=ROOT, env=env,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        took = time.time() - started
        status = "ok" if res.returncode == 0 else f"FAILED ({res.returncode})"
        print(f"  {name:<13} {took:>6.1f}s  {status}")
        if res.returncode != 0:
            print("\n" + (res.stdout[-2000:] + res.stderr[-3000:]).strip())
            raise SystemExit(1)
        if name == "score":
            demo = [line.strip() for line in res.stdout.splitlines() if "R00001/R00002" in line or "R00003/R00004" in line]
            for line in demo:
                print(f"                 {line}")
            if any(line.startswith("!!") for line in demo):
                raise SystemExit("a demo case failed - stopping")
    print(f"\n  total         {time.time() - total:>6.1f}s")

    if args.tests:
        res = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=ROOT, env=env,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("  tests         " + (res.stdout.strip().splitlines() or ["?"])[-1])
        if res.returncode != 0:
            raise SystemExit(1)

    print(f"\nnumbers: {paths.METRICS}\nbundle:  {paths.RESULTS}")


if __name__ == "__main__":
    main()
