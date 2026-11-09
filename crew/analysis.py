"""Required tables from results/runs.csv (tasks C7, C9). Owner: Member C (A adds the A16 profile functions here).

Shared interfaces (Master Plan §7.3):
    summary_table(df, method) -> DataFrame     one per method (H, AF, AF+S, SP, SP+S): instances in rows,
                                               an "Average" and a "Sum" row at the bottom
    comparison_table(df) -> DataFrame          methods in rows

Every number is recomputed from runs.csv (load_runs). Reporting rules (Master Plan §10.6, §10.10, §11.1):
  * solved = globally_proven == "yes" only (a full model, status OPTIMAL, certificate passed);
  * a gap is averaged only over runs WITH an incumbent; TIME_LIMIT_NOSOL is counted, never averaged as 0 or 100;
  * solver-time, #vars, #constrs and #nodes averages use built runs only (n_vars present), with the count shown;
  * a TIME_LIMIT run's time is "at least the limit": any average or sum that includes one is censored and is
    shown with "≥" by to_display(); the set of censored cells is in table.attrs["censored"];
  * superseded rows are ignored; mixed configuration hashes and duplicate live rows are refused (stale data).
Tables hold plain numbers (testable); to_display() formats them for the notebook and slides.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from crew import config
from crew.run_child import METHODS

NUMERIC = ["n", "m", "L", "W", "n_arcs", "seed", "gurobi_status_code", "objective", "best_bound", "gap_pct",
           "solver_time_s", "end_to_end_s", "t_pre_s", "t_heur_s", "t_enum_s", "t_build_s", "t_solve_s",
           "n_vars", "n_constrs", "n_nonzeros", "nodes", "n_duties", "heuristic_cost", "peak_rss_mb", "threads",
           "time_limit_s", "build_limit_s", "lp_obj", "root_bound", "obj_bound_raw", "t_first_incumbent_s",
           "first_incumbent_obj", "n_incumbents", "int_vio", "constr_vio"]
CENSORED_STATUSES = ("TIME_LIMIT", "TIME_LIMIT_NOSOL")          # stopped by the time limit: times are lower bounds
CENSORABLE = ("solver_time_s", "end_to_end_s", "nodes")
NOT_BUILT = tuple(config.BUILD_FAILURE_STATUSES)                # BUILD_LIMIT, COLUMN_CAP, MEM_LIMIT_BUILD, KILLED_BUILD
FEATURES = ["n", "m", "L", "W", "n_arcs", "class"]
RESULTS = ["status", "objective", "best_bound", "gap_pct", "solver_time_s", "end_to_end_s",
           "n_vars", "n_constrs", "nodes"]
SUM_COLUMNS = ["objective", "best_bound", "solver_time_s", "end_to_end_s", "n_vars", "n_constrs", "nodes"]
# The professor's tables cover the solution methods (Master Plan §11.1); LP-* rows feed the strength analysis (A12)
REQUIRED_METHODS = ("H", "AF", "AF+S", "SP", "SP+S")


# ------------------------------------------------------------------ loading

def load_runs(csv_path: str, expected_config_hash: Optional[str] = None,
              manifest: Optional[dict[str, str]] = None) -> pd.DataFrame:
    """Read runs.csv, keep live rows, convert numbers, and refuse stale or ambiguous data.
    expected_config_hash: e.g. config.config_hash() for the final runs; rows with another hash are stale.
    manifest: {instance name: sha256} from MANIFEST.csv (task B9); rows whose instance fingerprint differs are stale."""
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df = df[df["superseded"] != "yes"].copy()
    hashes = sorted(set(df["config_hash"]))
    if expected_config_hash is not None:
        stale = df[df["config_hash"] != expected_config_hash]
        if len(stale):
            raise ValueError(f"{len(stale)} rows have a different config_hash than expected (stale): "
                             f"{sorted(set(stale['run_id']))[:5]}")
    elif len(hashes) > 1:
        raise ValueError(f"runs.csv mixes {len(hashes)} configuration hashes; pass expected_config_hash")
    if manifest is not None:
        bad = df[[manifest.get(i) != s for i, s in zip(df["instance"], df["instance_sha256"])]]
        if len(bad):
            raise ValueError(f"{len(bad)} rows do not match MANIFEST.csv (stale instance files): "
                             f"{sorted(set(bad['instance']))[:5]}")
    dup = df[df.duplicated(["instance", "method"], keep=False)]
    if len(dup):
        raise ValueError(f"duplicate live rows for {sorted(set(zip(dup['instance'], dup['method'])))[:5]}")
    for col in NUMERIC:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")   # "" -> NaN; one dtype everywhere
    return df


def _ordered_methods(df: pd.DataFrame) -> list[str]:
    order = list(METHODS)
    return sorted(set(df["method"]), key=lambda m: (order.index(m) if m in order else len(order), m))


# ------------------------------------------------------------------ aggregation helpers

def _censored_mask(rows: pd.DataFrame) -> pd.Series:
    return rows["status"].isin(CENSORED_STATUSES)


def _built(rows: pd.DataFrame) -> pd.DataFrame:
    return rows[rows["n_vars"].notna()]


def _mean(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.mean()) if len(s) else np.nan


def _max(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.max()) if len(s) else np.nan


def _is_censored(rows: pd.DataFrame, col: str) -> bool:
    """An aggregate of `col` over `rows` is censored if it includes a time-limit run with a value in `col`."""
    return col in CENSORABLE and bool((_censored_mask(rows) & rows[col].notna()).any())


# ------------------------------------------------------------------ summary table (one per method)

def summary_table(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Instances in rows (by n, then L, then name); features + results; "Average" and "Sum" rows at the bottom."""
    rows = df[df["method"] == method].sort_values(["n", "L", "instance"])
    if rows.empty:
        raise ValueError(f"no rows for method {method!r}")
    features = [c for c in FEATURES if c != "class" or (rows["class"] != "").any()]
    table = rows.set_index("instance")[features + RESULTS].copy()
    table.index.name = f"{method}: instance"
    text_cols = [c for c in table.columns if c in ("status", "class")]
    # numeric columns as float64 and text columns as object BEFORE adding the Average/Sum rows, so no column ever
    # changes dtype on assignment (pandas 2.x warns about that and pandas 3 forbids it)
    table = table.astype({c: ("object" if c in text_cols else "float64") for c in table.columns})

    avg = {c: _mean(rows[c]) for c in ["n", "n_arcs", "objective", "best_bound", "gap_pct", "end_to_end_s"]}
    built = _built(rows)
    avg.update({c: _mean(built[c]) for c in ["solver_time_s", "n_vars", "n_constrs", "nodes"]})
    total = {c: (rows[c].sum(min_count=1) if c in ("objective", "best_bound", "end_to_end_s")
                 else built[c].sum(min_count=1)) for c in SUM_COLUMNS}
    total["n"] = rows["n"].sum()
    table.loc["Average"] = pd.Series(avg)
    table.loc["Sum"] = pd.Series(total)
    table.loc[["Average", "Sum"], "status"] = ""

    censored = {(label, c) for label in ("Average", "Sum") for c in CENSORABLE if _is_censored(rows, c)}
    table.attrs["censored"] = censored
    table.attrs["n_built"] = len(built)
    return table


