# Data licences

This repository redistributes small samples (300 items used per dataset) of four public datasets, together with
model generations produced on them. Each dataset file keeps the licence of its source. The MIT licence in
`LICENSE` covers the code only. Because two sources are non-commercial, **the data in this repository
may be used for non-commercial research only**.

| File | Source | Licence | Source URL |
|---|---|---|---|
| `data/triviaqa.jsonl` | TriviaQA, rc.nocontext validation (Joshi et al., 2017) | **Not stated.** The Hugging Face card gives the licence as "unknown" and says the University of Washington does not own the copyright of the questions. Redistributed here for research only; the copyright holders can ask for removal | https://huggingface.co/datasets/mandarjoshi/trivia_qa |
| `data/nqopen.jsonl` | NQ-open validation (Kwiatkowski et al., 2019; Lee et al., 2019) | CC BY-SA 3.0; this sample is shared under the same licence | https://huggingface.co/datasets/google-research-datasets/nq_open |
| `data/sciq.jsonl` | SciQ validation (Welbl et al., 2017) | CC BY-NC 3.0 | https://huggingface.co/datasets/allenai/sciq |
| `data/chaosnli.jsonl` | ChaosNLI v1.0 (Nie et al., 2020), SNLI and MNLI-m items | CC BY-NC 4.0 | https://github.com/easonnie/ChaosNLI |
| `results/*.jsonl` | Model generations on the items above (gpt-4o-mini, Claude Haiku 4.5, Gemini 2.5 Flash, Llama 3.1 8B, accessed through OpenRouter) | Contain the items above, so the most restrictive source licence applies (CC BY-NC) | — |

If you prefer not to use the redistributed samples, `make_datasets.py` rebuilds them from the original
sources with the same seed (set `CHAOSNLI_DIR` to a local copy of ChaosNLI v1.0).

Licence information was checked on 27 September 2026. Before any use other than non-commercial research,
re-check it at the source.
