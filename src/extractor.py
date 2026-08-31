"""
Spec extractor - the critical path.

Turns a messy one-line material description into typed attributes with a
confidence score on every field. Everything downstream consumes this output, so
if extraction is unreliable nothing else can work. Validate it by hand on 50
records before trusting any number the pipeline produces.

Two rules from CLAUDE.md are enforced here structurally, not by convention:

    ONE CALL PER RECORD, NEVER PER PAIR.
        Extraction happens once at ingestion and the result is cached in
        specs.json. Pairwise scoring is pure arithmetic over this file and never
        calls a model. Per-record on 1M records is a few hours and a few hundred
        dollars, run once. Per-pair is 20M+ calls, every single run.

    THE MODEL EXTRACTS, IT NEVER DECIDES A MERGE.
        Nothing in this file compares two records. It reads one description and
        reports what it sees.

Usage:

    set GEMINI_API_KEY=...                  (or GOOGLE_API_KEY)
    python extractor.py --limit 10          try ten records first
    python extractor.py                     full run, resumes from cache
    python extractor.py --no-llm            regex only, no network at all
    python extractor.py --validate          print a hand-checkable sample
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import paths
import schemas

# gemini-2.5-pro is listed by the models API but returns 404 on generateContent
# for our key, so the default tracks whatever the current best Pro model is.
# Override with GEMINI_MODEL; `python -c "from google import genai; ..."` lists
# what a given key can actually call.
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-pro-latest")

# Free tier is roughly 15 requests/minute. Overshooting it costs more time in
# backoff than pacing does up front.
REQUESTS_PER_MINUTE = int(os.environ.get("GEMINI_RPM", "14"))


PROMPT = """You are a materials cataloguing engineer at an Indian oil refinery \
(CPCL, Chennai). You read short, abbreviated material master descriptions and \
report the specifications they contain.

ABBREVIATIONS COMMON IN THIS DATA
  BRG / BEARNG / BER = BEARING          DP GRV / D/GROOVE = DEEP GROOVE
  M.S. / MS = MILD STEEL                S.S. / SS = STAINLESS STEEL
  C.S. / CS = CARBON STEEL              SMLS = SEAMLESS
  NB = NOMINAL BORE                     SCH = SCHEDULE
  HEX HD / HH = HEXAGONAL HEAD          WN / W/NECK = WELD NECK
  RF = RAISED FACE                      SPL WOUND / SW = SPIRAL WOUND
  FT MTD / B3 = FOOT MOUNTED            MECH SEAL / M/SEAL = MECHANICAL SEAL
  # after a number = ANSI pressure class (150# = class 150)

DOMAIN KNOWLEDGE YOU SHOULD APPLY
  ISO bearing numbers encode dimensions. 6205 is 25mm bore, 52mm OD, 15mm wide.
  6206 is 30mm bore, 62mm OD, 16mm wide. Derive these when the number is present
  but the dimensions are not written out - and lower the confidence when you do,
  because you derived it rather than read it.
  2RS, 2RSR, 2RS1, LLU and DDU all mean rubber sealed on both sides.

CATEGORIES AND THEIR SCHEMAS
{schemas}

RULES - FOLLOW THESE EXACTLY
  1. Pick exactly one category from the list above. If the description does not
     clearly belong to any of them, use "unknown".
  2. Only include fields belonging to the chosen category's schema.
  3. NEVER GUESS. If a value is not stated and cannot be derived from a named
     standard, omit the field entirely. A fabricated specification that later
     drives a merge is the worst error this system can make. Omitting is safe;
     inventing is not.
  4. Give every field you DO return a confidence between 0 and 1:
       0.95-1.0  stated explicitly in the text
       0.75-0.94 derived from a standard designation (e.g. bore from 6205)
       0.40-0.74 inferred from weak or ambiguous wording
     If you would score below 0.4, omit the field instead.
  5. Numeric fields must be plain numbers, with no units and no quotes.
  6. Typos are common. "BEARNG", "SEAELD", "GASKT" are misspellings, not
     different items. Read through them.
  7. Return ONLY a JSON object. No markdown fence, no commentary.

