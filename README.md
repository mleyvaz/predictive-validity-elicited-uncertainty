# Do elicited epistemic states predict error?

Code, data, and preregistration history for a test of whether an elicited three-component
epistemic state (T, I, F) from a large language model predicts answer errors better than one
verbalized confidence number. The result is negative. Manuscript: *Do Elicited (T, I, F) Epistemic States Predict Language-Model Errors? A
Pre-Specified Negative Result, with Exploratory Evidence that the Three Numbers Behave Largely as
One* (M. Y. Leyva Vázquez and R. Sánchez Casanova), submitted to *Inteligencia Artificial*.

**What was tested.**
- **Models:** gpt-4o-mini, Claude Haiku 4.5, Gemini 2.5 Flash and Llama 3.1 8B, all accessed through OpenRouter on 1 September 2026.
- **Datasets:** 300 items each from TriviaQA, NQ-open, SciQ (served as four-option multiple choice) and ChaosNLI.
- **Signals:** five, namely the elicited triple, verbalized scalar confidence, P(True), sequence log-probability and string-level sample entropy.
- **Prompts:** three elicitation protocols for each elicited signal.
- **Target:** Y = the greedy answer is wrong, graded by exact match.
- **Scale:** 4,800 valid item-cells and 105,857 logical model calls.
- **Cost:** about 33 USD, according to the author. This figure is not logged in the repository.

## Verifying the preregistration

The analysis plan (`ANALYSIS_PLAN.md`) and its pre-collection deviations were committed and tagged
before data collection:

```
git tag -l --format='%(refname:short) %(creatordate:iso)'
git log --format='%h %ad %s' --date=iso prereg-2026-09-01 -1
git show prereg-2026-09-01:ANALYSIS_PLAN.md | head
git diff prereg-2026-09-01c results-2026-09-01 -- ANALYSIS_PLAN.md   # what changed after collection
```

The tags are:

| Tag | Time (UTC−5) |
|---|---|
| `prereg-2026-09-01` | 09:03 |
| `prereg-2026-09-01b` | 09:06 |
| `prereg-2026-09-01c` | 09:09 |
| `results-2026-09-01` | 10:36 |

Full collection ran from 09:10 to 10:29. This is an internal preregistration in a local git
repository, not an entry in an external registry, and a same-day timeline is a weaker guarantee
than a registry.

## Reproducing every number (no API calls, a few minutes on a laptop)

```
pip install -r requirements.txt
cd repro
python compare_outputs.py            # regenerate all outputs from the raw file and compare (~30-40 min; --quick: ~1 min)
python verify_numbers.py results results/raw_paper2.jsonl > verify_output.txt   # recompute the quoted numbers
python make_figures.py               # figures -> repro/figures
```

`compare_outputs.py` prints the maximum absolute difference between each regenerated CSV and the distributed one (0.0 = exact). `verify_numbers.py` recomputes the numbers quoted in the manuscript from those outputs.

## Re-collecting the data (costs money)

```
set OPENROUTER_API_KEY=...        # never commit a key; the scripts read it from the environment
python make_datasets.py           # (repository root) rebuilds data/*.jsonl; set CHAOSNLI_DIR to a local ChaosNLI v1.0 copy
python run_experiment.py --datasets data/triviaqa.jsonl data/nqopen.jsonl data/sciq.jsonl data/chaosnli.jsonl --limit 300
```

Provider model versions change over time, so a re-collection will not reproduce the generations
byte for byte.

## Layout

| Path | Content |
|---|---|
| `ANALYSIS_PLAN.md` | Preregistered plan and deviation log |
| `prompts.py`, `run_experiment.py`, `make_datasets.py` | Elicitation prompts, collection and dataset sampling |
| `analyze.py` (root) | Preregistered analysis, as tagged (history) |
| `repro/` | Final reproducibility package: `code/` (all analysis scripts and sampled data), `results/` (raw generations and preregistered outputs), `results_v2/` and `results_extra/` (post-review and exploratory analyses), `verify_numbers.py`, `make_figures.py`, `figures/` |
| `data/` | Sampled items (see `DATA_LICENSES.md`) |
| `results/` (root) | Outputs as committed on 1 September 2026 |
| `repro/DATA_SHA256.txt` | SHA-256 hashes of the data and raw files |

## Licences

- **Code:** MIT (see `LICENSE`).
- **Data:** each file keeps the licence of its source. Some sources are non-commercial, so the data
  here are for non-commercial research only. See `DATA_LICENSES.md`.
