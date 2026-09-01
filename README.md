# Paper 2 — Do elicited epistemic states predict error?

**Target venue:** TMLR (rolling submission — no deadline to miss).
**Status:** draft v0.1, no data collected.

## What this paper decides

Whether an elicited (T, I, F) triple carries information that predicts answer correctness
**beyond simply asking the model for one confidence number**. That is the primary contrast, and
it has not been run before. If the triple loses, the paper says so in the abstract.

## Order of operations

1. `pip install openai numpy pandas scikit-learn tabulate datasets`
2. `python make_datasets.py` → writes `data/triviaqa.jsonl`, `data/sciq.jsonl`, `data/nqopen.jsonl`
3. Read `ANALYSIS_PLAN.md`. Fix it. **Commit and timestamp it before step 5.**
4. Pilot: `python run_experiment.py --datasets data/sciq.jsonl --limit 40 --only-model gpt-4o-mini`
   Check the parse rates in the raw file. If any elicited arm parses below 90%, fix the regex or
   the prompt now — not after the full run.
5. Full run: `set OPENROUTER_API_KEY=...` then
   `python run_experiment.py --datasets data/triviaqa.jsonl data/sciq.jsonl data/nqopen.jsonl`
   Resumable: re-running skips item-cells already in `results/raw_paper2.jsonl`.
6. `python analyze.py --raw results/raw_paper2.jsonl` (add `--n-boot 1000` for a fast pass;
   use the default 10000 for the paper).
7. Paste `results/SUMMARY.md` into Section 7 of `main.tex`, then write Section 8 by selecting
   the branch the data chose. Both branches are already drafted — do not write a third one.

## Files

| File | Role |
|---|---|
| `main.tex` | the paper. Results tables are structural placeholders (`--.--`) |
| `refs.bib` | verified references only; `TODO` marks fields to complete from the record |
| `ANALYSIS_PLAN.md` | preregistration. Timestamp it before collecting data |
| `prompts.py` | the three elicitation protocols, verbatim as they go in the appendix |
| `make_datasets.py` | builds the three QA sets, fixed seed |
| `run_experiment.py` | collection + mechanical grading, resumable |
| `analyze.py` | all preregistered metrics, contrasts, conformal, variance |

## Design decisions worth defending in review

- **No LLM grader.** Short-form QA with alias sets so `Y` is mechanical. An LLM grader would
  add an uncontrolled error term shared across all arms.
- **Protocol is a factor, not a robustness check.** Every elicited arm is reported as a range
  over P1–P3. If protocol variance exceeds signal variance, the ranking is not identifiable and
  the paper says that instead of naming a winner.
- **Paired bootstrap on the difference,** not two marginal intervals compared by eye.
- **Conformal abstention at fixed risk** is the headline, because achieved coverage at a
  guaranteed risk level is what a practitioner actually uses.
- **The ablation `s_TIF_lr` vs `s_TF`** is what isolates whether `I` does anything. If it does
  not, that conclusion holds regardless of how the primary contrast comes out.

## Cost

Roughly `N × (1 + 9 + K)` calls per model per dataset. With N=1000, K=10, 4 models, 3 datasets
that is on the order of 240k calls. **Pilot first, then decide whether to cut N to 500 or drop
to 3 models.** Record the realized number; it goes in the paper.

## Known limitations already written into the draft

Short-form only; discrete semantic entropy is weaker than NLI clustering; logprobs unavailable
for some providers; elicitation is behavioural and licenses no claim about internal states.
