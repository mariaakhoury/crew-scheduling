"""Heuristic contribution (task B12, owner B). Master Plan §11.1 item 7 and hypothesis H6.

All numbers are recomputed from results/runs.csv (Q25); no new runs are needed.
  heuristic_quality(df)  greedy / LS cost vs the best known value, with the gap to the optimum
                         (or an upper bound on the gap from the best proven bound)
  paired_effect(df)      AF vs AF+S and SP vs SP+S per instance: ratios of solver time, nodes,
                         time to first incumbent, final gap; win/tie/loss (tie = within 10 % or 1 s)
  h6_verdict(df)         H6: "the MIP start helps AF more than SP" (median improvement AF > SP)
  no_help_list(df)       instances where the start did not help, for the negative-results table
  plot_paired(df)        paired-ratio chart for slide 11
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PAIRS = [("AF", "AF+S"), ("SP", "SP+S")]
SOLVED = "OPTIMAL"


def _active(df: pd.DataFrame) -> pd.DataFrame:
    if "superseded" in df.columns:
        df = df[~df["superseded"].astype(str).str.lower().isin(["true", "1", "yes"])]
    return df


def best_known(df: pd.DataFrame) -> pd.DataFrame:
    """Per instance: best objective found by any method, best bound, and whether it is proven optimal."""
    df = _active(df)
    mip = df[df["method"].isin(["AF", "AF+S", "SP", "SP+S"])]
    g = mip.groupby("instance")
    return pd.DataFrame({
        "best_value": g["objective"].min(),
        "best_bound": g["best_bound"].max(),
        "proven": g["status"].apply(lambda s: (s == SOLVED).any()),
    })


def _greedy_costs(heuristic_dir: str | None, names) -> dict:
    """greedy_cost per instance from the runner's heuristic cache results/heuristic/<instance>.json."""
    import json
    import os
    out = {}
    if heuristic_dir:
        for name in names:
            path = os.path.join(heuristic_dir, f"{name}.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    out[name] = json.load(fh).get("greedy_cost")
    return out


def heuristic_quality(df: pd.DataFrame, heuristic_dir: str | None = None) -> pd.DataFrame:
    """Greedy/LS cost and gaps. LS cost comes from the H rows (heuristic_cost / objective); greedy cost from the
    heuristic cache folder if given (e.g. "results/heuristic"). Gap is exact if the instance is proven optimal,
    otherwise an upper bound computed from the best bound."""
    df = _active(df)
    h = df[df["method"] == "H"].set_index("instance")
    bk = best_known(df)
    out = pd.DataFrame(index=h.index)
    greedy = _greedy_costs(heuristic_dir, h.index)
    if greedy:
        out["greedy_cost"] = pd.Series(greedy)
    elif "greedy_cost" in h.columns:
        out["greedy_cost"] = h["greedy_cost"]
    out["ls_cost"] = h["heuristic_cost"].fillna(h.get("objective"))
    out["heuristic_time_s"] = h.get("t_heur_s")
    out = out.join(bk)
    ref = np.where(out["proven"], out["best_value"], out["best_bound"])
    out["ls_gap_pct"] = 100 * (out["ls_cost"] - ref) / out["ls_cost"]
    out["gap_kind"] = np.where(out["proven"], "exact", "upper bound")
    if "greedy_cost" in out.columns:
        out["greedy_gap_pct"] = 100 * (out["greedy_cost"] - ref) / out["greedy_cost"]
    out["ls_is_optimal"] = out["proven"] & (abs(out["ls_cost"] - out["best_value"]) < 0.01)
    return out


def _wtl(base: float, start: float) -> str:
    """win / tie / loss of the +S method (tie = within 10 % or 1 s)."""
    if pd.isna(base) or pd.isna(start):
        return "n/a"
    if abs(base - start) <= max(1.0, 0.1 * max(base, start)):
        return "tie"
    return "win" if start < base else "loss"


def paired_effect(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (instance, model): ratio = with start / without start (< 1 means the start helped)."""
    df = _active(df)
    rows = []
    for base, plus in PAIRS:
        a = df[df["method"] == base].set_index("instance")
        b = df[df["method"] == plus].set_index("instance")
        for inst in a.index.intersection(b.index):
            ra, rb = a.loc[inst], b.loc[inst]
            row = {"instance": inst, "model": base, "status": ra["status"], "status_S": rb["status"],
                   "start_accepted": rb.get("start_accepted")}
            for col in ["solver_time_s", "end_to_end_s", "nodes", "t_first_incumbent_s", "gap_pct"]:
                if col in df.columns:
                    va, vb = ra.get(col), rb.get(col)
                    row[col] = va
                    row[col + "_S"] = vb
                    row[col + "_ratio"] = (vb / va) if pd.notna(va) and pd.notna(vb) and va > 0 else np.nan
            row["wtl_time"] = _wtl(ra.get("solver_time_s"), rb.get("solver_time_s"))
            rows.append(row)
    return pd.DataFrame(rows)


def summary_paired(df: pd.DataFrame) -> pd.DataFrame:
    """Median and range of the ratios, start acceptance rate, and win/tie/loss counts per model."""
    p = paired_effect(df)
    out = []
    for model, g in p.groupby("model"):
        r = {"model": model, "instances": len(g)}
        for col in ["solver_time_s_ratio", "nodes_ratio", "t_first_incumbent_s_ratio"]:
            if col in g:
                s = g[col].dropna()
                r[f"median_{col}"] = s.median() if len(s) else np.nan
                r[f"min_{col}"] = s.min() if len(s) else np.nan
                r[f"max_{col}"] = s.max() if len(s) else np.nan
        acc = g["start_accepted"].astype(str).str.lower().isin(["true", "1", "yes"])
        r["start_acceptance_rate"] = acc.mean()
        for k in ["win", "tie", "loss"]:
            r[k] = int((g["wtl_time"] == k).sum())
        out.append(r)
    return pd.DataFrame(out)


def h6_verdict(df: pd.DataFrame) -> dict:
    """H6: the MIP start helps AF more than SP. Improvement = 1 - ratio of solver time (median).
    Confirmed if the median AF improvement is larger than the median SP improvement (§10.9)."""
    p = paired_effect(df)
    med = {m: 1 - g["solver_time_s_ratio"].dropna().median() for m, g in p.groupby("model")}
    af, sp = med.get("AF", np.nan), med.get("SP", np.nan)
    verdict = "confirmed" if af > sp else "not confirmed"
    return {"median_improvement_AF": af, "median_improvement_SP": sp, "verdict": verdict}


def no_help_list(df: pd.DataFrame) -> pd.DataFrame:
    """Instances where the start did not help (tie or loss), with a first automatic hint at the reason;
    the final explanation is written by hand in the discussion (e.g. SP solved at the root node)."""
    p = paired_effect(df)
    bad = p[p["wtl_time"].isin(["tie", "loss"])].copy()

    def hint(r):
        if str(r.get("start_accepted")).lower() not in ("true", "1", "yes"):
            return "start not accepted"
        if r.get("nodes", np.nan) == 0 or r.get("nodes", np.nan) == 1:
            return "solved at the root node: the start had nothing to add"
        if r.get("solver_time_s", 99) < 1:
            return "solved in under 1 s either way"
        return "explain from the log"
    bad["hint"] = bad.apply(hint, axis=1)
    return bad[["instance", "model", "status", "status_S", "solver_time_s", "solver_time_s_S", "wtl_time", "hint"]]


def plot_paired(df: pd.DataFrame, ax=None):
    """Paired ratio chart (log scale): one point per instance, one column per model. Below 1 = start helped."""
    import matplotlib.pyplot as plt
    p = paired_effect(df)
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 4))
    for k, (model, g) in enumerate(p.groupby("model")):
        y = g["solver_time_s_ratio"].dropna()
        ax.scatter(np.full(len(y), k) + np.random.default_rng(0).uniform(-0.1, 0.1, len(y)), y, alpha=0.7)
    ax.axhline(1.0, color="grey", lw=1, ls="--")
    ax.set_xticks(range(p["model"].nunique()), [f"{m}+S / {m}" for m in sorted(p["model"].unique())])
    ax.set_yscale("log")
    ax.set_ylabel("solver time with start / without (log)")
    ax.set_title("Effect of the heuristic MIP start (below 1 = faster)")
    return ax.figure
