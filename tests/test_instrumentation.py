"""Tests for the C12 incumbent recorder (crew/run_child.py: IncumbentRecorder).
    pytest -q tests/test_instrumentation.py
"""
import csv, glob, os, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from crew.instance import load_instance  # noqa: E402
from crew.integration import start_setpart  # noqa: E402
from crew.localsearch import heuristic  # noqa: E402
from standins import HAVE_GUROBI, all_duties, apply_params, setpart_model  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
pytestmark = pytest.mark.skipif(not HAVE_GUROBI, reason="gurobipy not installed")


def _solve(inst, with_start, **params):
    from crew.run_child import IncumbentRecorder
    duties = all_duties(inst)
    model, mvars = setpart_model(inst, duties)
    h = heuristic(inst)
    if with_start:
        start_setpart(model, mvars, duties, h.schedule)
    apply_params(model, **params)
    rec = IncumbentRecorder()
    model.optimize(rec.callback)
    return model, rec, h


@pytest.mark.parametrize("with_start", [False, True])
def test_trajectory_is_monotone_and_ends_at_the_optimum(with_start):
    with tempfile.TemporaryDirectory() as d:
        for f in PROTO:
            inst = load_instance(f)
            model, rec, h = _solve(inst, with_start)
            s = rec.summary(model, d, inst.name)
            times = [p[0] for p in rec.points]
            objs = [p[1] for p in rec.points]
            assert s["n_incumbents"] == len(rec.points) >= 1, f
            assert times == sorted(times) and all(a > b for a, b in zip(objs, objs[1:])), f   # strictly better
            assert abs(objs[-1] - model.ObjVal) < 1e-6, f                     # last incumbent = final answer
            assert s["root_bound"] <= model.ObjVal + 1e-6, f                  # a bound never exceeds the optimum
            assert 0 <= s["t_first_incumbent_s"] <= model.Runtime + 1e-6, f
            if with_start:                                                   # the accepted start is incumbent #1
                assert abs(s["first_incumbent_obj"] - h.cost) < 1e-6, (f, s["first_incumbent_obj"], h.cost)
            with open(os.path.join(d, s["trajectory_file"]), encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            assert [float(r["incumbent"]) for r in rows] == objs, f
            model.dispose()


def test_no_incumbent_means_no_trajectory():
    inst = load_instance(PROTO[0])
    with tempfile.TemporaryDirectory() as d:
        model, rec, _ = _solve(inst, False, TimeLimit=0)
        s = rec.summary(model, d, "none")
        assert s["n_incumbents"] == 0 and s["t_first_incumbent_s"] is None and "trajectory_file" not in s
        model.dispose()
