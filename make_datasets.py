"""
Build the QA datasets for Paper 2 (+ the ChaosNLI classification set added 2026-09-01).

Writes data/<name>.jsonl with one object per line:
    {"id": "...", "question": "...", "answers": ["gold", "alias", ...]}

2026-09-01: rewritten to read HF parquet files directly. `datasets>=4` no longer runs the
loading scripts that `trivia_qa`, `sciq` and `nq_open` shipped with, so the original
`load_dataset(...)` calls fail. Same splits, same seed, same N. Recorded in the deviations log.

Fixed seed: sampling must be reproducible or the calibration split is meaningless.
"""

from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path

import pandas as pd

SEED = 20260823
N = 1000
HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "data"
OUTDIR.mkdir(exist_ok=True)
CACHE = OUTDIR / "_parquet"
CACHE.mkdir(exist_ok=True)

HF = "https://huggingface.co/datasets/{repo}/resolve/main/{path}"
SOURCES = {
    "triviaqa": ("mandarjoshi/trivia_qa", "rc.nocontext/validation-00000-of-00001.parquet"),
    "sciq": ("allenai/sciq", "data/validation-00000-of-00001.parquet"),
    "nqopen": ("google-research-datasets/nq_open", "nq_open/validation-00000-of-00001.parquet"),
}
CHAOS = Path(r"C:\Users\HP\Documents\TwoSided_NLI\data\chaosNLI_v1.0")


def fetch(name: str) -> pd.DataFrame:
    repo, path = SOURCES[name]
    local = CACHE / f"{name}.parquet"
    if not local.exists():
        urllib.request.urlretrieve(HF.format(repo=repo, path=path), local)
    return pd.read_parquet(local)


def write(name: str, rows: list[dict]) -> None:
    path = OUTDIR / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{path}  n={len(rows)}")


def main() -> None:
    rng = random.Random(SEED)

    # 1. TriviaQA -- rc.nocontext validation. Rich alias sets, ideal for exact match.
    tq = fetch("triviaqa")
    idx = rng.sample(range(len(tq)), N)
    write("triviaqa", [
        {"id": f"tq-{i:05d}",
         "question": tq.iloc[i]["question"],
         "answers": sorted({tq.iloc[i]["answer"]["value"], *tq.iloc[i]["answer"]["aliases"]})}
        for i in idx
    ])

    # 2. SciQ -- 2026-09-01: served as 4-option multiple choice (its own distractors), because
    #    the free-form golds are cloze fragments ("thermal", "raises it") that exact match cannot
    #    grade. Closed-label task with CLEAN labels; ChaosNLI is the closed-label task with
    #    AMBIGUOUS labels. Options are shuffled with the fixed seed. Gold accepts the option text
    #    or its letter. Recorded in the deviations log.
    sq = fetch("sciq")
    idx = rng.sample(range(len(sq)), min(N, len(sq)))
    rows = []
    for i in idx:
        r = sq.iloc[i]
        opts = [r["correct_answer"], r["distractor1"], r["distractor2"], r["distractor3"]]
        rng.shuffle(opts)
        letters = "ABCD"
        k = opts.index(r["correct_answer"])
        rows.append({
            "id": f"sq-{i:05d}",
            "question": (r["question"] + "\n" + "\n".join(f"{letters[j]}) {o}" for j, o in enumerate(opts))
                         + "\nReply with the letter of the correct option only."),
            "answers": [letters[k], r["correct_answer"], f"{letters[k]}) {r['correct_answer']}"],
        })
    write("sciq", rows)

    # 3. Natural Questions open -- short answers, harder, different distribution.
    nq = fetch("nqopen")
    idx = rng.sample(range(len(nq)), min(N, len(nq)))
    write("nqopen", [
        {"id": f"nq-{i:05d}",
         "question": nq.iloc[i]["question"],
         "answers": list(nq.iloc[i]["answer"])}
        for i in idx
    ])

    # 4. ChaosNLI (added 2026-09-01) -- 3-label classification with 100 human labels per item.
    #    Gold = majority label. Half the sample is low-entropy (clear), half high-entropy
    #    (genuinely ambiguous), so the I channel can be checked against human disagreement.
    #    Extra fields (human_entropy, label_dist) are carried for the post-hoc I analysis;
    #    the collection pipeline ignores them.
    rows = []
    for fn in ("chaosNLI_snli.jsonl", "chaosNLI_mnli_m.jsonl"):
        with (CHAOS / fn).open(encoding="utf-8") as fh:
            rows += [json.loads(l) for l in fh if l.strip()]
    rows.sort(key=lambda r: r["entropy"])
    lo, hi = rows[: len(rows) // 3], rows[-(len(rows) // 3):]
    pick = rng.sample(lo, N // 2) + rng.sample(hi, N // 2)
    rng.shuffle(pick)
    LAB = {"e": "entailment", "n": "neutral", "c": "contradiction"}
    write("chaosnli", [
        {"id": f"cn-{r['uid']}",
         "question": (f"Premise: {r['example']['premise']}\n"
                      f"Hypothesis: {r['example']['hypothesis']}\n"
                      "Does the premise entail the hypothesis, contradict it, or neither? "
                      "Reply with exactly one word: entailment, contradiction, or neutral."),
         "answers": [LAB[r["majority_label"]]],
         "human_entropy": r["entropy"], "label_dist": r["label_dist"],
         "source": r["example"]["source"]}
        for r in pick
    ])

    print("\nRecord the dataset versions and the seed in the paper. "
          "If a split name changed upstream, note it in the deviations log.")


if __name__ == "__main__":
    main()
