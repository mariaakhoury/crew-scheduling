"""Heuristic contribution (task B12, owner B). Master Plan §11.1 item 7, hypothesis H6, professor §2.4
("It is fine, and valuable, if the heuristic does not help on some instances. Explain why.").

Every number is recomputed from runs.csv (Q25) plus the runner's heuristic cache (greedy cost); no new runs.

    python -m crew.analysis_heuristic --runs results/runs.csv --heuristic results/heuristic --out results/b12

  heuristic_quality(df, heuristic_dir)  greedy -> local search -> best known, with exact or upper-bound gaps
  paired_effect(df)                     AF vs AF+S and SP vs SP+S per instance, with the basis of comparison
  summary_paired(df)                    medians / ranges / win-tie-loss / start acceptance per model
  h6_verdict(df)                        H6 "the MIP start helps AF more than SP" (median improvement AF > SP)
  no_help_list(df)                      instances where the start did not help, with a first reason
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

PAIRS = [("AF", "AF+S"), ("SP", "SP+S")]
TL = ("TIME_LIMIT", "TIME_LIMIT_NOSOL")
YES = ("true", "1", "yes")


def _active(df: pd.DataFrame) -> pd.DataFrame:
    if "superseded" in df.columns:
        df = df[~df["superseded"].astype(str).str.lower().isin(YES)]
    return df


def _yes(v) -> bool:
    return str(v).strip().lower() in YES


def best_known(df: pd.DataFrame) -> pd.DataFrame:
    """Per instance: best objective of any MIP method, best (largest) proven bound, and whether it is proven optimal
    (an OPTIMAL row that passed the checker)."""
    df = _active(df)
    mip = df[df["method"].isin(["AF", "AF+S", "SP", "SP+S"])]
    g = mip.groupby("instance")
    proven = g.apply(lambda r: bool(((r["status"] == "OPTIMAL") &
                                     r.get("feasible_checked", pd.Series("yes", index=r.index)).map(_yes)).any()),
                     include_groups=False)
    return pd.DataFrame({"best_value": g["objective"].min(), "best_bound": g["best_bound"].max(), "proven": proven})


def _greedy_costs(heuristic_dir: str | None) -> dict:
    """{instance: greedy_cost} from the runner's cache results/heuristic/<instance>.json."""
    out = {}
    if heuristic_dir and os.path.isdir(heuristic_dir):
        for f in os.listdir(heuristic_dir):
            if f.endswith(".json"):
                with open(os.path.join(heuristic_dir, f), encoding="utf-8-sig") as fh:
                    d = json.load(fh)
                out[d.get("instance", f[:-5])] = d.get("greedy_cost")
    return out


def heuristic_quality(df: pd.DataFrame, heuristic_dir: str | None = None) -> pd.DataFrame:
    """Greedy and local-search (LS) cost per instance, and the gap to the best known value: exact if the instance is
    proven optimal, otherwise an UPPER BOUND on the gap computed from the best proven bound.
    LS cost comes from the H rows if they exist, else from the heuristic_cost column of the +S rows."""
    df = _active(df)
    h = df[df["method"] == "H"].groupby("instance")["objective"].first()
    plus = df[df["method"].isin(["AF+S", "SP+S"])].groupby("instance")["heuristic_cost"].first()
    ls = h.combine_first(plus).rename("ls_cost")
    out = pd.DataFrame(ls)
    greedy = _greedy_costs(heuristic_dir)
    if greedy:
        out["greedy_cost"] = pd.Series(greedy)
    out = out.join(best_known(df))
    ref = np.where(out["proven"], out["best_value"], out["best_bound"])
    out["ls_gap_pct"] = 100 * (out["ls_cost"] - ref) / out["ls_cost"]
    if "greedy_cost" in out:
        out["greedy_gap_pct"] = 100 * (out["greedy_cost"] - ref) / out["greedy_cost"]
        out["ls_improved_greedy"] = out["ls_cost"] < out["greedy_cost"] - 0.01
    out["gap_kind"] = np.where(out["proven"], "exact", np.where(pd.notna(out["best_bound"]), "upper bound", "n/a"))
    out["ls_is_best_known"] = (out["ls_cost"] - out["best_value"]).abs() < 0.01
    return out


