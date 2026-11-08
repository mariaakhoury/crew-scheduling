"""Tests for crew/integration.py (task C2: MIP starts).
    pytest -q tests/test_integration.py

Gate-1 criterion: "the start is accepted on P0-P5 for both models". The acceptance tests use the real
crew.model_arcflow / crew.duties + crew.model_setpart as soon as they exist; until then Model 2 is replaced by a
small stand-in set-partitioning model (test fixture only) and the Model 1 acceptance test is skipped.
"""
import glob, importlib.util, os, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.checker import check_schedule, duty_cost, is_legal_duty  # noqa: E402
from crew.instance import load_instance  # noqa: E402
from crew.integration import (arcflow_objective, arcflow_start_values, start_accepted,  # noqa: E402
                              start_arcflow, start_setpart)
from crew.localsearch import heuristic  # noqa: E402
from crew.run_child import _arcs  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))
HAVE_GUROBI = importlib.util.find_spec("gurobipy") is not None
HAVE_AF = importlib.util.find_spec("crew.model_arcflow") is not None
HAVE_SP = importlib.util.find_spec("crew.model_setpart") is not None and importlib.util.find_spec("crew.duties")


# ------------------------------------------------------------------ pure arc-flow values

def test_p0_arcflow_values_by_hand():
    vals = arcflow_start_values(P0, [[0, 1, 4, 5], [2, 3, 6, 7]])
    assert vals["x"] == {(0, 1), (1, 4), (4, 5), (2, 3), (3, 6), (6, 7)}
    assert [j for j, b in vals["u"].items() if b] == [0, 2]
    assert [j for j, b in vals["v"].items() if b] == [5, 7]
    assert vals["T"] == {0: 360, 1: 360, 4: 360, 5: 360, 2: 390, 3: 390, 6: 390, 7: 390}
    assert vals["D"] == {0: 60, 1: 120, 4: 180, 5: 240, 2: 60, 3: 120, 6: 180, 7: 240}


def test_arcflow_values_are_consistent_on_all_prototypes():
    for f in PROTO:
        inst = load_instance(f)
        sched = heuristic(inst).schedule
        vals = arcflow_start_values(inst, sched)
        arcs = set(_arcs(inst))
        assert vals["x"] <= arcs, f                                        # only arcs of the network
        assert len(vals["x"]) == len(inst.trips) - len(sched), f          # n - #duties arcs in a path cover
        assert sum(vals["u"].values()) == sum(vals["v"].values()) == len(sched), f
        for t in inst.trips:                                               # (3) and (7): within variable bounds
            assert vals["T"][t.id] <= t.start and t.end - vals["T"][t.id] <= inst.L, f
            assert t.end - t.start <= vals["D"][t.id] <= inst.W, f
        # Model 1's objective at the start == the checker's cost of the schedule
        assert abs(arcflow_objective(inst, vals) - check_schedule(inst, sched).cost) < 1e-9, f


def test_illegal_start_is_refused():
    try:
        arcflow_start_values(P0, [[0, 1, 4, 5]])
    except ValueError:
        return
    raise AssertionError("an illegal schedule must not become a MIP start")


# ------------------------------------------------------------------ log parsing

def test_start_accepted_reads_gurobi_wording():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "x.log")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("Loaded user MIP start with objective 945\n\nExplored 1 nodes\n")
        assert start_accepted(log, 945.0)
        assert not start_accepted(log, 1177.5)
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("User MIP start produced solution with objective 6.5495e+03 (0.01s)\n")
        assert start_accepted(log, 6549.5)
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("User MIP start did not produce a new incumbent solution\n")
        assert not start_accepted(log, 945.0)
        assert not start_accepted(os.path.join(d, "missing.log"), 945.0)


# ------------------------------------------------------------------ real Gurobi acceptance

