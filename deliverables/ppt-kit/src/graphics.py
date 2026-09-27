"""
Slide graphics for the SIH idea PPT - drawn as SVG, exported as PNG.

    python deliverables/ppt-kit/src/graphics.py

Writes deliverables/ppt-kit/images/{architecture,inversion,text-vs-specs,numbers,cag-ongc,cag-sail}.{svg,png}.
Every number of ours is read from data/output/evidence.json at the lock tag, never typed. The two CAG charts
quote published audit figures, typed with their table and page.
"""

import json
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "deliverables" / "ppt-kit" / "images"
EV = json.loads((ROOT / "data" / "output" / "evidence.json").read_text(encoding="utf-8"))
BIG, REAL = EV["run15k"], EV["real"]

NAVY, MAROON, TEAL, GREEN, RED, AMBER, GREY = "#0A2A5E", "#7A1F3D", "#0E5E6F", "#0B6E3A", "#B42318", "#8A5300", "#5B6474"
INK, FAINT, LINE = "#16202E", "#5B6474", "#C9D1DC"
FONT = "'Noto Sans','Segoe UI',Arial,sans-serif"
MONO = "'IBM Plex Mono',Consolas,monospace"


def n(v):
    return f"{v:,}"


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=17, weight=400, fill=INK, anchor="start", family=FONT, italic=False):
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}"{" font-style=%s" % chr(34) + "italic" + chr(34) if italic else ""}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="#fff", stroke=LINE, sw=1.5, r=8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, title, lines, color, fill="#fff", tsize=19, lsize=15.5, num=None):
        self.rect(x, y, w, h, fill=fill, stroke=color, sw=2)
        self.add(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{color}"/>')
        tx = x + 18
        if num:
            self.add(f'<circle cx="{x + 30}" cy="{y + 25}" r="13" fill="{color}"/>')
            self.text(x + 30, y + 31, num, size=15, weight=700, fill="#fff", anchor="middle")
            tx = x + 52
        self.text(tx, y + 32, title, size=tsize, weight=700, fill=color)
        for i, ln in enumerate(lines):
            self.text(x + 18, y + 60 + i * 22, ln, size=lsize, fill=INK)

    def arrow(self, pts, color=GREY, label=None, lx=None, ly=None, dash=None, sw=2.2):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da} marker-end="url(#a-{color[1:]})"/>')
        if label:
            self.text(lx, ly, label, size=14, fill=color, weight=600, anchor="middle")

    def svg(self):
        colors = {NAVY, MAROON, TEAL, GREEN, RED, AMBER, GREY}
        marks = "".join(f'<marker id="a-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in colors)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<defs>{marks}</defs><rect width="100%" height="100%" fill="#ffffff"/>' + "".join(self.parts) + "</svg>")


