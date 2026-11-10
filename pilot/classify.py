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
CLASS_ORDER = ["EASY", "MEDIUM", "HARD", "TIME_LIMIT", "NOT_BUILT", "UNCONFIRMED", "UNUSABLE"]
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


def load_runs(path) -> pd.DataFrame:
    """Read one runs CSV, or several (list) concatenated, and drop superseded rows (kept in the files, never used).
    Several files are allowed for the PILOT only (e.g. results/pilot.csv + results/pilot_small.csv); final results
    come from one runs.csv on one machine with one configuration."""
    if isinstance(path, (list, tuple)):
        return pd.concat([load_runs(p) for p in path], ignore_index=True)
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


MIN_SP_NOT_BUILT = 2        # Master Plan §10.3: the SP_not_built flag must appear at least twice in the benchmark
MIN_TOTAL = 15              # professor §2.2: at least 15 instances
FILL_ORDER = ("TIME_LIMIT", "HARD", "EASY")         # where the fill-up places come from (issue #1, 9 Nov)
RESERVE_FROM = ("TIME_LIMIT", "HARD", "MEDIUM")     # classes that may hold SP_not_built instances, in this order


PROCEDURE = [
    "## Selection procedure (exact, reproducible by hand; approved in issue #1, 9 Nov)",
    "",
    "**A. Spread-take k instances from a pool of N** (used in every step below):",
    "1. Order the pool by n, then L, then configuration id (the instance name), all ascending; number the",
    "   positions 0 .. N-1.",
    "2. If k >= N: take the whole pool. If k = 0: take nothing. If k = 1: take position floor(N / 2).",
    "3. Otherwise take positions round(i * (N - 1) / (k - 1)) for i = 0, 1, ..., k - 1 (Python round: halves go",
    "   to the nearest even integer), dropping duplicates. Position 0 (smallest) and N - 1 (largest) are",
    "   always taken.",
    "",
    "**B. Confirmation candidates (pilot stage, at most 24 files):**",
    "1. Spares: spread-take 2 from the EASY pool and 2 from the MEDIUM pool.",
    "2. Rechecks: the pool of all HARD, TIME_LIMIT and NOT_BUILT instances, k = 24 - number of spares.",
    "   First spread-take min(2, k) from the SP_not_built instances of that pool, then spread-take the",
    "   remaining places from the rest of the pool.",
    "",
    "**C. Final selection (after the confirmation runs):**",
    "1. Classes come from the confirmation rows; an instance without them keeps its pilot class only if that",
    "   class is EASY or a both-optimal MEDIUM; anything else is UNCONFIRMED and never selected.",
    "2. Go through the classes in the order TIME_LIMIT, HARD, MEDIUM, EASY with targets 6, 5, 5, 4; HARD's",
    "   target is increased by TIME_LIMIT's shortfall (places TIME_LIMIT could not fill).",
    "3. Keep a counter need = 2 (minimum number of SP_not_built instances). In TIME_LIMIT, HARD and MEDIUM:",
    "   first spread-take min(need, target) from the class's SP_not_built instances, then spread-take the",
    "   remaining places from the class's other instances. In EASY: spread-take the target directly.",
    "   After each class, lower need by the number of SP_not_built instances taken.",
    "4. Fill-up: if fewer than 15 are selected, take the missing number from the unused TIME_LIMIT",
    "   instances (spread-take); if still fewer than 15, from the unused HARD, then the unused EASY ones.",
    "   These rows are marked selected_as = 'fill-up to 15'.",
    "5. NOT_BUILT, UNCONFIRMED and UNUSABLE instances are never selected. No instance is hand-picked,",
    "   replaced or removed after the final runs start.",
    "",
]


