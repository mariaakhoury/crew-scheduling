"""Scalability analysis (task B13, owner B). Master Plan §11.1 item 8 and hypotheses H4, H5, H8.

    python -m crew.analysis_scaling --runs results/runs.csv --features instances/final/MANIFEST.csv --out results/b13

  plot_sizes(df)          |A| and |P| against n, coloured by L (log scale); x = SP not built (count at the stop)
  plot_build_cost(df)     enumeration time, build time and peak memory against |P|
  plot_status_map(df)     solver time vs n: build failures drawn apart from time limits (never mixed)
  h4_build_share(df)      H4: does the build share of SP's end-to-end time rise with |P|?
  h5_verdict(df)          H5: >= 2 SP_not_built and 0 AF build failures
  h8_features(df, feats)  H8: rank correlation of difficulty with trips per duty vs with n
Build failures are never counted as timeouts.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from crew import config

# Not built = the build-failure statuses of config.py (incl. KILLED_BUILD). Plain KILLED now means
# "killed DURING the solve" (runner failure, rerun once): the model WAS built, so it is not listed here.
BUILD_FAIL = set(config.BUILD_FAILURE_STATUSES)
TIME_LIMIT = {"TIME_LIMIT", "TIME_LIMIT_NOSOL"}
H4_RHO = 0.3            # our reading rule for H4 (stated in discussion.md): rho > 0.3 confirmed, 0..0.3 partly


def _active(df):
    if "superseded" in df.columns:
        df = df[~df["superseded"].astype(str).str.lower().isin(["true", "1", "yes"])]
    return df


def plot_sizes(df: pd.DataFrame):
    import matplotlib.pyplot as plt
    df = _active(df)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    af = df[df["method"] == "AF"].drop_duplicates("instance")
    sp = df[df["method"] == "SP"].drop_duplicates("instance")
    for L, g in af.groupby("L"):
        a1.scatter(g["n"], g["n_arcs"], label=f"L={L}")
    for L, g in sp.groupby("L"):
        built = g[~g["status"].isin(BUILD_FAIL)]
        fail = g[g["status"].isin(BUILD_FAIL)]
        sc = a2.scatter(built["n"], built["n_duties"], label=f"L={L}")
        a2.scatter(fail["n"], fail["n_duties"], marker="x", color=sc.get_facecolor()[0])
    a1.set(xlabel="trips n", ylabel="arcs |A|", yscale="log", title="Arc-flow size (polynomial)")
    a2.set(xlabel="trips n", ylabel="duties |P| (x = not built: count when stopped)", yscale="log",
           title="Set partitioning size (exponential)")
    a1.legend(); a2.legend()
    fig.tight_layout()
    return fig


def plot_build_cost(df: pd.DataFrame):
    import matplotlib.pyplot as plt
    df = _active(df)
    sp = df[(df["method"] == "SP") & df["n_duties"].notna()]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, col, lab in zip(axes, ["t_enum_s", "t_build_s", "peak_rss_mb"],
                            ["enumeration time (s)", "build time (s)", "peak memory (MB)"]):
        if col not in sp:
            ax.set_visible(False)
            continue
        ok = sp[~sp["status"].isin(BUILD_FAIL)]
        bad = sp[sp["status"].isin(BUILD_FAIL)]
        ax.scatter(ok["n_duties"], ok[col], label="built")
        ax.scatter(bad["n_duties"], bad[col], marker="x", color="red", label="not built")
        ax.set(xscale="log", yscale="log", xlabel="|P|", ylabel=lab)
        ax.legend()
    fig.suptitle("Cost of building set partitioning grows with |P|")
    fig.tight_layout()
    return fig


def plot_status_map(df: pd.DataFrame, time_limit_s: float | None = None):
    """Solver time vs n for the four MIP methods; TIME_LIMIT at the limit, build failures as x above it."""
    import matplotlib.pyplot as plt
    df = _active(df)
    limit = time_limit_s or (float(df["time_limit_s"].max()) if "time_limit_s" in df else config.GUROBI_TIME_LIMIT_S)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for m, g in df[df["method"].isin(["AF", "AF+S", "SP", "SP+S"])].groupby("method"):
        solved = g[g["status"] == "OPTIMAL"]
        tl = g[g["status"].isin(TIME_LIMIT)]
        bf = g[g["status"].isin(BUILD_FAIL)]
        sc = ax.scatter(solved["n"], solved["solver_time_s"].clip(lower=0.01), label=f"{m} optimal")
        c = sc.get_facecolor()[0]
        ax.scatter(tl["n"], np.full(len(tl), limit), marker="^", color=c, label=f"{m} time limit")
        ax.scatter(bf["n"], np.full(len(bf), limit * 1.6), marker="x", color=c, label=f"{m} not built")
    ax.axhline(limit, ls="--", color="grey", lw=1)
    ax.set(yscale="log", xlabel="trips n", ylabel="solver time (s)",
           title="Timeouts (triangles) vs build failures (x) - never mixed")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    return fig


def h4_build_share(df: pd.DataFrame) -> dict:
    """H4: build share of SP's end-to-end time = (t_enum + t_build) / end_to_end, against |P| (built SP runs only).
    Reading rule: Spearman rho > H4_RHO confirmed, 0 < rho <= H4_RHO partly confirmed, otherwise not confirmed."""
    df = _active(df)
    sp = df[(df["method"] == "SP") & ~df["status"].isin(BUILD_FAIL)].copy()
    sp["build_share"] = (sp["t_enum_s"].fillna(0) + sp["t_build_s"].fillna(0)) / sp["end_to_end_s"]
    rho = sp[["n_duties", "build_share"]].corr(method="spearman").iloc[0, 1] if len(sp) > 2 else np.nan
    verdict = ("not testable" if pd.isna(rho) else "confirmed" if rho > H4_RHO
               else "partly confirmed" if rho > 0 else "not confirmed")
    return {"built_SP_runs": len(sp), "spearman_rho": rho, "median_build_share": sp["build_share"].median(),
            "verdict": verdict}


def h5_verdict(df: pd.DataFrame) -> dict:
    """H5 (Master Plan §10.9): confirmed if at least 2 instances with SP not built and 0 AF build failures."""
    df = _active(df)
    sp_fail = df[(df["method"] == "SP") & df["status"].isin(BUILD_FAIL)]["instance"].nunique()
    af_fail = df[(df["method"] == "AF") & df["status"].isin(BUILD_FAIL)]["instance"].nunique()
    ok = sp_fail >= 2 and af_fail == 0
    return {"SP_not_built": sp_fail, "AF_build_failures": af_fail,
            "verdict": "confirmed" if ok else ("partly confirmed" if sp_fail >= 2 else "not confirmed")}


def h8_features(df: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.DataFrame:
    """H8: Spearman correlation of difficulty with n, L and trips per duty. Difficulty = largest plain-model solver
    time, with unsolved or unbuilt runs counted at the time limit (censored: a rank statistic is used for that reason).
    `features` = instances/final/MANIFEST.csv (trips_per_duty_ref) or results/pilot_preview.csv
    (median_trips_per_duty)."""
    df = _active(df)
    plain = df[df["method"].isin(["AF", "SP"])].copy()
    limit = float(plain["time_limit_s"].max()) if "time_limit_s" in plain else config.GUROBI_TIME_LIMIT_S
    plain["t"] = np.where(plain["status"] == "OPTIMAL", plain["solver_time_s"], limit)
    t = plain.groupby("instance").agg(n=("n", "first"), L=("L", "first"), difficulty=("t", "max"))
    if features is not None:
        key = "name" if "name" in features else "instance"
        col = next((c for c in ("trips_per_duty_ref", "median_trips_per_duty") if c in features), None)
        if col:
            t = t.join(features.set_index(key)[col].rename("trips_per_duty"))
    return t.corr(method="spearman")[["difficulty"]].drop(index="difficulty")


def report(runs_csv: str, features_csv: str | None, out_dir: str) -> dict:
    """Write the three B13 charts, the hypothesis checks and a markdown summary to out_dir.
    Does NOT change the matplotlib backend (safe inside the notebook); each figure is closed after saving."""
    import matplotlib.pyplot as plt
    df = pd.read_csv(runs_csv)
    feats = pd.read_csv(features_csv) if features_csv and os.path.exists(features_csv) else None
    os.makedirs(out_dir, exist_ok=True)
    for fn, name in ((plot_sizes, "sizes"), (plot_build_cost, "build_cost"), (plot_status_map, "status_map")):
        fig = fn(df)
        fig.savefig(os.path.join(out_dir, f"{name}.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)
    h4, h5, h8 = h4_build_share(df), h5_verdict(df), h8_features(df, feats)
    h8.to_csv(os.path.join(out_dir, "h8_correlations.csv"))
    lines = [f"# B13 scalability - source `{runs_csv}`", "",
             f"- H4 (SP build share rises with |P|): **{h4['verdict']}** - Spearman rho {h4['spearman_rho']:.2f} over "
             f"{h4['built_SP_runs']} built SP runs; median build share {h4['median_build_share']:.0%}.",
             f"- H5 (SP unbuildable for long duties / large n, AF always built): **{h5['verdict']}** - "
             f"SP not built on {h5['SP_not_built']} instances, AF build failures on {h5['AF_build_failures']}.",
             "- H8 (difficulty grows with trips per duty more than with n): rank correlations with difficulty",
             "", h8.round(2).to_string(), "",
             "Charts: sizes.png, build_cost.png, status_map.png", ""]
    with open(os.path.join(out_dir, "B13_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return {"H4": h4, "H5": h5, "H8": h8}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join("results", "runs.csv"))
    ap.add_argument("--features", default=os.path.join("instances", "final", "MANIFEST.csv"))
    ap.add_argument("--out", default=os.path.join("results", "b13"))
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")                      # command line only: no screen needed
    r = report(a.runs, a.features, a.out)
    print(f"B13 written to {a.out}; H4 {r['H4']['verdict']}, H5 {r['H5']['verdict']}")


if __name__ == "__main__":
    main()