# ------------------------------------------------------------------ comparison table (methods in rows)

def comparison_table(df: pd.DataFrame, methods: Optional[Iterable[str]] = None,
                     budget_s: Optional[float] = None) -> pd.DataFrame:
    """Methods in rows (default: the required H, AF, AF+S, SP, SP+S; LP-* only if listed in `methods`).
    Status counts, time and gap averages/maxima, model sizes over built runs.
    budget_s: equal-total-budget column "solved within budget_s end-to-end" (default GUROBI_TIME_LIMIT_S)."""
    budget_s = config.GUROBI_TIME_LIMIT_S if budget_s is None else budget_s
    out, censored = [], set()
    if methods is None:                                            # default: the required methods present in df
        methods = [m for m in _ordered_methods(df) if m in REQUIRED_METHODS]
    for method in methods:
        rows = df[df["method"] == method]
        built = _built(rows)
        proven = rows["globally_proven"] == "yes"
        status = rows["status"]
        known = proven | status.isin(("TIME_LIMIT", "TIME_LIMIT_NOSOL", "HEURISTIC") + NOT_BUILT)
        rec = {
            "method": method, "runs": len(rows),
            "OPTIMAL (proven)": int(proven.sum()),
            "TIME_LIMIT": int((status == "TIME_LIMIT").sum()),
            "TIME_LIMIT_NOSOL": int((status == "TIME_LIMIT_NOSOL").sum()),
            "not built": int(status.isin(NOT_BUILT).sum()),
            "heuristic only": int((status == "HEURISTIC").sum()),
            "other (see rows)": int((~known).sum()),         # ERROR, CHECK_FAILED, MEM_LIMIT_SOLVE, KILLED, ...
            f"proven within {budget_s:g} s end-to-end": int((proven & (rows["end_to_end_s"] <= budget_s)).sum()),
            "avg solver time (s)": _mean(built["solver_time_s"]), "max solver time (s)": _max(built["solver_time_s"]),
            "avg end-to-end (s)": _mean(rows["end_to_end_s"]), "max end-to-end (s)": _max(rows["end_to_end_s"]),
            "avg gap %": _mean(rows["gap_pct"]), "max gap %": _max(rows["gap_pct"]),
            "avg #vars": _mean(built["n_vars"]), "avg #constrs": _mean(built["n_constrs"]),
            "avg #nodes": _mean(built["nodes"]), "built runs": len(built),
        }
        out.append(rec)
        for col, src in (("avg solver time (s)", "solver_time_s"), ("max solver time (s)", "solver_time_s"),
                         ("avg end-to-end (s)", "end_to_end_s"), ("max end-to-end (s)", "end_to_end_s"),
                         ("avg #nodes", "nodes")):
            if _is_censored(rows, src):
                censored.add((method, col))
    table = pd.DataFrame(out).set_index("method")
    table.attrs["censored"] = censored
    return table


