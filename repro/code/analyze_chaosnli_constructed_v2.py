"""
Post hoc (2026-09-01): on ChaosNLI, does a triple CONSTRUCTED from the K=10 samples
(not elicited) track HUMAN label disagreement better than scalar semantic entropy,
and better than the elicited I?

Constructed from the sample label distribution (3 labels):
  T_c = share of samples equal to the greedy label
  F_c = share of the strongest rival label
  I_c = share of the remaining (third) label   (diffuse mass)
  H_c = Shannon entropy of the sample label distribution (scalar reference)
Also: JS divergence between the model's sample distribution and the human distribution.

Targets: human entropy (ambiguity) and error (majority label mismatch).
Usage: python analyze_chaosnli_constructed.py --raw results/raw_paper2.jsonl
"""
from __future__ import annotations
import argparse, json, math, re, string
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from scipy.spatial.distance import jensenshannon
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import cross_val_predict

HERE = Path(__file__).resolve().parent
LABS = ["entailment", "neutral", "contradiction"]


def norm(s):
    s = s.lower().strip(); s = "".join(c for c in s if c not in string.punctuation)
    return " ".join(s.split())


def comp(v, k):
    return v[k] if isinstance(v, (list, tuple)) and len(v) == 3 else np.nan


def main(raw):
    meta = {}
    for l in (HERE / "data" / "chaosnli.jsonl").open(encoding="utf-8"):
        r = json.loads(l); meta[r["id"]] = r
    rows = [json.loads(l) for l in open(raw, encoding="utf-8")]
    df = pd.DataFrame([r for r in rows if r["dataset"] == "chaosnli" and not r.get("error") and r["y_incorrect"] is not None])
    df["H_human"] = df.item_id.map(lambda i: meta[i]["human_entropy"])
    df["p_human"] = df.item_id.map(lambda i: meta[i]["label_dist"])   # order e, n, c
    med = np.median([m["human_entropy"] for m in meta.values()]); df["ambiguous"] = df.H_human > med

    def constructed(r):
        ss = [norm(s) for s in r["samples"] if s and not s.startswith("__ERROR__")]
        ss = [s for s in ss if s in LABS]
        if len(ss) < 5:
            return (np.nan,) * 6
        c = Counter(ss); n = len(ss); g = norm(r["answer"])
        p = np.array([c.get(k, 0) / n for k in LABS])
        T = c.get(g, 0) / n
        rest = sorted([v / n for k, v in c.items() if k != g], reverse=True) + [0, 0]
        F, I = rest[0], rest[1]
        H = float(-(p[p > 0] * np.log(p[p > 0])).sum())
        js = float(jensenshannon(p, np.array(r["p_human"], dtype=float), base=2) ** 2)
        return T, I, F, H, js, n
    df[["Tc", "Ic", "Fc", "Hc", "JS", "n_valid"]] = pd.DataFrame(df.apply(constructed, axis=1).tolist(), index=df.index)
    df = df.dropna(subset=["Tc"])

    print(f"ChaosNLI, n={len(df)} rows, {df.model.nunique()} models. Human entropy median split at {med:.2f}.")
    print("\n[A] Tracking HUMAN AMBIGUITY (Spearman with human entropy; higher = better)")
    print(f"{'model':16s} {'n':>4s} | {'Hc(sample ent.)':>15s} {'1-Tc':>6s} {'Ic':>6s} {'Fc':>6s} {'LR(Tc,Ic,Fc)cv':>14s} | {'I_elic P1':>9s} {'I_elic P2':>9s} {'I_elic P3':>9s} {'1-scalar P1':>11s} | {'AUROC amb: Hc':>13s} {'Ic':>6s} {'Ielic':>6s}")
    summary = []
    for m, g in df.groupby("model"):
        y = g.H_human.values
        rc = lambda s: stats.spearmanr(s, y)[0]
        X = g[["Tc", "Ic", "Fc"]].values
        pred = cross_val_predict(LinearRegression(), X, y, cv=5)
        r_lr = stats.spearmanr(pred, y)[0]
        Ie = {p: g[f"tif_{p}"].map(lambda v: comp(v, 1)) for p in ("P1", "P2", "P3")}
        sc1 = 1 - pd.to_numeric(g["scalar_P1"], errors="coerce")
        r_Ie = {p: stats.spearmanr(Ie[p][Ie[p].notna()], y[Ie[p].notna().values])[0] for p in Ie}
        r_sc = stats.spearmanr(sc1[sc1.notna()], y[sc1.notna().values])[0]
        amb = g.ambiguous.astype(int).values
        a_Hc = roc_auc_score(amb, g.Hc); a_Ic = roc_auc_score(amb, g.Ic)
        ok = Ie["P1"].notna().values; a_Ie = roc_auc_score(amb[ok], Ie["P1"][ok])
        print(f"{m:16s} {len(g):4d} | {rc(g.Hc):15.3f} {rc(1-g.Tc):6.3f} {rc(g.Ic):6.3f} {rc(g.Fc):6.3f} {r_lr:14.3f} | {r_Ie['P1']:9.3f} {r_Ie['P2']:9.3f} {r_Ie['P3']:9.3f} {r_sc:11.3f} | {a_Hc:13.3f} {a_Ic:6.3f} {a_Ie:6.3f}")
        summary.append(dict(model=m, n=len(g), rho_Hc=rc(g.Hc), rho_Ic=rc(g.Ic), rho_Fc=rc(g.Fc), rho_lr=r_lr,
                            rho_Ielic_P1=r_Ie["P1"], rho_Ielic_P2=r_Ie["P2"], rho_Ielic_P3=r_Ie["P3"], rho_scalar_P1=r_sc,
                            auroc_amb_Hc=a_Hc, auroc_amb_Ic=a_Ic, auroc_amb_Ielic=a_Ie, mean_JS=g.JS.mean()))

    print("\n[B] Does the constructed triple add to sample entropy for AMBIGUITY? (partial Spearman of Ic, Fc given Hc)")
    # v2 (27-sep-2026): standard partial Spearman = Pearson partial correlation of RANKS,
    # with a permutation p-value (x-residuals permuted, 5000 draws) instead of the parametric one.
    prng = np.random.default_rng(20260823)
    for m, g in df.groupby("model"):
        ry = stats.rankdata(g.H_human.values); rh = stats.rankdata(g.Hc.values).reshape(-1, 1)
        resid_y = ry - LinearRegression().fit(rh, ry).predict(rh)
        for comp_name in ("Ic", "Fc", "Tc"):
            x = g[comp_name].values
            if np.nanstd(x) == 0:
                print(f"  {m:16s} {comp_name} | Hc : constant, not estimable"); continue
            rx = stats.rankdata(x)
            resid_x = rx - LinearRegression().fit(rh, rx).predict(rh)
            r = float(np.corrcoef(resid_x, resid_y)[0, 1])
            perm = np.array([np.corrcoef(prng.permutation(resid_x), resid_y)[0, 1] for _ in range(5000)])
            p = float((np.abs(perm) >= abs(r)).mean())
            print(f"  {m:16s} {comp_name} | Hc : rho_partial={r:+.3f} p_perm={p:.3g}")

    print("\n[C] Predicting ERROR (AUROC) on clear vs ambiguous halves")
    for m, g in df.groupby("model"):
        for half, msk in (("clear", ~g.ambiguous), ("ambiguous", g.ambiguous)):
            gg = g[msk]; yy = gg.y_incorrect.astype(int).values
            if len(set(yy)) < 2: continue
            sc = 1 - pd.to_numeric(gg["scalar_P1"], errors="coerce"); ok = sc.notna().values
            print(f"  {m:16s} {half:9s} n={len(gg):3d} err={yy.mean():.2f} | Hc={roc_auc_score(yy, gg.Hc):.3f} 1-Tc={roc_auc_score(yy, 1-gg.Tc):.3f} Fc={roc_auc_score(yy, gg.Fc):.3f} | 1-scalar={roc_auc_score(yy[ok], sc[ok]):.3f}")

    print("\n[D] Model-vs-human distribution: mean JS divergence (0 = identical), by half")
    print(df.groupby(["model", "ambiguous"]).JS.mean().round(3).unstack().rename(columns={False: "clear", True: "ambiguous"}).to_string())
    pd.DataFrame(summary).to_csv(HERE / "results" / "chaosnli_constructed_vs_human.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", default=str(HERE / "results" / "raw_paper2.jsonl"))
    main(ap.parse_args().raw)
