"""Model strength (task A12, owner A). Master Plan §11.1, hypothesis H1 (Theorem 3), check Q22.

How tight is each model's bound, and what does building and solving it cost? Every number is recomputed from
runs.csv (Q25); no new runs.

    python -m crew.analysis_strength --runs results/runs.csv --out results/a12

  reference_values(df)   per instance: the value gaps are measured against (proven optimum, else best known)
  strength_table(df)     per instance and model: LP gap %, root gap %, nodes, build time, solve time
  q22_check(df)          LP(AF) <= LP(SP) on every instance where both LPs exist (must hold: Theorem 3)
  plot_gap_vs_time(df)   chart 1: LP gap (or root gap) against solve time, one marker per model
  plot_time_split(df)    chart 2: stacked enumerate / build / solve time for AF and SP on every instance

Gaps:  LP gap % = 100 * (reference - LP bound) / reference;  root gap % = 100 * (reference - root bound) / reference.
The LP bound comes from the LP-AF / LP-SP runs (model.relax()). The root bound is the bound Gurobi reports after
the root node of the MIP run (after its cuts), so root gap <= LP gap is expected.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from crew.analysis_heuristic import _active, best_known

MODELS = ("AF", "SP")
LP_METHOD = {"AF": "LP-AF", "SP": "LP-SP"}
NOT_BUILT = ("COLUMN_CAP", "BUILD_LIMIT", "KILLED_BUILD", "MEM_LIMIT_BUILD")


def reference_values(df: pd.DataFrame) -> pd.DataFrame:
    """Per instance: the best known value (any MIP method, or the heuristic's schedule if that is better) and
    whether it is a proven optimum. Same rule as B12 and C9, so all gaps in the report agree."""
    df = _active(df)
    ref = best_known(df)
    if "heuristic_cost" in df.columns:
        h = df.groupby("instance")["heuristic_cost"].min()
        ref["best_value"] = pd.concat([ref["best_value"], h.reindex(ref.index)], axis=1).min(axis=1)
    ref["ref_kind"] = np.where(ref["proven"], "optimum", "best known")
    return ref[["best_value", "proven", "ref_kind"]]


def _lp_values(df: pd.DataFrame) -> pd.DataFrame:
    """LP bound per instance and model, from the LP-AF / LP-SP rows (objective of an OPTIMAL LP run)."""
    df = _active(df)
    out = {}
    for model, method in LP_METHOD.items():
        rows = df[(df["method"] == method) & (df["status"] == "OPTIMAL")]
        out[model] = rows.groupby("instance")["objective"].first()
    return pd.DataFrame(out)


def strength_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (instance, model): status, LP gap %, root gap %, nodes, build time (enumeration + build) and
    solve time. A model that was not built has build time but no gaps or solve time."""
    df = _active(df)
    ref = reference_values(df)
    lp = _lp_values(df)
    rows = []
    for model in MODELS:
        mip = df[df["method"] == model].set_index("instance")
        for inst, r in mip.iterrows():
            refv = ref.loc[inst, "best_value"] if inst in ref.index else np.nan
            lpv = lp[model].get(inst, np.nan) if model in lp else np.nan
            built = str(r["status"]) not in NOT_BUILT
            enum = float(r["t_enum_s"]) if pd.notna(r.get("t_enum_s")) else 0.0
            build = float(r["t_build_s"]) if pd.notna(r.get("t_build_s")) else 0.0
            rows.append({
                "instance": inst, "n": r.get("n"), "L": r.get("L"), "model": model, "status": r["status"],
                "reference": refv, "ref_kind": ref.loc[inst, "ref_kind"] if inst in ref.index else "n/a",
                "lp_bound": lpv,
                "lp_gap_pct": 100 * (refv - lpv) / refv if pd.notna(lpv) and refv else np.nan,
                "root_bound": r.get("root_bound") if built else np.nan,
                "root_gap_pct": (100 * (refv - r["root_bound"]) / refv
                                 if built and pd.notna(r.get("root_bound")) and refv else np.nan),
                "nodes": r.get("nodes") if built else np.nan,
                "enum_s": enum, "build_s": build,
                "solve_s": float(r["t_solve_s"]) if built and pd.notna(r.get("t_solve_s")) else np.nan,
                "built": built,
            })
    return pd.DataFrame(rows).sort_values(["n", "L", "instance", "model"]).reset_index(drop=True)


def q22_check(df: pd.DataFrame, tol: float = 1e-6) -> pd.DataFrame:
    """Theorem 3 says LP(AF) <= LP(SP). Returns one row per instance with both LPs; 'ok' must be True everywhere.
    A violation is a bug, never a finding (Master Plan Q22)."""
    lp = _lp_values(df).dropna()
    out = lp.rename(columns={"AF": "lp_AF", "SP": "lp_SP"})
    out["ok"] = out["lp_AF"] <= out["lp_SP"] + tol * np.maximum(1.0, out["lp_SP"].abs())
    return out


def plot_gap_vs_time(df: pd.DataFrame, gap: str = "lp", ax=None):
    """Chart 1: bound gap against solve time (log scale), one marker per model. Instances that hit the time limit
    sit at the right edge. gap='lp' uses the LP runs; gap='root' the MIP root bound (useful before LP runs exist)."""
    import matplotlib.pyplot as plt
    t = strength_table(df)
    col = f"{gap}_gap_pct"
    t = t[t["built"] & t[col].notna() & t["solve_s"].notna()]
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for model, marker, color in (("AF", "o", "tab:blue"), ("SP", "s", "tab:orange")):
        g = t[t["model"] == model]
        ax.scatter(g["solve_s"].clip(lower=0.01), g[col], marker=marker, color=color, alpha=0.8,
                   label=f"{model} ({len(g)} instances)")
    ax.set_xscale("log")
    ax.set_xlabel("solve time (s, log scale)")
    ax.set_ylabel(f"{'LP' if gap == 'lp' else 'root'} gap to best known (%)")
    ax.set_title(f"Bound strength vs solve time ({'LP relaxation' if gap == 'lp' else 'root node'})")
    ax.grid(color="0.9")
    ax.legend(fontsize=8)
    return ax.figure


def plot_time_split(df: pd.DataFrame, ax=None):
    """Chart 2: for every instance (sorted by n, then L), one AF bar and one SP bar, stacked into enumerate /
    build / solve time. Hatched bars: the model could not be built (only the enumeration time was spent)."""
    import matplotlib.pyplot as plt
    t = strength_table(df)
    insts = list(dict.fromkeys(t["instance"]))
    if ax is None:
        _, ax = plt.subplots(figsize=(max(6, 0.45 * len(insts) + 2), 4.5))
    x = np.arange(len(insts))
    width = 0.4
    parts = (("enum_s", "enumerate duties", "tab:purple"), ("build_s", "build model", "tab:gray"),
             ("solve_s", "solve", "tab:green"))
    for k, model in enumerate(MODELS):
        g = t[t["model"] == model].set_index("instance").reindex(insts)
        bottom = np.zeros(len(insts))
        for col, label, color in parts:
            vals = g[col].fillna(0).to_numpy(dtype=float)
            hatch = ["//" if not b else "" for b in g["built"].fillna(True)]
            bars = ax.bar(x + (k - 0.5) * width, vals, width, bottom=bottom, color=color,
                          edgecolor="black" if model == "SP" else "white", linewidth=0.4,
                          label=label if k == 0 else None)
            for bar, h in zip(bars, hatch):
                bar.set_hatch(h)
            bottom += vals
    ax.set_xticks(x, [f"{i}" for i in insts], rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("time (s)")
    ax.set_title("Where the time goes: left bar AF, right bar SP (black edge); hatched = not built")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    ax.figure.tight_layout()
    return ax.figure


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per model: instances built, median LP and root gap, median nodes, median build and solve time."""
    t = strength_table(df)
    out = []
    for model, g in t.groupby("model"):
        b = g[g["built"]]
        out.append({"model": model, "instances": len(g), "built": len(b),
                    "median_lp_gap_pct": b["lp_gap_pct"].median(), "median_root_gap_pct": b["root_gap_pct"].median(),
                    "median_nodes": b["nodes"].median(), "median_build_s": (g["enum_s"] + g["build_s"]).median(),
                    "median_solve_s": b["solve_s"].median()})
    return pd.DataFrame(out)


def report(runs_csv: str, out_dir: str) -> pd.DataFrame:
    """Write every A12 table (CSV), both charts (PNG) and a short markdown summary; return the Q22 check."""
    import matplotlib
    matplotlib.use("Agg")
    df = pd.read_csv(runs_csv)
    os.makedirs(out_dir, exist_ok=True)
    t, s, q = strength_table(df), summary(df), q22_check(df)
    t.to_csv(os.path.join(out_dir, "strength_table.csv"), index=False)
    s.to_csv(os.path.join(out_dir, "strength_summary.csv"), index=False)
    q.to_csv(os.path.join(out_dir, "q22_check.csv"))
    gap = "lp" if t["lp_gap_pct"].notna().any() else "root"
    plot_gap_vs_time(df, gap=gap).savefig(os.path.join(out_dir, "gap_vs_time.png"), dpi=150, bbox_inches="tight")
    plot_time_split(df).savefig(os.path.join(out_dir, "time_split.png"), dpi=150, bbox_inches="tight")
    lines = [f"# A12 model strength - source `{runs_csv}`", "",
             f"- Chart 1 uses the **{'LP' if gap == 'lp' else 'root-node'}** gap"
             + ("" if gap == "lp" else " (no LP-AF / LP-SP rows in this file yet)") + ".",
             f"- Q22, LP(AF) <= LP(SP): {'not testable yet (no instance with both LPs)' if q.empty else ('holds on all ' + str(len(q)) + ' instances' if q['ok'].all() else 'VIOLATED on ' + str(int((~q['ok']).sum())) + ' instances: a bug, check before reporting')}.",
             "", "## Per model", "", s.to_string(index=False), ""]
    with open(os.path.join(out_dir, "A12_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return q


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join("results", "runs.csv"))
    ap.add_argument("--out", default=os.path.join("results", "a12"))
    a = ap.parse_args(argv)
    q = report(a.runs, a.out)
    print(f"A12 written to {a.out}; Q22 instances checked: {len(q)}, all ok: {bool(q['ok'].all()) if len(q) else 'n/a'}")


if __name__ == "__main__":
    main()
