"""Extra checker tests (review 7 Nov): rules C1 and C3, and numpy ids from solver output.
    pytest -q tests/test_checker_extra.py
"""
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance  # noqa: E402
from crew.checker import check_schedule  # noqa: E402

P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))
GOOD = [[0, 1, 4, 5], [2, 3, 6, 7]]          # the optimal schedule, $945


def has(res, rule):
    return not res.ok and any(e.startswith(rule + ":") for e in res.errors)


def test_numpy_ids_are_accepted():
    res = check_schedule(P0, [list(np.array(d)) for d in GOOD])
    assert res.ok and res.cost == 945.0


def test_unknown_id_C1():
    assert has(check_schedule(P0, [[0, 1, 4, 5], [2, 3, 6, 99]]), "C1")


def test_weird_ids_rejected_not_crash_C1():
    for bad in ["7", 7.0, True, [7]]:
        assert has(check_schedule(P0, [[0, 1, 4, 5], [2, 3, 6, bad]]), "C1"), bad


def test_wrong_order_C3():
    assert has(check_schedule(P0, [[1, 0, 4, 5], [2, 3, 6, 7]]), "C3")


def test_empty_duty_C3():
    assert has(check_schedule(P0, [[0, 1, 4, 5], [], [2, 3, 6, 7]]), "C3")


def test_badly_shaped_schedules_give_C1_not_crash():
    for bad in [None, 7, "abc", [[0, 1, 4, 5], 7], [[0, 1, 4, 5], None]]:
        assert has(check_schedule(P0, bad), "C1"), bad


def test_numpy_array_duties_are_accepted():
    res = check_schedule(P0, [np.array(d) for d in GOOD])
    assert res.ok and res.cost == 945.0
