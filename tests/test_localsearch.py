"""Acceptance tests for crew/localsearch.py (task C14).
    pytest -q tests/test_localsearch.py
"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance  # noqa: E402
from crew.checker import check_schedule  # noqa: E402
from crew.greedy import greedy_insertion as greedy  # noqa: E402
from crew.localsearch import heuristic, improve, local_search  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))


def test_p0_goes_from_1177_50_to_945_by_swap_then_merge():
    res = heuristic(P0)
    assert res.start_cost == 1177.50 and res.cost == 945.0, res
    assert sorted(map(sorted, res.schedule)) == [[0, 1, 4, 5], [2, 3, 6, 7]]
    assert res.moves == {"tail_swap": 0, "merge": 0, "swap_then_merge": 1}, res.moves   # the A11 "P0 story"


def test_never_worse_than_greedy_and_always_legal():
    for f in PROTO:
        inst = load_instance(f)
        g = check_schedule(inst, greedy(inst))
        res = heuristic(inst)
        assert check_schedule(inst, res.schedule, res.cost).ok, f
        assert res.cost <= g.cost, (f, g.cost, res.cost)
        assert res.cost >= inst.reference["cost"] - 0.01, (f, res.cost)    # cannot beat the proven optimum


def test_deterministic():
    for f in PROTO:
        inst = load_instance(f)
        assert heuristic(inst).schedule == heuristic(inst).schedule, f


def test_already_optimal_input_is_returned_unchanged():
    ref = P0.reference["schedule"]
    res = improve(P0, ref)
    assert res.schedule == ref and sum(res.moves.values()) == 0 and res.stopped_by == "local_optimum"
    assert local_search(P0, ref) == ref                      # shared interface returns a plain Schedule


def test_zero_time_limit_still_returns_a_legal_schedule():
    res = heuristic(P0, time_limit_s=0.0)
    assert res.timed_out and check_schedule(P0, res.schedule).ok


def test_illegal_start_is_refused():
    try:
        local_search(P0, [[0, 1, 4, 5]])          # trips 2, 3, 6, 7 missing
    except ValueError:
        return
    raise AssertionError("an illegal starting schedule must raise ValueError")
