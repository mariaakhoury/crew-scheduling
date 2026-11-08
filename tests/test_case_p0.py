"""Test for the P0 story (task A11): greedy $1177.50, local search $945, optimum $945 (plan §2.5)."""
import matplotlib
matplotlib.use("Agg")

import pytest

from crew.instance import load_instance
from crew.viz import case_study, cost_table

P0 = load_instance("instances/proto/P0_example8.json")


def _schedules():
    from crew.greedy import greedy_insertion
    from crew.localsearch import heuristic
    return {"Greedy": greedy_insertion(P0),
            "After local search": heuristic(P0).schedule,
            "Optimal": P0.reference["schedule"]}


def test_cost_table_matches_plan():
    table = cost_table(P0, _schedules())
    assert table.loc["Greedy", "total $"] == pytest.approx(1177.50)
    assert table.loc["Greedy", "drivers"] == 3 and table.loc["Greedy", "paid minutes"] == 555
    assert table.loc["After local search", "total $"] == pytest.approx(945.00)
    assert table.loc["Optimal", "paid minutes"] == 690


def test_greedy_strands_trip_7():
    assert [7] in [list(d) for d in _schedules()["Greedy"]]


def test_case_study_draws_every_trip_three_times():
    fig = case_study(P0, _schedules(), highlight=[7])
    assert sum(len(ax.patches) for ax in fig.axes) == 3 * len(P0.trips)