def _all_duties(inst):
    """All legal duties by DFS on the arcs (stand-in for B2, test fixture only)."""
    succ = {}
    for a, b in _arcs(inst):
        succ.setdefault(a, []).append(b)
    out = []

    def dfs(d):
        out.append(tuple(d))
        for nxt in succ.get(d[-1], []):
            if is_legal_duty(inst, d + [nxt])[0]:
                dfs(d + [nxt])
    for t in range(len(inst.trips)):
        dfs([t])
    return out


def _setpart(inst, duties):
    if HAVE_SP:
        from crew.model_setpart import build_setpart
        return build_setpart(inst, duties)
    import gurobipy as gp                                                   # stand-in Model 2 (fixture only)
    m = gp.Model()
    z = m.addVars(len(duties), vtype=gp.GRB.BINARY, obj=[duty_cost(inst, list(d)) for d in duties])
    for t in range(len(inst.trips)):
        m.addConstr(gp.quicksum(z[k] for k, d in enumerate(duties) if t in d) == 1, name=f"c8_cover[{t}]")
    return m, {"z": z}


def _solve_with_log(model, d, name):
    log = os.path.join(d, name + ".log")
    for k, v in config.GUROBI_PARAMS.items():
        model.setParam(k, v)
    model.setParam("LogFile", log)
    model.optimize()
    return log


def test_setpart_start_is_accepted_on_all_prototypes():
    if not HAVE_GUROBI:
        pytest.skip("gurobipy not installed")
    with tempfile.TemporaryDirectory() as d:
        for f in PROTO:
            inst = load_instance(f)
            h = heuristic(inst)
            if HAVE_SP:
                from crew.duties import enumerate_duties
                import time
                duties, status, _ = enumerate_duties(inst, _arcs(inst), config.COLUMN_CAP, time.perf_counter() + 60)
                assert status == "complete", f
            else:
                duties = _all_duties(inst)
            model, mvars = _setpart(inst, duties)
            start_setpart(model, mvars, duties, h.schedule)
            log = _solve_with_log(model, d, inst.name)
            assert start_accepted(log, h.cost), (f, h.cost)
            assert abs(model.ObjVal - inst.reference["cost"]) < 0.01, f      # and the model still reaches the optimum
            model.dispose()


def test_setpart_start_rejects_unknown_duty():
    try:
        start_setpart(None, {"z": {}}, [(0, 1)], [[0, 1, 4, 5]])
    except ValueError:
        return
    raise AssertionError("a duty missing from the list must raise")


def test_arcflow_start_sets_every_variable():
    if not HAVE_GUROBI:
        pytest.skip("gurobipy not installed")
    import gurobipy as gp
    arcs = _arcs(P0)
    m = gp.Model()
    m.setParam("OutputFlag", 0)
    n = range(len(P0.trips))
    mv = {"x": m.addVars(arcs, vtype=gp.GRB.BINARY), "u": m.addVars(n, vtype=gp.GRB.BINARY),
          "v": m.addVars(n, vtype=gp.GRB.BINARY), "T": m.addVars(n), "D": m.addVars(n)}
    m.update()
    start_arcflow(m, mv, P0, [[0, 1, 4, 5], [2, 3, 6, 7]])
    used = {(0, 1), (1, 4), (4, 5), (2, 3), (3, 6), (6, 7)}
    assert all(var.Start == (1 if key in used else 0) for key, var in mv["x"].items())
    assert mv["T"][7].Start == 390 and mv["D"][7].Start == 240 and mv["u"][2].Start == 1
    m.dispose()


def test_arcflow_start_is_accepted_on_all_prototypes():
    if not (HAVE_GUROBI and HAVE_AF):
        pytest.skip("crew/model_arcflow.py (task A2) not written yet")   # activates automatically when it exists
    from crew.model_arcflow import build_arcflow
    with tempfile.TemporaryDirectory() as d:
        for f in PROTO:
            inst = load_instance(f)
            h = heuristic(inst)
            model, mvars = build_arcflow(inst, _arcs(inst))
            start_arcflow(model, mvars, inst, h.schedule)
            log = _solve_with_log(model, d, inst.name)
            assert start_accepted(log, h.cost), (f, h.cost)
            model.dispose()
