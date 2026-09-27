"""
Figures for Paper 2 (Predictive Validity). Reads ONLY saved outputs; no API calls, no numbers typed
by hand. Every plotted value comes from:
  results/raw_paper2.jsonl         (design counts; per-item scores for risk-coverage, via analyze_v2)
  results/metrics.csv              (per-cell AUROC)
  results_v2/contrasts_v2.csv      (per-cell paired differences)
  results_v2/pooled_v2.csv         (pooled means + item-cluster bootstrap intervals)
  results_v2/conformal_v2.csv      (tie-aware risk-calibrated thresholds, H5)
Usage: python make_figures.py [--out DIR]   (default: repro/figures) -> DIR/*.pdf|png
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
R, V2 = HERE / "results", HERE / "results_v2"
import argparse as _ap
_p = _ap.ArgumentParser(); _p.add_argument("--out", default=str(HERE / "figures")); OUT = Path(_p.parse_args().out)
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE / "code"))

# Reference palette (dataviz skill), first three categorical slots + neutral inks
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": "DejaVu Sans", "pdf.fonttype": 42})
DS_LABEL = {"triviaqa": "TriviaQA", "nqopen": "NQ-open", "sciq": "SciQ-MC", "chaosnli": "ChaosNLI"}
DS_ORDER = ["triviaqa", "nqopen", "sciq", "chaosnli"]
m = pd.read_csv(R / "metrics.csv"); c2 = pd.read_csv(V2 / "contrasts_v2.csv")
pooled = pd.read_csv(V2 / "pooled_v2.csv"); k2 = pd.read_csv(V2 / "conformal_v2.csv")
log = []


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig); log.append(name)


# ------------------------------------------------------------------ Fig 1: design
rows = [json.loads(l) for l in open(R / "raw_paper2.jsonl", encoding="utf-8")]
raw = pd.DataFrame(rows); raw = raw[~raw.get("error", pd.Series(False, index=raw.index)).fillna(False).astype(bool)]
n_items = raw.groupby("dataset").item_id.nunique()
models = sorted(raw.model.unique()); n_cells = len(raw)
fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 30)
cols = [
    ("Items", [f"{DS_LABEL[d]} ({n_items[d]})" for d in DS_ORDER], "generation, clean MC,\nambiguous NLI"),
    ("Models", [x.replace("claude-haiku-4.5", "Claude Haiku 4.5").replace("gemini-2.5-flash", "Gemini 2.5 Flash")
                .replace("llama-3.1-8b", "Llama 3.1 8B") for x in models], "greedy answer,\nexact-match grading"),
    ("Elicitation", ["P1 terse numeric", "P2 reason first", "P3 verbal grades"], "3 protocols per\nelicited arm"),
    ("Signals", ["A  triple (T, I, F)", "B  scalar confidence", "C  P(True)", "D  log-probability", "E  sample entropy"], "A-C elicited; D-E sampled\nor internal (K=10)"),
    ("Target & tests", ["Y = answer wrong", "AUROC + bootstrap", "abstention at", "  target risk", "H1-H5 rules"], f"{n_cells:,} item-cells"),
]
x0, w, gap = 1, 17.6, 2.5
for i, (title, items, note) in enumerate(cols):
    x = x0 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 5), w, 21, boxstyle="round,pad=0.2,rounding_size=1.2", fc="#f4f3f0", ec=MUTED, lw=0.8))
    ax.text(x + w / 2, 24.3, title, ha="center", va="center", fontsize=8, weight="bold", color=INK)
    for j, it in enumerate(items):
        col = BLUE if it.startswith("A ") else (ORANGE if it.startswith("B ") else INK2)
        ax.text(x + 1, 21 - j * 3.2, it, ha="left", va="center", fontsize=6.4, color=col)
    ax.text(x + w / 2, 2.2, note, ha="center", va="center", fontsize=6.0, color=MUTED)
    if i < len(cols) - 1:
        ax.annotate("", xy=(x + w + gap - 0.2, 15.5), xytext=(x + w + 0.3, 15.5), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))
save(fig, "fig1_design")

# ------------------------------------------------------------------ Fig 2: forest of confirmatory hypotheses
def cells(h):
    return c2[c2.hypothesis == h].dropna(subset=["delta_auroc"])

E = ["s_TIF_lr", "s_TIF_fixed", "s_TF", "verbalized_scalar", "p_true"]
h4 = []
for (mo, ds), g in m[m.signal.isin(E)].groupby(["model", "dataset"]):
    pv = g.pivot(index="signal", columns="protocol", values="auroc")
    rng_ = (pv.max(1) - pv.min(1)).mean()
    d = [abs(a - b) for p in pv.columns for i, a in enumerate(pv[p].values) for b in pv[p].values[i + 1:]]
    h4.append(np.mean(d) - rng_)   # >0 would support H4 (signal differences exceed protocol range)
kk = k2[k2.alpha == 0.1].set_index(["model", "dataset", "protocol"])
t_, s_ = kk[kk.signal == "s_TIF_lr"], kk[kk.signal == "verbalized_scalar"]
j = t_.join(s_, lsuffix="_t", rsuffix="_s"); j = j[np.isfinite(j.threshold_t) & np.isfinite(j.threshold_s)]
h5 = (j.achieved_coverage_t - j.achieved_coverage_s).values
P = pooled[pooled.set == "all48"].set_index("contrast")
spec = [  # label, per-cell values, pooled (mean, lo, hi) or None, verdict
    ("H1  fitted triple − scalar\n(AUROC)", cells("H1").delta_auroc.values, P.loc["H1"], "fails"),
    ("H2  fitted triple − fixed F−T\n(AUROC, preregistered)", cells("H2").delta_auroc.values, P.loc["H2"], "fails"),
    ("H2n fitted T,I,F − fitted T,F\n(AUROC, POST HOC nested contrast)", cells("H2n").delta_auroc.values, P.loc["H2n"], "small, inconsistent"),
    ("H3  sample entropy − fitted triple\n(AUROC)", cells("H3_vs_s_TIF_lr").delta_auroc.values, None, "holds on generation"),
    ("H4  between-signal diff − protocol range\n(AUROC, per model × dataset)", np.array(h4), None, "fails"),
    (f"H5  coverage triple − scalar at α=0.10\n({len(h5)} comparable cells)", h5, None, "not supported"),
]
fig, ax = plt.subplots(figsize=(7.2, 3.9))
rngj = np.random.default_rng(0)
for i, (lab, vals, pl, verdict) in enumerate(spec):
    y = len(spec) - 1 - i
    ax.scatter(vals, y + rngj.uniform(-0.18, 0.18, len(vals)), s=9, color=MUTED, alpha=0.55, lw=0, zorder=2)
    if pl is not None:
        ax.plot([pl.ci_lo, pl.ci_hi], [y, y], color=BLUE, lw=2.2, zorder=3, solid_capstyle="round")
        ax.scatter([pl.pooled_mean], [y], s=42, color=BLUE, zorder=4, edgecolor="white", lw=1)
        txt = f"{pl.pooled_mean:+.3f} [{pl.ci_lo:+.3f}, {pl.ci_hi:+.3f}]"
    else:
        mu = float(np.mean(vals)); ax.scatter([mu], [y], s=42, marker="D", color=ORANGE, zorder=4, edgecolor="white", lw=1)
        txt = f"mean {mu:+.3f} (n={len(vals)})"
    ax.text(1.02, y, f"{txt}\n{verdict}", transform=ax.get_yaxis_transform(), va="center", fontsize=7, color=INK)
ax.axvline(0, color=INK, lw=0.8, zorder=1)
ax.set_yticks(range(len(spec))); ax.set_yticklabels([s[0] for s in spec][::-1], fontsize=7.2)
ax.set_xlabel("difference (positive favours the first-named signal / the hypothesis)")
ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.scatter([], [], s=9, color=MUTED, label="single cell"); ax.scatter([], [], s=42, color=BLUE, label="pooled mean, 95% item-cluster bootstrap CI")
ax.scatter([], [], s=42, marker="D", color=ORANGE, label="mean over cells (no pooled CI)")
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=3, frameon=False, fontsize=7)
save(fig, "fig2_forest")

# ------------------------------------------------------------------ Fig 3: protocol vs signal (H4)
SIGLAB = {"s_TIF_lr": "triple (fitted)", "s_TIF_fixed": "triple (fixed)", "s_TF": "F − T", "verbalized_scalar": "scalar", "p_true": "P(True)"}
hm = m[m.signal.isin(E)].groupby(["signal", "protocol"]).auroc.mean().unstack().loc[E]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw=dict(width_ratios=[1, 1.25]))
im = a1.imshow(hm.values, cmap="Blues", vmin=np.floor(hm.values.min() * 20) / 20, vmax=np.ceil(hm.values.max() * 20) / 20, aspect="auto")
a1.set_xticks(range(3)); a1.set_xticklabels(hm.columns); a1.set_yticks(range(len(E))); a1.set_yticklabels([SIGLAB[e] for e in E])
for (r_, c_), v in np.ndenumerate(hm.values):
    a1.text(c_, r_, f"{v:.3f}", ha="center", va="center", fontsize=7, color="white" if (v - hm.values.min()) / (hm.values.max() - hm.values.min()) > 0.6 else INK)
a1.set_title("mean test AUROC (16 cells)", fontsize=8.5, color=INK); a1.spines[:].set_visible(False)
a1.tick_params(length=0)
pr, sd = [], []
for (mo, ds), g in m[m.signal.isin(E)].groupby(["model", "dataset"]):
    pv = g.pivot(index="signal", columns="protocol", values="auroc")
    pr.append((pv.max(1) - pv.min(1)).mean())
    sd.append(np.mean([abs(a - b) for p in pv.columns for i, a in enumerate(pv[p].values) for b in pv[p].values[i + 1:]]))
    a2.scatter(sd[-1], pr[-1], s=30, color=BLUE if ds in ("triviaqa", "nqopen") else ORANGE, edgecolor="white", lw=0.8, zorder=3)
lim = max(max(pr), max(sd)) * 1.1
a2.plot([0, lim], [0, lim], color=MUTED, lw=0.8, ls="--"); a2.set_xlim(0, lim); a2.set_ylim(0, lim)
a2.text(lim * 0.62, lim * 0.52, "H4 holds\nbelow the line", color=MUTED, fontsize=7)
a2.set_xlabel("mean |difference| between elicited signals\nat fixed protocol (AUROC)"); a2.set_ylabel("mean range across protocols\n(AUROC)")
a2.scatter([], [], color=BLUE, s=30, label="generation"); a2.scatter([], [], color=ORANGE, s=30, label="closed-label")
a2.legend(frameon=False, fontsize=7, loc="upper left"); a2.set_title(f"{int((np.array(pr) < np.array(sd)).sum())} of {len(pr)} model × dataset cells below the line", fontsize=8.5, color=INK)
a2.grid(color=GRID, lw=0.6); a2.set_axisbelow(True)
fig.tight_layout(); save(fig, "fig3_protocol_vs_signal")

# ------------------------------------------------------------------ Fig 4: risk-coverage (appendix)
import analyze as A, analyze_v2 as A2
df = A.build_frame(R / "raw_paper2.jsonl")
grid = np.linspace(0.05, 1.0, 96)
curves = {ds: {k: [] for k in ("s_TIF_lr", "verbalized_scalar", "semantic_entropy")} for ds in DS_ORDER}
for (mo, ds), g in df[~df["excluded"]].groupby(["model", "dataset"]):
    g = g.reset_index(drop=True); cal = A.split_mask(len(g), np.random.default_rng(A.SEED))
    for proto in A.PROTOCOLS:
        y, sig = A2.cell_signals(g, proto, cal); t = ~cal
        for k in curves[ds]:
            s = sig[k][t]; yy = y[t]; ok = ~np.isnan(s); s, yy = s[ok], yy[ok]
            order = np.argsort(s, kind="mergesort"); r = np.cumsum(yy[order]) / np.arange(1, len(yy) + 1)
            cov = np.arange(1, len(yy) + 1) / len(yy)
            curves[ds][k].append(np.interp(grid, cov, r))
fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.3), sharey=False)
for a, ds in zip(axs, DS_ORDER):
    for k, col, lab in (("semantic_entropy", AQUA, "semantic entropy (string)"), ("verbalized_scalar", ORANGE, "scalar"), ("s_TIF_lr", BLUE, "fitted triple")):
        a.plot(grid, np.mean(curves[ds][k], axis=0), color=col, lw=1.6, label=lab)
    a.set_title(DS_LABEL[ds], fontsize=8.5, color=INK); a.set_xlabel("coverage"); a.grid(color=GRID, lw=0.6); a.set_axisbelow(True)
axs[0].set_ylabel("selective risk (error rate)")
axs[0].legend(frameon=False, fontsize=6.8, loc="upper left")
fig.tight_layout(); save(fig, "fig4_risk_coverage")

# ------------------------------------------------------------------ Fig 5: ChaosNLI positive control (results_extra)
cc = pd.read_csv(HERE / "results_extra" / "chaosnli_control.csv")
MLAB = {"claude-haiku-4.5": "Claude", "gemini-2.5-flash": "Gemini", "gpt-4o-mini": "gpt-4o-mini", "llama-3.1-8b": "Llama"}
cc["lab"] = cc.model.map(MLAB) + " " + cc.protocol
cc = cc.iloc[::-1].reset_index(drop=True)
fig, (b1, b2) = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
for ax_, mid, lo, hi, ttl in ((b1, "diff", "diff_lo", "diff_hi", "rho(I, human entropy) - rho(1-scalar, human entropy)"),
                               (b2, "partial_I_H_given_scalar", "partial_lo", "partial_hi", "partial rank corr. of I with human entropy | scalar")):
    for i, r in cc.iterrows():
        col = ORANGE if r[hi] < 0 else (BLUE if r[lo] > 0 else MUTED)
        ax_.plot([r[lo], r[hi]], [i, i], color=col, lw=1.8, solid_capstyle="round")
        ax_.scatter([r[mid]], [i], color=col, s=22, zorder=3, edgecolor="white", lw=0.8)
    ax_.axvline(0, color=INK, lw=0.8); ax_.set_title(ttl, fontsize=7.8, color=INK)
    ax_.grid(axis="x", color=GRID, lw=0.6); ax_.set_axisbelow(True)
b1.set_yticks(range(len(cc))); b1.set_yticklabels(cc.lab, fontsize=7)
b1.plot([], [], color=ORANGE, lw=1.8, label="95% CI below 0"); b1.plot([], [], color=MUTED, lw=1.8, label="CI includes 0")
b1.plot([], [], color=BLUE, lw=1.8, label="95% CI above 0")
b1.legend(frameon=False, fontsize=6.8, loc="lower left")
fig.tight_layout(); save(fig, "fig5_chaosnli_control")

(OUT / "FIGURES_LOG.txt").write_text("generated: " + ", ".join(log) + "\n", encoding="utf-8")
print("generated:", log)
