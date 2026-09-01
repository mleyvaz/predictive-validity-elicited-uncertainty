# Paper 2 — Preregistered analysis plan

**Fix this file, commit it, and timestamp it (OSF or a signed git tag) BEFORE running
`run_experiment.py` on the full design.** A pilot of ≤50 items per model is permitted for
debugging prompts and parsers; pilot data are discarded and not analysed.

Version: v1.0 — 2026-08-23
Seed: `20260823` (used for item sampling and the calibration/test split)

---

## 1. Question

Holding the prediction target fixed at answer correctness, does an elicited (T, I, F) triple
predict error better than simpler signals obtained from the same model?

## 2. Target

For item *x*, `Y(x) = 1` if the greedy answer is incorrect under normalized exact match against
the gold answer set; `Y(x) = 0` otherwise. Refusals (`I DON'T KNOW`) and API errors are excluded
from the discrimination analysis and reported as a separate rate per model × protocol.

No LLM grader is used. Grading is mechanical and is computed at collection time, before any
signal is inspected.

## 3. Signals

| Arm | Signal | Elicited? | Orientation |
|---|---|---|---|
| A | `s_TF = F − T` | yes | higher ⇒ more likely incorrect |
| A | `s_TIF_fixed = F + ½I − T` | yes | " |
| A | `s_TIF_lr` = logistic on (T, I, F), fitted on calibration split | yes | " |
| B | verbalized scalar confidence, `1 − conf` | yes | **primary baseline** |
| C | `1 − P(True)` | yes | " |
| D | `−` mean token logprob | no | " |
| E | discrete semantic entropy over K=10 samples | no | " |

## 4. Design factors

- Elicitation protocol: P1, P2, P3 (applies to arms A, B, C only)
- Model: 4, at least 3 vendors
- Dataset: 3 short-form QA sets, N = 1000 each
- Split: 50/50 calibration / test, fixed seed

Every elicited arm is reported as a **range over P1–P3**, never as a single point.

## 5. Metrics

Discrimination: AUROC (primary), AUPRC.
Calibration: Brier, ECE (10 bins), after isotonic mapping fitted on the calibration split only.
Selective prediction: risk–coverage curve, AURC, accuracy at coverage {0.9, 0.8, 0.5}.
Decision: conformal abstention threshold calibrated to selective risk α ∈ {0.05, 0.10};
report **achieved risk and achieved coverage on the test split**.

## 6. Inference

Paired bootstrap over items, B = 10 000, for every reported contrast. Report the difference and
its 95% interval. Do not report two separate intervals and eyeball the overlap.

## 7. Hypotheses and decision rules

| ID | Statement | Rule |
|---|---|---|
| **H1** | `s_TIF_lr` > verbalized scalar in AUROC | Retain the triple **only if** the paired CI excludes zero under **all three protocols** and the difference is positive in a majority of model × dataset cells |
| **H2** | `s_TIF_lr` > `s_TF` in AUROC | If the CI includes zero, conclude the **I channel adds no predictive information**, regardless of H1 |
| **H3** | semantic entropy > all elicited arms | Expected; bounds what elicitation can buy. Not a failure of the triple |
| **H4** | between-protocol AUROC range < between-signal difference at fixed protocol | If violated, the ranking of elicited signals is **not identifiable**; report that instead of a winner |
| **H5** | at α = 0.10, triple yields higher achieved coverage than arm B | Decision-relevant version of H1 |

## 8. Reporting commitment

All five hypotheses are reported with effect sizes and intervals **regardless of direction**.

If H1 and H2 both fail, the conclusion of the paper is that elicited three-component states do
not carry predictive information beyond a single elicited number, **and the abstract says so**.
This commitment is the reason the plan is timestamped.

## 9. What would invalidate the study

- Parse rate for any elicited arm below 90% on any model × protocol cell → that cell is reported
  as missing, not imputed, and the arm is flagged as format-fragile.
- Refusal rate above 25% for a model → that model is reported separately; the exclusion
  changes the population and pooling would be misleading.
- Base error rate below 5% or above 95% on a dataset → AUROC is unstable; drop the dataset and
  say so.

## 10. Deviations log

Any departure from this plan is recorded here with a date and a reason, and is reproduced in
the Limitations section of the paper. Deviations that favour the hypothesis are marked as such.

- **2026-09-01 — Dataset loader.** `make_datasets.py` rewritten to read the HF parquet files directly
  (`datasets>=4` no longer executes the loading scripts of `trivia_qa`, `sciq`, `nq_open`). Same
  splits, same seed, same N. Neutral.
- **2026-09-01 — Model swap.** `google/gemini-2.0-flash-001` is no longer served on OpenRouter;
  replaced by `google/gemini-2.5-flash`. Neutral (still 3 vendors + 1).
- **2026-09-01 — Parallel collection.** `run_experiment.py` collects items with a thread pool.
  The per-item record is built by the same code path; only scheduling changed. Neutral.
- **2026-09-01 — Fourth dataset, ChaosNLI (ADDITION, post hoc).** A 3-label classification set
  (SNLI + MNLI items with 100 human labels each; gold = majority label; N = 1000, half from the
  lowest-entropy third, half from the highest-entropy third) is added so the same five signals are
  measured on a closed-label task. H1-H5 apply to it exactly as to the QA sets. One additional
  **exploratory** analysis is registered here before collection: Spearman correlation of the
  elicited I component (each protocol) with human label entropy, contrasted with the correlation of
  the scalar arm and of semantic entropy with the same target. This does not enter the H1-H5
  verdicts and is labelled post hoc in the paper. Motivation: a Banking77 pilot (TypeK folder,
  1-sep) found I never exceeds 0.3 in closed classification; this tests whether that holds when
  ambiguity is real and measured. Direction of possible bias: none toward the hypothesis (the
  added analysis can only show I to be uninformative or informative about a target other than error).
- **2026-09-01 — Scale.** Pilot first (≤30 items/model, discarded). Full run at N = 300 per dataset
  (not 1000) for cost/time, all four models, four datasets. The calibration/test split stays
  50/50 with the same seed. Reduces power; a null on H1 at N=300 is weaker evidence than at
  N=1000 and will be stated as such. Recorded before collection.
