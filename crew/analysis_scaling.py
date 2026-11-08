"""Scalability analysis (task B13, owner B). Master Plan §11.1 item 8 and hypotheses H4, H5, H8.

  plot_sizes(df)          |A| and |P| against n, coloured by L (log scale; pilot + final rows)
  plot_build_cost(df)     enumeration time, build time and peak memory against |P|
  plot_status_map(df)     solver time vs n: BUILD failures drawn with a different marker from TIME_LIMIT
  h4_build_share(df)      H4: does the build share of SP's end-to-end time rise with |P|?
  h5_verdict(df)          H5: >= 2 SP_not_built and 0 AF build failures
  h8_features(df)         H8: correlation of solver time with trips-per-duty vs with n
Build failures are never counted as timeouts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crew import config

# Not built = the build-failure statuses of config.py (incl. KILLED_BUILD). Plain KILLED now means
# "killed DURING the solve" (runner failure, rerun once): the model WAS built, so it is not listed here.
BUILD_FAIL = set(config.BUILD_FAILURE_STATUSES)
TIME_LIMIT = {"TIME_LIMIT", "TIME_LIMIT_NOSOL"}


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
    a2.set(xlabel="trips n", ylabel="duties |P| (x = not built, count at stop)", yscale="log",
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


def plot_status_map(df: pd.DataFrame):
    """Solver time vs n for the four MIP methods; TIME_LIMIT at the limit, build failures as x at the top."""
    import matplotlib.pyplot as plt
    df = _active(df)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    top = config.GUROBI_TIME_LIMIT_S * 1.6
    for m, g in df[df["method"].isin(["AF", "AF+S", "SP", "SP+S"])].groupby("method"):
        solved = g[g["status"] == "OPTIMAL"]
        tl = g[g["status"].isin(TIME_LIMIT)]
        bf = g[g["status"].isin(BUILD_FAIL)]
        sc = ax.scatter(solved["n"], solved["solver_time_s"].clip(lower=0.01), label=f"{m} optimal")
        c = sc.get_facecolor()[0]
        ax.scatter(tl["n"], np.full(len(tl), config.GUROBI_TIME_LIMIT_S), marker="^", color=c, label=f"{m} time limit")
        ax.scatter(bf["n"], np.full(len(bf), top), marker="x", color=c, label=f"{m} not built")
    ax.axhline(config.GUROBI_TIME_LIMIT_S, ls="--", color="grey", lw=1)
    ax.set(yscale="log", xlabel="trips n", ylabel="solver time (s)",
           title="Timeouts (triangles) vs build failures (x) - never mixed")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    return fig


def h4_build_share(df: pd.DataFrame) -> dict:
    """H4: build share of SP's end-to-end time = (t_enum + t_build) / end_to_end, against |P|.
    Confirmed if the Spearman rank correlation is positive."""
    df = _active(df)
    sp = df[(df["method"] == "SP") & ~df["status"].isin(BUILD_FAIL)].copy()
    sp["build_share"] = (sp["t_enum_s"] + sp["t_build_s"]) / sp["end_to_end_s"]
    rho = sp[["n_duties", "build_share"]].corr(method="spearman").iloc[0, 1] if len(sp) > 2 else np.nan
    return {"instances": len(sp), "spearman_rho": rho,
            "verdict": "confirmed" if rho > 0.3 else ("partly confirmed" if rho > 0 else "not confirmed")}


def h5_verdict(df: pd.DataFrame) -> dict:
    df = _active(df)
    sp_fail = df[(df["method"] == "SP") & df["status"].isin(BUILD_FAIL)]["instance"].nunique()
    af_fail = df[(df["method"] == "AF") & df["status"].isin(BUILD_FAIL)]["instance"].nunique()
    ok = sp_fail >= 2 and af_fail == 0
    return {"SP_not_built": sp_fail, "AF_build_failures": af_fail, "verdict": "confirmed" if ok else "not confirmed"}


def h8_features(df: pd.DataFrame, features: pd.DataFrame | None = None) -> pd.DataFrame:
    """H8: Spearman correlation of the largest plain-model solver time with n, L and trips per duty.
    `features` (e.g. instances/final/MANIFEST.csv) supplies trips_per_duty_ref; otherwise only n and L."""
    df = _active(df)
    plain = df[df["method"].isin(["AF", "SP"])]
    t = plain.groupby("instance").agg(n=("n", "first"), L=("L", "first"), time=("solver_time_s", "max"))
    if features is not None and "trips_per_duty_ref" in features:
        t = t.join(features.set_index("name")["trips_per_duty_ref"])
    return t.corr(method="spearman")[["time"]].drop(index="time")
