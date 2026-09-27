"""Recompute every number quoted in the manuscript from the saved results / raw data.
Usage: python verify_numbers.py <results_dir> <raw_jsonl>
"""
import sys, json
import numpy as np, pandas as pd

R = sys.argv[1]; RAW = sys.argv[2]
m = pd.read_csv(f"{R}/metrics.csv"); c = pd.read_csv(f"{R}/contrasts.csv"); k = pd.read_csv(f"{R}/conformal.csv")
P = ["P1", "P2", "P3"]

def hdr(s): print("\n=== " + s)

hdr("Table 1 main: mean [min,max] AUROC by signal x protocol")
for s in ["s_TIF_lr", "s_TIF_fixed", "s_TF", "verbalized_scalar", "p_true", "seq_logprob", "semantic_entropy"]:
    row = []
    for p in P:
        x = m[(m.signal == s) & (m.protocol == p)].auroc.dropna()
        row.append(f"{x.mean():.3f} [{x.min():.2f},{x.max():.2f}] n={len(x)}")
    print(s, " | ".join(row))

hdr("Table 2 by dataset (mean over protocols & models)")
print(m[m.signal.isin(["s_TIF_lr", "s_TF", "verbalized_scalar", "p_true", "seq_logprob", "semantic_entropy"])]
      .groupby(["signal", "dataset"]).auroc.mean().unstack().round(3))

for h in ["H1", "H2", "H3"]:
    hdr(h)
    d = c[c.hypothesis == h]
    for p in P:
        x = d[d.protocol == p]
        print(p, f"mean={x.delta_auroc.mean():+.3f}", "+", int((x.excludes_zero & (x.delta_auroc > 0)).sum()),
              "-", int((x.excludes_zero & (x.delta_auroc < 0)).sum()))
    print("overall mean", round(d.delta_auroc.mean(), 4), "positive share", round((d.delta_auroc > 0).mean(), 3),
          "sig+", int((d.excludes_zero & (d.delta_auroc > 0)).sum()), "sig-", int((d.excludes_zero & (d.delta_auroc < 0)).sum()))
    print("by dataset", d.groupby("dataset").delta_auroc.mean().round(3).to_dict())
    print("sig by dataset (+/-)", d[d.excludes_zero].groupby("dataset").apply(lambda z: (int((z.delta_auroc > 0).sum()), int((z.delta_auroc < 0).sum()))).to_dict())
    ns = d[d.dataset != "sciq"]
    print("excl SciQ mean", round(ns.delta_auroc.mean(), 4), "n", len(ns))
    cell = d.groupby(["model", "dataset", "protocol"]).delta_auroc.mean()
    print("between-cell SE of mean", round(cell.std(ddof=1) / np.sqrt(len(cell)), 4))
    print("mean CI half-width", round(((d.ci_hi - d.ci_lo) / 2).mean(), 3))
    if h == "H2":
        x = d[(d.protocol == "P3") & d.excludes_zero]; print("H2 P3 sig cells:", x[["model", "dataset", "delta_auroc"]].values.tolist())

hdr("Post hoc label arm")
for h in ["H1lab", "Hlab_vs_A", "H2lab"]:
    d = c[c.hypothesis == h]
    print(h, {p: round(d[d.protocol == p].delta_auroc.mean(), 3) for p in P})

hdr("H4 variance"); print(pd.read_csv(f"{R}/variance.csv"))

