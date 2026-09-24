# Deliverables

Shareable outputs. Everything here is generated from or derived from the docs and
code — nothing is authored only in this folder.

---

## Published links

| Item | Link | Source file |
|---|---|---|
| Architecture reference | https://claude.ai/code/artifact/492ff1ce-7e12-4478-b869-a4078f2bdd77 | `architecture.html` |
| Team sprint brief | https://claude.ai/code/artifact/b2873154-71d8-4afc-8a4e-098a5d96d0f8 | `team-brief.html` |

Both are **private by default** — share from the page's share menu.

⚠️ **These files moved** into `deliverables/` after they were first published. To
update one and keep its existing link, the publish must reference the URL above —
publishing from the new path alone creates a separate artifact with a new link.

---

## Files

| File | What it is |
|---|---|
| `architecture.html` | Full stage-by-stage architecture, written in plain English for the whole team |
| `Architecture.pdf` | The same document, 25 pages — for WhatsApp and offline reading |
| `team-brief.html` | Per-person task cards, file contracts, and the UI design spec |
| `progress-explained.html` | The whole project in plain words: before vs now, the 14-step workflow, every feature built or not, the plan (24 Sept 2026) |
| `Overwatch-Progress-Explained.pdf` | The same document, 25 pages. Printed with system fonts, so the font issue below does not apply |

---

## Regenerating the PDF

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --headless --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=25000 \
  --print-to-pdf="deliverables/Architecture.pdf" \
  "file:///C:/Users/MSI-PC/Desktop/SIH/deliverables/architecture.html"
```

**Known issue:** Chrome's print-to-PDF silently drops variable fonts, so body text
falls back to Times New Roman instead of Source Serif 4. Content is correct;
typography is not what the HTML shows. The fix is to inline static font instances
from the v1 Google Fonts API before printing.

---

## Not yet here

- The deck (PPT) — Meghna
- Screenshots of all five demo screens, for the deck's fallback slides
- Evidence screenshots of real GeM / eprocure descriptions — Isha, these belong in
  `docs/03-reference/evidence/`