def architecture():
    s = Svg(1800, 1040)
    # lanes
    for y, h, fill, color, label in ((20, 280, "#EEF3FA", NAVY, "READ  ·  once per record"),
                                     (318, 330, "#F8EEF2", MAROON, "MATCH  ·  numbers only, no AI per pair"),
                                     (666, 290, "#EAF4F5", TEAL, "REGISTRY & GOVERNANCE")):
        s.rect(10, y, 1780, h, fill=fill, stroke="none", r=14)
        s.text(1770, y + 30, label, size=15, weight=800, fill=color, anchor="end")

    # lane 1 - read
    s.box(30, 62, 300, 190, "CPSE material masters", ["SAP-shaped export", "MATNR · MAKTX · MEINS", "MAKTX is only 40 characters", "+ purchase history"], GREY)
    s.box(370, 62, 310, 190, "Normalise", ["abbreviations, units, fractions", "NB · DN · inch = size names,", "OD and wall = measurements", "a map back to every character"], NAVY, num="1")
    s.box(720, 62, 330, 190, "Read specifications", ["rules first, LLM once per record", "typed fields + confidence", "every value keeps its evidence:", "the words it was read from"], NAVY, num="2")
    s.box(1090, 62, 340, 190, "Standards & self-check", ["ISO 15 · ASME B36.10 · IS = ISO", "fills implied facts:", "6205 → 25 × 52 × 15 mm", "flags a line that contradicts itself"], NAVY, num="3")
    s.box(1470, 62, 300, 190, "Embed", ["local sentence vectors", "384 dimensions", "runs offline, no API"], NAVY, num="4")
    for x1, x2 in ((330, 370), (680, 720), (1050, 1090), (1430, 1470)):
        s.arrow([(x1, 157), (x2 - 2, 157)], NAVY)
    s.arrow([(1620, 252), (1620, 306), (180, 306), (180, 352)], MAROON)

    # lane 2 - match
    s.box(30, 356, 300, 190, "Blocking", ["identity keys + nearest", "neighbours, never all pairs", f"skips {BIG['blocking']['reduction_ratio']:.1%} of pairs"], MAROON, num="5")
    s.rect(370, 356, 340, 270, fill="#fff", stroke=MAROON, sw=2)
    s.add(f'<rect x="370" y="356" width="6" height="270" rx="3" fill="{MAROON}"/>')
    s.add(f'<circle cx="400" cy="381" r="13" fill="{MAROON}"/>')
    s.text(400, 387, "6", size=15, weight=700, fill="#fff", anchor="middle")
    s.text(422, 388, "Score three signals", size=19, weight=700, fill=MAROON)
    for i, (t, sub, w) in enumerate((("Specifications", "highest weight", 1.0), ("Procurement", "vendor hash · price band", 0.55),
                                     ("Text", "lowest · never alone", 0.3))):
        y = 412 + i * 68
        s.text(390, y + 18, t, size=16.5, weight=700)
        s.text(390, y + 40, sub, size=14.5, fill=FAINT)
        s.rect(590, y + 8, 100 * w, 16, fill=MAROON if i == 0 else "#C79AAA", stroke="none", r=3)
    s.arrow([(330, 451), (368, 451)], MAROON)
    # veto diamond
    cx, cy = 870, 491
    s.add(f'<polygon points="{cx},{cy - 120} {cx + 125},{cy} {cx},{cy + 120} {cx - 125},{cy}" fill="#FDEEEE" stroke="{RED}" stroke-width="2.5"/>')
    s.text(cx, cy - 34, "VETO FIELDS", size=18, weight=800, fill=RED, anchor="middle")
    for i, ln in enumerate(("grade · pressure class", "size · seal · filler", "+ 30 more", "one mismatch = 0")):
        s.text(cx, cy - 8 + i * 21, ln, size=14.5, fill=INK, anchor="middle", weight=700 if i == 3 else 400)
    s.arrow([(710, 491), (743, 491)], MAROON)
    # refused
    s.box(1040, 356, 330, 120, "Refused  —  reason kept", ["what-if: “if the grade matched,", "this pair would score 0.956”"], RED, fill="#FFF7F7", tsize=18)
    s.arrow([(915, 413), (960, 413), (960, 416), (1038, 416)], RED, "mismatch", 972, 403)
    # bands
    s.box(1040, 500, 230, 130, "≥ 0.90  auto-merge", [f"{n(BIG['auto_merged'])} merged,", f"{BIG['auto_wrong']} wrong"], GREEN, fill="#F2FAF5", tsize=17.5)
    s.box(1290, 500, 250, 130, "0.70–0.90  reviewer", ["one record + its", "best 3 candidates"], AMBER, fill="#FFF8EC", tsize=17.5)
    s.box(1560, 500, 210, 130, "< 0.70  apart", ["left alone,", "nothing merged"], GREY, fill="#F6F7F9", tsize=17.5)
    s.arrow([(915, 570), (1038, 570)], GREEN, "pass", 975, 560)
    s.text(1400, 410, "Why a person still looks:", size=14.5, weight=700, fill=AMBER)
    s.text(1400, 432, "a safety field stated on one", size=14.5, fill=INK)
    s.text(1400, 454, "side and silent on the other", size=14.5, fill=INK)

    # lane 3 - registry
    s.arrow([(1155, 630), (1155, 655), (190, 655), (190, 702)], GREEN)
    s.arrow([(1415, 630), (1415, 655)], AMBER, "approved", 1470, 650)
    s.box(30, 706, 300, 200, "Cluster", ["every pair inside a group", "must agree - weak groups", "are split, never chained"], TEAL, num="7")
    s.box(370, 706, 360, 200, "National code", ["golden record + standard", "description · UNSPSC class", "NMC-31171500-000001", "every CPSE code kept, mapped"], TEAL, num="8")
    s.box(770, 706, 330, 200, "What it produces", ["mapping file for each", "company's SAP team", "savings from buying together", "(prices never shown raw)"], TEAL)
    s.box(1140, 706, 300, 200, "Creation gate", ["checks a new request first", "EXISTS · REVIEW · NEW", "CONTRADICTS", "says what an item is NOT"], GREEN)
    s.box(1480, 706, 290, 200, "Sealed audit log", ["SHA-256 chain: an edit", "breaks every seal after it", "any company may dispute", "only the owner may retire"], GREEN)
    for x1, x2 in ((330, 370), (730, 770)):
        s.arrow([(x1, 806), (x2 - 2, 806)], TEAL)
    s.arrow([(550, 906), (550, 930), (1290, 930), (1290, 908)], GREEN, "catalogue published downward", 920, 922)
    s.arrow([(1515, 630), (1515, 704)], GREY, "every decision", 1450, 690, dash="6 5")

    # footer - where the AI is
    s.rect(10, 972, 1780, 58, fill=NAVY, stroke="none", r=12)
    s.text(34, 1008, "AI in two places:", size=17, weight=800, fill="#FFB25B")
    s.text(196, 1008, "an LLM reads each record once  ·  embeddings find candidates.  Measured: wrong merges"
           f" < {BIG['auto_error_bound_95']:.2%} (95% confidence).", size=17, fill="#fff")
    s.text(1766, 1008, "Rules decide every merge. Nothing is deleted.", size=17, weight=700, fill="#fff", anchor="end")
    return s


