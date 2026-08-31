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

from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

DATA = ROOT / "data"
INPUT = DATA / "input"
TRUTH = DATA / "truth"
OUTPUT = DATA / "output"

DOCS = ROOT / "docs"
UI = ROOT / "ui"
DELIVERABLES = ROOT / "deliverables"

# --- input: what a CPSE gives us (in reality, a SAP export) -----------------
MATERIALS = INPUT / "materials.csv"
PURCHASES = INPUT / "purchases.csv"

# --- truth: evaluation only ------------------------------------------------
GROUND_TRUTH = TRUTH / "ground_truth.csv"
TRAPS = TRUTH / "traps.json"

# --- output: one file per pipeline stage -----------------------------------
SPECS = OUTPUT / "specs.json"                  # 02 spec extractor
EMBEDDINGS = OUTPUT / "embeddings.npz"         # 03 embeddings
PAIR_SCORES = OUTPUT / "pair_scores.json"      # 05 scorer
CLUSTERS = OUTPUT / "clusters.json"            # 06 clustering
NATIONAL_CODES = OUTPUT / "national_codes.json"  # 08 canonicaliser
MAPPINGS = OUTPUT / "mappings.csv"             # 08 canonicaliser
SAVINGS = OUTPUT / "savings.json"              # 09 savings report
RESULTS = OUTPUT / "results.json"              # 09 everything the UI reads
METRICS = OUTPUT / "metrics.json"           # -- evaluate.py, read by results.py

# Optional researched seed list. When present, generate_dataset.py can use it
# instead of the built-in SEED_ITEMS.
SEED_ITEMS = INPUT / "seed_items.csv"


def ensure_dirs() -> None:
    """Create the data folders if they are missing. Safe to call every run."""
    for folder in (INPUT, TRUTH, OUTPUT):
        folder.mkdir(parents=True, exist_ok=True)