def spread_take(pool: pd.DataFrame, k: int) -> pd.DataFrame:
    """Spread rule (issue #1, 9 Nov): from a pool already ordered by (n, L, configuration id), take k rows at evenly
    spaced positions from the first to the last, so small AND large instances are kept. Deterministic, no
    hand-picking; with k >= len(pool) the whole pool is taken."""
    if k <= 0 or pool.empty:
        return pool.iloc[0:0]
    if k >= len(pool):
        return pool
    if k == 1:
        return pool.iloc[[len(pool) // 2]]
    step = (len(pool) - 1) / (k - 1)
    return pool.iloc[sorted({round(i * step) for i in range(k)})]


def _take_with_reserve(pool: pd.DataFrame, want: int, reserve: int) -> pd.DataFrame:
    """Spread-take `want` rows, of which at least min(reserve, available) are SP_not_built (themselves spread)."""
    flagged = pool[pool["SP_not_built"].astype(bool)]
    reserved = spread_take(flagged, min(reserve, want))
    rest = spread_take(pool.drop(reserved.index), want - len(reserved))
    return pd.concat([reserved, rest])


def select(classes: pd.DataFrame) -> pd.DataFrame:
    """The written selection rule (Master Plan §10.3 step 3, spread version agreed in issue #1):
    within each class, order the candidates by (n, L, configuration id) and take the target number at evenly spaced
    positions (spread_take). At least MIN_SP_NOT_BUILT selected instances must carry the SP_not_built flag: places
    are reserved for them in TIME_LIMIT, then HARD, then MEDIUM, chosen by the same spread rule.
    Missing TIME_LIMIT places are filled with HARD instances, and we say so."""
    ordered = classes.sort_values(["n", "L", "instance"])
    chosen, shortfall, need = [], 0, MIN_SP_NOT_BUILT
    for cls in ["TIME_LIMIT", "HARD", "MEDIUM", "EASY"]:
        pool = ordered[ordered["class"] == cls]
        want = TARGETS[cls] + (shortfall if cls == "HARD" else 0)
        take = _take_with_reserve(pool, want, need if cls in RESERVE_FROM else 0)
        need = max(0, need - int(take["SP_not_built"].astype(bool).sum()))
        if cls == "TIME_LIMIT":
            shortfall = max(0, TARGETS[cls] - len(take))
        chosen.append(take.assign(selected_as="class target"))
    sel = pd.concat(chosen)
    # Fill up to MIN_TOTAL (issue #1, 9 Nov): the professor requires at least 15 instances. Remaining places come
    # from the UNUSED instances of TIME_LIMIT, then HARD, then EASY, each pool taken with the spread rule.
    for cls in FILL_ORDER:
        missing = MIN_TOTAL - len(sel)
        if missing <= 0:
            break
        pool = ordered[(ordered["class"] == cls) & ~ordered.index.isin(sel.index)]
        sel = pd.concat([sel, spread_take(pool, missing).assign(selected_as="fill-up to 15")])
    return sel.sort_values(["n", "L", "instance"])


def confirmation_candidates(classes: pd.DataFrame) -> pd.DataFrame:
    """Pilot stage (Master Plan §10.1 B2, §10.3 step 2): the files to rerun with plain AF and SP at the FINAL limits.
    = every preliminary HARD, TIME_LIMIT and NOT_BUILT instance (30 s cannot tell hard from time-limit, and a model
    not built in 30 s may build in 120 s) + up to SPARES_PER_CLASS spares of EASY and MEDIUM, all in the rule order
    (n, L, configuration id), all chosen with the spread rule (evenly spaced from the smallest to the largest). If more
    than MAX_CONFIRM_FILES qualify, the spares are kept and the rechecks are spread-taken, reserving at least
    MIN_SP_NOT_BUILT SP_not_built instances so the final selection can meet its minimum. UNUSABLE instances are never
    candidates (rerun the pilot row first)."""
    ordered = classes.sort_values(["n", "L", "instance"])
    spares = pd.concat([spread_take(ordered[ordered["class"] == c], SPARES_PER_CLASS) for c in ("EASY", "MEDIUM")])
    main = ordered[ordered["class"].isin(["HARD", "TIME_LIMIT", "NOT_BUILT"])]
    main = _take_with_reserve(main, max(0, MAX_CONFIRM_FILES - len(spares)), MIN_SP_NOT_BUILT)
    out = pd.concat([spares, main]).sort_values(["n", "L", "instance"])
    out["why_candidate"] = out["class"].map(lambda c: "spare" if c in ("EASY", "MEDIUM") else "recheck at 120 s")
    return out


def merge_with_pilot(confirm: pd.DataFrame, pilot: pd.DataFrame) -> pd.DataFrame:
    """Selection population for Wed 11 (B16): confirmation classes (final limits) win; an instance WITHOUT
    confirmation rows keeps its pilot class only if that class cannot change at the final limits:
      EASY, or MEDIUM because both models were OPTIMAL (both solved below the hard threshold, so a longer time
      limit or build limit does not bind). A pilot MEDIUM that is a BUILD result (one model not built in 30 s)
      may build at 120 s, so it - like every pilot HARD / TIME_LIMIT / NOT_BUILT - becomes UNCONFIRMED.
    Column class_source says where each class comes from."""
    conf = confirm.assign(class_source="confirmation")
    rest = pilot[~pilot["instance"].isin(confirm["instance"])].copy()
    stable = (rest["class"] == "EASY") | ((rest["class"] == "MEDIUM") & ~rest["reason"].str.startswith("BUILD"))
    rest.loc[stable, "class_source"] = "pilot (both solved below the hard threshold)"
    rest.loc[~stable, "reason"] = "not confirmed at the final limits (pilot: " + rest.loc[~stable, "class"] + ")"
    rest.loc[~stable, "class"] = "UNCONFIRMED"
    rest.loc[~stable, "class_source"] = "pilot only"
    return pd.concat([conf, rest], ignore_index=True)


def supply_report(classes: pd.DataFrame) -> list[str]:
    """Compare the class supply with the selection targets, so a shortage is visible BEFORE the freeze."""
    have = classes["class"].value_counts()
    lines = ["| class | target | in this population |", "|---|---|---|"]
    for c in ["EASY", "MEDIUM", "HARD", "TIME_LIMIT"]:
        lines.append(f"| {c} | {TARGETS[c]} | {int(have.get(c, 0))} |")
    return lines


def _class_mix(sel: pd.DataFrame) -> list[str]:
    """Class mix against the targets, and - if the fill-up was used - how many places it took from which class and
    why (issue #1: 'state the resulting class mix and why')."""
    lines = ["", "| class | target | selected |", "|---|---|---|"]
    for c in ["EASY", "MEDIUM", "HARD", "TIME_LIMIT"]:
        lines.append(f"| {c} | {TARGETS[c]} | {int((sel['class'] == c).sum())} |")
    if "selected_as" in sel and (sel["selected_as"] == "fill-up to 15").any():
        filled = sel[sel["selected_as"] == "fill-up to 15"]["class"].value_counts()
        short = [f"{c} {int((sel['class'] == c).sum())}/{TARGETS[c]}" for c in ["EASY", "MEDIUM", "HARD", "TIME_LIMIT"]
                 if int(((sel["class"] == c) & (sel["selected_as"] == "class target")).sum()) < TARGETS[c]]
        lines += ["", f"**Fill-up used:** {int(filled.sum())} place(s), taken from "
                  + ", ".join(f"{c} ({n})" for c, n in filled.items())
                  + f", because these classes had fewer instances than their targets: {', '.join(short)}. "
                  "The course minimum of 15 instances is therefore met with a heavier share of the classes that "
                  "had spare instances; the results discussion reports this mix."]
    return lines + [""]


def _src(runs_path) -> str:
    """Source file(s) as text for SELECTION.md."""
    paths = runs_path if isinstance(runs_path, (list, tuple)) else [runs_path]
    return " + ".join(f"`{p}`" for p in paths)


def _config_note(runs_path) -> list[str]:
    """A visible note when the rows come from more than one configuration (allowed for the pilot, never for final)."""
    try:
        df = load_runs(runs_path)
    except (OSError, ValueError):
        return []
    notes = []
    for col, what in (("config_hash", "configurations"), ("machine_id", "machine fingerprints")):
        if col in df and df[col].nunique() > 1:
            parts = [f"`{str(h)[:12]}` ({n} rows)" for h, n in df[col].value_counts().items()]
            notes.append(f"**Data note:** the rows come from {len(parts)} {what}: " + ", ".join(parts) + ". "
                         "Allowed for the pilot (used only to choose candidates) when the difference is explained "
                         "here; final rows must share one configuration and one machine.")
    return [*notes, ""] if notes else []


def write_candidates_md(classes: pd.DataFrame, cand: pd.DataFrame, path: str, runs_path, note: str = "") -> None:
    """Pilot-stage SELECTION.md: the rule, the class supply, the confirmation candidates, the whole population."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    counts = {k: int(v) for k, v in classes["class"].value_counts().reindex(CLASS_ORDER, fill_value=0).items()}
    lines = [
        "# Benchmark selection (Group M) - pilot stage", "",
        f"Source rows: {_src(runs_path)} (pilot limits). Written by `pilot/classify.py`. Pilot classes are PRELIMINARY:",
        "at the pilot limit a hard instance and a time-limit instance look the same (Master Plan §10.3 step 1).", "",
        "## Rule (fixed before the confirmation runs)",
        "1. Classes from the plain AF and SP runs, first rule wins: NOT_BUILT (neither model built) -> TIME_LIMIT",
        f"   (a built plain model hit the limit) -> HARD (max solver time > {config.HARD_THRESHOLD_S} s at the final",
        "   limits) -> MEDIUM (both optimal and times differ x10, or only one model built) -> EASY.",
        "2. Confirmation candidates = every HARD, TIME_LIMIT and NOT_BUILT instance + "
        f"{SPARES_PER_CLASS} spares per EASY/MEDIUM class, at most {MAX_CONFIRM_FILES} files. Spread rule: order by",
        "   (n, L, configuration id) and take evenly spaced positions from the smallest to the largest; if the cap",
        f"   binds, at least {MIN_SP_NOT_BUILT} SP_not_built instances are kept.",
        "3. Final selection (after the confirmation runs): within each class, order by (n, L, configuration id) and",
        f"   take the targets {TARGETS} with the spread rule; at least {MIN_SP_NOT_BUILT} selected instances carry",
        "   SP_not_built (places reserved in TIME_LIMIT, then HARD, then MEDIUM); missing TIME_LIMIT places are",
        "   filled with HARD. If fewer than 15 are then selected, the remaining places up to 15 are filled from the",
        "   unused TIME_LIMIT, then HARD, then EASY instances with the same spread rule (column selected_as).",
        "   (Changed from 'smallest n first' on 9 Nov, issue #1, before the confirmation runs: smallest-first",
        "   dropped every instance with n > 80 and every SP_not_built instance; the fill-up guarantees 15.)",
        "4. No instance is hand-picked, replaced or removed after the final runs start.", "",
        *PROCEDURE,
        *_config_note(runs_path),
        *([f"**Explanation:** {note}", ""] if note else []),
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
        f"Source rows: {_src(runs_path)} (stage: {stage}). Written by `pilot/classify.py`.", "",
        "## Rule (fixed before the confirmation runs)",
        "1. Classes from the plain AF and SP runs, first rule wins: TIME_LIMIT (a built plain model hit the limit) ->",
        f"   HARD (max solver time > {config.HARD_THRESHOLD_S} s) -> MEDIUM (both optimal and times differ x10, or only one",
        "   model built) -> EASY.",
        "2. Within each class, candidates are ordered by (n, L, configuration id) and the targets",
        f"   {TARGETS} are taken at evenly spaced positions (spread rule, issue #1, 9 Nov); at least",
        f"   {MIN_SP_NOT_BUILT} selected instances carry SP_not_built. Missing TIME_LIMIT places are filled with HARD.",
        f"   If fewer than {MIN_TOTAL} are selected, the remaining places are filled from the unused TIME_LIMIT, then",
        "   HARD, then EASY instances with the spread rule (column selected_as = 'fill-up to 15').",
        "3. No instance is hand-picked, replaced or removed after the final runs start.", "",
        *PROCEDURE,
        "## Selected instances", "",
        f"Counts: {counts} (total {len(sel)}); SP_not_built inside the classes: {int(sel['SP_not_built'].sum())}.",
        *_class_mix(sel),
    ]
    n_bad = int((classes["class"] == "UNUSABLE").sum())
    if n_bad:
        lines.append(f"\n**WARNING:** {n_bad} candidate(s) UNUSABLE (errored / killed / check failed) - rerun them "
                     "before the freeze; they are listed below and were not selected.")
    if counts["TIME_LIMIT"] < MIN_TIME_LIMIT:
        lines.append(f"\n**WARNING:** fewer than {MIN_TIME_LIMIT} time-limit instances - apply the §10.3 contingency.")
    if len(sel) < 15:
        lines.append("\n**WARNING:** fewer than 15 instances - the professor's minimum is not met.")
    if int(sel["SP_not_built"].astype(bool).sum()) < MIN_SP_NOT_BUILT:
        lines.append(f"\n**WARNING:** fewer than {MIN_SP_NOT_BUILT} SP_not_built instances in the selection "
                     "(Master Plan §10.3 minimum; hypothesis H5 cannot be tested).")
    cols = ["instance", "class", "reason", "SP_not_built", "n", "m", "L", "W", "n_arcs", "n_duties",
            "AF_status", "AF_time", "SP_status", "SP_time"]
    sel_cols = cols[:2] + ["selected_as"] + cols[2:] if "selected_as" in sel else list(cols)   # a copy, never cols
    if "class_source" in classes:
        cols.insert(2, "class_source")
        sel_cols.insert(3 if "selected_as" in sel else 2, "class_source")
        lines.append("\nClasses come from the confirmation runs at the final limits; instances that were not re-run keep "
                     "their pilot class only if it is EASY or a both-optimal MEDIUM (column class_source).")
    lines += ["", md_table(sel[sel_cols]), "", "## Every candidate considered", "",
              md_table(classes.sort_values(["class", "n", "L", "instance"])[cols]), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, nargs="+", help="one runs CSV, or several pilot CSVs")
    ap.add_argument("--out", default=None, help="SELECTION.md path (pilot/confirm stages)")
    ap.add_argument("--stage", choices=["pilot", "confirm", "final"], default="pilot")
    ap.add_argument("--classes-csv", default=None, help="also write the per-instance classes as CSV")
    ap.add_argument("--selected-csv", default=None, help="write the selected instances (input of pilot.freeze)")
    ap.add_argument("--candidates-csv", default=None, help="pilot stage: write the confirmation candidates")
    ap.add_argument("--pilot", default=None, nargs="+",
                    help="confirm stage: the pilot CSV(s), so EASY / both-optimal MEDIUM instances that were not "
                         "re-run keep their pilot class")
    ap.add_argument("--note", default="", help="explanation printed in SELECTION.md (e.g. why the data note appears)")
    a = ap.parse_args(argv)
    classes = classify_all(load_runs(a.runs))
    if a.stage == "confirm" and a.pilot:
        classes = merge_with_pilot(classes, classify_all(load_runs(a.pilot)))
    if a.classes_csv:
        classes.to_csv(a.classes_csv, index=False)
    print(classes["class"].value_counts().reindex(CLASS_ORDER, fill_value=0).to_string())
    if a.stage == "pilot":                                   # pilot: choose what to CONFIRM, never the benchmark
        cand = confirmation_candidates(classes)
        if a.out:
            write_candidates_md(classes, cand, a.out, a.runs, a.note)
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
