# Setup

Getting a machine ready to run the pipeline.

---

## Minimum — enough to run everything except real extraction

```bash
python --version        # 3.11 or newer
pip install numpy
```

That is genuinely it. The dataset generator, the regex extractor and the
validation view all run with nothing else installed.

```bash
python src/generate_dataset.py
python src/extractor.py --no-llm
python src/extractor.py --validate --limit 4
```

Both demo cases work at this level, with no API key and no internet.

---

## For real spec extraction

```bash
pip install google-genai
```

Get a key from [aistudio.google.com](https://aistudio.google.com/apikey) — the
free tier covers our volume outright.

**Windows (cmd):**
```
set GEMINI_API_KEY=your_key_here
```

**Windows (PowerShell):**
```
$env:GEMINI_API_KEY = "your_key_here"
```

**bash:**
```bash
export GEMINI_API_KEY=your_key_here
```

Verify on ten records before the full run:

```bash
python src/extractor.py --limit 10
```

### Optional environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | — | The key |
| `GEMINI_MODEL` | `gemini-2.5-pro` | Switch models without editing code |
| `GEMINI_RPM` | `14` | Requests per minute. Free tier is around 15. |

### Cost

Around **₹2 for 100 records**, and development re-runs are free because results
are cached. Even with several full re-extractions, under ₹10.

---

## For embeddings

```bash
pip install sentence-transformers
```

**Check the GPU first — today, not Monday night:**

```bash
python src/embed.py --check
```

```
CUDA available -> NVIDIA GeForce RTX ... (8.0 GB)     good
CUDA NOT available - will run on CPU                   see below
```

If CPU: install a CUDA build of PyTorch from [pytorch.org](https://pytorch.org).
It is a ~2 GB download, which is why it cannot wait until the night before.

**Not urgent for Tuesday** — 100 records encode in about five seconds on CPU. It
matters when the dataset grows.

### The model

`BAAI/bge-small-en-v1.5` — 384 dimensions, ~130 MB. Downloads once on first run,
then works entirely offline, cached at:

```
C:\Users\<name>\.cache\huggingface\hub\
```

**Verify it is truly offline:**

```bash
set HF_HUB_OFFLINE=1
python src/embed.py
```

Or simply turn wifi off and run it.

---

## ⚠️ Demo machine preparation

Do this on whichever laptop presents on Tuesday, **before** Tuesday:

```
[ ] pip install sentence-transformers
[ ] python src/embed.py            <- caches the 130 MB model
[ ] wifi off, run the whole pipeline once
```

Downloading 130 MB on venue wifi is not a plan. If the demo machine is different
from the development machine, copying `~/.cache/huggingface/` across also works.

---

## For the UI

```bash
cd ui
npm install
npm run dev        # development
npm run build      # produces dist/
```

**Required in `vite.config.js`:**

```js
export default { base: './' }
```

Without it, `dist/index.html` requests assets from the filesystem root and renders
a blank white page.

**Test by double-clicking `dist/index.html`** — not just by checking `npm run dev`.

---

## Verify the whole install

```bash
python src/generate_dataset.py
python src/extractor.py --no-llm --fresh
python src/extractor.py --validate --limit 4
```

Expected:

```
materials.csv       100 records
ground_truth.csv    100 rows, 15 true items
purchases.csv       ~245 purchase orders
duplication rate    85.0%

R00001  [bearing]   iso_designation 6205, seal_type 2RS
R00002  [bearing]   iso_designation 6205, bore_mm 25, ...
R00003  [gasket]    material_grade SS316
R00004  [gasket]    material_grade SS304
```

If R00003 and R00004 show different `material_grade` values, the demo's blocking
case works. If R00001 and R00002 both show `6205`, the matching case works.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: paths` | Running from inside `src/` | Run from the project root: `python src/extractor.py` |
| Specs describe records that do not exist | Stale cache after regenerating data | `python src/extractor.py --fresh` |
| `no API key found` | Variable not set in this shell | Env vars do not persist between terminals — set it again |
| Extraction stalls | Free-tier rate limit | Expected. Lower `GEMINI_RPM`, or wait — it retries with backoff |
| `torch ... +cpu` | CPU-only PyTorch | Fine for 100 records. CUDA build from pytorch.org when needed. |
| Blank page from `dist/index.html` | `base` not set | `base: './'` in `vite.config.js` |