hdr("H5 conformal alpha=0.10")
kk = k[k.alpha == 0.1]
a = kk[kk.signal == "s_TIF_lr"].set_index(["model", "dataset", "protocol"])
b = kk[kk.signal == "verbalized_scalar"].set_index(["model", "dataset", "protocol"])
j = a.join(b, lsuffix="_t", rsuffix="_s")
feas = j[np.isfinite(j.threshold_t) & np.isfinite(j.threshold_s) & (j.n_selected_t > 0) & (j.n_selected_s > 0)]
print("n cells total", len(j), "feasible (finite thr, n_sel>0)", len(feas))
dd = feas.achieved_coverage_t - feas.achieved_coverage_s
print("mean diff", round(dd.mean(), 3), {p: round(dd.xs(p, level=2).mean(), 3) for p in P})
print("more", int((dd > 1e-12).sum()), "less", int((dd < -1e-12).sum()), "same", int((dd.abs() <= 1e-12).sum()))
print("risk>0.10 triple", round((feas.achieved_risk_t > 0.10).mean(), 3), "scalar", round((feas.achieved_risk_s > 0.10).mean(), 3))
e = kk[kk.signal == "semantic_entropy"].set_index(["model", "dataset", "protocol"])
je = e.join(b, lsuffix="_e", rsuffix="_s").loc[feas.index]
de = je.achieved_coverage_e - je.achieved_coverage_s
print("SE - scalar coverage", round(de.mean(), 3), "up", int((de > 1e-12).sum()), "down", int((de < -1e-12).sum()))
print("thresholds distribution check: n nonfinite triple", int((~np.isfinite(j.threshold_t)).sum()), "scalar", int((~np.isfinite(j.threshold_s)).sum()))

hdr("Protocol movement of s_TIF_lr AUROC within model x dataset (max-min)")
g = m[m.signal == "s_TIF_lr"].groupby(["model", "dataset"]).auroc.agg(lambda x: x.max() - x.min()).round(3)
print(g.unstack())

hdr("Effective dimensionality: |AUROC(s_TIF_lr) - AUROC(s_TF)|")
pv = m[m.signal.isin(["s_TIF_lr", "s_TF"])].pivot_table(index=["model", "dataset", "protocol"], columns="signal", values="auroc")
gap = (pv.s_TIF_lr - pv.s_TF).abs()
print("share <0.01", round((gap < 0.01).mean(), 3), "median", round(gap.median(), 4), "n", len(gap))

hdr("Parse rates of preregistered elicited arms (metrics parse_rate, test split)")
pr = m[m.signal.isin(["s_TF", "verbalized_scalar", "p_true"])]
print("n", len(pr), ">=0.90:", int((pr.parse_rate >= 0.90).sum()))
print(pr[pr.parse_rate < 0.90][["model", "dataset", "protocol", "signal", "parse_rate"]].round(3).to_string())
pl = m[m.signal == "s_TFlab"]; print("label arm <0.90:", pl[pl.parse_rate < 0.90][["model", "dataset", "protocol", "parse_rate"]].round(3).values.tolist())

hdr("Raw data: refusals, error rates, logprob availability, I shares")
rows = [json.loads(l) for l in open(RAW, encoding="utf-8") if l.strip()]
df = pd.DataFrame(rows)
if "error" not in df.columns: df["error"] = False
df["error"] = df["error"].fillna(False).astype(bool)
v = df[~df.error].drop_duplicates(["model", "dataset", "item_id"], keep="last")
print("valid item-cells", len(v), "raw rows", len(df), "error rows", int(df.error.sum()))
print("refusal by dataset %", (v.groupby("dataset").refusal.mean() * 100).round(1).to_dict())
print("refusal by model %", (v.groupby("model").refusal.mean() * 100).round(1).to_dict())
nr = v[~v.refusal.astype(bool)]
print("error rate by dataset", nr.groupby("dataset").y_incorrect.mean().round(3).to_dict())
print(nr.groupby(["model", "dataset"]).y_incorrect.mean().round(3).unstack())
print((v.groupby(["model", "dataset"]).refusal.mean() * 100).round(1).unstack())
print("logprob available share by model", v.groupby("model").seq_logprob.apply(lambda s: round(s.notna().mean(), 3)).to_dict())
def comp(x, i): return x[i] if isinstance(x, (list, tuple)) and len(x) == 3 else np.nan
for p in P:
    T = nr[f"tif_{p}"].map(lambda x: comp(x, 0)); I = nr[f"tif_{p}"].map(lambda x: comp(x, 1))
    nr = nr.assign(**{f"IgtT_{p}": (I > T).where(I.notna() & T.notna()), f"Ige05_{p}": (I >= 0.5).where(I.notna())})
