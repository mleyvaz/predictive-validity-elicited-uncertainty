"""
Paper 2 -- data collection.

Do LLMs know when they are wrong? Predictive validity of elicited epistemic states.

For every (model, dataset, item):
  1. greedy answer                       -> the thing whose correctness we predict
  2. arm A: (T,I,F) triple    x P1,P2,P3
  3. arm B: scalar confidence x P1,P2,P3   <- PRIMARY BASELINE
  4. arm C: P(True)           x P1,P2,P3
  5. arm D: mean token logprob of the greedy answer (when the provider exposes it)
  6. arm E: K samples at temperature 1.0 -> discrete semantic entropy

Writes one JSON object per item per model per dataset to a JSONL file, appended
incrementally so the run is resumable. Grading happens here (mechanical exact
match, no judge model) so that Y is fixed before any analysis is run.

Usage
-----
  set OPENROUTER_API_KEY=...
  python run_experiment.py --datasets data/triviaqa.jsonl --limit 50 --dry-run
  python run_experiment.py --datasets data/triviaqa.jsonl data/sciq.jsonl

Dataset format (JSONL), one object per line:
  {"id": "tq-0001", "question": "...", "answers": ["gold", "alias 1", "alias 2"]}

Build these with make_datasets.py, or hand-build them. Keep the seed fixed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import string
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
_LOCK = threading.Lock()
from pathlib import Path

from openai import OpenAI

import prompts as P

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)

MODELS = [
    {"id": "anthropic/claude-haiku-4-5", "label": "claude-haiku-4.5", "logprobs": False},
    {"id": "openai/gpt-4o-mini", "label": "gpt-4o-mini", "logprobs": True},
    {"id": "google/gemini-2.5-flash", "label": "gemini-2.5-flash", "logprobs": False},  # 2026-09-01: 2.0-flash-001 no longer served
    {"id": "meta-llama/llama-3.1-8b-instruct", "label": "llama-3.1-8b", "logprobs": True},
]

K_SAMPLES = 10          # arm E
SAMPLE_TEMP = 1.0
MAX_RETRIES = 4
SLEEP_ON_ERROR = 3.0

REFUSAL_MARKERS = ("i don't know", "i do not know", "unknown", "cannot determine")


def client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def call(cl, model_id, system, user, temperature=0.0, want_logprobs=False, max_tokens=300):
    """One chat completion. Returns (text, mean_logprob_or_None)."""
    kwargs = dict(
        model=model_id,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if want_logprobs:
        kwargs["logprobs"] = True

    for attempt in range(MAX_RETRIES):
        try:
            r = cl.chat.completions.create(**kwargs)
            choice = r.choices[0]
            text = (choice.message.content or "").strip()
            mean_lp = None
            lp = getattr(choice, "logprobs", None)
            content = getattr(lp, "content", None) if lp else None
            if content:
                vals = [t.logprob for t in content if getattr(t, "logprob", None) is not None]
                if vals:
                    mean_lp = sum(vals) / len(vals)
            return text, mean_lp
        except Exception as exc:                       # noqa: BLE001
            if attempt == MAX_RETRIES - 1:
                return f"__ERROR__ {exc}", None
            time.sleep(SLEEP_ON_ERROR * (attempt + 1))
    return "__ERROR__ unreachable", None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

NUM = r"([01](?:\.\d+)?|\.\d+)"


def parse_tif(text: str, protocol: str):
    """Return (T, I, F) or None. Never guess: unparseable is missing data."""
    if protocol in ("P1", "P2"):
        m = re.search(rf"T\s*=\s*{NUM}\s+I\s*=\s*{NUM}\s+F\s*=\s*{NUM}", text, re.I)
        if m:
            return tuple(float(g) for g in m.groups())
        # tolerate line breaks between the three assignments
        t = re.search(rf"\bT\s*=\s*{NUM}", text, re.I)
        i = re.search(rf"\bI\s*=\s*{NUM}", text, re.I)
        f = re.search(rf"\bF\s*=\s*{NUM}", text, re.I)
        if t and i and f:
            return float(t.group(1)), float(i.group(1)), float(f.group(1))
        return None

    grades = {}
    for key in ("TRUTH", "INDETERMINACY", "FALSITY"):
        m = re.search(rf"{key}\s*=\s*([A-Z ]+)", text, re.I)
        if not m:
            return None
        g = m.group(1).strip().upper()
        if g not in P.VERBAL_SCALE:
            return None
        grades[key] = P.VERBAL_SCALE[g]
    return grades["TRUTH"], grades["INDETERMINACY"], grades["FALSITY"]


def parse_scalar(text: str, protocol: str):
    if protocol == "P1":
        m = re.search(r"\b(\d{1,3})\b", text)
        return float(m.group(1)) / 100.0 if m and int(m.group(1)) <= 100 else None
    if protocol == "P2":
        m = re.search(r"CONFIDENCE\s*=\s*(\d{1,3})", text, re.I)
        return float(m.group(1)) / 100.0 if m and int(m.group(1)) <= 100 else None
    m = re.search(r"CORRECTNESS\s*=\s*([A-Z ]+)", text, re.I)
    if not m:
        return None
    g = m.group(1).strip().upper()
    return P.VERBAL_SCALE.get(g)


def parse_ptrue(text: str, protocol: str):
    if protocol in ("P1", "P2"):
        m = re.search(r"\b(true|false)\b", text, re.I)
        if not m:
            return None
        return 1.0 if m.group(1).lower() == "true" else 0.0
    m = re.search(rf"{NUM}", text)
    return float(m.group(1)) if m else None


PARSERS = {"tif": parse_tif, "scalar": parse_scalar, "ptrue": parse_ptrue}


# ---------------------------------------------------------------------------
# Grading -- mechanical, no judge model
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def is_refusal(answer: str) -> bool:
    return any(m in answer.lower() for m in REFUSAL_MARKERS)


def grade(answer: str, golds) -> int:
    """1 = incorrect (this is Y), 0 = correct."""
    a = normalize(answer)
    return 0 if any(a == normalize(g) for g in golds) else 1


def discrete_semantic_entropy(samples) -> float:
    """Shannon entropy over normalised-answer equivalence classes."""
    valid = [normalize(s) for s in samples if s and not s.startswith("__ERROR__")]
    if not valid:
        return float("nan")
    counts = Counter(valid)
    n = sum(counts.values())
    import math
    return -sum((c / n) * math.log(c / n) for c in counts.values())


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def load_dataset(path: Path, limit=None):
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows[:limit] if limit else rows


def done_keys(out_path: Path):
    seen = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    seen.add((r["model"], r["dataset"], r["item_id"]))
                except Exception:                      # noqa: BLE001
                    continue
    return seen


def _one_item(cl, model, ds_name, item):
    """All calls for one (model, dataset, item). Returns the record."""
    rec = {
        "prompt_version": P.PROMPT_VERSION,
        "model": model["label"],
        "model_id": model["id"],
        "dataset": ds_name,
        "item_id": item["id"],
        "question": item["question"],
        "golds": item["answers"],
    }
    n_calls = 0
    # 1. greedy answer + arm D
    ans, mean_lp = call(
        cl, model["id"], P.ANSWER_SYSTEM,
        P.ANSWER_USER.format(question=item["question"]),
        temperature=0.0, want_logprobs=model["logprobs"], max_tokens=64,
    )
    n_calls += 1
    rec["answer"] = ans
    rec["refusal"] = is_refusal(ans)
    rec["y_incorrect"] = None if rec["refusal"] else grade(ans, item["answers"])
    rec["seq_logprob"] = mean_lp
    if ans.startswith("__ERROR__"):
        rec["error"] = True
        return rec, n_calls

    # 2-4. elicited arms x protocols
    for arm_name, arm in P.ARMS.items():
        for proto in P.PROTOCOLS:
            spec = arm[proto]
            text, _ = call(
                cl, model["id"], spec["system"],
                spec["user"].format(question=item["question"], answer=ans),
                temperature=0.0,
                max_tokens=300 if proto == "P2" else 60,
            )
            n_calls += 1
            rec[f"{arm_name}_{proto}_raw"] = text
            rec[f"{arm_name}_{proto}"] = PARSERS[arm_name](text, proto)

    # 5. arm E
    samples = []
    for _ in range(K_SAMPLES):
        s, _ = call(
            cl, model["id"], P.ANSWER_SYSTEM,
            P.ANSWER_USER.format(question=item["question"]),
            temperature=SAMPLE_TEMP, max_tokens=64,
        )
        n_calls += 1
        samples.append(s)
    rec["samples"] = samples
    rec["semantic_entropy"] = discrete_semantic_entropy(samples)
    return rec, n_calls


def run(datasets, limit, dry_run, models, workers=8, out_name="raw_paper2.jsonl"):
    """2026-09-01: items are collected in parallel threads (workers). The per-item record
    is built by _one_item exactly as in the sequential version; only scheduling changed."""
    cl = client()
    out_path = OUT / out_name
    seen = done_keys(out_path)
    print(f"resuming: {len(seen)} item-cells already recorded")

    n_calls = 0
    for ds_path in datasets:
        ds_name = Path(ds_path).stem
        items = load_dataset(Path(ds_path), limit)
        for model in models:
            todo = [it for it in items if (model["label"], ds_name, it["id"]) not in seen]
            print(f"[{model['label']}/{ds_name}] {len(todo)} items to collect", flush=True)
            with ThreadPoolExecutor(workers) as ex:
                futs = [ex.submit(_one_item, cl, model, ds_name, it) for it in todo]
                for k, fu in enumerate(as_completed(futs), 1):
                    rec, nc = fu.result()
                    n_calls += nc
                    with _LOCK:
                        _append(out_path, rec, dry_run)
                    if k % 10 == 0:
                        print(f"[{model['label']}/{ds_name}] {k}/{len(todo)} calls={n_calls}", flush=True)

    print(f"done. total API calls this run: {n_calls}")
    print(f"RECORD THIS NUMBER IN THE PAPER (Section: Cost): {n_calls}")


def _append(path: Path, rec: dict, dry_run: bool):
    if dry_run:
        print(json.dumps(rec, ensure_ascii=False)[:400])
        return
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-model", default=None,
                    help="label of a single model to run")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="raw_paper2.jsonl",
                    help="output file inside results/ (use a different name for the pilot)")
    a = ap.parse_args()
    ms = [m for m in MODELS if a.only_model in (None, m["label"])]
    run(a.datasets, a.limit, a.dry_run, ms, a.workers, a.out)