OUTPUT SHAPE
{{"category": "<name>",
  "attributes": {{"<field>": <value>, ...}},
  "confidence": {{"<field>": <0-1>, ...}}}}

DESCRIPTION TO EXTRACT
{description}"""


# --------------------------------------------------------------------------
# Model client. Three people on different machines will run this, so it accepts
# either Gemini SDK rather than pinning one and breaking on the other.
# --------------------------------------------------------------------------

class Gemini:
    def __init__(self, api_key: str, model: str):
        self.model_name = model
        self._new = None
        try:
            from google import genai
            from google.genai import types
            self._client = genai.Client(api_key=api_key)
            self._types = types
            self._new = True
        except ImportError:
            import google.generativeai as genai          # type: ignore
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(model)
            self._new = False

    def generate(self, prompt: str) -> str:
        if self._new:
            resp = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,          # extraction, not creativity
                ),
            )
            return resp.text or ""
        resp = self._client.generate_content(
            prompt, generation_config={"response_mime_type": "application/json",
                                       "temperature": 0.0})
        return resp.text or ""


def _unwrap(parsed):
    """Some models return [ {...} ] instead of {...} despite the schema.

    Take the first dict out of a list rather than discarding an otherwise
    perfectly good extraction.
    """
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                return item
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_json(text: str) -> dict | None:
    """Models occasionally wrap JSON in a fence, or in an array, despite the prompt."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return _unwrap(json.loads(text))
    except json.JSONDecodeError:
        pass
    m = re.search(r"[\{\[].*[\}\]]", text, re.S)
    if m:
        try:
            return _unwrap(json.loads(m.group(0)))
        except json.JSONDecodeError:
            return None
    return None


def clean(raw: dict, description: str) -> dict:
    """Validate against the schema, canonicalise values, drop anything invented.

    A field the model returned that does not exist in the chosen category's
    schema is a hallucination and is discarded silently - it is not evidence and
    must never reach the scorer.
    """
    category = str(raw.get("category", "unknown")).strip().lower()
    if category not in schemas.CATEGORIES:
        category = "unknown"

    spec_by_name = {f.name: f for f in schemas.fields_for(category)}
    attrs_in = raw.get("attributes") or {}
    conf_in = raw.get("confidence") or {}

    attrs, conf, dropped = {}, {}, []
    for name, value in attrs_in.items():
        spec = spec_by_name.get(name)
        if spec is None:
            dropped.append(name)
            continue
        if value in (None, "", "null", "N/A", "unknown"):
            continue

        if spec.kind == "num":
            try:
                value = float(re.sub(r"[^\d.\-]", "", str(value)))
            except (ValueError, TypeError):
                continue
        else:
            value = schemas.canonical_value(name, value)
            if value is None:
                continue

        try:
            c = float(conf_in.get(name, 0.8))
        except (TypeError, ValueError):
            c = 0.8
        if c < 0.4:                       # the model itself is unsure - drop it
            continue

        attrs[name] = value
        conf[name] = round(min(max(c, 0.0), 1.0), 2)

    return {"category": category, "attributes": attrs, "confidence": conf,
            "method": "llm", "dropped_fields": dropped,
            "description": description}


def extract_one(client: Gemini | None, description: str) -> dict:
    if client is None:
        out = schemas.regex_extract(description)
        out["description"] = description
        return out

    prompt = PROMPT.format(schemas=schemas.all_schemas_block(), description=description)
    for attempt in range(4):
        try:
            raw = parse_json(client.generate(prompt))
            if raw:
                return clean(raw, description)
        except Exception as exc:                                  # noqa: BLE001
            msg = str(exc).lower()
            transient = any(w in msg for w in
                            ("429", "rate", "quota", "503", "500", "timeout", "unavailable"))
            if not transient or attempt == 3:
                print(f"    ! {type(exc).__name__}: {str(exc)[:110]}", file=sys.stderr)
                break
            wait = 2 ** attempt + random.random()
            print(f"    . retry in {wait:.0f}s ({str(exc)[:60]})", file=sys.stderr)
            time.sleep(wait)

    out = schemas.regex_extract(description)          # never leave a record empty
    out["description"] = description
    return out