print("share I>T by model x dataset x protocol")
print(nr.groupby(["model", "dataset"])[[f"IgtT_{p}" for p in P]].mean().round(3))
print("share I>=0.5 on chaosnli")
print(nr[nr.dataset == "chaosnli"].groupby("model")[[f"Ige05_{p}" for p in P]].mean().round(3))
# API calls estimate
print("columns", [c_ for c_ in df.columns][:60])

# ---- Added after R1: H4 as literally preregistered, on preregistered elicited signals only
hdr("H4 literal (elicited preregistered signals): protocol range vs between-signal |diff| at fixed protocol")
E = ['s_TIF_lr', 's_TIF_fixed', 's_TF', 'verbalized_scalar', 'p_true']
x = m[m.signal.isin(E)]
pr, sd = [], []
for (mo, ds), g in x.groupby(['model', 'dataset']):
    pv = g.pivot(index='signal', columns='protocol', values='auroc')
    pr.append((pv.max(1) - pv.min(1)).mean())
    d = []
    for p in pv.columns:
        v = pv[p].values; d += [abs(a - b) for i, a in enumerate(v) for b in v[i + 1:]]
    sd.append(np.mean(d))
pr, sd = np.array(pr), np.array(sd)
print('mean protocol range', round(pr.mean(), 3), 'mean between-signal |diff|', round(sd.mean(), 3), 'cells with range<diff', int((pr < sd).sum()), 'of', len(pr))
x2 = x.dropna(subset=['auroc']); gm = x2.auroc.mean(); ss = ((x2.auroc - gm) ** 2).sum()
print('marginal eta2 (elicited only)', {f: round(x2.groupby(f).auroc.apply(lambda z: len(z) * (z.mean() - gm) ** 2).sum() / ss, 3) for f in ['signal', 'protocol', 'model', 'dataset']})
hdr("H1 excluding the 3 cells with parse rate < 0.90")
bad = m[m.signal.isin(['s_TF', 'verbalized_scalar', 'p_true']) & (m.parse_rate < 0.9)][['model', 'dataset', 'protocol']].drop_duplicates(); bad['bad'] = 1
h1 = c[c.hypothesis == 'H1'].merge(bad, how='left', on=['model', 'dataset', 'protocol']); kk1 = h1[h1['bad'].isna()]
print('H1 mean', round(kk1.delta_auroc.mean(), 4), 'n', len(kk1))
hdr("Effective test n per dataset (s_TIF_lr, verbalized_scalar)")
print(m[m.signal.isin(['s_TIF_lr', 'verbalized_scalar'])].groupby(['signal', 'dataset']).n_test.agg(['min', 'max']))

# ---- Added after R2 (v2 analysis: results_v2/, produced by code/analyze_v2.py from the same raw file)
import os
V2 = os.path.join(os.path.dirname(os.path.abspath(R)), "results_v2")
c2 = pd.read_csv(f"{V2}/contrasts_v2.csv"); k2 = pd.read_csv(f"{V2}/conformal_v2.csv")
hdr("v2 contrasts (per-protocol means, sig+/sig-, by dataset)")
for h in c2.hypothesis.unique():
    x = c2[c2.hypothesis == h].dropna(subset=['delta_auroc'])
    print(h, 'n', len(x), 'mean', round(x.delta_auroc.mean(), 4), {p: round(x[x.protocol == p].delta_auroc.mean(), 3) for p in P},
          'sig+', int((x.excludes_zero & (x.delta_auroc > 0)).sum()), 'sig-', int((x.excludes_zero & (x.delta_auroc < 0)).sum()),
          'by ds', x.groupby('dataset').delta_auroc.mean().round(3).to_dict())
gen = c2[c2.dataset.isin(['triviaqa', 'nqopen']) & c2.hypothesis.str.startswith('H3_vs')]
print('H3 on generation, min over elicited signals of mean delta:', round(gen.groupby('hypothesis').delta_auroc.mean().min(), 3),
      gen.groupby('hypothesis').delta_auroc.mean().round(3).to_dict())
