"""Acceptance tests for crew/greedy.py (task C1).
    pytest -q tests/test_greedy.py
"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance  # noqa: E402
from crew.checker import check_schedule  # noqa: E402
from crew.greedy import greedy_insertion as greedy  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))


def test_p0_greedy_is_exactly_1177_50():
    schedule = greedy(P0)
    assert schedule == [[0, 1, 4, 5, 6], [2, 3], [7]]
    res = check_schedule(P0, schedule)
    assert res.ok and res.cost == 1177.50, res


def test_same_answer_every_run():
    assert greedy(P0) == greedy(P0)


def test_legal_and_never_below_the_optimum_on_all_prototypes():
    for f in PROTO:
        inst = load_instance(f)
        res = check_schedule(inst, greedy(inst))
        assert res.ok, (f, res.errors)
        assert res.cost >= inst.reference["cost"] - 0.01, (f, res.cost)   # a heuristic can't beat the optimum