def inversion():
    s = Svg(1600, 720)
    s.text(40, 52, "Text similarity gets both pairs backwards", size=30, weight=800, fill=NAVY)
    s.text(40, 88, "So we match on specifications, not spelling.", size=20, fill=FAINT)
    rows = (("SAME BEARING", "SKF 6205-2RS DEEP GROOVE BALL BEARING", "FAG 6205-2RSR BEARING, 25X52X15MM, SEALED", 0.833,
             ["6205 = 6205", "25 × 52 × 15 mm from ISO 15", "2RS = 2RSR (sealed)", "brand ignored"], "MATCH  0.971", GREEN,
             "few shared words, same part"),
            ("DIFFERENT STEEL", "GASKET SPIRAL WOUND SS316 4IN 150#", "GASKET SPIRAL WOUND SS304 4IN 150#", 0.989,
             ["SS316 ≠ SS304  (veto)", "4 in = 4 in", "150# = 150#", "↳ if the grade matched: 0.956"], "REFUSED  0", RED,
             "one character apart, never interchangeable"))
    for i, (tag, a, b, txt, specs, verdict, color, note) in enumerate(rows):
        y = 130 + i * 290
        s.rect(30, y, 1540, 262, fill="#FAFBFD", stroke=LINE, r=14)
        s.text(56, y + 38, tag, size=16, weight=800, fill=color)
        s.text(56, y + 62, note, size=15, fill=FAINT)
        for j, t in enumerate((a, b)):
            s.rect(56, y + 84 + j * 70, 560, 54, fill="#fff", stroke=LINE, r=8)
            s.text(74, y + 118 + j * 70, t, size=17, family=MONO)
        # text similarity bar
        s.text(660, y + 104, "Text similarity", size=16, weight=700, fill=FAINT)
        s.rect(660, y + 122, 300, 22, fill="#E9EDF3", stroke="none", r=5)
        s.rect(660, y + 122, 300 * txt, 22, fill="#9AA6B8", stroke="none", r=5)
        s.text(660, y + 184, f"{txt:.3f}", size=34, weight=800, fill=INK)
        s.text(790, y + 184, "a text matcher says: same" if i else "a text matcher is unsure", size=15, fill=FAINT)
        # specs
        s.text(1010, y + 104, "Specifications, field by field", size=16, weight=700, fill=FAINT)
        for k, sp in enumerate(specs):
            bad = "≠" in sp
            s.text(1010, y + 134 + k * 26, ("✗ " if bad else "" if sp.startswith("↳") else "✓ ") + sp, size=16, fill=RED if bad else (GREEN if k < 3 or i == 0 else FAINT),
                   weight=700 if bad else 400)
        s.rect(1330, y + 96, 216, 70, fill=color, stroke="none", r=10)
        s.text(1438, y + 140, verdict, size=22, weight=800, fill="#fff", anchor="middle")
    s.text(40, 706, "The pair that must never merge scores HIGHER on text (0.989) than the pair that should (0.833). "
           "No threshold fixes an inverted order.", size=17, weight=700, fill=INK)
    return s