def _improvement(a: pd.Series, b: pd.Series) -> tuple[float, str]:
    """How much the +S run (b) improved on the plain run (a), in [-1, 1], and the basis used:
       both OPTIMAL           -> 1 - solver_time_S / solver_time      (basis 'time')
       plain TL, +S OPTIMAL   -> +1                                   ('solved only with start')
       plain OPTIMAL, +S TL   -> -1                                   ('solved only without start')
       both TL with gaps      -> (gap - gap_S) / gap                   ('final gap')
       anything else          -> NaN (not built, no incumbent, ...)"""
    sa, sb = str(a["status"]), str(b["status"])
    if sa == "OPTIMAL" and sb == "OPTIMAL":
        ta, tb = max(float(a["solver_time_s"]), 0.01), max(float(b["solver_time_s"]), 0.01)
        return max(-1.0, 1 - tb / ta), "time"
    if sa in TL and sb == "OPTIMAL":
        return 1.0, "solved only with start"
    if sa == "OPTIMAL" and sb in TL:
        return -1.0, "solved only without start"
    if sa == "TIME_LIMIT" and sb == "TIME_LIMIT" and pd.notna(a["gap_pct"]) and pd.notna(b["gap_pct"]) \
            and float(a["gap_pct"]) > 0:
        return max(-1.0, (float(a["gap_pct"]) - float(b["gap_pct"])) / float(a["gap_pct"])), "final gap"
    return np.nan, "not comparable"


def _wtl(imp: float, a: pd.Series, b: pd.Series, basis: str) -> str:
    """win / tie / loss of the +S run. Tie: within 10 % or 1 s on time; within 10 % on gap (Master Plan §10.10)."""
    if pd.isna(imp):
        return "n/a"
    if basis == "time" and abs(float(a["solver_time_s"]) - float(b["solver_time_s"])) <= 1.0:
        return "tie"
    if abs(imp) <= 0.10:
        return "tie"
    return "win" if imp > 0 else "loss"


