"""
Paper 2 -- analysis v2 (27-sep-2026, after adversarial review R2). Uses ONLY the saved raw file;
no API calls. Reuses the preregistered pipeline in analyze.py (same seed, same split, same
signals) and adds:

  1. Tie-aware risk-calibrated threshold (fixes a bug in analyze.conformal_threshold, which
     could return a threshold inside a block of tied scores and then select the whole block).
  2. s_TF_lr: logistic combination of (T, F) fitted on calibration, so that the H2 ablation
     compares nested fitted models  LR(T,I,F) vs LR(T,F)  and isolates I (H2n).
  3. H3 against every preregistered elicited signal (H3_vs_<signal>).
  4. Hierarchical (item-cluster) bootstrap of the POOLED mean differences for H1, H2, H2n,
     resampling item_ids within dataset, shared across models and protocols.
  5. Split sensitivity: point estimates of pooled H1 / H2n over 50 alternative random splits.
  6. Sensitivity excluding item-cells with any internal call failure (elicited or sample).

Outputs into --out:  metrics_v2.csv, contrasts_v2.csv, conformal_v2.csv, pooled_v2.csv,
                     split_sensitivity_v2.csv, incomplete_v2.txt
Usage: python analyze_v2.py --raw ../results/raw_paper2.jsonl --out ../results_v2
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

import analyze as A

SEED = A.SEED
ELICITED = ["s_TIF_lr", "s_TIF_fixed", "s_TF", "s_TF_lr", "verbalized_scalar", "p_true"]


def risk_threshold_ties(y_cal, s_cal, alpha):
    """Largest score value v such that the empirical risk of ALL calibration items with
    s <= v (ties included) is <= alpha. Returns -inf if none, nan if no data."""
    ok = ~np.isnan(s_cal)
    y, s = y_cal[ok], s_cal[ok]
    if len(y) == 0:
        return np.nan
    vals = np.unique(s)
    best = -np.inf
    for v in vals:
        sel = s <= v
        if y[sel].mean() <= alpha:
            best = v
    return float(best)


def fit_lr(X, y, train):
    ok = ~np.isnan(X).any(axis=1)
    out = np.full(len(y), np.nan)
    tr = train & ok
    if tr.sum() >= 50 and len(np.unique(y[tr])) == 2:
        lr = LogisticRegression(max_iter=1000).fit(X[tr], y[tr])
        out[ok] = lr.predict_proba(X[ok])[:, 1]
    return out


def incomplete_mask(g):
    """True for item-cells with any internal failure after the greedy answer."""
    def bad(r):
        if any(isinstance(v, str) and v.startswith("__ERROR__") for k, v in r.items() if k.endswith("_raw")):
            return True
        s = r["samples"] if isinstance(r["samples"], list) else []
        return sum(1 for x in s if x and not str(x).startswith("__ERROR__")) < 10
    return g.apply(bad, axis=1).to_numpy()


def cell_signals(g, proto, cal):
    y = g["y_incorrect"].to_numpy(dtype=float)
    sig = A.signals_for(g, proto)
    comps = sig.pop("_TIF_components")
    sig.pop("_TIFlab_components", None); sig.pop("s_TFlab", None)
    sig["s_TIF_lr"] = fit_lr(comps, y, cal)
    sig["s_TF_lr"] = fit_lr(comps[:, [0, 2]], y, cal)
    return y, {k: np.asarray(v, dtype=float) for k, v in sig.items()}


def run(raw, out, n_boot, n_hboot, n_splits):
    out.mkdir(parents=True, exist_ok=True)
    df = A.build_frame(Path(raw))
    rng = np.random.default_rng(SEED)
    mrows, crows, krows, cells = [], [], [], []
    for (model, dataset), g in df[~df["excluded"]].groupby(["model", "dataset"]):
        g = g.reset_index(drop=True)
        cal = A.split_mask(len(g), np.random.default_rng(SEED))
        inc = incomplete_mask(g)
        for proto in A.PROTOCOLS:
            y, sig = cell_signals(g, proto, cal)
            test = ~cal
            cells.append(dict(model=model, dataset=dataset, protocol=proto, y=y, sig=sig, cal=cal,
                              item_id=g["item_id"].to_numpy(), inc=inc, g=g))
            for name in ["s_TF_lr"]:
                s = sig[name]
                mrows.append(dict(model=model, dataset=dataset, protocol=proto, signal=name,
                                  auroc=A.safe_auroc(y[test], s[test])))
            for name, s in sig.items():
                for alpha in A.ALPHAS:
                    thr = risk_threshold_ties(y[cal], s[cal], alpha)
                    st = s[test]
                    sel = (~np.isnan(st)) & (st <= thr)
                    selc = (~np.isnan(s[cal])) & (s[cal] <= thr)
                    krows.append(dict(model=model, dataset=dataset, protocol=proto, signal=name, alpha=alpha,
                                      threshold=thr, cal_risk=float(y[cal][selc].mean()) if selc.sum() else np.nan,
                                      achieved_coverage=float(sel.mean()),
                                      achieved_risk=float(y[test][sel].mean()) if sel.sum() else np.nan,
                                      n_selected=int(sel.sum())))
            pairs = [("H1", "s_TIF_lr", "verbalized_scalar"), ("H2", "s_TIF_lr", "s_TF"),
                     ("H2n", "s_TIF_lr", "s_TF_lr")]
            pairs += [(f"H3_vs_{b}", "semantic_entropy", b) for b in ELICITED if b != "s_TF_lr"]
            pairs += [("LP_vs_SE", "seq_logprob", "semantic_entropy"), ("LP_vs_scalar", "seq_logprob", "verbalized_scalar")]
            for lab, a, b in pairs:
                pt, (lo, hi) = A.paired_bootstrap_diff(y[test], sig[a][test], sig[b][test], rng, n_boot)
                crows.append(dict(hypothesis=lab, model=model, dataset=dataset, protocol=proto, a=a, b=b,
                                  delta_auroc=pt, ci_lo=lo, ci_hi=hi,
                                  excludes_zero=bool(not np.isnan(lo) and (lo > 0 or hi < 0))))
    pd.DataFrame(mrows).to_csv(out / "metrics_v2.csv", index=False)
    pd.DataFrame(crows).to_csv(out / "contrasts_v2.csv", index=False)
    pd.DataFrame(krows).to_csv(out / "conformal_v2.csv", index=False)

    # ---- 4. hierarchical bootstrap of pooled means (item clusters shared across models/protocols)
    def auc_w(y, s, w):
        ok = (~np.isnan(s)) & (w > 0)
        if len(np.unique(y[ok])) < 2:
            return np.nan
        return roc_auc_score(y[ok], s[ok], sample_weight=w[ok])

    contr = {"H1": ("s_TIF_lr", "verbalized_scalar"), "H2": ("s_TIF_lr", "s_TF"), "H2n": ("s_TIF_lr", "s_TF_lr")}
    ids_by_ds = {ds: np.array(sorted(set(np.concatenate([c["item_id"] for c in cells if c["dataset"] == ds]))))
                 for ds in sorted({c["dataset"] for c in cells})}
    hr = np.random.default_rng(SEED + 1)
    rows = []

    def pooled(weights_by_ds, subset=None):
        res = {}
        for h, (a, b) in contr.items():
            d = []
            for c in cells:
                if subset is not None and not subset(c):
                    continue
                t = ~c["cal"]
                ok = (~np.isnan(c["sig"][a])) & (~np.isnan(c["sig"][b])) & t
                w = weights_by_ds[c["dataset"]](c["item_id"]) if weights_by_ds else np.ones(len(c["y"]))
                w = w * ok
                da = auc_w(c["y"], c["sig"][a], w); db = auc_w(c["y"], c["sig"][b], w)
                d.append(da - db)
            res[h] = np.nanmean(d)
        return res

    for label, subset in (("all48", None), ("noSciQ36", lambda c: c["dataset"] != "sciq")):
        point = pooled(None, subset)
        boots = {h: [] for h in contr}
        for _ in range(n_hboot):
            wmap = {}
            for ds, ids in ids_by_ds.items():
                draw = hr.choice(ids, size=len(ids), replace=True)
                u, cnt = np.unique(draw, return_counts=True)
                lut = dict(zip(u, cnt))
                wmap[ds] = (lambda lut: (lambda arr: np.array([lut.get(i, 0) for i in arr], dtype=float)))(lut)
            r = pooled(wmap, subset)
            for h in contr:
                boots[h].append(r[h])
        for h in contr:
            lo, hi = np.nanpercentile(boots[h], [2.5, 97.5])
            rows.append(dict(set=label, contrast=h, pooled_mean=point[h], ci_lo=lo, ci_hi=hi, n_boot=n_hboot))
    pd.DataFrame(rows).to_csv(out / "pooled_v2.csv", index=False)

    # ---- 5. split sensitivity (point estimates only)
    srows = []
    for k in range(n_splits):
        d1, d2n = [], []
        for (model, dataset), g in df[~df["excluded"]].groupby(["model", "dataset"]):
            g = g.reset_index(drop=True)
            cal = A.split_mask(len(g), np.random.default_rng(1000 + k))
            for proto in A.PROTOCOLS:
                y, sig = cell_signals(g, proto, cal)
                t = ~cal
                d1.append(A.safe_auroc(y[t], sig["s_TIF_lr"][t]) - A.safe_auroc(y[t], sig["verbalized_scalar"][t]))
                d2n.append(A.safe_auroc(y[t], sig["s_TIF_lr"][t]) - A.safe_auroc(y[t], sig["s_TF_lr"][t]))
        srows.append(dict(split_seed=1000 + k, H1_pooled=np.nanmean(d1), H2n_pooled=np.nanmean(d2n)))
    pd.DataFrame(srows).to_csv(out / "split_sensitivity_v2.csv", index=False)

    # ---- 6. incomplete item-cells: count and sensitivity (same split, incomplete rows dropped from test)
    lines = []
    n_inc = sum(int(c["inc"].sum()) for c in cells if c["protocol"] == "P1")
    lines.append(f"item-cells with any internal failure (elicited error or <10 valid samples): {n_inc} of "
                 f"{sum(len(c['y']) for c in cells if c['protocol'] == 'P1')} non-refused")
    for h, (a, b) in contr.items():
        d = []
        for c in cells:
            t = (~c["cal"]) & (~c["inc"])
            d.append(A.safe_auroc(c["y"][t], c["sig"][a][t]) - A.safe_auroc(c["y"][t], c["sig"][b][t]))
        lines.append(f"{h} pooled mean excluding incomplete test items: {np.nanmean(d):+.4f}")
    d = []
    for c in cells:
        t = (~c["cal"]) & (~c["inc"])
        d.append(A.safe_auroc(c["y"][t], c["sig"]["semantic_entropy"][t]) - A.safe_auroc(c["y"][t], c["sig"]["s_TIF_lr"][t]))
    lines.append(f"H3 pooled mean excluding incomplete test items: {np.nanmean(d):+.4f}")
    (out / "incomplete_v2.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--n-boot", type=int, default=10_000)
    ap.add_argument("--n-hboot", type=int, default=1_000)
    ap.add_argument("--n-splits", type=int, default=50)
    a = ap.parse_args()
    run(a.raw, Path(a.out), a.n_boot, a.n_hboot, a.n_splits)
