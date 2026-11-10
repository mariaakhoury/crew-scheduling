"""Performance profiles and summary statistics (task A16, owner A). Master Plan §11.1, slide 12.

Which method is fastest, how often, and by how much? Every number is recomputed from runs.csv (Q25).

    python -m crew.analysis_profiles --runs results/runs.csv --out results/a16

  run_times(df, metric)          per instance x method: time, or inf if the method did not solve it
  ratios(df, metric)             each method's time divided by the fastest method's time on that instance
  profile_curve(df, metric)      share of instances each method solves within a factor tau of the fastest
  plot_profile(df, metric)       the performance-profile chart (Dolan and More 2002)
  sgm(times, shift=10)           shifted geometric mean, the usual average for solver times
  summary_table(df, metric)      per method: solved, solved within 120 s end-to-end, shifted geometric mean
  win_tie_loss(df, metric)       every pair of methods: wins / ties / losses per instance

"Solved" means OPTIMAL and accepted by the checker. A method that did not solve an instance counts as never
solving it in the profile (ratio = inf). In the shifted geometric mean it counts with the most time it could
have used (time limit + build limit), so a fast failure (e.g. COLUMN_CAP after 30 s) is not rewarded.
Default metric: end-to-end time, which includes duty enumeration and model building.
"""
from __future__ import annotations

import argparse
import itertools
import os

import numpy as np
import pandas as pd

from crew.analysis_heuristic import _active, _yes

MIP_METHODS = ("H", "AF", "AF+S", "SP", "SP+S")
METRICS = {"end_to_end": "end_to_end_s", "solver": "solver_time_s"}
TIE_REL, TIE_ABS = 0.10, 1.0      # tie: within 10 % or 1 s (Master Plan §10.10, same rule as B12)
E2E_CUTOFF = 120.0


def _solved(r) -> bool:
    return str(r["status"]) == "OPTIMAL" and _yes(r.get("feasible_checked", "yes"))


def _rows(df: pd.DataFrame) -> pd.DataFrame:
    df = _active(df)
    return df[df["method"].isin(MIP_METHODS) & (df["method"] != "H")]


def run_times(df: pd.DataFrame, metric: str = "end_to_end") -> pd.DataFrame:
    """Instances in rows, methods in columns: the time to a proven optimum, or inf if not solved."""
    col = METRICS[metric]
    d = _rows(df).copy()
    d["t"] = np.where(d.apply(_solved, axis=1), d[col].astype(float).clip(lower=0.01), np.inf)
    return d.pivot_table(index="instance", columns="method", values="t", aggfunc="first")


def ratios(df: pd.DataFrame, metric: str = "end_to_end") -> pd.DataFrame:
    """Time / fastest time on that instance. Instances no method solved are dropped (no fastest exists)."""
    t = run_times(df, metric)
    best = t.min(axis=1)
    t = t[np.isfinite(best)]
    return t.div(best[np.isfinite(best)], axis=0)


def profile_curve(df: pd.DataFrame, metric: str = "end_to_end", taus=None) -> pd.DataFrame:
    """rho_m(tau) = share of instances (that at least one method solved) where method m is within tau x fastest."""
    r = ratios(df, metric)
    if taus is None:
        finite = r.to_numpy()[np.isfinite(r.to_numpy())]
        top = max(2.0, float(finite.max()) * 1.5) if finite.size else 2.0
        taus = np.unique(np.concatenate([[1.0], np.sort(finite), [top]]))
    return pd.DataFrame({m: [(r[m] <= tau).mean() for tau in taus] for m in r.columns}, index=pd.Index(taus, name="tau"))


def plot_profile(df: pd.DataFrame, metric: str = "end_to_end", ax=None):
    """Step curves: higher and further left is better. The value at tau = 1 is the share of instances where the
    method was the fastest; the right end is the share it solved at all."""
    import matplotlib.pyplot as plt
    p = profile_curve(df, metric)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    styles = {"AF": ("tab:blue", "-"), "AF+S": ("tab:blue", "--"), "SP": ("tab:orange", "-"),
              "SP+S": ("tab:orange", "--")}
    for m in p.columns:
        color, ls = styles.get(m, ("black", ":"))
        ax.step(p.index, p[m], where="post", color=color, ls=ls, lw=2, label=m)
    ax.set_xscale("log")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel(f"within this factor of the fastest method ({metric.replace('_', '-')} time, log scale)")
    ax.set_ylabel("share of instances solved")
    ax.set_title(f"Performance profile ({len(ratios(df, metric))} instances solved by at least one method)")
    ax.grid(color="0.9")
    ax.legend()
    return ax.figure


