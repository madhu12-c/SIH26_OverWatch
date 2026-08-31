# Schemas, hard blockers and ignored fields

The contract between extraction and matching. Defined once in
[`src/schemas.py`](../../src/schemas.py) — nothing else hard-codes field names.

```python
import schemas

schemas.fields_for("gasket")       # every Field object
schemas.hard_fields("gasket")      # ['material_grade', 'nominal_size_in', 'pressure_class']
schemas.ignored_fields("bearing")  # ['brand', 'part_number']
schemas.scoring_fields("valve")    # everything not ignored, with .weight
```

---

## The three field properties

| Property | Meaning |
|---|---|
| `hard=True` | **Veto field.** A mismatch is an instant zero, however well everything else lines up. |
| `ignore=True` | **Never counts toward a match.** Extracted for display only. |
| `weight` | Relative pull of an ordinary field when both records state it. |

And one rule that is not a flag, because it cannot be — the scorer must honour it:

> **Missing is not mismatched.** If one record states a field and the other is
> silent, that is absent information, not evidence of difference. No penalty, no
> credit.

Easy to get wrong, and it matters here: in our own data R00001 extracts two fields
and R00002 extracts five, and they must still match.

---

## Why brand and part number are ignored

This is the single decision that makes the headline demo case work.

```
"SKF 6205-2RS Deep Groove Ball Bearing"
"FAG 6205-2RSR bearing, 25x52x15mm"
```

Different brand, different part number, same bearing. If brand contributes *even
slightly* to the score, this pair stops matching and the demo collapses.

Functional equivalence does not care who manufactured the item.

---

## Why grade and rating are vetoes

Not a tuning choice — a safety property.

| Field | Mismatch means |
|---|---|
| `material_grade` | SS304 where SS316 is specified → pitting corrosion → leak |
| `pressure_class` | 150# gasket in a 300# joint → joint failure |
| `iso_designation` | 6205 vs 6206 → the bearing does not fit |
| `thread` / `length_mm` | Wrong fastener in a structural joint |
| `nominal_size_in` | Does not fit |

A high text similarity must never override these. That is exactly the failure mode
of a fuzzy matcher, and it is what our second demo case demonstrates.

---

## The nine categories

Hard blockers marked **★**. Ignored fields marked ⊗. `brand` and `part_number` are
ignored in every category.

### bearing
```
  sub_type          enum   deep_groove_ball, angular_contact, cylindrical_roller, ...
★ iso_designation   str    6205, 6206, 22215        weight 3.0
★ bore_mm           num    mm                       weight 2.0
  od_mm             num    mm
  width_mm          num    mm
  seal_type         enum   2RS, RS, 2Z, Z, OPEN     (2RSR/2RS1/LLU all → 2RS)
⊗ brand, part_number
```

### gasket
```
  gasket_type       enum   spiral_wound, ring_joint, full_face, flat, camprofile
★ material_grade    str    SS316 / SS304 / SS316L / CS      weight 3.0
★ nominal_size_in   num    inch
★ pressure_class    str    150#, 300#, 600#
  filler            str    graphite, PTFE
  thickness_mm      num
```

### pipe
```
★ construction      enum   seamless, welded, erw, saw
★ material_grade    str    carbon_steel / SS316 / SS304     weight 3.0
  standard          str    ASTM A106 GR B, ASTM A312 TP316
★ nominal_size_in   num    inch
★ schedule          str    SCH 40, SCH 80
```

### valve
```
★ valve_type        enum   gate, globe, ball, check, butterfly, plug, ...
★ nominal_size_in   num    inch
★ pressure_class    str    150#, 300#, 600#, 800#           weight 2.5
★ body_material     str    cast_steel / SS316 / carbon_steel
  end_connection    enum   flanged, screwed, socket_weld, butt_weld, wafer
  bore_type         enum   full, reduced
  standard          str    API 600, API 6D
```

### fastener
```
★ fastener_type     enum   bolt, stud_bolt, screw, nut, washer, anchor
  head_type         enum   hex, socket, csk, pan, none
★ thread            str    M12, M20, 1/2-13 UNC             weight 2.5
★ length_mm         num    mm
★ material_grade    str    SS316 / A193 B7 / 8.8 / 4.6      weight 2.5
  standard          str    IS 1364, ASTM A193
```

### flange
```
★ flange_type       enum   weld_neck, slip_on, blind, socket_weld, threaded, lap_joint
  face_type         enum   raised_face, flat_face, ring_joint
★ nominal_size_in   num    inch
★ pressure_class    str
★ material_grade    str    ASTM A105, F316
  bore_schedule     str
```

### rotating
```
★ component_type    enum   mechanical_seal, impeller, coupling, shaft_sleeve, wear_ring
  arrangement       enum   single, double, tandem, cartridge_single, cartridge_double
★ shaft_dia_mm      num    mm                               weight 2.5
  face_materials    str    SIC vs carbon
  elastomer         str    viton, nitrile, EPDM
```

### instrument
```
★ instrument_type   enum   pressure_gauge, temperature_gauge, transmitter, ...
  dial_size_mm      num
★ range_min         num
★ range_max         num
  range_unit        str    bar, kg/cm2, psi, degC
★ wetted_material   str    SS316
  connection        str    1/2 IN NPT bottom
```

### electrical
```
★ equipment_type    enum   motor, cable, switchgear, transformer, lighting, starter
★ phases            num
★ power_hp          num                                     weight 2.5
★ speed_rpm         num
★ voltage_v         num
  mounting          enum   foot, flange, face, vertical
  protection_class  str    IP55
```

### unknown
Records that fit no schema. Only `noun` plus the ignored fields. **Route to human
review** — never auto-merge an unknown.

---

## Value canonicalisation

The extractor returns `"SS 316"`, `"ss316"` and `"316 SS"` for the same thing.
Matching compares values directly, so they must converge before storage.

`schemas.canonical_value(field, value)` handles this:

```
ss316, SS 316, stainless steel 316   ->  SS316
cs, C.S., carbon steel, carb stl      ->  CARBON_STEEL
2RS, 2RSR, 2RS1, LLU, DDU             ->  2RS
150, 150#, class 150                  ->  150#
sch40, SCH 40, schedule 40            ->  SCH 40
```

Punctuation is stripped and the compacted form is tried too — otherwise `C.S.`
becomes `c s` and never matches `^cs$`. That bug was real and is fixed.

---

## Adding a category

1. Add the entry to `CATEGORIES` in `src/schemas.py`, ending with `*COMMON`.
2. Mark the veto fields `hard=True`. **Ask what happens if the wrong one is
   issued** — if the answer is a safety or fit failure, it is hard.
3. Add a detection pattern to `_CATEGORY_HINTS` so the regex fallback can find it.
4. Add regex patterns for the fields worth catching without a model.
5. Add alias rules to `canonical_value` if the field has spelling variants.

The extraction prompt builds itself from the schema, so nothing else changes.
