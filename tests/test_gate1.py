"""Gate 1 suite (task B4, owner B): Q3-Q9, Q12 and Q28 on the prototype instances P0..P5.

    pytest -q tests/test_gate1.py

Tests that need another member's module (graph.py and model_arcflow.py from A, greedy.py,
localsearch.py and integration.py from C) are SKIPPED, with the reason shown, until that module
exists. They turn on automatically as soon as the module is pushed - nothing to edit here.
"""
import glob
import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crew import config                                       # noqa: E402
from crew.instance import load_instance                       # noqa: E402
from crew.checker import check_schedule                       # noqa: E402
from crew.brute import brute_force, count_legal_duties_brute  # noqa: E402
from crew.duties import (COMPLETE, count_duties, enumerate_duties,  # noqa: E402
                         get_arcs, temp_build_arcs)

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
INST = {os.path.basename(f).split("_")[0]: load_instance(f) for f in PROTO}   # "P0" -> Instance
TINY = ["P0", "P1", "P2"]                                                       # n <= 10: brute force


def _module(name):
    """Import crew.<name>, or skip the test if that module (or its function) does not exist yet."""
    try:
        return importlib.import_module(f"crew.{name}")
    except ImportError as exc:
        pytest.skip(f"crew.{name} not available yet ({exc})")


def _gurobi():
    return pytest.importorskip("gurobipy", reason="gurobipy not installed")


# ---------------------------------------------------------------- Q3 trip compatibility (A's graph.py)
@pytest.mark.parametrize("key", sorted(INST))
def test_q3_build_arcs_equals_pair_check(key):
    graph = _module("graph")
    inst = INST[key]
    try:
        arcs = graph.build_arcs(inst)
    except NotImplementedError:
        pytest.skip("graph.build_arcs not implemented yet")
    assert sorted(arcs) == sorted(temp_build_arcs(inst))


def test_build_setpart_sets_no_gurobi_parameters():
    """Repo rule (AGENTS.md): the runner sets every parameter from config.py, the model sets none."""
    _gurobi()
    from crew.model_setpart import build_setpart
    inst = INST["P0"]
    duties, _, _ = enumerate_duties(inst, get_arcs(inst))
    model, vars = build_setpart(inst, duties)
    assert model.Params.TimeLimit > 1e99                              # Gurobi default (infinite): not set
    assert model.Params.MIPGapAbs != config.GUROBI_PARAMS["MIPGapAbs"]   # still Gurobi's default
    assert set(vars) >= {"z"} and len(vars["z"]) == len(duties)
    model.dispose()


def test_q3_p0_has_14_arcs():
    assert len(temp_build_arcs(INST["P0"])) == 14


# ---------------------------------------------------------------- Q12 enumeration completeness
def test_q12_p0_has_40_duties():
    duties, status, count = enumerate_duties(INST["P0"], get_arcs(INST["P0"]))
    assert status == COMPLETE and count == 40 == len(duties)


@pytest.mark.parametrize("key", TINY)
def test_q12_dfs_count_equals_brute_subset_count(key):
    inst = INST[key]
    dfs_count, stopped, _ = count_duties(inst, get_arcs(inst))
    assert not stopped
    assert dfs_count == count_legal_duties_brute(inst)


@pytest.mark.parametrize("key", sorted(INST))
def test_q12_every_enumerated_duty_is_legal_and_unique(key):
    from crew.checker import is_legal_duty
    inst = INST[key]
    duties, status, _ = enumerate_duties(inst, get_arcs(inst))
    assert status == COMPLETE
    assert len(set(duties)) == len(duties)
    assert all(is_legal_duty(inst, list(d))[0] for d in duties)


def test_q12_cap_and_deadline_statuses(monkeypatch):
    """The three statuses the runner understands: complete / capped / anything else = out of time."""
    import time
    inst = INST["P3"]
    arcs = get_arcs(inst)
    assert enumerate_duties(inst, arcs, cap=5) == (None, "capped", 6)
    assert enumerate_duties(inst, arcs, config.COLUMN_CAP, time.perf_counter() + 60)[1] == "complete"
    monkeypatch.setattr(config, "CLOCK_CHECK_EVERY", 1)          # check the clock after every duty
    duties, status, count = enumerate_duties(inst, arcs, config.COLUMN_CAP, time.perf_counter() - 1)
    assert duties is None and status == "out_of_time" and count == 1


# ---------------------------------------------------------------- Q7 brute force
@pytest.mark.parametrize("key", TINY)
def test_q7_brute_force_matches_reference(key):
    inst = INST[key]
    cost, schedule = brute_force(inst)
    assert abs(cost - inst.reference["cost"]) <= config.COST_TOL
    assert check_schedule(inst, schedule, cost).ok


