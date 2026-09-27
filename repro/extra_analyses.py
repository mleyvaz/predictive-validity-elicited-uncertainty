"""
Extra analyses (27-sep-2026), EXPLORATORY, computed only from the saved raw file; no API calls.

 (a) Dimensional collapse of the elicited triple: Spearman correlations among T, I, F and the
     verbalized scalar per model x dataset x protocol; PCA of standardized (T, I, F) with the share
     of variance of the first component; how close F is to 1 - T.
 (b) Equivalence test (TOST) of the fitted triple vs the verbalized scalar in AUROC, margin +-0.02,
     on the pooled mean over cells, with an item-cluster bootstrap (90% interval) -- same resampling
     scheme as analyze_v2 (item ids resampled within dataset, shared across models and protocols).
 (c) ChaosNLI as a positive control for a task that needs an indeterminacy channel: does the
     elicited I track human label entropy better than the scalar? Per model and protocol:
     Spearman rho(I, H), rho(1-scalar, H), their difference with a bootstrap CI (items resampled),
     and the partial rank correlation of I with H given the scalar, with bootstrap CI.

Outputs: results_extra/collapse_cells.csv, collapse_summary.txt, tost.csv, chaosnli_control.csv,
         extra_summary.txt
Usage (from repro/): python extra_analyses.py [--n-boot 2000]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "code"))
import analyze as A, analyze_v2 as A2

OUT = HERE / "results_extra"; OUT.mkdir(exist_ok=True)
SEED = A.SEED


def comp(v, k):
    return v[k] if isinstance(v, (list, tuple)) and len(v) == 3 else np.nan


def part_a(df, lines):
    rows = []
    for (mo, ds), g in df[~df["excluded"]].groupby(["model", "dataset"]):
        for p in A.PROTOCOLS:
            T = g[f"tif_{p}"].map(lambda v: comp(v, 0)).astype(float)
            I = g[f"tif_{p}"].map(lambda v: comp(v, 1)).astype(float)
            F = g[f"tif_{p}"].map(lambda v: comp(v, 2)).astype(float)
            sc = pd.to_numeric(g[f"scalar_{p}"], errors="coerce")
            ok = T.notna() & I.notna() & F.notna()
            X = np.column_stack([T[ok], I[ok], F[ok]])
            sd = X.std(axis=0)
            Z = (X - X.mean(0)) / np.where(sd > 0, sd, 1)
            ev = np.sort(np.linalg.eigvalsh(np.cov(Z.T)))[::-1] if ok.sum() > 3 else [np.nan] * 3
            pc1 = float(ev[0] / np.sum(ev)) if np.sum(ev) > 0 else np.nan
            ok2 = ok & sc.notna()
            r = lambda a, b, m: stats.spearmanr(a[m], b[m])[0] if m.sum() > 3 and a[m].nunique() > 1 and b[m].nunique() > 1 else np.nan
            rows.append(dict(model=mo, dataset=ds, protocol=p, n=int(ok.sum()),
                             rho_T_F=r(T, F, ok), rho_T_I=r(T, I, ok), rho_I_F=r(I, F, ok),
                             rho_T_scalar=r(T, sc, ok2), rho_F_scalar=r(F, sc, ok2), rho_I_scalar=r(I, sc, ok2),
                             pc1_share=pc1, mean_abs_F_minus_1mT=float(np.mean(np.abs(F[ok] - (1 - T[ok])))),
                             share_F_eq_1mT_005=float(np.mean(np.abs(F[ok] - (1 - T[ok])) <= 0.05)),
                             sd_I=float(I[ok].std()), share_I_zero=float(np.mean(I[ok] == 0))))
    c = pd.DataFrame(rows); c.to_csv(OUT / "collapse_cells.csv", index=False)
    lines.append("== (a) dimensional collapse (48 model x dataset x protocol cells)")
    for col in ["rho_T_F", "rho_T_scalar", "rho_F_scalar", "rho_T_I", "rho_I_F", "rho_I_scalar", "pc1_share",
                "mean_abs_F_minus_1mT", "share_F_eq_1mT_005", "share_I_zero"]:
        x = c[col].dropna()
        lines.append(f"{col}: median {x.median():.3f}  IQR [{x.quantile(.25):.3f}, {x.quantile(.75):.3f}]  min {x.min():.3f}  max {x.max():.3f}  n {len(x)}")
    for p in A.PROTOCOLS:
        x = c[c.protocol == p]
        lines.append(f"  {p}: median pc1 {x.pc1_share.median():.3f}; median rho_T_F {x.rho_T_F.median():.3f}; median rho_T_scalar {x.rho_T_scalar.median():.3f}; median share I=0 {x.share_I_zero.median():.3f}")
    lines.append(f"cells with pc1_share >= 0.80: {(c.pc1_share >= 0.80).sum()} of {c.pc1_share.notna().sum()}; >= 0.67: {(c.pc1_share >= 2/3).sum()}")
    lines.append(f"cells with |rho_T_F| >= 0.8: {(c.rho_T_F.abs() >= 0.8).sum()}; with rho_T_scalar >= 0.8: {(c.rho_T_scalar >= 0.8).sum()}")
    return c


def part_b(df, n_boot, lines):
    cells = []
    for (mo, ds), g in df[~df["excluded"]].groupby(["model", "dataset"]):
        g = g.reset_index(drop=True); cal = A.split_mask(len(g), np.random.default_rng(SEED))
        for p in A.PROTOCOLS:
            y, sig = A2.cell_signals(g, p, cal)
            t = ~cal
            ok = t & ~np.isnan(sig["s_TIF_lr"]) & ~np.isnan(sig["verbalized_scalar"])
            cells.append(dict(ds=ds, y=y[ok], a=sig["s_TIF_lr"][ok], b=sig["verbalized_scalar"][ok], ids=g["item_id"].to_numpy()[ok]))
    ids_by_ds = {ds: np.array(sorted(set(np.concatenate([c["ids"] for c in cells if c["ds"] == ds])))) for ds in {c["ds"] for c in cells}}
    rng = np.random.default_rng(SEED + 7)

    def pooled(w_by_ds, subset):
        d = []
        for c in cells:
            if subset and c["ds"] == "sciq":
                continue
            w = w_by_ds[c["ds"]](c["ids"]) if w_by_ds else np.ones(len(c["y"]))
            m = w > 0
            if len(np.unique(c["y"][m])) < 2:
                d.append(np.nan); continue
            d.append(roc_auc_score(c["y"][m], c["a"][m], sample_weight=w[m]) - roc_auc_score(c["y"][m], c["b"][m], sample_weight=w[m]))
        return np.nanmean(d)
    rows = []
    for label, subset in (("all48", False), ("noSciQ36", True)):
        pt = pooled(None, subset); boots = []
        for _ in range(n_boot):
            wm = {}
            for ds, ids in ids_by_ds.items():
                u, cnt = np.unique(rng.choice(ids, size=len(ids), replace=True), return_counts=True)
                lut = dict(zip(u, cnt)); wm[ds] = (lambda lut: (lambda arr: np.array([lut.get(i, 0) for i in arr], float)))(lut)
            boots.append(pooled(wm, subset))
        b = np.array(boots)
        lo90, hi90 = np.nanpercentile(b, [5, 95]); lo95, hi95 = np.nanpercentile(b, [2.5, 97.5])
        for margin in (0.02, 0.03):
            rows.append(dict(set=label, margin=margin, pooled=pt, ci90_lo=lo90, ci90_hi=hi90, ci95_lo=lo95, ci95_hi=hi95,
                             p_lower=float(np.mean(b <= -margin)), p_upper=float(np.mean(b >= margin)),
                             equivalent=bool(lo90 > -margin and hi90 < margin), n_boot=n_boot))
    t = pd.DataFrame(rows); t.to_csv(OUT / "tost.csv", index=False)
    lines.append("== (b) TOST, fitted triple - scalar, pooled AUROC difference (item-cluster bootstrap)")
    for r in rows:
        lines.append(f"{r['set']} margin {r['margin']}: pooled {r['pooled']:+.4f}, 90% CI [{r['ci90_lo']:+.4f}, {r['ci90_hi']:+.4f}], "
                     f"bootstrap p(<=-m) {r['p_lower']:.3f}, p(>=+m) {r['p_upper']:.3f}, equivalent={r['equivalent']}")
    return t


def part_c(df, n_boot, lines):
    meta = {json.loads(l)["id"]: json.loads(l) for l in open(HERE / "code" / "data" / "chaosnli.jsonl", encoding="utf-8")}
    ch = df[(df.dataset == "chaosnli") & ~df["excluded"]].copy()
    ch["H"] = ch.item_id.map(lambda i: meta[i]["human_entropy"])
    rng = np.random.default_rng(SEED + 11)
    rows = []

    def prank(x, y, z):
        rx, ry, rz = stats.rankdata(x), stats.rankdata(y), stats.rankdata(z)
        ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz); ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
        return float(np.corrcoef(ex, ey)[0, 1])
    for mo, g in ch.groupby("model"):
        for p in A.PROTOCOLS:
            I = g[f"tif_{p}"].map(lambda v: comp(v, 1)).astype(float).to_numpy()
            s = (1 - pd.to_numeric(g[f"scalar_{p}"], errors="coerce")).to_numpy()
            H = g["H"].to_numpy(float)
            ok = ~np.isnan(I) & ~np.isnan(s)
            I, s, H = I[ok], s[ok], H[ok]
            if np.std(I) == 0 or np.std(s) == 0:
                continue
            rI, rS = stats.spearmanr(I, H)[0], stats.spearmanr(s, H)[0]
            pr = prank(I, H, s)
            bd, bp = [], []
            n = len(H)
            for _ in range(n_boot):
                ix = rng.integers(0, n, n)
                if np.std(I[ix]) == 0 or np.std(s[ix]) == 0:
                    continue
                bd.append(stats.spearmanr(I[ix], H[ix])[0] - stats.spearmanr(s[ix], H[ix])[0])
                bp.append(prank(I[ix], H[ix], s[ix]))
            amb = (H > np.median([m["human_entropy"] for m in meta.values()])).astype(int)
            rows.append(dict(model=mo, protocol=p, n=n, rho_I_H=rI, rho_scalar_H=rS, diff=rI - rS,
                             diff_lo=np.percentile(bd, 2.5), diff_hi=np.percentile(bd, 97.5),
                             partial_I_H_given_scalar=pr, partial_lo=np.percentile(bp, 2.5), partial_hi=np.percentile(bp, 97.5),
                             auroc_amb_I=roc_auc_score(amb, I), auroc_amb_scalar=roc_auc_score(amb, s)))
    c = pd.DataFrame(rows); c.to_csv(OUT / "chaosnli_control.csv", index=False)
    lines.append("== (c) ChaosNLI positive control: does elicited I track human label entropy better than the scalar?")
    for r in rows:
        lines.append(f"{r['model']:17s} {r['protocol']}: rho(I,H) {r['rho_I_H']:+.3f}  rho(1-scalar,H) {r['rho_scalar_H']:+.3f}  "
                     f"diff {r['diff']:+.3f} [{r['diff_lo']:+.3f}, {r['diff_hi']:+.3f}]  partial(I,H|scalar) {r['partial_I_H_given_scalar']:+.3f} "
                     f"[{r['partial_lo']:+.3f}, {r['partial_hi']:+.3f}]  AUROC ambiguous-half: I {r['auroc_amb_I']:.3f} scalar {r['auroc_amb_scalar']:.3f}")
    lines.append(f"cells (model x protocol) where diff CI is entirely > 0: {int((c.diff_lo > 0).sum())}; entirely < 0: {int((c.diff_hi < 0).sum())}; of {len(c)}")
    lines.append(f"cells where partial(I,H|scalar) CI excludes 0 (positive): {int((c.partial_lo > 0).sum())}; negative: {int((c.partial_hi < 0).sum())}")
    lines.append(f"mean AUROC for ambiguous half: I {c.auroc_amb_I.mean():.3f}, scalar {c.auroc_amb_scalar.mean():.3f}")
    return c


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n-boot", type=int, default=2000); a = ap.parse_args()
    df = A.build_frame(HERE / "results" / "raw_paper2.jsonl")
    lines = []
    part_a(df, lines); part_c(df, a.n_boot, lines); part_b(df, a.n_boot, lines)
    (OUT / "extra_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