hdr("v2 H5: tie-aware thresholds, alpha=0.10")
kk = k2[k2.alpha == 0.1].set_index(['model', 'dataset', 'protocol'])
print('calibration risk above alpha in any cell/signal:', int((kk.cal_risk > 0.1 + 1e-12).sum()))
print('finite thresholds per signal (of 48):', kk.groupby('signal').threshold.apply(lambda x: int(np.isfinite(x).sum())).to_dict())
t = kk[kk.signal == 's_TIF_lr']; s_ = kk[kk.signal == 'verbalized_scalar']; e = kk[kk.signal == 'semantic_entropy']
j = t.join(s_, lsuffix='_t', rsuffix='_s'); f = j[np.isfinite(j.threshold_t) & np.isfinite(j.threshold_s)]
d = f.achieved_coverage_t - f.achieved_coverage_s
print('cells', len(f), 'mean diff', round(d.mean(), 3), {p: round(d.xs(p, level=2).mean(), 3) for p in P},
      'more', int((d > 1e-12).sum()), 'less', int((d < -1e-12).sum()), 'same', int((d.abs() <= 1e-12).sum()))
print('mean coverage triple', round(f.achieved_coverage_t.mean(), 3), 'scalar', round(f.achieved_coverage_s.mean(), 3))
print('test risk > 0.10: triple', round((f.achieved_risk_t > 0.1).mean(), 3), 'scalar', round((f.achieved_risk_s > 0.1).mean(), 3))
je = e.join(s_, lsuffix='_e', rsuffix='_s'); fe = je[np.isfinite(je.threshold_e) & np.isfinite(je.threshold_s)]
de = fe.achieved_coverage_e - fe.achieved_coverage_s
print('SE vs scalar: cells', len(fe), 'mean', round(de.mean(), 3), 'up', int((de > 1e-12).sum()), 'down', int((de < -1e-12).sum()))
hdr("v2 pooled means with hierarchical (item-cluster) bootstrap"); print(pd.read_csv(f"{V2}/pooled_v2.csv").round(4).to_string())
hdr("v2 split sensitivity (50 alternative splits)")
ss = pd.read_csv(f"{V2}/split_sensitivity_v2.csv")
print(ss[['H1_pooled', 'H2n_pooled']].describe().round(4).to_string()); print('share H1>0', (ss.H1_pooled > 0).mean(), 'share H2n>0', (ss.H2n_pooled > 0).mean())
hdr("v2 incomplete item-cells"); print(open(f"{V2}/incomplete_v2.txt", encoding='utf-8').read())
hdr("Appendix: secondary metrics (mean over cells with a value)")
S = ['s_TIF_lr', 's_TIF_fixed', 's_TF', 'verbalized_scalar', 'p_true', 'seq_logprob', 'semantic_entropy']
xm = m[m.signal.isin(S)]
print(xm.groupby('signal')[['auroc', 'auprc', 'brier', 'ece', 'aurc', 'acc@cov0.9', 'acc@cov0.8', 'acc@cov0.5']].mean().loc[S].round(3).to_string())
lp = m[(m.signal == 'seq_logprob') & m.auroc.notna()][['model', 'dataset', 'protocol']]
print('AUROC on the 8 log-prob cells:', m.merge(lp, on=['model', 'dataset', 'protocol']).query('signal in @S').groupby('signal').auroc.mean().round(3).to_dict())
hdr("ChaosNLI partial Spearman (rank-based, permutation p) -- from results/chaosnli_c_v2.log")
txt = open(os.path.join(R, 'chaosnli_c_v2.log'), encoding='utf-8').read(); i = txt.find('[B]'); print(txt[i:txt.find('[C]')])

# ---- Added for the extra exploratory analyses (results_extra/, produced by extra_analyses.py)
EX = os.path.join(os.path.dirname(os.path.abspath(R)), "results_extra")
hdr("Extra analyses (collapse, TOST, ChaosNLI control) -- results_extra/extra_summary.txt")
print(open(os.path.join(EX, "extra_summary.txt"), encoding="utf-8").read())
