"""
Blocking - which pairs are worth scoring at all.

All-pairs is n(n-1)/2: 4,950 pairs at 100 records, 112 million at 15,000,
which exhausts memory long before it finishes. Blocking puts each record into
a few small buckets and scores only the pairs that share one. It must be
generous - a true pair that never meets can never be matched - and cheap.

A record joins a bucket through any of these keys:

    1. ANCHOR       category + the standard designation that names the item:
                    bearing|6205, pipe|4|SCH 40, cable|3.5|240|AL. Built from
                    the standard number, never the maker's part number, so
                    SKF 6205-2RS and FAG 6205-2RSR share bearing|6205.
    2. LEAVE-ONE-OUT signatures over the hard fields a record has: one key
                    with all of them, and one per field left out. A record
                    missing one field still meets its twin - and a near-miss
                    (SS316 against SS304) still meets on the key without grade,
                    which is what we want: the veto then refuses it, and the
                    safety report can count the refusal.
    3. NEIGHBOURS   the 10 nearest records by embedding, in the same
                    category, computed in chunks of 1,000 rows - added only
                    for records whose extraction is thin, which is what they
                    are for.

    PURGE           a key holding more than 200 records is too generic to
                    mean anything (pipe| with nothing else). It emits no pairs
                    and is logged. One- and two-field keys are purged sooner.
    PRUNE           meta-blocking: pairs are weighted by the keys they share
                    and each record keeps its best TOP_K partners. See
                    candidate_pairs.

Numbers go into keys at two significant figures, so 457 and 457.2 mm share a
bucket. That over-includes on purpose; the scorer decides.

This file never reads data/truth. Pair completeness - the share of true pairs
that blocking lets through - is measured in evaluate.py, which may.
"""

from __future__ import annotations

import math
from collections import defaultdict
from itertools import combinations

import schemas

MAX_BLOCK = 200
MAX_SINGLE = 25      # a key on one field alone (grade=SS316) - broad, so purged sooner
MAX_PAIR = 100       # a key on two fields
TOP_K = 10           # partners each record keeps after weighting (meta-blocking)
MAX_K = 60           # ...plus any tied with the last of them, up to this many
NEIGHBOURS = 10
CHUNK = 1000

# The designation that names an item in each category. All fields must be
# present for the anchor key to exist.
ANCHORS = {
    "bearing":    ("iso_designation",),
    "fastener":   ("thread", "length_mm"),
    "pipe":       ("nominal_size_in",),
    "valve":      ("valve_type", "nominal_size_in"),
    "flange":     ("nominal_size_in", "pressure_class"),
    "gasket":     ("nominal_size_in",),
    "fitting":    ("fitting_type", "nominal_size_in"),
    "cable":      ("cores", "cross_section_mm2"),
    "tube":       ("od_mm", "wall_mm"),
    "plate":      ("thickness_mm",),
    "electrical": ("equipment_type", "power_hp"),
    "rotating":   ("component_type", "shaft_dia_mm"),
    "instrument": ("instrument_type", "range_max"),
    "other":      ("noun",),
}


# Fields that name an item although they are not REQUIRED veto fields: a
# transformer is its kVA and voltage (the required electrical fields are a
# motor's); a mechanical seal is its arrangement as much as its shaft.
IDENTITY_EXTRA = {
    "electrical": ["rating_kva", "voltage_hv_kv"],
    "rotating": ["arrangement"],
    "gasket": ["gasket_type"],
}


def _v(value) -> str:
    """A value as it goes into a key. Numbers at two significant figures."""
    if isinstance(value, (int, float)):
        x = float(value)
        if x == 0:
            return "0"
        digits = 1 - int(math.floor(math.log10(abs(x))))
        return f"{round(x, digits):g}"
    return str(value).strip().upper().replace("_", " ")


def keys_for(spec: dict) -> set[str]:
    cat = spec.get("category", "unknown")
    attrs = dict(spec.get("attributes", {}))
    schemas.derive(cat, attrs, {})
    keys = set()

    anchor = ANCHORS.get(cat)
    if anchor and all(f in attrs for f in anchor):
        keys.add(f"A|{cat}|" + "|".join(_v(attrs[f]) for f in anchor))

    # Signature keys are just "category + these fields = these values", with
    # no label for how they were made. A record missing grade must produce
    # EXACTLY the key its complete twin produces when grade is left out - a
    # label such as "all fields" versus "left one out" once kept them apart
    # and lost 30% of true pairs at 15,000 records.
    # Identity fields only - the REQUIRED veto fields. Variant fields (seal,
    # filler, ends, armour) must not split a block: near-misses that differ
    # only there have to meet, so the veto can refuse them and be counted.
    hard = [f for f in schemas.required_hard_fields(cat) + IDENTITY_EXTRA.get(cat, []) if f in attrs]

    def sig(fields):
        return f"K|{cat}|" + "|".join(f"{f}={_v(attrs[f])}" for f in sorted(fields))

    # Every subset that leaves out at most two fields: a duplicate written
    # without grade AND schedule still meets its complete twin. Real text
    # drops two fields often. A one-field key is broad, so it gets a tighter
    # purge (MAX_SINGLE).
    for size in range(len(hard), max(1, len(hard) - 2) - 1, -1):
        for subset in combinations(hard, size):
            keys.add(sig(subset))
    if not keys:
        keys.add(f"C|{cat}")          # nothing typed: category only, usually purged
    return keys


