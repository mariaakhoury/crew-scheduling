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
    """Methods in rows. Status counts, time and gap averages/maxima, model sizes over built runs.
    budget_s: equal-total-budget column "solved within budget_s end-to-end" (default GUROBI_TIME_LIMIT_S)."""
    budget_s = config.GUROBI_TIME_LIMIT_S if budget_s is None else budget_s
    out, censored = [], set()
    for method in (list(methods) if methods is not None else _ordered_methods(df)):
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
