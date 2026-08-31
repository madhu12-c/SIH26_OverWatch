# Aditya — the demo frontend

You are building the thing judges actually look at. Read this whole file before
opening an editor.

---

## Stack

| Piece | Choice | Why |
|---|---|---|
| Build | Vite + React | `npm run build` gives a folder that opens from a file |
| Styling | Tailwind | 21st.dev components assume it |
| Motion | Framer Motion | The spec-alignment animation is the demo |
| Components | 21st.dev | Lift and adapt. Do not build a design system this week. |
| Data | `import results from './results.json'` | Bundled at build time — no fetch, no server, no CORS, works offline |

**No backend.** That is deliberate: it is what makes the demo impossible to crash
on stage. Reasoning in [`../02-decisions/009-static-demo-no-backend.md`](../02-decisions/009-static-demo-no-backend.md).

---

## ⚠️ Set this or the build opens blank

```js
// vite.config.js
export default { base: './' }     // relative asset paths
```

Without it, `dist/index.html` requests `/assets/...` from the filesystem root and
renders a white page.

**Test by double-clicking `dist/index.html`.** `npm run dev` working proves
nothing about whether the built folder opens on a phone.

---

## Five screens, in demo order

| # | Screen | What it does |
|---|---|---|
| 01 | **Headline** | Records in, unique items out, duplication rate, rupees. Numbers count up on load. |
| 02 | **The Match** | SKF vs FAG. Text 0.31, then specs align field by field. **The money screen.** |
| 03 | **The Block** | SS316 vs SS304. Text 0.97, blocked on grade. The reverse case. |
| 04 | **Review queue** | Approve / reject with keyboard shortcuts. The actual product. |
| 05 | **Savings** | One item, four CPSEs, four prices. Then the total. |

**Build 02 first and build it well.** It is the argument; everything else is
context.

---

## Screen 02, in detail

The sequence only works in this order, because the reveal depends on the audience
first believing a fuzzy matcher would fail.

```
1.  Two description cards appear, side by side.
    Deliberately hard to read. Almost no shared words.

2.  A text-similarity meter fills to 0.31 and stops, in red.
    Label: "a conventional fuzzy matcher stops here"
    PAUSE. Let it sit. This beat is the setup.

3.  Specs slide in beneath each card, one row at a time, ~120ms apart.
    As each pair lands, a tick appears between them.
      iso_designation  6205  ✓  6205
      bore_mm            25  ✓  25
      od_mm              52  ✓  52
      width_mm           15  ✓  15
      seal_type         2RS  ✓  2RS

4.  The brand row lands LAST and greys out, struck through:
      brand             SKF  ⊗  FAG    ignored
    This single row is the entire technical idea. Give it its own beat.

5.  Final score counts up to 0.94, in green.
```

### Motion notes

- `staggerChildren: 0.12` on the spec list. **Do not animate all rows at once** —
  the sequence *is* the explanation.
- Ticks: `scale 0 → 1.15 → 1`, spring. Small overshoot, not a bounce party.
- Score counter: ease-out over ~800ms, `tabular-nums` so digits do not jitter.
- Honour `prefers-reduced-motion` — render the end state instantly.
- **A replay button.** Presenters re-run a moment. Do not make them refresh.

---

## Mobile: stack, never shrink

Side-by-side on a laptop. **Stacked vertically on a phone** — record A with its
specs, then record B with its specs, with the match indicator running down the
left edge.

Two columns squeezed onto a 390px screen is unreadable, and the phone build is the
backup that has to work when the laptop does not.

---

## The data you read

Madhu ships a stub with fake numbers first. **Start against the stub.** Real values
replace it Monday; the shape does not change.

```json
{
  "meta": { "records": 100, "items": 15, "duplication": 0.85,
            "precision": 0.98, "recall": 0.87, "savings_cr": 3.3 },

  "cases": {
    "match": {
      "a": { "record_id": "R00001", "cpse": "CPCL", "source_code": "100001445",
             "description": "SKF 6205-2RS DEEP GROOVE BALL BEARING",
             "attributes": { "iso_designation": "6205", "bore_mm": 25 } },
      "b": { "...": "same shape" },
      "text_sim": 0.31, "spec_sim": 0.97, "proc_sim": 0.88, "final": 0.94,
      "matched_fields": ["iso_designation","bore_mm","od_mm","width_mm","seal_type"],
      "ignored_fields": ["brand","part_number"]
    },
    "block": {
      "a": { "...": "" }, "b": { "...": "" },
      "text_sim": 0.97, "final": 0.0,
      "blocked_by": "material_grade",
      "reason": "SS316 vs SS304 - grade is a veto field"
    }
  },

  "clusters": [
    { "national_code": "NMC-31171500-000042",
      "std_description": "BEARING, BALL, DEEP GROOVE, 6205, 25X52X15 MM, 2RS SEALED",
      "unspsc": "31171500", "confidence": 0.94, "band": "auto",
      "members": [ { "record_id": "", "cpse": "", "source_code": "", "description": "" } ] }
  ],

  "review_queue": [ { "cluster_id": "", "confidence": 0.0,
                      "a": {}, "b": {}, "evidence": {} } ],

  "blocked": [ { "a": "", "b": "", "rule": "material_grade",
                 "reason": "SS316 vs SS304" } ],

  "savings": [
    { "national_code": "", "description": "Ball Bearing 6205-2RS",
      "cpses": [ { "cpse": "IOCL", "qty": 230, "avg_price": 1205, "value": 277150 } ],
      "total_qty": 2660, "total_value": 3570000,
      "best_price": 1205, "saving": 370000 }
  ]
}
```

---

## Screen 04 matters more than it looks

The review queue is the **actual product**. The reviewer is the only person who
uses this system daily, and if their experience is slow the whole project fails —
that is how master-data projects die everywhere in the world.

So: **keyboard shortcuts** (`A` approve, `R` reject, `S` skip), all evidence on
one screen, no hunting for context. A decision should take five seconds, not two
minutes.

---

## Done when

- [ ] `dist/index.html` opens by double-clicking, with wifi off
- [ ] The comparison is readable on a 390px screen
- [ ] Screen 02's sequence lands in the right order, with the brand row last
- [ ] A replay button exists
- [ ] Review queue works entirely from the keyboard

**Do not worry about the dashboard.** It is one slide. If time runs out, it is
what gets cut — not the review screen.