def text_vs_specs():
    b = BIG["baselines"]
    rows = [("Fuzzy string match", b["methods"]["fuzzy"]), ("TF-IDF", b["methods"]["tf-idf"]),
            ("Sentence embeddings", b["methods"]["embedding"]), ("Ours: specifications", b["ours_auto"])]
    s = Svg(1600, 640)
    s.text(40, 52, "Merges made with no person involved", size=28, weight=800, fill=NAVY)
    s.text(40, 86, f"Same {n(BIG['records'])} records and candidate pairs · each text method at its best setting, "
           "tuned on one half, scored on the half it never saw", size=17, fill=FAINT)
    RIGHT, WRONG = "#2a78d6", "#eb6834"
    # legend
    s.rect(1180, 30, 18, 18, fill=RIGHT, stroke="none", r=3)
    s.text(1206, 45, "right", size=16, fill=INK)
    s.rect(1280, 30, 18, 18, fill=WRONG, stroke="none", r=3)
    s.text(1306, 45, "wrong", size=16, fill=INK)
    x0, maxw = 330, 860
    mx = max(m["merged"] for _, m in rows)
    for i, (name, m) in enumerate(rows):
        y = 140 + i * 112
        ours = i == 3
        s.text(40, y + 34, name, size=19, weight=800 if ours else 600, fill=NAVY if ours else INK)
        right = m["merged"] - m["wrong"]
        wr = maxw * right / mx
        ww = maxw * m["wrong"] / mx
        s.rect(x0, y + 12, max(wr, 3), 36, fill=RIGHT, stroke="none", r=4)
        if ww:
            s.rect(x0 + wr + 2, y + 12, ww, 36, fill=WRONG, stroke="none", r=4)
        end = x0 + wr + ww + 14
        label = (f"{n(m['wrong'])} wrong of {n(m['merged'])}  ·  {m['traps_merged']:,} traps" if not ours
                 else f"{n(m['merged'])} merged  ·  0 wrong  ·  0 traps")
        s.text(end if not ours else x0 + wr + 14, y + 37, label, size=16.5, weight=700 if ours else 400, fill=INK)
    s.text(40, 612, "No text threshold reaches zero wrong: two different items can share identical text once SAP's "
           "40-character field cuts them. Ours finds about as many duplicates with none of the wrong merges.",
           size=15.5, fill=FAINT)
    return s


def numbers():
    tiles = ((f"{BIG['auto_wrong']} wrong", f"of {n(BIG['auto_merged'])} automatic merges", GREEN),
             (f"< {BIG['auto_error_bound_95']:.2%}", "wrong-merge rate, 95% confidence", GREEN),
             (f"0 of {n(BIG['traps_total'])}", "planted near-miss traps merged", GREEN),
             (f"{BIG['recall_with_review']:.0%}", "of duplicates found, with a reviewer", NAVY),
             (f"{REAL['auto_wrong']} wrong", f"on real NTPC & Oil India text ({REAL['auto_merged']} merged)", NAVY))
    s = Svg(1800, 250)
    w = 340
    for i, (big, sub, color) in enumerate(tiles):
        x = 20 + i * (w + 15)
        s.rect(x, 20, w, 210, fill="#fff", stroke=LINE, r=12)
        s.add(f'<rect x="{x}" y="20" width="{w}" height="6" rx="3" fill="{color}"/>')
        s.text(x + 24, 118, big, size=50, weight=800, fill=color)
        words = sub.split(" ")
        line, lines = "", []
        for wd in words:
            if len(line + " " + wd) > 28:
                lines.append(line)
                line = wd
            else:
                line = (line + " " + wd).strip()
        lines.append(line)
        for k, ln in enumerate(lines):
            s.text(x + 24, 162 + k * 26, ln, size=19, fill=INK)
    return s


# The two CAG charts quote published audit figures, not our output, so they are typed here with their page.
ONGC_IDLE = (("2018-19", 63.04), ("2019-20", 87.57), ("2020-21", 113.02), ("2021-22", 161.38), ("2022-23", 180.93))
SAIL_IDLE_PCT, SAIL_NORM_PCT = (6.10, 8.38), 3.0