def paired_effect(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (instance, model): plain vs +S on status, solver time, nodes, time to first incumbent, final gap."""
    df = _active(df)
    rows = []
    for base, plus in PAIRS:
        a_all = df[df["method"] == base].set_index("instance")
        b_all = df[df["method"] == plus].set_index("instance")
        for inst in a_all.index.intersection(b_all.index):
            a, b = a_all.loc[inst], b_all.loc[inst]
            imp, basis = _improvement(a, b)
            row = {"instance": inst, "model": base, "status": a["status"], "status_S": b["status"],
                   "start_accepted": b.get("start_accepted"), "improvement": imp, "basis": basis,
                   "wtl": _wtl(imp, a, b, basis)}
            for col in ["solver_time_s", "nodes", "t_first_incumbent_s", "gap_pct", "first_incumbent_obj"]:
                if col in df.columns:
                    row[col], row[col + "_S"] = a.get(col), b.get(col)
            fa, fb = row.get("t_first_incumbent_s"), row.get("t_first_incumbent_s_S")
            row["first_incumbent_ratio"] = (fb / fa) if pd.notna(fa) and pd.notna(fb) and fa > 0 else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def summary_paired(df: pd.DataFrame) -> pd.DataFrame:
    """Per model: comparable pairs, median and range of the improvement, win/tie/loss, start acceptance rate,
    median ratio of time to first incumbent (with / without start)."""
    p = paired_effect(df)
    out = []
    for model, g in p.groupby("model"):
        imp = g["improvement"].dropna()
        out.append({"model": model, "pairs": len(g), "comparable": len(imp),
                    "median_improvement": imp.median() if len(imp) else np.nan,
                    "min_improvement": imp.min() if len(imp) else np.nan,
                    "max_improvement": imp.max() if len(imp) else np.nan,
                    "win": int((g["wtl"] == "win").sum()), "tie": int((g["wtl"] == "tie").sum()),
                    "loss": int((g["wtl"] == "loss").sum()),
                    "start_accepted": f"{int(g['start_accepted'].map(_yes).sum())}/{int(g['start_accepted'].notna().sum())}",
                    "median_first_incumbent_ratio": g["first_incumbent_ratio"].median()})
    return pd.DataFrame(out)


def h6_verdict(df: pd.DataFrame) -> dict:
    """H6 (Master Plan §10.9): the MIP start helps AF more than SP. Confirmed if the median AF improvement is larger
    than the median SP improvement; 'not testable' if either model has no comparable pair."""
    s = summary_paired(df).set_index("model")
    af = s["median_improvement"].get("AF", np.nan)
    sp = s["median_improvement"].get("SP", np.nan)
    if pd.isna(af) or pd.isna(sp):
        verdict = "not testable (no comparable pairs for one model)"
    else:
        verdict = "confirmed" if af > sp else "not confirmed"
    return {"median_improvement_AF": af, "median_improvement_SP": sp,
            "comparable_AF": int(s["comparable"].get("AF", 0)), "comparable_SP": int(s["comparable"].get("SP", 0)),
            "verdict": verdict}


def no_help_list(df: pd.DataFrame) -> pd.DataFrame:
    """Pairs where the start did not help (tie or loss) or cannot be compared, with a first reason taken from the
    data. The final explanation is written by hand in discussion.md (professor §2.4)."""
    p = paired_effect(df)
    bad = p[p["wtl"].isin(["tie", "loss", "n/a"])].copy()

    def reason(r):
        if r["basis"] == "not comparable":
            return f"not comparable ({r['status']} / {r['status_S']})"
        if not _yes(r.get("start_accepted")):
            return "start not accepted"
        if r.get("nodes_S") in (0, 1) and r.get("nodes") in (0, 1):
            return "solved at the root node either way: the start had nothing to add"
        if r["basis"] == "time" and max(r["solver_time_s"], r["solver_time_s_S"]) < 1:
            return "solved in under 1 s either way"
        if r["basis"] == "final gap":
            return "time limit either way: the start gave an incumbent early, but the bound (not the incumbent) " \
                   "is what keeps the gap open"
        return "check the Gurobi log"
    bad["reason"] = bad.apply(reason, axis=1)
    cols = ["instance", "model", "status", "status_S", "basis", "improvement", "wtl", "reason"]
    return bad[cols].sort_values(["model", "instance"])


def plot_paired(df: pd.DataFrame, ax=None):
    """Improvement per instance (one dot per instance, one column per model); above 0 = the start helped."""
    import matplotlib.pyplot as plt
    p = paired_effect(df).dropna(subset=["improvement"])
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 4))
    rng = np.random.default_rng(0)
    styles = (("time", "o", "tab:blue"), ("final gap", "s", "tab:orange"),
              ("solved only with start", "^", "tab:green"), ("solved only without start", "v", "tab:red"))
    for k, (model, g) in enumerate(p.groupby("model")):
        for basis, marker, color in styles:          # fixed colour per basis, so the legend matches both columns
            s = g[g["basis"] == basis]
            ax.scatter(k + rng.uniform(-0.12, 0.12, len(s)), s["improvement"], marker=marker, color=color,
                       alpha=0.75, label=basis if k == 0 else None)
    ax.axhline(0, color="grey", lw=1, ls="--")
    models = sorted(p["model"].unique())
    ax.set_xticks(range(len(models)), [f"{m}+S vs {m}" for m in models])
    ax.set_ylabel("improvement from the MIP start (1 = best, 0 = none)")
    ax.set_title("Effect of the heuristic start")
    ax.legend(fontsize=7)
    return ax.figure


def report(runs_csv: str, heuristic_dir: str | None, out_dir: str) -> dict:
    """Write every B12 table (CSV), the chart (PNG) and a short markdown summary to out_dir; return the H6 verdict."""
    import matplotlib
    matplotlib.use("Agg")
    df = pd.read_csv(runs_csv)
    os.makedirs(out_dir, exist_ok=True)
    q = heuristic_quality(df, heuristic_dir)
    p, s, nh, v = paired_effect(df), summary_paired(df), no_help_list(df), h6_verdict(df)
    q.to_csv(os.path.join(out_dir, "heuristic_quality.csv"))
    p.to_csv(os.path.join(out_dir, "paired_effect.csv"), index=False)
    s.to_csv(os.path.join(out_dir, "summary_paired.csv"), index=False)
    nh.to_csv(os.path.join(out_dir, "no_help.csv"), index=False)
    plot_paired(df).savefig(os.path.join(out_dir, "paired_effect.png"), dpi=150, bbox_inches="tight")
    proven = q[q["gap_kind"] == "exact"]
    lines = [f"# B12 heuristic contribution - source `{runs_csv}`", "",
             f"- Instances with a heuristic: {len(q)}; proven optimum known for {len(proven)}.",
             f"- LS equals the best known value on {int(q['ls_is_best_known'].sum())}; median LS gap "
             f"{q['ls_gap_pct'].median():.2f} % (exact on proven instances, upper bound otherwise).",
             (f"- LS improved greedy on {int(q['ls_improved_greedy'].sum())} of {len(q)}."
              if "ls_improved_greedy" in q else "- Greedy costs not available (no heuristic cache given)."),
             f"- H6 (start helps AF more than SP): **{v['verdict']}** - median improvement AF "
             f"{v['median_improvement_AF']:.2f} ({v['comparable_AF']} pairs) vs SP "
             f"{v['median_improvement_SP']:.2f} ({v['comparable_SP']} pairs).", "",
             "## Per model", "", s.to_string(index=False), "",
             f"## Did not help / not comparable ({len(nh)} pairs)", "", nh.to_string(index=False), ""]
    with open(os.path.join(out_dir, "B12_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return v


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join("results", "runs.csv"))
    ap.add_argument("--heuristic", default=os.path.join("results", "heuristic"))
    ap.add_argument("--out", default=os.path.join("results", "b12"))
    a = ap.parse_args(argv)
    v = report(a.runs, a.heuristic, a.out)
    print(f"B12 written to {a.out}; H6: {v['verdict']}")


if __name__ == "__main__":
    main()