def sgm(times, shift: float = 10.0) -> float:
    """Shifted geometric mean: exp(mean(log(t + shift))) - shift. The shift stops tiny times dominating."""
    t = np.asarray(list(times), dtype=float)
    return float(np.exp(np.log(t + shift).mean()) - shift) if t.size else np.nan


def _sgm_times(g: pd.DataFrame, col: str) -> list[float]:
    out = []
    for _, r in g.iterrows():
        if _solved(r):
            out.append(float(r[col]))
        else:
            cap = float(r.get("time_limit_s", 120) or 120) + float(r.get("build_limit_s", 120) or 120)
            out.append(max(cap, float(r[col]) if pd.notna(r[col]) else cap))
    return out


def summary_table(df: pd.DataFrame, metric: str = "end_to_end") -> pd.DataFrame:
    """Per method: runs, solved, fastest on, solved within 120 s end-to-end, shifted geometric mean (shift 10 s)."""
    col = METRICS[metric]
    d = _rows(df)
    r = ratios(df, metric)
    out = []
    for m, g in d.groupby("method"):
        solved = g.apply(_solved, axis=1)
        e2e = g["end_to_end_s"].astype(float)
        out.append({"method": m, "runs": len(g), "solved": int(solved.sum()),
                    "fastest_on": int((r[m] <= 1.0 + 1e-12).sum()) if m in r else 0,
                    "solved_within_120s_end_to_end": int((solved & (e2e <= E2E_CUTOFF)).sum()),
                    f"sgm_{metric}_s": sgm(_sgm_times(g, col))})
    return pd.DataFrame(out).set_index("method")


def win_tie_loss(df: pd.DataFrame, metric: str = "end_to_end") -> pd.DataFrame:
    """For each pair (A, B): on how many instances A beat B, tied, or lost. Solved beats unsolved; both solved:
    tie if within 10 % or 1 s; neither solved: tie."""
    t = run_times(df, metric)
    out = []
    for a, b in itertools.combinations(t.columns, 2):
        w = ti = lo = 0
        for ta, tb in zip(t[a], t[b]):
            if pd.isna(ta) or pd.isna(tb):
                continue
            if np.isinf(ta) and np.isinf(tb):
                ti += 1
            elif np.isinf(tb) or (not np.isinf(ta) and tb - ta > max(TIE_ABS, TIE_REL * tb)):
                w += 1
            elif np.isinf(ta) or (ta - tb > max(TIE_ABS, TIE_REL * ta)):
                lo += 1
            else:
                ti += 1
        out.append({"A": a, "B": b, "A_wins": w, "ties": ti, "A_losses": lo})
    return pd.DataFrame(out)


def report(runs_csv: str, out_dir: str, metric: str = "end_to_end") -> pd.DataFrame:
    """Write the A16 tables (CSV), the profile chart (PNG) and a markdown summary; return the summary table."""
    import matplotlib
    matplotlib.use("Agg")
    df = pd.read_csv(runs_csv)
    os.makedirs(out_dir, exist_ok=True)
    s, w = summary_table(df, metric), win_tie_loss(df, metric)
    s.to_csv(os.path.join(out_dir, "profile_summary.csv"))
    w.to_csv(os.path.join(out_dir, "win_tie_loss.csv"), index=False)
    ratios(df, metric).to_csv(os.path.join(out_dir, "time_ratios.csv"))
    plot_profile(df, metric).savefig(os.path.join(out_dir, "performance_profile.png"), dpi=150, bbox_inches="tight")
    lines = [f"# A16 performance profiles - source `{runs_csv}`, metric: {metric} time", "",
             "## Per method", "", s.to_string(), "", "## Win / tie / loss", "", w.to_string(index=False), ""]
    with open(os.path.join(out_dir, "A16_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return s


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join("results", "runs.csv"))
    ap.add_argument("--out", default=os.path.join("results", "a16"))
    ap.add_argument("--metric", choices=sorted(METRICS), default="end_to_end")
    a = ap.parse_args(argv)
    report(a.runs, a.out, a.metric)
    print(f"A16 written to {a.out}")


if __name__ == "__main__":
    main()