# ---------------------------------------------------------------- Q6 / Q7 / Q28 set partitioning
@pytest.mark.parametrize("key", sorted(INST))
def test_q6_q7_q28_setpart_optimum_and_sizes(key):
    _gurobi()
    from crew.model_setpart import build_setpart, decode_setpart
    inst = INST[key]
    duties, status, _ = enumerate_duties(inst, get_arcs(inst))
    assert status == COMPLETE
    model, vars = build_setpart(inst, duties)
    from crew.model_setpart import apply_params
    apply_params(model)                                              # build_setpart sets no parameters itself
    # Q28: sizes come from Gurobi and must match the formulas |P| and n
    assert model.NumVars == len(duties)
    assert model.NumConstrs == len(inst.trips)
    assert model.NumNZs == sum(len(d) for d in duties)
    assert all(c.ConstrName.startswith("c8_cover") for c in model.getConstrs())
    model.optimize()
    assert model.Status == 2                                         # OPTIMAL
    sched = decode_setpart(inst, duties, vars)
    res = check_schedule(inst, sched, model.ObjVal)                  # independent check of the decoded schedule
    assert res.ok, res.errors
    assert abs(model.ObjVal - inst.reference["cost"]) <= config.COST_TOL
    assert model.ObjVal - model.ObjBound <= config.GUROBI_PARAMS["MIPGapAbs"]   # Q23 certificate
    model.dispose()


@pytest.mark.parametrize("key", sorted(INST))
def test_lp_sp_is_a_lower_bound(key):
    _gurobi()
    from crew.model_setpart import solve_setpart
    inst = INST[key]
    duties, _, _ = enumerate_duties(inst, get_arcs(inst))
    lp = solve_setpart(inst, duties, relax=True)
    assert lp["status"] == 2
    assert lp["objective"] <= inst.reference["cost"] + 1e-6


# ---------------------------------------------------------------- Q6 / Q22 / Q28 arc-flow (A's model)
@pytest.mark.parametrize("key", sorted(INST))
def test_q6_arcflow_equals_setpart(key):
    _gurobi()
    af = _module("model_arcflow")
    inst = INST[key]
    arcs = get_arcs(inst)
    try:
        model, vars = af.build_arcflow(inst, arcs)
    except NotImplementedError:
        pytest.skip("build_arcflow not implemented yet")
    n = len(inst.trips)
    assert model.NumVars == len(arcs) + 4 * n                         # Q28
    assert model.NumConstrs == 3 * n + 2 * len(arcs)                  # Q28
    model.optimize()
    assert model.Status == 2
    sched = af.decode_arcflow(inst, vars)
    assert check_schedule(inst, sched, model.ObjVal).ok
    assert abs(model.ObjVal - inst.reference["cost"]) <= config.COST_TOL   # same optimum as SP / reference
    model.dispose()


@pytest.mark.parametrize("key", sorted(INST))
def test_q22_lp_af_le_lp_sp(key):
    _gurobi()
    af = _module("model_arcflow")
    from crew.model_setpart import solve_setpart
    inst = INST[key]
    arcs = get_arcs(inst)
    try:
        m_af, _ = af.build_arcflow(inst, arcs, relax=True)
    except NotImplementedError:
        pytest.skip("build_arcflow not implemented yet")
    m_af.optimize()
    duties, _, _ = enumerate_duties(inst, arcs)
    lp_sp = solve_setpart(inst, duties, relax=True)["objective"]
    assert m_af.ObjVal <= lp_sp + 1e-6                                 # Theorem 3
    m_af.dispose()


# ---------------------------------------------------------------- Q8 heuristic (C's greedy + local search)
def test_q8_greedy_and_local_search_on_p0():
    greedy = _module("greedy")
    ls = _module("localsearch")
    inst = INST["P0"]
    try:
        g = greedy.greedy_insertion(inst)
        improved = ls.local_search(inst, g)
    except NotImplementedError:
        pytest.skip("heuristic not implemented yet")
    rg, rl = check_schedule(inst, g), check_schedule(inst, improved)
    assert rg.ok and abs(rg.cost - 1177.5) <= config.COST_TOL
    assert rl.ok and abs(rl.cost - 945.0) <= config.COST_TOL
    assert greedy.greedy_insertion(inst) == g                          # deterministic


@pytest.mark.parametrize("key", sorted(INST))
def test_q8_monotone(key):
    greedy = _module("greedy")
    ls = _module("localsearch")
    inst = INST[key]
    try:
        g = greedy.greedy_insertion(inst)
        improved = ls.local_search(inst, g)
    except NotImplementedError:
        pytest.skip("heuristic not implemented yet")
    cg, cl = check_schedule(inst, g), check_schedule(inst, improved)
    assert cg.ok and cl.ok
    assert inst.reference["cost"] - config.COST_TOL <= cl.cost <= cg.cost + config.COST_TOL


# ---------------------------------------------------------------- Q9 MIP start for SP (C's integration.py)
@pytest.mark.parametrize("key", sorted(INST))
def test_q9_setpart_mip_start_accepted(key, tmp_path):
    _gurobi()
    integ = _module("integration")
    from crew.model_setpart import build_setpart
    inst = INST[key]
    duties, _, _ = enumerate_duties(inst, get_arcs(inst))
    model, vars = build_setpart(inst, duties)
    from crew.model_setpart import apply_params
    apply_params(model)
    log = tmp_path / "sp_start.log"
    model.setParam("LogFile", str(log))
    sched = inst.reference["schedule"]                                 # any checked schedule works as a start
    try:
        integ.start_setpart(model, vars, duties, sched)
    except NotImplementedError:
        pytest.skip("start_setpart not implemented yet")
    model.optimize()
    model.dispose()
    assert integ.start_accepted(str(log), inst.reference["cost"])
