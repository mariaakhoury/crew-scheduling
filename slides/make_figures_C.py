"""Figures for slides 11, 12 and 14 (Member C). Every number is recomputed here from the final runs.

    py slides/make_figures_C.py            # writes slides/figures/C_*.png and prints the numbers used

slide 10: P0 case study - greedy / after local search / optimal, trip 7 outlined (A11 `viz.case_study`)
slide 11: effect of the heuristic start, AF+S vs AF and SP+S vs SP (B12 chart, `analysis_heuristic.plot_paired`)
slide 12: performance profile on end-to-end time (A16 chart, `analysis_profiles.plot_profile`)
slide 14: the largest final instance with a verified schedule, drawn with A7 `viz.gantt`
Only reads `results/runs.csv` + its solution files; never runs a solver.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from crew import analysis_heuristic, analysis_profiles
from crew.checker import check_schedule
from crew.instance import load_instance
from crew.localsearch import heuristic
from crew.greedy import greedy_insertion
from crew.viz import case_study, cost_table, gantt

RESULTS = os.path.join(ROOT, "results")
RUNS = os.path.join(RESULTS, "runs.csv")
OUT = os.path.join(ROOT, "slides", "figures")


def _save(fig, name: str) -> None:
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))


def largest_verified(df: pd.DataFrame) -> pd.Series:
    """The run to draw on slide 14: the largest n, then the cheapest schedule among the MIP methods."""
    mip = df[df["method"].isin(["AF", "AF+S", "SP", "SP+S"]) & df["objective"].notna()]
    top = mip[mip["n"] == mip["n"].max()]
    return top.sort_values("objective").iloc[0]


def slide14(df: pd.DataFrame) -> None:
    row = largest_verified(df)
    inst = load_instance(os.path.join(ROOT, "instances", "final", row["instance"] + ".json"))
    with open(os.path.join(RESULTS, row["solution_file"]), encoding="utf-8") as fh:
        schedule = json.load(fh)["schedule"]
    res = check_schedule(inst, schedule, float(row["objective"]))     # independent re-check before drawing
    if not res.ok:
        raise SystemExit(f"checker rejects {row['run_id']}: {res}")
    title = f"{len(inst.trips)} trips, {row['method']}"
    # drawn small (7 x 3.9 in) so that the text stays readable when the picture is ~4.4 in wide on the slide
    _, ax = plt.subplots(figsize=(7, 3.9))
    fig = gantt(inst, schedule, title=title, ax=ax)
    _save(fig, "C_slide14_gantt.png")
    print(f"  slide 14: {row['run_id']}  duties={len(schedule)}  cost={row['objective']:,.2f}  "
          f"gap={row['gap_pct']:.2f} %  checker OK")


def slide10() -> None:
    p0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))
    schedules = {"Greedy": greedy_insertion(p0), "After local search": heuristic(p0).schedule,
                 "Optimal": p0.reference["schedule"]}
    table = cost_table(p0, schedules)                                   # asserts every cost against the checker
    assert table["total $"].tolist() == [1177.5, 945.0, 945.0], table
    _save(case_study(p0, schedules, highlight=[7]), "C_slide10_case.png")
    print(table.to_string())


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    slide10()
    df = pd.read_csv(RUNS)
    _save(analysis_heuristic.plot_paired(df), "C_slide11_start_effect.png")
    v = analysis_heuristic.h6_verdict(df)
    print(f"  slide 11: H6 {v['verdict']} (median AF {v['median_improvement_AF']:.3f}, "
          f"SP {v['median_improvement_SP']:.3f})")
    _save(analysis_profiles.plot_profile(df), "C_slide12_profile.png")
    print(analysis_profiles.summary_table(df).to_string())
    slide14(df)


if __name__ == "__main__":
    main()
