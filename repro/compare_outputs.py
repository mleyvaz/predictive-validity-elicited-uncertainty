"""
Regenerate every analysis output from the raw file into fresh directories and compare it with the
distributed outputs. No API calls. Run from repro/:   python compare_outputs.py [--quick]
  --quick skips the slow bootstrap parts (analyze.py with 10,000 draws, the item-cluster bootstrap in
  analyze_v2.py and the TOST bootstrap); without it the full run takes roughly 30-40 minutes.
Prints the maximum absolute difference per CSV; 0.0 means the distributed file is reproduced exactly.
"""
import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "results" / "raw_paper2.jsonl"


def cmp(a, b, cols=None):
    x, y = pd.read_csv(a), pd.read_csv(b)
    if cols:
        x, y = x[cols], y[cols]
    if x.shape != y.shape:
        return f"SHAPE {x.shape} vs {y.shape}"
    num = x.select_dtypes("number").columns
    return float(np.nanmax(np.abs(x[num].values - y[num].values))) if len(num) else "no numeric columns"


def run(cmd):
    subprocess.run([sys.executable] + cmd, cwd=HERE, check=True, capture_output=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    code_results = HERE / "code" / "results"
    backup = None
    if code_results.exists():
        backup = Path(tempfile.mkdtemp()) / "results_backup"; shutil.move(str(code_results), backup)
    code_results.mkdir(parents=True, exist_ok=True)
    try:
        # 1. preregistered analysis -> code/results (analyze.py writes next to itself)
        if not a.quick:
            run(["code/analyze.py", "--raw", str(RAW)])
            for f in ["metrics.csv", "contrasts.csv", "conformal.csv", "variance.csv"]:
                print(f"results/{f}:", cmp(code_results / f, HERE / "results" / f))
        run(["code/analyze_chaosnli_constructed_v2.py", "--raw", str(RAW)])
        print("results/chaosnli_constructed_vs_human.csv:",
              cmp(code_results / "chaosnli_constructed_vs_human.csv", HERE / "results" / "chaosnli_constructed_vs_human.csv"))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # 2. post-review analyses
            run(["code/analyze_v2.py", "--raw", str(RAW), "--out", str(td / "v2")] + (["--n-hboot", "3", "--n-splits", "2", "--n-boot", "50"] if a.quick else []))
            files = ["contrasts_v2.csv", "conformal_v2.csv", "metrics_v2.csv"] if a.quick else ["contrasts_v2.csv", "conformal_v2.csv", "metrics_v2.csv", "pooled_v2.csv", "split_sensitivity_v2.csv"]
            for f in files:
                cols = ["delta_auroc"] if (a.quick and f == "contrasts_v2.csv") else None
                v = cmp(td / "v2" / f, HERE / "results_v2" / f, cols)
                print(f"results_v2/{f}:", v, "(point estimates only in --quick)" if cols else "")
            # 3. exploratory analyses
            run(["extra_analyses.py", "--out", str(td / "ex"), "--parts", "ac" if a.quick else "acb"])
            for f in ["collapse_cells.csv", "chaosnli_control.csv"] + ([] if a.quick else ["tost.csv"]):
                print(f"results_extra/{f}:", cmp(td / "ex" / f, HERE / "results_extra" / f))
    finally:
        if code_results.exists():
            shutil.rmtree(code_results)
        if backup is not None:
            shutil.move(str(backup), code_results)
