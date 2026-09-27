# Paper 2 -- preregistered verdicts

Excluded (refusal or API error): 39.1%

## H1 -- fitted triple vs verbalized scalar (PRIMARY)
delta mean=-0.0103; CI excludes zero in all cells per protocol: {'P1': np.False_, 'P2': np.False_, 'P3': np.False_}; positive in 50% of cells

## H2 -- fitted triple vs T/F only (does I add anything?)
delta mean=0.0028; CI excludes zero in all cells per protocol: {'P1': np.False_, 'P2': np.False_, 'P3': np.False_}; positive in 48% of cells

## H3 -- semantic entropy vs fitted triple (reference bound)
delta mean=0.0786; CI excludes zero in all cells per protocol: {'P1': np.False_, 'P2': np.False_, 'P3': np.False_}; positive in 75% of cells

## H4 -- marginal eta-squared of AUROC by design factor

| component   |   eta_squared |   n_levels |
|:------------|--------------:|-----------:|
| signal      |     0.168388  |          9 |
| protocol    |     0.0241635 |          3 |
| model       |     0.0114527 |          4 |
| dataset     |     0.280595  |          4 |

If `protocol` eta-squared exceeds `signal` eta-squared, the ranking of elicited
signals is NOT identifiable from this design. Report that, not a winner.

## H5 -- achieved coverage at guaranteed risk 0.10

| signal            |   achieved_coverage |
|:------------------|--------------------:|
| s_TIF_lr          |            0.474013 |
| verbalized_scalar |            0.532008 |

## Main table (mean AUROC by signal x protocol)

| signal            |     P1 |     P2 |     P3 |
|:------------------|-------:|-------:|-------:|
| p_true            | 0.6138 | 0.6032 | 0.6522 |
| s_TF              | 0.6539 | 0.7028 | 0.6273 |
| s_TFlab           | 0.6171 | 0.7058 | 0.5907 |
| s_TIF_fixed       | 0.6532 | 0.6966 | 0.6424 |
| s_TIF_lr          | 0.6464 | 0.6998 | 0.6463 |
| s_TIFlab_lr       | 0.5531 | 0.6871 | 0.6052 |
| semantic_entropy  | 0.744  | 0.744  | 0.744  |
| seq_logprob       | 0.796  | 0.796  | 0.796  |
| verbalized_scalar | 0.6569 | 0.7103 | 0.6582 |