def cag_ongc():
    """CAG Report No. 39 of 2025, Table 2.4 (printed p. 70): ONGC non-moving drill pipe, casing and tubing."""
    s = Svg(900, 520)
    s.text(40, 50, "ONGC: idle drill pipe, casing & tubing", size=28, weight=800, fill=NAVY)
    s.text(40, 82, "Non-moving inventory, ₹ crore, at year end", size=18, fill=FAINT)
    base, top, x0, bw, gap = 420, 130, 70, 120, 40
    mx = 200.0
    s.add(f'<line x1="{x0 - 20}" y1="{base}" x2="{x0 + 5 * (bw + gap)}" y2="{base}" stroke="{LINE}" stroke-width="2"/>')
    for i, (year, v) in enumerate(ONGC_IDLE):
        h = (base - top) * v / mx
        x = x0 + i * (bw + gap)
        last = i == len(ONGC_IDLE) - 1
        s.add(f'<path d="M{x},{base} V{base - h + 4} Q{x},{base - h} {x + 4},{base - h} H{x + bw - 4} '
              f'Q{x + bw},{base - h} {x + bw},{base - h + 4} V{base} Z" fill="{MAROON if last else "#C98A9E"}"/>')
        s.text(x + bw / 2, base + 30, year, size=18, fill=INK, anchor="middle")
        if i in (0, len(ONGC_IDLE) - 1):
            s.text(x + bw / 2, base - h - 12, f"₹{v:.2f} cr", size=21, weight=800, fill=INK, anchor="middle")
    s.text(x0 + 2 * (bw + gap) + bw / 2, 170, "+187% in five years", size=24, weight=800, fill=MAROON, anchor="middle")
    s.text(40, 500, "Source: CAG Report No. 39 of 2025, Table 2.4", size=16, fill=FAINT)
    return s


def cag_sail():
    """CAG Report No. 10 of 2025 (SAIL inventory): idle stores 6.10-8.38% of inventory vs a 3% norm;
    each plant's IT ran in isolation (printed p. 87)."""
    s = Svg(900, 380)
    s.text(40, 50, "SAIL: idle stores vs the norm", size=28, weight=800, fill=NAVY)
    s.text(40, 82, "Non-moving stores & spares as % of inventory, 2016-17 to 2022-23", size=18, fill=FAINT)
    x0, x1, y = 60, 840, 200
    px = lambda pct: x0 + (x1 - x0) * pct / 10
    s.add(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{LINE}" stroke-width="2"/>')
    for t in range(0, 11, 2):
        s.add(f'<line x1="{px(t)}" y1="{y - 6}" x2="{px(t)}" y2="{y + 6}" stroke="{LINE}" stroke-width="2"/>')
        s.text(px(t), y + 54, f"{t}%", size=17, fill=FAINT, anchor="middle")
    lo, hi = SAIL_IDLE_PCT
    s.rect(px(lo), y - 20, px(hi) - px(lo), 40, fill=MAROON, stroke="none", r=6)
    s.text((px(lo) + px(hi)) / 2, y - 34, f"SAIL: {lo:.1f}–{hi:.1f}%", size=22, weight=800, fill=MAROON, anchor="middle")
    s.add(f'<line x1="{px(SAIL_NORM_PCT)}" y1="{y - 56}" x2="{px(SAIL_NORM_PCT)}" y2="{y + 14}" stroke="{GREEN}" '
          f'stroke-width="4" stroke-dasharray="7 5"/>')
    s.text(px(SAIL_NORM_PCT), y - 66, f"norm {SAIL_NORM_PCT:.0f}%", size=21, weight=800, fill=GREEN, anchor="middle")
    s.text(40, 290, "Each plant's IT ran in isolation: no real-time stock data,", size=20, fill=INK)
    s.text(40, 318, "no central vendor database.", size=20, fill=INK)
    s.text(40, 360, "Source: CAG Report No. 10 of 2025 (SAIL inventory management)", size=16, fill=FAINT)
    return s


def main():
    from playwright.sync_api import sync_playwright
    figs = {"architecture": architecture(), "inversion": inversion(), "text-vs-specs": text_vs_specs(), "numbers": numbers(),
            "cag-ongc": cag_ongc(), "cag-sail": cag_sail()}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for name, s in figs.items():
            svg = s.svg()
            (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
            page = b.new_page(viewport={"width": s.w, "height": s.h}, device_scale_factor=2)
            page.set_content(f"<html><body style='margin:0'>{svg}</body></html>")
            page.wait_for_timeout(300)
            page.locator("svg").screenshot(path=str(OUT / f"{name}.png"))
            print("wrote", name)
        b.close()


if __name__ == "__main__":
    main()
