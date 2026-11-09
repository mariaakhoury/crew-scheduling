"""Difficulty classes and the written selection rule (tasks B6 and B16, owner B). Master Plan §10.3.

Usage
  python -m pilot.classify --runs results/pilot.csv   --out instances/final/SELECTION.md --stage pilot
  python -m pilot.classify --runs results/confirm.csv --out instances/final/SELECTION.md --stage confirm
  python -m pilot.classify --runs results/runs.csv    --stage final        # final classes (Fri 13)

Classes are mutually exclusive and computed from the PLAIN AF and SP runs only; the first rule that applies wins:
  1. TIME_LIMIT : at least one plain model was fully built and ended TIME_LIMIT or TIME_LIMIT_NOSOL
  2. HARD       : the largest solver time of a built plain model > config.HARD_THRESHOLD_S (24 s)
  3. MEDIUM     : both OPTIMAL and solver times differ by a factor >= 10 (floored at 0.1 s),
                  or only one model could be built (labelled as a BUILD result, not a speed difference)
  4. EASY       : everything else
Extra flag (overlaps the classes): SP_not_built. A build failure is never counted as a time-limit case.
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crew import config  # noqa: E402

PLAIN = ("AF", "SP")
TIME_LIMIT_STATUSES = ("TIME_LIMIT", "TIME_LIMIT_NOSOL")
TARGETS = {"EASY": 4, "MEDIUM": 5, "HARD": 5, "TIME_LIMIT": 6}      # selection targets, not results
MIN_TIME_LIMIT = 3
CLASS_ORDER = ["EASY", "MEDIUM", "HARD", "TIME_LIMIT", "NOT_BUILT", "UNUSABLE"]
MAX_CONFIRM_FILES = 24      # Master Plan §10.1: confirmation runs on at most 24 files (48 runs, <= 3.2 h)
SPARES_PER_CLASS = 2


def md_table(df: pd.DataFrame) -> str:
    """Markdown table without the optional 'tabulate' package (not in requirements.txt)."""
    def fmt(v):
        if isinstance(v, float):
            return "" if pd.isna(v) else f"{v:g}"
        return "" if v is None else str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def load_runs(path: str) -> pd.DataFrame:
    """Read a runs CSV and drop superseded rows (they are kept in the file, never used)."""
    df = pd.read_csv(path)
    if "superseded" in df.columns:
        df = df[~df["superseded"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])]
    return df


UNUSABLE = ("ERROR", "NUMERIC", "SUBOPTIMAL", "INFEASIBLE", "INF_OR_UNBD", "CHECK_FAILED")


def is_built(row) -> bool:
    """A model counts as built unless its status is a build failure (config.BUILD_FAILURE_STATUSES, which
    includes KILLED_BUILD). The runner reports a kill during the solve as KILLED: built, but a runner failure
    (the instance becomes UNUSABLE until the run is repeated). killed_phase is checked too for older rows."""
    status = str(row["status"])
    if status in config.BUILD_FAILURE_STATUSES:
        return False
    if status == "KILLED":
        return str(row.get("killed_phase", "")) == "solve"
    return True


def classify_instance(rows: pd.DataFrame) -> dict:
    """rows: the plain AF and SP rows of ONE instance. Returns the class, the reason and the flag.
    An instance whose plain run ERRORED (e.g. licence size limit), failed the checker or was killed during
    the solve gets class UNUSABLE: it is never classified as EASY by accident and never selected."""
    by = {r["method"]: r for _, r in rows.iterrows() if r["method"] in PLAIN}
    bad = [f"{m}:{r['status']}" for m, r in by.items()
           if str(r["status"]) in UNUSABLE or (str(r["status"]) == "KILLED" and is_built(r))]
    if bad or len(by) < len(PLAIN):
        why = ", ".join(bad) if bad else f"missing plain rows (have {sorted(by)})"
        return {"class": "UNUSABLE", "reason": f"rerun or investigate: {why}", "SP_not_built": False}
    built = {m: r for m, r in by.items() if is_built(r)}
    sp = by.get("SP")
    sp_not_built = sp is not None and not is_built(sp)
    if not built:                         # neither plain model was built: no speed information at all
        why = ", ".join(f"{m}:{r['status']}" for m, r in by.items())
        return {"class": "NOT_BUILT", "reason": f"neither model built ({why}); recheck at the final limits",
                "SP_not_built": sp_not_built}

    if any(str(r["status"]) in TIME_LIMIT_STATUSES for r in built.values()):
        who = [m for m, r in built.items() if str(r["status"]) in TIME_LIMIT_STATUSES]
        return {"class": "TIME_LIMIT", "reason": f"{'/'.join(who)} hit the time limit", "SP_not_built": sp_not_built}

    times = {m: float(r["solver_time_s"]) for m, r in built.items() if pd.notna(r["solver_time_s"])}
    if times and max(times.values()) > config.HARD_THRESHOLD_S:
        return {"class": "HARD", "reason": f"max solver time {max(times.values()):.1f} s > {config.HARD_THRESHOLD_S} s",
                "SP_not_built": sp_not_built}

    if len(built) == 1 and len(by) == 2:
        only = next(iter(built))
        return {"class": "MEDIUM", "reason": f"BUILD: only {only} could be built", "SP_not_built": sp_not_built}

    if len(built) == 2 and all(str(r["status"]) == "OPTIMAL" for r in built.values()):
        t = [max(times.get(m, 0.0), 0.1) for m in PLAIN]
        ratio = max(t) / min(t)
        if ratio >= 10:
            faster = PLAIN[t.index(min(t))]
            return {"class": "MEDIUM", "reason": f"{faster} faster by x{ratio:.1f}", "SP_not_built": sp_not_built}

    return {"class": "EASY", "reason": "both fast / similar", "SP_not_built": sp_not_built}


def classify_all(df: pd.DataFrame) -> pd.DataFrame:
    """One row per instance with its class, reason, flag and the features used by the selection rule."""
    out = []
    for name, rows in df.groupby("instance"):
        c = classify_instance(rows)
        first = rows.iloc[0]
        c.update(instance=name, n=first.get("n"), m=first.get("m"), L=first.get("L"), W=first.get("W"),
                 n_arcs=first.get("n_arcs"),
                 n_duties=rows.loc[rows["method"] == "SP", "n_duties"].max() if "n_duties" in rows else None)
        for m in PLAIN:
            r = rows[rows["method"] == m]
            c[f"{m}_status"] = r["status"].iloc[0] if len(r) else None
            c[f"{m}_time"] = r["solver_time_s"].iloc[0] if len(r) else None
        out.append(c)
    return pd.DataFrame(out)


def select(classes: pd.DataFrame) -> pd.DataFrame:
    """The written selection rule: within each class, take candidates in increasing n, then L, then name
    (configuration id), up to the target. Missing TIME_LIMIT places are filled with HARD instances."""
    ordered = classes.sort_values(["n", "L", "instance"])
    chosen = []
    shortfall = 0
    for cls in ["TIME_LIMIT", "HARD", "MEDIUM", "EASY"]:
        pool = ordered[ordered["class"] == cls]
        want = TARGETS[cls] + (shortfall if cls == "HARD" else 0)
        take = pool.head(want)
        if cls == "TIME_LIMIT":
            shortfall = max(0, TARGETS[cls] - len(take))
        chosen.append(take)
    sel = pd.concat(chosen)
    return sel.sort_values(["n", "L", "instance"])


def confirmation_candidates(classes: pd.DataFrame) -> pd.DataFrame:
    """Pilot stage (Master Plan §10.1 B2, §10.3 step 2): the files to rerun with plain AF and SP at the FINAL limits.
    = every preliminary HARD, TIME_LIMIT and NOT_BUILT instance (30 s cannot tell hard from time-limit, and a model
    not built in 30 s may build in 120 s) + up to SPARES_PER_CLASS spares of EASY and MEDIUM, all in the rule order
    (n, L, configuration id). If more than MAX_CONFIRM_FILES qualify, the spares are kept and the rest is cut in the
    same order. UNUSABLE instances are never candidates (rerun the pilot row first)."""
    ordered = classes.sort_values(["n", "L", "instance"])
    spares = pd.concat([ordered[ordered["class"] == c].head(SPARES_PER_CLASS) for c in ("EASY", "MEDIUM")])
    main = ordered[ordered["class"].isin(["HARD", "TIME_LIMIT", "NOT_BUILT"])]
    main = main.head(max(0, MAX_CONFIRM_FILES - len(spares)))
    out = pd.concat([spares, main]).sort_values(["n", "L", "instance"])
    out["why_candidate"] = out["class"].map(lambda c: "spare" if c in ("EASY", "MEDIUM") else "recheck at 120 s")
    return out


def supply_report(classes: pd.DataFrame) -> list[str]:
    """Compare the class supply with the selection targets, so a shortage is visible BEFORE the freeze."""
    have = classes["class"].value_counts()
    lines = ["| class | target | in this population |", "|---|---|---|"]
    for c in ["EASY", "MEDIUM", "HARD", "TIME_LIMIT"]:
        lines.append(f"| {c} | {TARGETS[c]} | {int(have.get(c, 0))} |")
    return lines


def write_candidates_md(classes: pd.DataFrame, cand: pd.DataFrame, path: str, runs_path: str) -> None:
    """Pilot-stage SELECTION.md: the rule, the class supply, the confirmation candidates, the whole population."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    counts = {k: int(v) for k, v in classes["class"].value_counts().reindex(CLASS_ORDER, fill_value=0).items()}
    lines = [
        "# Benchmark selection (Group M) - pilot stage", "",
        f"Source rows: `{runs_path}` (pilot limits). Written by `pilot/classify.py`. Pilot classes are PRELIMINARY:",
        "at the pilot limit a hard instance and a time-limit instance look the same (Master Plan §10.3 step 1).", "",
        "## Rule (fixed before the confirmation runs)",
        "1. Classes from the plain AF and SP runs, first rule wins: NOT_BUILT (neither model built) -> TIME_LIMIT",
        f"   (a built plain model hit the limit) -> HARD (max solver time > {config.HARD_THRESHOLD_S} s at the final",
        "   limits) -> MEDIUM (both optimal and times differ x10, or only one model built) -> EASY.",
        "2. Confirmation candidates = every HARD, TIME_LIMIT and NOT_BUILT instance + "
        f"{SPARES_PER_CLASS} spares per EASY/MEDIUM class, at most {MAX_CONFIRM_FILES} files, in increasing n, L, id.",
        "3. Final selection (after the confirmation runs): within each class take candidates in increasing n, then L,",
        f"   then configuration id, up to the targets {TARGETS}; missing TIME_LIMIT places are filled with HARD.",
        "4. No instance is hand-picked, replaced or removed after the final runs start.", "",
        f"## Preliminary classes: {counts}", "", *supply_report(classes), "",
    ]
    short = [c for c in ("EASY", "MEDIUM") if int((classes["class"] == c).sum()) < TARGETS[c]]
    if short:
        lines.append(f"**WARNING:** too few {'/'.join(short)} instances in this population for the targets. "
                     "Add smaller configurations to the candidate pool (same generator, same rule) and pilot them "
                     "before the freeze; record the addition here.")
    lines += ["", f"## Confirmation candidates ({len(cand)} files, {2 * len(cand)} runs: plain AF and SP at the final "
              "limits)", "", md_table(cand[["instance", "class", "why_candidate", "reason", "SP_not_built", "n", "m",
                                              "L", "W", "n_duties", "AF_status", "AF_time", "SP_status", "SP_time"]]),
              "", "## Whole pilot population", "",
              md_table(classes.sort_values(["class", "n", "L", "instance"])[
                  ["instance", "class", "reason", "SP_not_built", "n", "m", "L", "W", "n_arcs", "n_duties",
                   "AF_status", "AF_time", "SP_status", "SP_time"]]), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def write_selection_md(classes: pd.DataFrame, sel: pd.DataFrame, path: str, stage: str, runs_path: str) -> None:
    """SELECTION.md: the rule, every candidate considered and the chosen set (Master Plan §10.3, step 3)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    counts = {k: int(v) for k, v in sel["class"].value_counts().reindex(CLASS_ORDER, fill_value=0).items()}
    lines = [
        "# Benchmark selection (Group M)", "",
        f"Source rows: `{runs_path}` (stage: {stage}). Written by `pilot/classify.py`.", "",
        "## Rule (fixed before the confirmation runs)",
        "1. Classes from the plain AF and SP runs, first rule wins: TIME_LIMIT (a built plain model hit the limit) ->",
        f"   HARD (max solver time > {config.HARD_THRESHOLD_S} s) -> MEDIUM (both optimal and times differ x10, or only one",
        "   model built) -> EASY.",
        "2. Within each class, candidates are taken in increasing n, then L, then configuration id, up to the target",
        f"   {TARGETS}. Missing TIME_LIMIT places are filled with HARD instances, and we say so.",
        "3. No instance is hand-picked, replaced or removed after the final runs start.", "",
        "## Selected instances", "",
        f"Counts: {counts} (total {len(sel)}); SP_not_built inside the classes: {int(sel['SP_not_built'].sum())}.",
    ]
    n_bad = int((classes["class"] == "UNUSABLE").sum())
    if n_bad:
        lines.append(f"\n**WARNING:** {n_bad} candidate(s) UNUSABLE (errored / killed / check failed) - rerun them "
                     "before the freeze; they are listed below and were not selected.")
    if counts["TIME_LIMIT"] < MIN_TIME_LIMIT:
        lines.append(f"\n**WARNING:** fewer than {MIN_TIME_LIMIT} time-limit instances - apply the §10.3 contingency.")
    if len(sel) < 15:
        lines.append("\n**WARNING:** fewer than 15 instances - the professor's minimum is not met.")
    cols = ["instance", "class", "reason", "SP_not_built", "n", "m", "L", "W", "n_arcs", "n_duties",
            "AF_status", "AF_time", "SP_status", "SP_time"]
    lines += ["", md_table(sel[cols]), "", "## Every candidate considered", "",
              md_table(classes.sort_values(["class", "n", "L", "instance"])[cols]), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", default=None, help="SELECTION.md path (pilot/confirm stages)")
    ap.add_argument("--stage", choices=["pilot", "confirm", "final"], default="pilot")
    ap.add_argument("--classes-csv", default=None, help="also write the per-instance classes as CSV")
    ap.add_argument("--selected-csv", default=None, help="write the selected instances (input of pilot.freeze)")
    ap.add_argument("--candidates-csv", default=None, help="pilot stage: write the confirmation candidates")
    a = ap.parse_args(argv)
    classes = classify_all(load_runs(a.runs))
    if a.classes_csv:
        classes.to_csv(a.classes_csv, index=False)
    print(classes["class"].value_counts().reindex(CLASS_ORDER, fill_value=0).to_string())
    if a.stage == "pilot":                                   # pilot: choose what to CONFIRM, never the benchmark
        cand = confirmation_candidates(classes)
        if a.out:
            write_candidates_md(classes, cand, a.out, a.runs)
        if a.candidates_csv:
            cand.to_csv(a.candidates_csv, index=False)
        print(f"{len(cand)} confirmation candidates ({2 * len(cand)} runs at the final limits)"
              + (f" -> {a.out}" if a.out else ""))
        return
    if a.stage == "confirm" and a.out:
        sel = select(classes)
        write_selection_md(classes, sel, a.out, a.stage, a.runs)
        if a.selected_csv:
            sel.to_csv(a.selected_csv, index=False)
        print(f"selected {len(sel)} instances -> {a.out}")


if __name__ == "__main__":
    main()