# --------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    materials = list(csv.DictReader((args.materials).open(encoding="utf-8-sig")))
    if args.limit:
        materials = materials[: args.limit]

    paths.ensure_dirs()
    cache: dict[str, dict] = {}
    if args.out.exists() and not args.fresh:
        cache = json.loads(args.out.read_text(encoding="utf-8"))
        print(f"resuming - {len(cache)} records already in {args.out.name}")

    client = None
    if not args.no_llm:
        key = args.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            print("no API key found (GEMINI_API_KEY / GOOGLE_API_KEY) - regex only\n",
                  file=sys.stderr)
        else:
            client = Gemini(key, args.model)
            print(f"model: {args.model}   pacing: {REQUESTS_PER_MINUTE} req/min\n")

    interval = 60.0 / REQUESTS_PER_MINUTE if client else 0.0
    todo = [m for m in materials if m["record_id"] not in cache]
    print(f"{len(materials)} records, {len(todo)} to extract\n")

    started = time.time()
    for i, row in enumerate(todo, 1):
        tick = time.time()
        result = extract_one(client, row["description"])
        result["record_id"] = row["record_id"]
        result["cpse"] = row["cpse"]
        result["source_code"] = row["source_code"]
        cache[row["record_id"]] = result

        n_fields = len(result["attributes"])
        flag = " " if result["method"] == "llm" else "R"
        print(f"[{i:>3}/{len(todo)}] {flag} {row['record_id']}  "
              f"{result['category']:<11} {n_fields:>2} fields   "
              f"{row['description'][:52]}")

        if i % 10 == 0 or i == len(todo):
            args.out.write_text(json.dumps(cache, indent=1), encoding="utf-8")

        if client and i < len(todo):
            time.sleep(max(0.0, interval - (time.time() - tick)))

    args.out.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    by_cat: dict[str, int] = {}
    by_method: dict[str, int] = {}
    field_counts = []
    for r in cache.values():
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
        by_method[r["method"]] = by_method.get(r["method"], 0) + 1
        field_counts.append(len(r["attributes"]))

    print(f"\nwrote {args.out.name}  ({len(cache)} records, {time.time()-started:.0f}s)")
    print("method:   " + "  ".join(f"{k}={v}" for k, v in by_method.items()))
    print("category: " + "  ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))
    if field_counts:
        print(f"fields:   avg {sum(field_counts)/len(field_counts):.1f} per record, "
              f"min {min(field_counts)}, max {max(field_counts)}")
    if by_cat.get("unknown"):
        print(f"\n{by_cat['unknown']} records landed in 'unknown' - these route to review")


def validate(args: argparse.Namespace) -> None:
    """Print a sample side by side with its source text, for hand-checking.

    CLAUDE.md build order step 1: validate on 50 records BY HAND before trusting
    anything downstream. This is that view.
    """
    data = json.loads(args.out.read_text(encoding="utf-8"))
    picks = list(data.values())[: args.limit or 50]
    for r in picks:
        print(f"\n{r['record_id']}  [{r['category']}]  via {r['method']}")
        print(f"  {r['description']}")
        for name, value in sorted(r["attributes"].items()):
            c = r["confidence"].get(name, 0)
            bar = "#" * int(c * 10)
            star = " *" if name in schemas.hard_fields(r["category"]) else "  "
            grey = " (ignored)" if name in schemas.ignored_fields(r["category"]) else ""
            print(f"   {star} {name:<18} {str(value):<22} {c:.2f} {bar}{grey}")
        if r.get("dropped_fields"):
            print(f"      dropped (not in schema): {r['dropped_fields']}")
    print("\n  * = hard blocker: a mismatch here is an instant zero in the scorer")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--materials", type=Path, default=paths.MATERIALS)
    ap.add_argument("--out", type=Path, default=paths.SPECS)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--api-key")
    ap.add_argument("--limit", type=int, help="only the first N records")
    ap.add_argument("--no-llm", action="store_true", help="regex only, no network")
    ap.add_argument("--fresh", action="store_true", help="ignore the cache and re-extract")
    ap.add_argument("--validate", action="store_true", help="print a hand-checkable sample")
    args = ap.parse_args()

    if args.validate:
        validate(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
