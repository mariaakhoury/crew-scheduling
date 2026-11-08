"""Acceptance tests for crew/checker.py (B0) and the loader round-trip (A0).
    pytest -q tests/test_checker.py
"""
import glob, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance, save_instance  # noqa: E402
from crew.checker import check_schedule, duty_cost  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))


def test_reference_schedules_accepted_with_their_cost():
    for f in PROTO:
        inst = load_instance(f)
        res = check_schedule(inst, inst.reference["schedule"], inst.reference["cost"])
        assert res.ok and abs(res.cost - inst.reference["cost"]) < 0.01, (f, res)


def test_p0_duty_cost():
    assert duty_cost(P0, [0, 1, 4, 5]) == 442.50


def test_p0_greedy_schedule_cost():
    # Greedy schedule of master plan §2.5: legal, $1177.50
    res = check_schedule(P0, [[0, 1, 4, 5, 6], [2, 3], [7]])
    assert res.ok and res.cost == 1177.50


# The six bad schedules on P0: each must be rejected by the rule shown.
BAD = [
    ("missing trip",           [[0, 1, 4, 5], [2, 3, 6]],          "C2"),
    ("duplicate trip",         [[0, 1, 4, 5], [2, 3, 6, 7], [5]],  "C2"),
    ("wrong terminal",         [[0, 4], [1], [2, 3, 6, 7], [5]],   "C4"),   # 0 ends at B, 4 starts at A
    ("turnaround below 10",    [[2, 1], [0], [3], [4, 5], [6, 7]], "C4"),   # 2 ends 450, 1 starts 435
    ("spread above L",         [[0, 1, 4, 5, 6, 7], [2, 3]],       "C5"),   # 360 -> 795 = 435 > 420
    ("driving above W",        [[0, 1, 4, 5, 6, 7], [2, 3]],       "C6"),   # 6 x 60 = 360 > 300
]


def test_bad_schedules_rejected_by_the_right_rule():
    for name, schedule, rule in BAD:
        res = check_schedule(P0, schedule)
        assert not res.ok and any(e.startswith(rule + ":") for e in res.errors), (name, res.errors)


def test_claimed_cost_mismatch_rejected():
    res = check_schedule(P0, P0.reference["schedule"], claimed_cost=944.5)
    assert not res.ok and res.errors[0].startswith("C7:")


def test_save_load_round_trip():
    for f in PROTO:
        inst = load_instance(f)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, os.path.basename(f))
            save_instance(inst, out)
            assert load_instance(out) == inst, f
