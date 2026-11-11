"""Tests for A12 (analysis_strength) and A16 (analysis_profiles) on a tiny hand-made results table."""
import math
import os

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest

from crew import analysis_profiles as prof
from crew import analysis_strength as strength


def _row(inst, method, status, obj, e2e, **kw):
    r = {"instance": inst, "n": 10, "L": 360, "method": method, "status": status, "objective": obj,
         "best_bound": obj, "feasible_checked": "yes", "superseded": "no", "heuristic_cost": np.nan,
         "end_to_end_s": e2e, "solver_time_s": e2e, "t_enum_s": np.nan, "t_build_s": 0.1, "t_solve_s": e2e,
         "root_bound": obj, "nodes": 1, "time_limit_s": 120, "build_limit_s": 120}
    r.update(kw)
    return r


@pytest.fixture
def df():
    return pd.DataFrame([
        # i1: both solve, SP 10x faster; LPs 90 (AF) and 100 (SP), optimum 100
        _row("i1", "AF", "OPTIMAL", 100.0, 20.0, root_bound=95.0, nodes=50),
        _row("i1", "SP", "OPTIMAL", 100.0, 2.0, t_enum_s=0.5),
        _row("i1", "LP-AF", "OPTIMAL", 90.0, 0.1),
        _row("i1", "LP-SP", "OPTIMAL", 100.0, 0.1),
        # i2: AF hits the time limit, SP solves
        _row("i2", "AF", "TIME_LIMIT", 210.0, 120.0, best_bound=180.0, root_bound=160.0),
        _row("i2", "SP", "OPTIMAL", 200.0, 5.0, t_enum_s=1.0),
        # i3: SP cannot be built, AF hits the time limit: nobody solves it
        _row("i3", "AF", "TIME_LIMIT", 310.0, 120.0, best_bound=280.0, heuristic_cost=300.0),
        _row("i3", "SP", "COLUMN_CAP", np.nan, 30.0, t_enum_s=30.0, t_build_s=np.nan, root_bound=np.nan),
    ])


# ---------------------------------------------------------------- A12

def test_reference_uses_heuristic_when_better(df):
    ref = strength.reference_values(df)
    assert ref.loc["i1", "best_value"] == 100 and ref.loc["i1", "proven"]
    assert ref.loc["i3", "best_value"] == 300 and not ref.loc["i3", "proven"]   # heuristic 300 < AF 310


def test_lp_and_root_gaps(df):
    t = strength.strength_table(df).set_index(["instance", "model"])
    assert t.loc[("i1", "AF"), "lp_gap_pct"] == pytest.approx(10.0)
    assert t.loc[("i1", "SP"), "lp_gap_pct"] == pytest.approx(0.0)
    assert t.loc[("i2", "AF"), "root_gap_pct"] == pytest.approx(20.0)
    assert not t.loc[("i3", "SP"), "built"] and math.isnan(t.loc[("i3", "SP"), "root_gap_pct"])


def test_q22_holds_and_catches_a_violation(df):
    assert strength.q22_check(df)["ok"].all()
    bad = df.copy()
    bad.loc[(bad["instance"] == "i1") & (bad["method"] == "LP-AF"), "objective"] = 101.0
    assert not strength.q22_check(bad)["ok"].all()


def test_strength_charts_draw(df):
    strength.plot_gap_vs_time(df)
    strength.plot_time_split(df)


# ---------------------------------------------------------------- A16

def test_ratios_and_unsolved_is_inf(df):
    r = prof.ratios(df)
    assert r.loc["i1", "SP"] == 1.0 and r.loc["i1", "AF"] == pytest.approx(10.0)
    assert np.isinf(r.loc["i2", "AF"])
    assert np.isinf(r.loc["i3"]).all()               # nobody solved it: inf for every method


def test_profile_end_points(df):
    p = prof.profile_curve(df)
    assert p["SP"].iloc[0] == pytest.approx(2 / 3)   # share of ALL 3 instances: SP fastest on 2
    assert p["AF"].iloc[-1] == pytest.approx(1 / 3)  # AF solves 1 of the 3 at any factor


def test_sgm_formula():
    assert prof.sgm([0, 0]) == pytest.approx(0.0)
    assert prof.sgm([10, 40], shift=10) == pytest.approx(math.sqrt(20 * 50) - 10)


def test_summary_and_wtl(df):
    s = prof.summary_table(df)
    assert s.loc["SP", "solved"] == 2 and s.loc["AF", "solved"] == 1
    assert s.loc["SP", "solved_within_120s_end_to_end"] == 2
    w = prof.win_tie_loss(df).iloc[0]
    assert (w["A"], w["B"], w["A_wins"], w["ties"], w["A_losses"]) == ("AF", "SP", 0, 1, 2)


def test_reports_on_confirmation_runs(tmp_path):
    path = os.path.join("results", "confirm.csv")
    if not os.path.exists(path):
        pytest.skip("results/confirm.csv not present")
    strength.report(path, str(tmp_path / "a12"))
    prof.report(path, str(tmp_path / "a16"))
    assert os.path.exists(tmp_path / "a12" / "time_split.png")
    assert os.path.exists(tmp_path / "a16" / "performance_profile.png")