def neighbour_pairs(specs: dict, vecs) -> set[tuple[str, str]]:
    """Top-k cosine neighbours inside each category, in row chunks."""
    if vecs is None:
        return set()
    import numpy as np
    out = set()
    by_cat = defaultdict(list)
    for rid, s in specs.items():
        if rid in vecs["lookup"]:
            by_cat[s.get("category", "unknown")].append(rid)
    for ids in by_cat.values():
        if len(ids) < 2:
            continue
        m = vecs["vectors"][[vecs["lookup"][r] for r in ids]]
        k = min(NEIGHBOURS, len(ids) - 1)
        for start in range(0, len(ids), CHUNK):
            sims = m[start:start + CHUNK] @ m.T               # CHUNK x n, ~60 MB at 15,000
            for i, row in enumerate(sims):
                row[start + i] = -2.0                        # never your own neighbour
                for j in np.argpartition(-row, k)[:k]:
                    a, b = ids[start + i], ids[int(j)]
                    out.add((a, b) if a < b else (b, a))
    return out


def candidate_pairs(specs: dict, vecs=None) -> tuple[list[tuple[str, str]], dict]:
    """(sorted candidate pairs, stats). Deterministic: same input, same pairs.

    META-BLOCKING. Sharing a bucket is only a hint; sharing many specific
    buckets is strong evidence. Each pair is weighted by the keys it shares -
    a key on more fields, in a smaller bucket, weighs more - and each record
    keeps only its TOP_K partners. A true duplicate shares its full signature
    and most subsets of it; a chance collision shares one broad key. This is
    what takes the candidate set from millions to about one pair in a
    thousand at 15,000 records, without losing the duplicates.
    """
    ids = sorted(specs)
    index = {rid: i for i, rid in enumerate(ids)}
    buckets = defaultdict(list)
    thin = set()
    for rid in ids:
        keys = keys_for(specs[rid])
        for key in keys:
            buckets[key].append(index[rid])
        cat = specs[rid].get("category", "unknown")
        stated = sum(1 for f in schemas.required_hard_fields(cat) if f in specs[rid].get("attributes", {}))
        if stated * 2 <= len(schemas.required_hard_fields(cat)):
            thin.add(rid)          # half its safety fields or fewer: typed keys can't place it

    n = len(ids)
    weight = defaultdict(float)
    purged = {}
    for key, members in buckets.items():
        fields = key.count("=") if key.startswith("K|") else 2
        limit = MAX_SINGLE if fields == 1 else MAX_PAIR if fields == 2 else MAX_BLOCK
        if len(members) > limit:
            purged[key] = len(members)
            continue
        w = fields / math.log2(len(members) + 1)
        for a, b in combinations(members, 2):
            weight[a * n + b] += w

    best = defaultdict(list)
    for code, w in weight.items():
        a, b = divmod(code, n)
        best[a].append((-w, b))
        best[b].append((-w, a))
    pairs = set()
    for a, partners in best.items():
        partners.sort()
        # Keep ties at the cut. A record that never states its grade is
        # exactly as close to the SS304 variant as to the SS316 one; dropping
        # some of a tie at random would drop true pairs at random.
        cut = partners[min(TOP_K, len(partners)) - 1][0]
        for rank, (w, b) in enumerate(partners[:MAX_K]):
            if rank >= TOP_K and w > cut + 1e-9:
                break
            pairs.add((ids[min(a, b)], ids[max(a, b)]))

    # Embedding neighbours only for records extraction could barely read -
    # everything else already has its typed keys.
    from_vectors = {p for p in neighbour_pairs({r: specs[r] for r in specs}, vecs)
                    if p[0] in thin or p[1] in thin} - pairs
    pairs |= from_vectors

    all_pairs = n * (n - 1) // 2
    stats = {
        "records": n, "all_pairs": all_pairs, "candidate_pairs": len(pairs),
        "reduction_ratio": 1 - len(pairs) / all_pairs if all_pairs else 0.0,
        "keys": len(buckets), "largest_block": max((len(v) for v in buckets.values()), default=0),
        "weighted_pairs_before_pruning": len(weight),
        "purged_keys": dict(sorted(purged.items(), key=lambda x: -x[1])[:20]),
        "from_neighbours_only": len(from_vectors),
    }
    return sorted(pairs), stats
