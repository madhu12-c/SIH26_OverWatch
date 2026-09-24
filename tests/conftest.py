import csv
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# The suite always tests the demo set, whatever run the shell has selected -
# the same answers every time, in seconds.
os.environ["SIH_RUN"] = ""

import paths  # noqa: E402


@pytest.fixture(scope="session")
def dev():
    """Dev rows of the real set, by id. Refuses any id the split calls test."""
    split = {r["id"]: r["split"] for r in csv.DictReader(paths.REAL_SPLIT.open(encoding="utf-8-sig"))}
    rows = {r["id"]: r for r in csv.DictReader(paths.REAL_DEV.open(encoding="utf-8-sig"))}

    def get(i):
        i = str(i)
        assert split.get(i) == "dev", f"row {i} is not a dev row - tests never read test rows"
        return rows[i]
    return get
