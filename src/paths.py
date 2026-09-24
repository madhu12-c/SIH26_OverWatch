"""
Every file path in the project, defined once.

No other module builds a path out of string pieces. If a file moves, it moves
here and nowhere else. Import what you need:

    from paths import MATERIALS, SPECS

The three data folders exist to make one rule impossible to break by accident:

    data/input/    what a CPSE hands us. Read-only to the pipeline.
    data/truth/    the answer key. Read ONLY by evaluation, NEVER by matching -
                   a matcher that has seen ground_truth.csv is cheating and its
                   precision number is worthless.
    data/output/   what each stage produces. Safe to delete and regenerate.
"""

import os
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

DATA = ROOT / "data"

# RUNS. The 100-record demo set lives in data/input, data/truth and
# data/output, and its specs were read by the model - it is what the demo
# plays, so it never moves. A bigger run (15,000 records, rule extraction)
# gets its own folder: set SIH_RUN=15k and every script reads and writes
# data/runs/15k/{input,truth,output} instead. run_all.py sets it for you.
RUN = os.environ.get("SIH_RUN", "").strip()
_BASE = DATA / "runs" / RUN if RUN else DATA
INPUT = _BASE / "input"
TRUTH = _BASE / "truth"
OUTPUT = _BASE / "output"

DOCS = ROOT / "docs"
UI = ROOT / "ui"
DELIVERABLES = ROOT / "deliverables"

# The frontend imports its data at BUILD time, so it needs its own copy inside
# ui/src. results.py writes both in one go - a hand-copied second file is how
# a demo ends up showing last week's numbers.
UI_RESULTS = UI / "src" / "results.json"

# --- input: what a CPSE gives us (in reality, a SAP export) -----------------
MATERIALS = INPUT / "materials.csv"
PURCHASES = INPUT / "purchases.csv"

# --- truth: evaluation only ------------------------------------------------
GROUND_TRUTH = TRUTH / "ground_truth.csv"
TRAPS = TRUTH / "traps.json"
ITEMS = TRUTH / "items.json"                   # factory runs: every item's true specs

# --- real: public CPSE text, the real hold-out -----------------------------
# Material lines mined from published Oil India / NTPC / IOCL tender extracts.
# candidates.csv is plain text and may be read by anything. Everything under
# labels/ is an answer key and follows the same rule as data/truth -
# evaluation only, never a matching stage.
REAL = DATA / "real"
REAL_SOURCE = REAL / "source"                   # downloaded extracts, re-fetchable
REAL_CANDIDATES = REAL / "candidates.csv"       # ranked, deduplicated, unlabelled
REAL_LABELS = REAL / "labels"
REAL_SPLIT = REAL_LABELS / "split.csv"          # which rows are dev and which are test
REAL_DEV = REAL_LABELS / "dev.csv"              # dev labels - for building, never evidence
REAL_DISAGREEMENTS = REAL_LABELS / "disagreements.csv"
REAL_GOLD = REAL_LABELS / "final.csv"           # agreed human test labels - the real result

# --- output: one file per pipeline stage -----------------------------------
SPECS = OUTPUT / "specs.json"                  # 02 spec extractor
EMBEDDINGS = OUTPUT / "embeddings.npz"         # 03 embeddings
BLOCKING = OUTPUT / "blocking.json"            # 04 blocking: candidate pairs + stats
PAIR_SCORES = OUTPUT / "pair_scores.json"      # 05 scorer
CLUSTERS = OUTPUT / "clusters.json"            # 06 clustering
NATIONAL_CODES = OUTPUT / "national_codes.json"  # 08 canonicaliser
MAPPINGS = OUTPUT / "mappings.csv"             # 08 canonicaliser
SAVINGS = OUTPUT / "savings.json"              # 09 savings report
UOM = OUTPUT / "uom.json"                      # 09 unit harmonisation report
GATE = OUTPUT / "gate.json"                    # 10 creation-gate scenarios
RESULTS = OUTPUT / "results.json"              # 09 everything the UI reads
METRICS = OUTPUT / "metrics.json"           # -- evaluate.py, read by results.py

# Optional researched seed list. When present, generate_dataset.py can use it
# instead of the built-in SEED_ITEMS.
SEED_ITEMS = INPUT / "seed_items.csv"


def ensure_dirs() -> None:
    """Create the data folders if they are missing. Safe to call every run."""
    for folder in (INPUT, TRUTH, OUTPUT):
        folder.mkdir(parents=True, exist_ok=True)
