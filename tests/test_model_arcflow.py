"""Tests for Model 1 (tasks A2 and A6): Q6, Q7, Q21, Q28 on the prototype instances."""
import glob

import pytest

gp = pytest.importorskip("gurobipy")

from crew.checker import check_schedule
from crew.graph import build_arcs
from crew.instance import load_instance
from crew.model_arcflow import build_arcflow, decode_arcflow

FILES = sorted(glob.glob("instances/proto/P*.json"))


def _solve(inst, **kw):
    model, mv = build_arcflow(inst, build_arcs(inst), **kw)
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 0.0
    model.Params.MIPGapAbs = 0.49
    model.optimize()
    return model, mv


@pytest.mark.parametrize("f", FILES)
def test_optimum_matches_reference_and_checker(f):          # Q6, Q7
    inst = load_instance(f)
    model, mv = _solve(inst)
    assert model.Status == gp.GRB.OPTIMAL
    assert abs(model.ObjVal - inst.reference["cost"]) < 0.01
    result = check_schedule(inst, decode_arcflow(inst, mv))
    assert result.ok and abs(result.cost - model.ObjVal) < 0.01
    model.dispose()


@pytest.mark.parametrize("f", FILES)
def test_model_size(f):                                      # Q28
    inst = load_instance(f)
    arcs = build_arcs(inst)
    model, _ = build_arcflow(inst, arcs)
    n = len(inst.trips)
    assert model.NumVars == len(arcs) + 4 * n
    assert model.NumConstrs == 3 * n + 2 * len(arcs)
    model.dispose()


def test_p0_is_945():
    inst = load_instance("instances/proto/P0_example8.json")
    model, _ = _solve(inst)
    assert abs(model.ObjVal - 945.0) < 0.01


@pytest.mark.parametrize("f", FILES)
def test_naive_big_m(f):                                     # Q21: same optimum, LP bound never higher
    inst = load_instance(f)
    m_tight, _ = _solve(inst)
    m_naive, _ = _solve(inst, naive_m=True)
    assert abs(m_tight.ObjVal - m_naive.ObjVal) < 0.01
    lp_tight, _ = _solve(inst, relax=True)
    lp_naive, _ = _solve(inst, relax=True, naive_m=True)
    assert lp_naive.ObjVal <= lp_tight.ObjVal + 1e-6
    for m in (m_tight, m_naive, lp_tight, lp_naive):
        m.dispose()
