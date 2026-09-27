"""
Post-hoc exploratory analysis registered in ANALYSIS_PLAN.md (deviation 2026-09-01):
on the ChaosNLI cells, does the elicited I component track HUMAN label entropy
(a target other than error)? Contrasted with the scalar arm and with semantic entropy.

Also reports, per model x protocol:
  - effective dimensionality of the verbal triple: share of items with I > T, F > T, I >= 0.5
  - AUROC of each signal for error, separately on the clear (low-entropy) and
    ambiguous (high-entropy) halves.

Usage: python analyze_chaosnli_I.py --raw results/raw_paper2.jsonl
"""
from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np, pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
PROTOCOLS = ("P1", "P2", "P3")


def comp(v, k):
    return v[k] if isinstance(v, (list, tuple)) and len(v) == 3 else np.nan


def main(raw):
    meta = {}
    with (HERE / "data" / "chaosnli.jsonl").open(encoding="utf-8") as fh:
        for l in fh:
            r = json.loads(l); meta[r["id"]] = r
    rows = [json.loads(l) for l in open(raw, encoding="utf-8")]
    df = pd.DataFrame([r for r in rows if r["dataset"] == "chaosnli" and not r.get("error")])
    if df.empty:
        print("no chaosnli rows"); return
    df["H_human"] = df.item_id.map(lambda i: meta[i]["human_entropy"])
    df["ambiguous"] = df.H_human > np.median([m["human_entropy"] for m in meta.values()])
    df["y"] = df.y_incorrect
    out = []
    for model, g in df.groupby("model"):
        print(f"\n=== {model}  n={len(g)}  error rate={g.y.mean():.3f}  refusals={g.refusal.mean():.1%}")
        print("  Spearman with HUMAN entropy (target = ambiguity, not error):")
        for p in PROTOCOLS:
            T = g[f"tif_{p}"].map(lambda v: comp(v, 0)); I = g[f"tif_{p}"].map(lambda v: comp(v, 1)); F = g[f"tif_{p}"].map(lambda v: comp(v, 2))
            sc = pd.to_numeric(g[f"scalar_{p}"], errors="coerce")
            ok = I.notna() & sc.notna()
            rI = stats.spearmanr(I[ok], g.H_human[ok])[0]; rT = stats.spearmanr(T[ok], g.H_human[ok])[0]
            rS = stats.spearmanr(1 - sc[ok], g.H_human[ok])[0]
            dim = f"I>T {(I > T).mean():.1%} | F>T {(F > T).mean():.1%} | I>=0.5 {(I >= .5).mean():.1%} | I median {I.median():.2f}"
            print(f"    {p}: rho(I,H)={rI:+.3f}  rho(T,H)={rT:+.3f}  rho(1-scalar,H)={rS:+.3f}  parse={ok.mean():.0%}   dims: {dim}")
            yv = g.y.astype(float)
            for half, m in (("clear", ~g.ambiguous), ("ambiguous", g.ambiguous)):
                mm = m & ok & yv.notna()
                if mm.sum() > 20 and yv[mm].nunique() == 2:
                    aI = roc_auc_score(yv[mm], I[mm]); aT = roc_auc_score(yv[mm], F[mm] - T[mm]); aS = roc_auc_score(yv[mm], 1 - sc[mm])
                    print(f"        {half:9s} n={mm.sum():3d} err={yv[mm].mean():.2f}  AUROC(error): I={aI:.3f}  F-T={aT:.3f}  1-scalar={aS:.3f}")
            out.append(dict(model=model, protocol=p, rho_I_human=rI, rho_T_human=rT, rho_scalar_human=rS,
                            share_I_gt_T=(I > T).mean(), share_I_ge_05=(I >= .5).mean()))
        se = pd.to_numeric(g.semantic_entropy, errors="coerce"); ok = se.notna()
        print(f"  semantic entropy: rho(SE,H)={stats.spearmanr(se[ok], g.H_human[ok])[0]:+.3f}")
        if g.seq_logprob.notna().any():
            lp = pd.to_numeric(g.seq_logprob, errors="coerce"); ok = lp.notna()
            print(f"  -logprob:         rho(-lp,H)={stats.spearmanr(-lp[ok], g.H_human[ok])[0]:+.3f}")
    pd.DataFrame(out).to_csv(HERE / "results" / "chaosnli_I_vs_human.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", default=str(HERE / "results" / "raw_paper2.jsonl"))
    main(ap.parse_args().raw)