# ------------------------------------------------------------------ display

AGGREGATE_ROWS = ("Average", "Sum")


def _is_time(col) -> bool:
    return str(col).endswith("_s") or "(s)" in str(col)


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v))


def to_display(table: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    """Strings for the notebook/slides. Uniform per column: a column whose data rows are all whole numbers is shown
    without decimals (aggregates keep decimals only when not whole); times and every other column use `decimals`.
    Missing values show '–'; censored aggregates show '≥ x'."""
    censored = table.attrs.get("censored", set())
    data_rows = [r for r in table.index if r not in AGGREGATE_ROWS]
    shown = table.astype(object).copy()
    for c in table.columns:
        values = [table.at[r, c] for r in data_rows if not _is_missing(table.at[r, c])]
        numeric = [v for v in values if not isinstance(v, str)]
        whole_column = not _is_time(c) and all(float(v).is_integer() for v in numeric)
        for r in table.index:
            v = table.at[r, c]
            if isinstance(v, str):
                text = v
            elif _is_missing(v):
                text = "–"
            elif whole_column and (r not in AGGREGATE_ROWS or float(v).is_integer()):
                text = f"{int(round(float(v))):,}"
            else:
                text = f"{float(v):,.{decimals}f}"
            shown.at[r, c] = ("≥ " + text) if (r, c) in censored and text != "–" else text
    return shown


# ================================================================== C9: charts (Master Plan §11.1)
# Static matplotlib figures for the notebook and slides; each function returns a Figure (no pyplot state).
# Colour roles follow the reference data-viz palette, light mode: the MODEL is the identity (AF blue, SP orange:
# categorical slots 1-2, documented as passing the all-pairs CVD and normal-vision floors); the WARM START is a
# secondary encoding (hollow marker), so four methods need only two hues; run outcomes are marker SHAPES
# (o proven, ^ time limit = censored, x not built), never colour. Ordered L values use one blue ramp,
# steps 250/450/650 (no lighter than 250, the ordinal floor on the light surface).

_INK = {"surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7"}
MODEL_COLOR = {"AF": "#2a78d6", "SP": "#eb6834"}
ORDINAL_BLUE = ("#86b6ef", "#2a78d6", "#104281")
MIP_METHODS = ("AF", "AF+S", "SP", "SP+S")
CLASS_ORDER = ("EASY", "MEDIUM", "HARD", "TIME_LIMIT")
_FONT_PREFERENCE = ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans")


def _font() -> dict:
    """The first installed system sans from the preference list (no missing-font warnings), as rc settings."""
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    family = next((f for f in _FONT_PREFERENCE if f in installed), "DejaVu Sans")
    return {"font.family": [family], "font.size": 9}


def _figure(ncols: int = 1, width: float = 7.0, height: float = 4.0, sharey: bool = False):
    from matplotlib.figure import Figure
    fig = Figure(figsize=(width, height), dpi=150, facecolor=_INK["surface"], layout="constrained")
    axes = fig.subplots(1, ncols, sharey=sharey, squeeze=False)[0]
    for ax in axes:
        ax.set_facecolor(_INK["surface"])
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(_INK["axis"])
        ax.tick_params(colors=_INK["axis"], labelcolor=_INK["secondary"], labelsize=8)
        ax.grid(True, axis="y", which="major", color=_INK["grid"], linewidth=0.6)
        ax.set_axisbelow(True)
    return fig, axes


def _n_axis(ax, ns) -> None:
    """Log-scale n axis with plain-number ticks at the n values present (50, 100, 200 ... not 6 x 10^1)."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(sorted({float(v) for v in ns if pd.notna(v)})))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def _labels(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", color=_INK["primary"], fontsize=10, fontweight="bold")
    ax.set_xlabel(xlabel, color=_INK["secondary"])
    ax.set_ylabel(ylabel, color=_INK["secondary"])


def _method_style(method: str) -> dict:
    """AF / SP -> hue; '+S' (warm start) -> hollow marker of the same hue."""
    color = MODEL_COLOR[method.split("+")[0]]
    face = _INK["surface"] if method.endswith("+S") else color
    return {"color": color, "markerfacecolor": face, "markeredgecolor": color, "markeredgewidth": 1.4}


def _legend(ax, handles, **kw) -> None:
    ax.legend(handles=handles, frameon=False, fontsize=8, labelcolor=_INK["secondary"], **kw)


def _method_handles(methods) -> list:
    from matplotlib.lines import Line2D
    return [Line2D([], [], linestyle="none", marker="o", markersize=7, label=m, **_method_style(m)) for m in methods]


def _shape_handles(entries) -> list:
    from matplotlib.lines import Line2D
    return [Line2D([], [], linestyle="none", marker=mk, markersize=7, color=_INK["muted"], label=lab)
            for mk, lab in entries]


def best_known(df: pd.DataFrame) -> pd.DataFrame:
    """Per instance: best known solution value (min over checked MIP incumbents AND the heuristic schedule, which the
    runner also checks), whether the optimum is proven, the best valid lower bound (max of MIP best bounds and LP
    relaxation values), and the heuristic cost. Index = instance."""
    mip = df[df["method"].isin(MIP_METHODS)]
    feasible = mip[mip["feasible_checked"] == "yes"]
    lp = df[df["method"].str.startswith("LP-")]
    bounds = pd.concat([mip[["instance", "best_bound"]].rename(columns={"best_bound": "b"}),
                        lp[["instance", "lp_obj"]].rename(columns={"lp_obj": "b"})])
    first = df.groupby("instance")[["n", "m", "L"]].first()
    heuristic = df.groupby("instance")["heuristic_cost"].min()
    best_mip = feasible.groupby("instance")["objective"].min()
    out = first.assign(
        best=pd.concat([best_mip, heuristic], axis=1).min(axis=1),   # the heuristic schedule is a checked solution too
        proven=(mip.assign(p=mip["globally_proven"] == "yes").groupby("instance")["p"].any()),
        bound=bounds.groupby("instance")["b"].max(),
        heuristic=heuristic,
    )
    out["proven"] = out["proven"].astype("boolean").fillna(False).astype(bool)
    return out


def chart_time_vs_n(df: pd.DataFrame, time_col: str = "solver_time_s"):
    """Solver time (log) against n for the four MIP methods. Time-limit runs are drawn as ^ at their stopped time
    (true time is at least that); runs whose model was not built are drawn as x in a band above the limit."""
    from matplotlib import rc_context
    rows = df[df["method"].isin(MIP_METHODS)]
    if rows.empty:
        raise ValueError("no MIP rows to chart")
    limit = float(rows["time_limit_s"].max())
    band = limit * 4
    shift = {"AF": 0.93, "AF+S": 0.97, "SP": 1.03, "SP+S": 1.07}        # side by side on the log x-axis
    methods = [m for m in MIP_METHODS if m in set(rows["method"])]
    counts = {"solved": 0, "time_limit": 0, "not_built": 0, "other": 0}
    with rc_context(_font()):
        fig, (ax,) = _figure()
        for method in methods:
            r = rows[rows["method"] == method]
            x = r["n"] * shift[method]
            solved = r["globally_proven"] == "yes"
            timed = r["status"].isin(CENSORED_STATUSES)
            unbuilt = r["status"].isin(NOT_BUILT)
            st = _method_style(method)
            ax.plot(x[solved], r.loc[solved, time_col], linestyle="none", marker="o", markersize=6, **st)
            ax.plot(x[timed], r.loc[timed, time_col], linestyle="none", marker="^", markersize=7, **st)
            ax.plot(x[unbuilt], [band] * int(unbuilt.sum()), linestyle="none", marker="x", markersize=7,
                    color=st["color"], markeredgewidth=1.6)
            counts["solved"] += int(solved.sum())
            counts["time_limit"] += int(timed.sum())
            counts["not_built"] += int(unbuilt.sum())
            counts["other"] += int((~(solved | timed | unbuilt)).sum())
        _n_axis(ax, rows["n"])
        ax.set_yscale("log")
        ax.set_ylim(top=band * 2.2)
        x0 = ax.get_xlim()[0]
        ax.axhline(limit, color=_INK["axis"], linewidth=1)
        ax.text(x0, limit * 1.12, f" time limit {limit:g} s", color=_INK["muted"], fontsize=8)
        ax.text(x0, band * 1.15, " not built", color=_INK["muted"], fontsize=8)
        which = "Solver" if time_col == "solver_time_s" else "End-to-end"
        _labels(ax, f"{which} time grows with n; SP is fast when it can be built",
                "trips n (log scale)", "seconds (log scale)")
        _legend(ax, _method_handles(methods)
                + _shape_handles([("o", "proven optimal"), ("^", "time limit (≥)"), ("x", "not built")]),
                loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0)
    fig.crew_counts = counts
    return fig


def _class_series(df: pd.DataFrame, classes=None) -> pd.Series:
    if classes is None:
        s = df.groupby("instance")["class"].first()
    elif isinstance(classes, pd.DataFrame):
        s = classes.set_index("instance")["class"]
    else:
        s = pd.Series(classes)
    s = s[s.notna() & (s.astype(str) != "")]
    if s.empty:
        raise ValueError("no instance classes: pass classes= (e.g. results/pilot_classes.csv) or fill runs.csv 'class'")
    return s


def chart_gap_by_class(df: pd.DataFrame, classes=None):
    """Final MIP gap % of every run with an incumbent, by instance class and method. Runs without an incumbent are
    counted under the class label, never plotted as 0 % or 100 %."""
    from matplotlib import rc_context
    cls = _class_series(df, classes)
    rows = df[df["method"].isin(MIP_METHODS)].assign(cls=lambda d: d["instance"].map(cls)).dropna(subset=["cls"])
    if rows.empty:
        raise ValueError("no MIP rows for the classified instances")
    order = [c for c in CLASS_ORDER if c in set(rows["cls"])] + sorted(set(rows["cls"]) - set(CLASS_ORDER))
    offset = {"AF": -0.27, "AF+S": -0.09, "SP": 0.09, "SP+S": 0.27}
    methods = [m for m in MIP_METHODS if m in set(rows["method"])]
    with rc_context(_font()):
        fig, (ax,) = _figure()
        for method in methods:
            r = rows[(rows["method"] == method) & rows["gap_pct"].notna()]
            ax.plot([order.index(c) + offset[method] for c in r["cls"]], r["gap_pct"], linestyle="none",
                    marker="o", markersize=6, **_method_style(method))
        ticks = []
        for c in order:
            g = rows[rows["cls"] == c]
            no_inc = int((g["status"] == "TIME_LIMIT_NOSOL").sum())
            not_built = int(g["status"].isin(NOT_BUILT).sum())
            k = g["instance"].nunique()
            extra = "".join([f"\n{no_inc} runs without incumbent" if no_inc else "",
                             f"\n{not_built} runs not built" if not_built else ""])
            ticks.append(f"{c}\n{k} instance{'' if k == 1 else 's'}{extra}")
        ax.set_xticks(range(len(order)), ticks)
        ax.set_ylim(bottom=0)
        _labels(ax, "Final gap by instance class (runs with an incumbent)", "", "gap % = (value − bound) / value")
        _legend(ax, _method_handles(methods), loc="upper left")
    return fig


def chart_lp_vs_optimum(df: pd.DataFrame):
    """LP relaxation value as % of the proven optimum, LP-AF vs LP-SP (the visual form of Theorem 3).
    Only instances with a proven optimum are shown."""
    from matplotlib import rc_context
    lp = df[df["method"].isin(("LP-AF", "LP-SP")) & df["lp_obj"].notna()]
    if lp.empty:
        raise ValueError("no LP-AF / LP-SP rows: run those methods first")
    bk = best_known(df)
    opt = bk.loc[bk["proven"], "best"]
    inst = sorted(set(lp["instance"]) & set(opt.index), key=lambda i: (bk.at[i, "n"], i))
    if not inst:
        raise ValueError("no instance has both an LP value and a proven optimum")
    with rc_context(_font()):
        fig, (ax,) = _figure()
        for method in ("LP-AF", "LP-SP"):
            r = lp[lp["method"] == method].set_index("instance")
            xs = [k for k, i in enumerate(inst) if i in r.index]
            ys = [100 * r.at[inst[k], "lp_obj"] / opt[inst[k]] for k in xs]
            ax.plot(xs, ys, linestyle="none", marker="o", markersize=6, label=method,
                    **_method_style(method.replace("LP-", "")))
        ax.axhline(100, color=_INK["axis"], linewidth=1)
        ax.set_xticks(range(len(inst)), [f"n={bk.at[i, 'n']:.0f}" for i in inst], rotation=60, ha="right")
        _labels(ax, "LP relaxation as % of the optimum: SP's bound is much tighter", "", "LP value / optimum (%)")
        _legend(ax, ax.get_legend_handles_labels()[0], loc="lower right")
    return fig


def chart_duties(df: pd.DataFrame):
    """Number of legal duties |P| (log) against n, one line per L, one panel per m. Points where enumeration
    stopped (cap or build limit) are lower bounds (^)."""
    from matplotlib import rc_context
    from matplotlib.lines import Line2D
    sp = df[df["method"].isin(("SP", "SP+S", "LP-SP")) & df["n_duties"].notna()]
    if sp.empty:
        raise ValueError("no set-partitioning rows with a duty count")
    per = (sp.assign(lower=sp["enumeration_complete"] != "yes")
             .groupby("instance").agg(n=("n", "first"), m=("m", "first"), L=("L", "first"),
                                      duties=("n_duties", "max"), lower=("lower", "all")))
    ms, Ls = sorted(per["m"].unique()), sorted(per["L"].unique())
    if len(Ls) > len(ORDINAL_BLUE):
        raise ValueError(f"{len(Ls)} L values: more than {len(ORDINAL_BLUE)} ordered steps; facet by L instead")
    steps = [ORDINAL_BLUE[-1]] if len(Ls) == 1 else (
        [ORDINAL_BLUE[0], ORDINAL_BLUE[-1]] if len(Ls) == 2 else list(ORDINAL_BLUE))
    colors = dict(zip(Ls, steps))
    with rc_context(_font()):
        fig, axes = _figure(ncols=len(ms), width=3.6 * len(ms) + 1.4, sharey=True)
        for ax, m in zip(axes, ms):
            for L in Ls:
                r = per[(per["m"] == m) & (per["L"] == L)].sort_values("n")
                if r.empty:
                    continue
                c = colors[L]
                done, low = r[~r["lower"]], r[r["lower"]]
                ax.plot(done["n"], done["duties"], color=c, linewidth=1.5)      # lower bounds are not joined
                ax.plot(done["n"], done["duties"], linestyle="none", marker="o", markersize=6, color=c,
                        markeredgecolor=_INK["surface"], markeredgewidth=1)
                ax.plot(low["n"], low["duties"], linestyle="none", marker="^", markersize=7, color=c,
                        markerfacecolor=_INK["surface"], markeredgewidth=1.4)
            _n_axis(ax, per["n"])
            ax.set_yscale("log")
            ax.axhline(config.COLUMN_CAP, color=_INK["axis"], linewidth=1)
            ax.text(ax.get_xlim()[0], config.COLUMN_CAP * 1.25, f" column cap {config.COLUMN_CAP:,}",
                    color=_INK["muted"], fontsize=8)
            _labels(ax, f"m = {m:.0f} terminals", "trips n (log scale)",
                    "legal duties |P| (log scale)" if m == ms[0] else "")
        fig.suptitle("Longer duty limits L multiply the number of duties SP must list", x=0.01, ha="left",
                     color=_INK["primary"], fontsize=10, fontweight="bold")
        handles = [Line2D([], [], color=colors[L], linewidth=1.5, label=f"L = {L:.0f} min") for L in Ls]
        _legend(axes[-1], handles + _shape_handles([("o", "complete count"), ("^", "stopped early (≥)")]),
                loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0)
    return fig


def chart_heuristic_gap(df: pd.DataFrame):
    """Heuristic cost above the optimum, by n. Proven optimum: a dot. Otherwise the true gap lies between the gap
    to the best incumbent and the gap to the best lower bound: drawn as a range with a hollow dot at the low end."""
    from matplotlib import rc_context
    from matplotlib.lines import Line2D
    bk = best_known(df).dropna(subset=["heuristic", "best"])
    if bk.empty:
        raise ValueError("no instance has both a heuristic cost and a checked MIP incumbent")
    lo = 100 * (bk["heuristic"] - bk["best"]) / bk["best"]
    hi = 100 * (bk["heuristic"] - bk["bound"]) / bk["bound"]
    color = MODEL_COLOR["AF"]
    proven, open_ = bk["proven"], ~bk["proven"]
    with rc_context(_font()):
        fig, (ax,) = _figure()
        for i in bk.index[open_]:
            if pd.notna(hi[i]):
                ax.plot([bk.at[i, "n"]] * 2, [lo[i], hi[i]], color=color, linewidth=1.5, alpha=0.6)
        ax.plot(bk.loc[proven, "n"], lo[proven], linestyle="none", marker="o", markersize=6, color=color,
                markeredgecolor=_INK["surface"], markeredgewidth=1)
        ax.plot(bk.loc[open_, "n"], lo[open_], linestyle="none", marker="o", markersize=6, color=color,
                markerfacecolor=_INK["surface"], markeredgewidth=1.4)
        ax.axhline(0, color=_INK["axis"], linewidth=1)
        _n_axis(ax, bk["n"])
        _labels(ax, "How far greedy + local search is from the optimum", "trips n (log scale)",
                "heuristic cost above optimum (%)")
        _legend(ax, [Line2D([], [], linestyle="none", marker="o", markersize=6, color=color,
                            label="vs proven optimum"),
                     Line2D([], [], color=color, linewidth=1.5, alpha=0.6, marker="o", markersize=6,
                            markerfacecolor=_INK["surface"], label="not proven: true gap lies in this range")],
                loc="upper left")
    fig.crew_points = {"proven": int(proven.sum()), "open": int(open_.sum())}
    return fig


def save_charts(df: pd.DataFrame, outdir: str, classes=None) -> dict[str, str]:
    """Render every chart the data supports to PNG in outdir. Returns {name: path or 'skipped: reason'}."""
    import os
    os.makedirs(outdir, exist_ok=True)
    makers = {"time_vs_n": lambda: chart_time_vs_n(df), "gap_by_class": lambda: chart_gap_by_class(df, classes),
              "lp_vs_optimum": lambda: chart_lp_vs_optimum(df), "duties_vs_n_L": lambda: chart_duties(df),
              "heuristic_gap": lambda: chart_heuristic_gap(df)}
    out = {}
    for name, make in makers.items():
        try:
            fig = make()
        except ValueError as exc:
            out[name] = f"skipped: {exc}"
            continue
        path = os.path.join(outdir, name + ".png")
        fig.savefig(path, facecolor=_INK["surface"])
        out[name] = path
    return out
