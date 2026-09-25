"""
Self-check - a record checked against itself, before it can match anything.

A line that says "6205" and "30 x 62 x 16 mm" contradicts itself: ISO 15 makes
a 6205 25 x 52 x 15, and 30 x 62 x 16 is a 6206. One of the two facts is wrong
and nothing in the line says which. Matching it to either bearing would be a
guess, so a pair that involves a contradicted record never auto-merges; a
person sees the contradiction first.

Only facts the line STATES are checked. A value filled in from a standard
(derive) agrees with its source by construction, so it can never contradict
it. With the rule reader, "stated" means the value has an evidence span; a
model-read record has no spans, and all its fields are treated as stated.

Rules, each with its source:
    bearing   designation against stated bore / OD / width      ISO 15
              bore smaller than OD                              geometry
    pipe      stated OD against the OD of the nominal size      ASME B36.10M
              stated wall against the wall of the schedule      ASME B36.10M / B36.19M
              wall less than half the OD                        geometry
    motor     kW against hp (1 hp = 0.746 kW)                   IS 12615 nameplates
              rpm against poles (synchronous 50 or 60 Hz)       120 f / p
    gauge     range from below range to                         -
    any       a dimension in mm that is zero or negative        -

Tolerances are loose on purpose (OD 3%, wall 5%, power 6%): IS 1239 pipe
ODs differ from ASME by up to 2%, and nameplates round. A false alarm costs
a reviewer a look; the point is to catch the 6205 that is really a 6206.
"""

from __future__ import annotations

import normalise as nz
import standards
from schemas import _octg

OD_TOL, WALL_TOL, POWER_TOL = 0.03, 0.05, 0.06


def _stated(out: dict) -> set:
    attrs = out.get("attributes") or {}
    spans = out.get("evidence")
    if spans:
        return {k for k in attrs if k in spans}
    return set(attrs)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def check(out: dict) -> list[dict]:
    """Contradictions inside one extracted record: [{field, stated, expected, rule}]."""
    category = out.get("category")
    attrs = out.get("attributes") or {}
    said = _stated(out)
    found = []

    def flag(field, stated, expected, rule):
        found.append({"field": field, "stated": stated, "expected": expected, "rule": rule})

    def val(name):
        return _num(attrs.get(name)) if name in said else None

    for name in said:
        if name.endswith("_mm") or name == "nominal_size_in":
            v = _num(attrs.get(name))
            if v is not None and v <= 0:
                flag(name, v, "> 0", "a size cannot be zero or negative")

    if category == "bearing":
        des = attrs.get("iso_designation") if "iso_designation" in said else None
        dims = standards.bearing_dims(des) if des else None
        if dims:
            stated = [val(n) for n in ("bore_mm", "od_mm", "width_mm")]
            if any(v is not None and abs(v - e) > 0.5 for v, e in zip(stated, dims)):
                twin = next((d for d, row in standards.ISO15.items()
                             if all(v is None or abs(v - e) <= 0.5 for v, e in zip(stated, row))), None)
                flag("dimensions", " x ".join("?" if v is None else f"{v:g}" for v in stated) + " mm",
                     " x ".join(f"{e:g}" for e in dims) + " mm",
                     f"ISO 15: a {des} is {dims[0]:g} x {dims[1]:g} x {dims[2]:g} mm"
                     + (f" - these dimensions are a {twin}" if twin else ""))
        bore, od = val("bore_mm"), val("od_mm")
        if bore and od and bore >= od:
            flag("bore_mm", bore, f"< {od:g}", "the bore must be smaller than the outside diameter")

    if category == "pipe" and not _octg(attrs):
        nps, od, wall = val("nominal_size_in"), val("od_mm"), val("wall_mm")
        expect_od = nz.od_for_nps(nps) if nps else None
        if expect_od and od and abs(od - expect_od) / expect_od > OD_TOL:
            flag("od_mm", od, expect_od, f"ASME B36.10M: a {nps:g} in pipe is {expect_od:g} mm OD")
        schedule = attrs.get("schedule") if "schedule" in said else None
        expect_wall = standards.pipe_wall(nps, schedule) if nps and schedule else None
        if expect_wall and wall and abs(wall - expect_wall) / expect_wall > WALL_TOL:
            flag("wall_mm", wall, expect_wall, f"ASME B36.10M: {nps:g} in {schedule} is {expect_wall:g} mm wall")
        outer = od or expect_od
        if outer and wall and wall >= outer / 2:
            flag("wall_mm", wall, f"< {outer / 2:g}", "the wall must be less than half the outside diameter")

    if category == "electrical":
        kw, hp = val("power_kw"), val("power_hp")
        if kw and hp and abs(hp - kw / 0.746) / (kw / 0.746) > POWER_TOL:
            flag("power_hp", hp, round(kw / 0.746, 1), f"{kw:g} kW is {kw / 0.746:.1f} hp")
        rpm, poles = val("speed_rpm"), val("poles")
        if rpm and poles and poles >= 2:
            sync = [120 * f / poles for f in (50, 60)]
            if not any(0.85 * s <= rpm <= s for s in sync):
                flag("speed_rpm", rpm, f"about {sync[0]:g}",
                     f"a {poles:g}-pole motor runs just under {sync[0]:g} rpm (50 Hz)")

    if category == "instrument":
        lo, hi = val("range_min"), val("range_max")
        if lo is not None and hi is not None and lo >= hi:
            flag("range_min", lo, f"< {hi:g}", "the range must run from low to high")

    return found


def describe(c: dict) -> str:
    """One plain sentence for a reviewer."""
    return f"{c['field'].replace('_', ' ')} {c['stated']:g} - {c['rule']}" if isinstance(c["stated"], float) \
        else f"{c['field'].replace('_', ' ')} {c['stated']} - {c['rule']}"
