"""
Paper 2 -- analysis.

Implements exactly the preregistered plan in ANALYSIS_PLAN.md and Section 6 of
main.tex. Nothing here is exploratory; if you add an analysis, add it to the
plan file first and mark it post hoc in the paper.

Outputs (into results/):
  metrics.csv        one row per (model, dataset, protocol, signal)
  contrasts.csv      H1/H2/H3/H5 paired differences with bootstrap CIs
  conformal.csv      achieved risk and coverage at alpha in {0.05, 0.10}
  variance.csv       H4 variance decomposition of AUROC
  SUMMARY.md         the five hypotheses with verdicts, ready to paste

Usage
-----
  python analyze.py --raw results/raw_paper2.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

SEED = 20260823
N_BOOT = 10_000
ALPHAS = (0.05, 0.10)
COVERAGES = (0.9, 0.8, 0.5)
PROTOCOLS = ("P1", "P2", "P3")

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"


# ---------------------------------------------------------------------------
# Signal construction
# ---------------------------------------------------------------------------

def build_frame(raw_path: Path) -> pd.DataFrame:
    rows = []
    with raw_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)

    # Refusals and API errors are excluded from discrimination, and reported.
    if "error" not in df.columns:
        df["error"] = False
    df["error"] = df["error"].fillna(False).astype(bool)
    df["excluded"] = df["y_incorrect"].isna() | df["error"]
    return df


def signals_for(df: pd.DataFrame, protocol: str) -> dict:
    """All candidate signals, oriented so that HIGHER = more likely INCORRECT."""
    tif = df[f"tif_{protocol}"]
    T = tif.map(lambda v: v[0] if isinstance(v, (list, tuple)) else np.nan).astype(float)
    I = tif.map(lambda v: v[1] if isinstance(v, (list, tuple)) else np.nan).astype(float)
    F = tif.map(lambda v: v[2] if isinstance(v, (list, tuple)) else np.nan).astype(float)

    scalar = pd.to_numeric(df[f"scalar_{protocol}"], errors="coerce")
    ptrue = pd.to_numeric(df[f"ptrue_{protocol}"], errors="coerce")

    out = {
        "s_TF":              F - T,                       # eq. (1): ignores I
        "s_TIF_fixed":       F + 0.5 * I - T,             # eq. (2)
        "verbalized_scalar": 1.0 - scalar,                # arm B, PRIMARY BASELINE
        "p_true":            1.0 - ptrue,                 # arm C
        "seq_logprob":       -pd.to_numeric(df["seq_logprob"], errors="coerce"),
        "semantic_entropy":  pd.to_numeric(df["semantic_entropy"], errors="coerce"),
    }
    out["_TIF_components"] = np.column_stack([T, I, F])   # for the fitted arm
    return out


def split_mask(n: int, rng: np.random.Generator) -> np.ndarray:
    """Fixed 50/50 calibration/test split. Calibration = True."""
    m = np.zeros(n, dtype=bool)
    m[rng.permutation(n)[: n // 2]] = True
    return m


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def ece(y, p, bins=10):
    ok = ~np.isnan(p)
    y, p = y[ok], p[ok]
    if len(y) == 0:
        return np.nan
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (p > lo) & (p <= hi) if lo > 0 else (p >= lo) & (p <= hi)
        if sel.sum():
            total += sel.sum() / len(y) * abs(y[sel].mean() - p[sel].mean())
    return total


def risk_coverage(y, s):
    """y = 1 means incorrect. Lower s = more trusted. Returns (cov, risk, aurc)."""
    ok = ~np.isnan(s)
    y, s = y[ok], s[ok]
    order = np.argsort(s)
    y = y[order]
    n = len(y)
    cov = np.arange(1, n + 1) / n
    risk = np.cumsum(y) / np.arange(1, n + 1)
    return cov, risk, float(np.trapezoid(risk, cov)) if n > 1 else np.nan


def accuracy_at_coverage(y, s, c):
    ok = ~np.isnan(s)
    y, s = y[ok], s[ok]
    if len(y) == 0:
        return np.nan
    k = max(1, int(round(c * len(y))))
    keep = np.argsort(s)[:k]
    return float(1.0 - y[keep].mean())


def conformal_threshold(y_cal, s_cal, alpha):
    """Largest threshold whose empirical selective risk on calibration <= alpha."""
    ok = ~np.isnan(s_cal)
    y, s = y_cal[ok], s_cal[ok]
    if len(y) == 0:
        return np.nan
    order = np.argsort(s)
    y, s = y[order], s[order]
    running = np.cumsum(y) / np.arange(1, len(y) + 1)
    feasible = np.where(running <= alpha)[0]
    return float(s[feasible[-1]]) if len(feasible) else -np.inf


def safe_auroc(y, s):
    ok = ~np.isnan(s)
    if ok.sum() < 20 or len(np.unique(y[ok])) < 2:
        return np.nan
    return float(roc_auc_score(y[ok], s[ok]))


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def _fast_auc(y: np.ndarray, s: np.ndarray) -> float:
    """Rank-based AUROC with midranks for ties. Same value as sklearn, ~100x faster
    inside a bootstrap loop because it skips validation overhead."""
    n_pos = y.sum()
    n_neg = y.size - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = np.empty(s.size, dtype=np.float64)
    ranks[order] = np.arange(1, s.size + 1, dtype=np.float64)
    # midranks for tied scores
    i = 0
    while i < s.size:
        j = i + 1
        while j < s.size and s_sorted[j] == s_sorted[i]:
            j += 1
        if j - i > 1:
            ranks[order[i:j]] = (i + 1 + j) / 2.0
        i = j
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def paired_bootstrap_diff(y, sa, sb, rng, n_boot=N_BOOT):
    """Paired bootstrap over items for AUROC(a) - AUROC(b).

    Paired: the SAME resampled item indices are used for both signals, so the
    interval is on the difference and not on two marginal estimates.
    """
    ok = (~np.isnan(sa)) & (~np.isnan(sb))
    y, sa, sb = y[ok], sa[ok], sb[ok]
    if len(y) < 30 or len(np.unique(y)) < 2:
        return np.nan, (np.nan, np.nan)
    point = _fast_auc(y, sa) - _fast_auc(y, sb)
    diffs = np.empty(n_boot)
    n = len(y)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        yb = y[idx]
        if yb.sum() in (0, n):
            diffs[b] = np.nan
            continue
        diffs[b] = _fast_auc(yb, sa[idx]) - _fast_auc(yb, sb[idx])
    lo, hi = np.nanpercentile(diffs, [2.5, 97.5])
    return float(point), (float(lo), float(hi))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def analyse(raw_path: Path, n_boot: int = N_BOOT):
    rng = np.random.default_rng(SEED)
    df = build_frame(raw_path)

    excl = df["excluded"].mean()
    print(f"excluded (refusal or API error): {excl:.1%}")

    metric_rows, contrast_rows, conf_rows = [], [], []

    for (model, dataset), g in df[~df["excluded"]].groupby(["model", "dataset"]):
        g = g.reset_index(drop=True)
        y = g["y_incorrect"].to_numpy(dtype=float)
        cal = split_mask(len(g), np.random.default_rng(SEED))

        for proto in PROTOCOLS:
            sig = signals_for(g, proto)
            comps = sig.pop("_TIF_components")

            # Fitted triple, eq. (3). Fit on calibration only.
            fit_ok = ~np.isnan(comps).any(axis=1)
            s_lr = np.full(len(g), np.nan)
            train = cal & fit_ok
            if train.sum() >= 50 and len(np.unique(y[train])) == 2:
                lr = LogisticRegression(max_iter=1000)
                lr.fit(comps[train], y[train])
                s_lr[fit_ok] = lr.predict_proba(comps[fit_ok])[:, 1]
            sig["s_TIF_lr"] = pd.Series(s_lr)

            test = ~cal
            for name, s in sig.items():
                s = np.asarray(s, dtype=float)
                st, yt = s[test], y[test]

                # isotonic calibration for Brier/ECE, fitted on calibration split
                p = np.full(len(yt), np.nan)
                ok_c = cal & ~np.isnan(s)
                if ok_c.sum() >= 50 and len(np.unique(y[ok_c])) == 2:
                    iso = IsotonicRegression(out_of_bounds="clip")
                    iso.fit(s[ok_c], y[ok_c])
                    ok_t = ~np.isnan(st)
                    p[ok_t] = iso.predict(st[ok_t])

                _, _, aurc = risk_coverage(yt, st)
                ok_ap = ~np.isnan(st)
                metric_rows.append({
                    "model": model, "dataset": dataset, "protocol": proto, "signal": name,
                    "n_test": int(ok_ap.sum()),
                    "auroc": safe_auroc(yt, st),
                    "auprc": (float(average_precision_score(yt[ok_ap], st[ok_ap]))
                              if ok_ap.sum() >= 20 and len(np.unique(yt[ok_ap])) == 2 else np.nan),
                    "brier": float(np.nanmean((p - yt) ** 2)) if not np.all(np.isnan(p)) else np.nan,
                    "ece": ece(yt, p),
                    "aurc": aurc,
                    **{f"acc@cov{c}": accuracy_at_coverage(yt, st, c) for c in COVERAGES},
                    "parse_rate": float(ok_ap.mean()),
                })

                for alpha in ALPHAS:
                    thr = conformal_threshold(y[cal], s[cal], alpha)
                    sel = (~np.isnan(st)) & (st <= thr)
                    conf_rows.append({
                        "model": model, "dataset": dataset, "protocol": proto,
                        "signal": name, "alpha": alpha, "threshold": thr,
                        "achieved_coverage": float(sel.mean()),
                        "achieved_risk": float(yt[sel].mean()) if sel.sum() else np.nan,
                        "n_selected": int(sel.sum()),
                    })

            # Preregistered contrasts
            pairs = [
                ("H1", "s_TIF_lr", "verbalized_scalar"),
                ("H2", "s_TIF_lr", "s_TF"),
                ("H3", "semantic_entropy", "s_TIF_lr"),
            ]
            for label, a, b in pairs:
                pt, (lo, hi) = paired_bootstrap_diff(
                    y[test], np.asarray(sig[a], dtype=float)[test],
                    np.asarray(sig[b], dtype=float)[test], rng, n_boot,
                )
                contrast_rows.append({
                    "hypothesis": label, "model": model, "dataset": dataset,
                    "protocol": proto, "a": a, "b": b,
                    "delta_auroc": pt, "ci_lo": lo, "ci_hi": hi,
                    "excludes_zero": bool(not np.isnan(lo) and (lo > 0 or hi < 0)),
                })

    OUT.mkdir(exist_ok=True)
    m = pd.DataFrame(metric_rows); m.to_csv(OUT / "metrics.csv", index=False)
    c = pd.DataFrame(contrast_rows); c.to_csv(OUT / "contrasts.csv", index=False)
    k = pd.DataFrame(conf_rows); k.to_csv(OUT / "conformal.csv", index=False)

    # H4: marginal eta-squared of AUROC per design factor.
    # eta2_f = SS_between(f) / SS_total, bounded in [0,1]. These are MARGINAL, so with
    # correlated factors they need not sum to 1; report them as such, do not renormalise.
    v = m.dropna(subset=["auroc"])
    grand = v["auroc"].mean() if len(v) else np.nan
    ss_total = float(((v["auroc"] - grand) ** 2).sum()) if len(v) > 1 else np.nan
    var_rows = []
    for f in ("signal", "protocol", "model", "dataset"):
        if not ss_total or math.isnan(ss_total) or v[f].nunique() < 2:
            var_rows.append({"component": f, "eta_squared": np.nan, "n_levels": int(v[f].nunique())})
            continue
        gm = v.groupby(f)["auroc"].agg(["mean", "size"])
        ss_between = float((gm["size"] * (gm["mean"] - grand) ** 2).sum())
        var_rows.append({"component": f, "eta_squared": ss_between / ss_total,
                         "n_levels": int(v[f].nunique())})
    pd.DataFrame(var_rows).to_csv(OUT / "variance.csv", index=False)

    write_summary(m, c, k, pd.DataFrame(var_rows), excl)
    print(f"wrote {OUT/'metrics.csv'}, contrasts.csv, conformal.csv, variance.csv, SUMMARY.md")


def write_summary(m, c, k, var, excl):
    lines = ["# Paper 2 -- preregistered verdicts", "",
             f"Excluded (refusal or API error): {excl:.1%}", ""]

    def verdict(h):
        sub = c[c["hypothesis"] == h]
        if sub.empty:
            return "no data"
        all_proto = sub.groupby("protocol")["excludes_zero"].all()
        pos = (sub["delta_auroc"] > 0).mean()
        return (f"delta mean={sub['delta_auroc'].mean():.4f}; "
                f"CI excludes zero in all cells per protocol: "
                f"{dict(all_proto.astype(bool))}; positive in {pos:.0%} of cells")

    lines += ["## H1 -- fitted triple vs verbalized scalar (PRIMARY)", verdict("H1"), "",
              "## H2 -- fitted triple vs T/F only (does I add anything?)", verdict("H2"), "",
              "## H3 -- semantic entropy vs fitted triple (reference bound)", verdict("H3"), ""]

    lines += ["## H4 -- marginal eta-squared of AUROC by design factor", "",
              var.to_markdown(index=False), "",
              "If `protocol` eta-squared exceeds `signal` eta-squared, the ranking of elicited",
              "signals is NOT identifiable from this design. Report that, not a winner.", ""]

    h5 = k[(k["alpha"] == 0.10) & (k["signal"].isin(["s_TIF_lr", "verbalized_scalar"]))]
    lines += ["## H5 -- achieved coverage at guaranteed risk 0.10", "",
              h5.groupby("signal")["achieved_coverage"].mean().to_frame().to_markdown(), ""]

    lines += ["## Main table (mean AUROC by signal x protocol)", "",
              m.pivot_table(index="signal", columns="protocol", values="auroc",
                            aggfunc="mean").round(4).to_markdown(), ""]

    (OUT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(OUT / "raw_paper2.jsonl"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT,
                    help="bootstrap resamples; use 1000 for a pilot, 10000 for the paper")
    a = ap.parse_args()
    N_BOOT = a.n_boot
    analyse(Path(a.raw), a.n_boot)
