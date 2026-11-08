"""Independent feasibility checker (rules C1-C7 of data_dictionary.md). Owner: Member B.

INDEPENDENCE RULE: this file imports only crew.config and the data classes in crew.instance.
It never imports graph.py, the models, the heuristic or any Gurobi code, so it can judge
their output without sharing their mistakes.
"""
from __future__ import annotations
import numbers
from typing import NamedTuple

from crew import config
from crew.instance import Instance, Schedule


class CheckResult(NamedTuple):
    ok: bool                 # True only if every rule C1-C7 holds
    cost: float | None       # recomputed total cost in $ (None if not ok)
    errors: list[str]        # human-readable reasons, empty if ok


def _is_id(i, n: int) -> bool:
    """A trip id is any whole number 0..n-1 (Python int or numpy int), but not True/False."""
    return isinstance(i, numbers.Integral) and not isinstance(i, bool) and 0 <= i < n


def _as_list(x):
    """A duty or schedule may be a list, a tuple or a numpy array; anything else is badly shaped (None)."""
    if isinstance(x, (list, tuple)):
        return list(x)
    if hasattr(x, "tolist") and not isinstance(x, (str, bytes)):   # numpy array
        y = x.tolist()
        return y if isinstance(y, list) else None
    return None


def _clean(schedule) -> list[list]:
    """Turn numpy ints (e.g. from Gurobi or numpy arrays) into plain Python ints; leave bad ids as they are."""
    return [[int(i) if isinstance(i, numbers.Integral) and not isinstance(i, bool) else i for i in duty]
            for duty in schedule]


def duty_cost(inst: Instance, duty: list[int]) -> float:
    """F + c_per_min * spread, where spread = end of last trip - start of first trip (minutes).
    Assumes the duty is already in increasing start time (call is_legal_duty first)."""
    first, last = inst.trips[duty[0]], inst.trips[duty[-1]]
    return inst.F + inst.c_per_min * (last.end - first.start)


def is_legal_duty(inst: Instance, duty: list[int]) -> tuple[bool, list[str]]:
    """Rules C3-C6 for one duty. Returns (ok, reasons)."""
    errors: list[str] = []
    n = len(inst.trips)
    duty = _as_list(duty)
    if duty is None:                                        # C1: a duty must be a list of trip ids
        return False, ["C1: duty is not a list of trip ids"]
    duty = _clean([duty])[0]
    if not duty:                                            # C3: no empty duty
        return False, ["C3: empty duty"]
    bad_ids = [i for i in duty if not _is_id(i, n)]
    if bad_ids:                                             # C1 (needed before reading trips)
        return False, [f"C1: unknown trip id(s) {bad_ids} in duty {duty}"]
    trips = [inst.trips[i] for i in duty]
    for a, b in zip(trips, trips[1:]):
        if not a.start < b.start:                           # C3: strictly increasing start time
            errors.append(f"C3: duty {duty} is not in increasing start time ({a.id} before {b.id})")
        if a.dest != b.origin:                              # C4: same terminal
            errors.append(f"C4: trip {a.id} ends at terminal {a.dest} but trip {b.id} starts at {b.origin}")
        if a.end + inst.tau > b.start:                      # C4: turnaround of at least tau minutes
            errors.append(f"C4: only {b.start - a.end} min between trips {a.id} and {b.id} (need {inst.tau})")
    spread = trips[-1].end - trips[0].start
    if spread > inst.L:                                     # C5: spread <= L
        errors.append(f"C5: duty {duty} has spread {spread} min > L = {inst.L}")
    driving = sum(t.end - t.start for t in trips)
    if driving > inst.W:                                    # C6: driving <= W
        errors.append(f"C6: duty {duty} drives {driving} min > W = {inst.W}")
    return not errors, errors


def check_schedule(inst: Instance, schedule: Schedule, claimed_cost: float | None = None) -> CheckResult:
    """Rules C1-C7 for a whole schedule. If claimed_cost is given, it must match within config.COST_TOL."""
    errors: list[str] = []
    n = len(inst.trips)
    # C1 (shape): the schedule must be a list of duties, and every duty a list of trip ids.
    # A badly shaped answer from a solver gets a C1 error, never a crash.
    schedule = _as_list(schedule)
    if schedule is None:
        return CheckResult(False, None, ["C1: schedule is not a list of duties"])
    duties = [_as_list(d) for d in schedule]
    bad = [k for k, d in enumerate(duties) if d is None]
    if bad:
        return CheckResult(False, None, [f"C1: duty at position(s) {bad} is not a list of trip ids"])
    schedule = _clean(duties)
    seen = [t for duty in schedule for t in duty]

    unknown = [t for t in seen if not _is_id(t, n)]
    if unknown:                                             # C1: every id exists
        errors.append(f"C1: unknown trip id(s) {unknown}")
    counts: dict[int, int] = {}
    for t in (t for t in seen if _is_id(t, n)):
        counts[t] = counts.get(t, 0) + 1
    missing = [i for i in range(n) if i not in counts]
    twice = sorted(t for t, k in counts.items() if k > 1)
    if missing:                                             # C2: every trip exactly once
        errors.append(f"C2: trip(s) {missing} not covered")
    if twice:
        errors.append(f"C2: trip(s) {twice} covered more than once")

    for duty in schedule:                                   # C3-C6 per duty
        _, duty_errors = is_legal_duty(inst, duty)
        errors.extend(duty_errors)

    if errors:
        return CheckResult(False, None, errors)

    cost = sum(duty_cost(inst, duty) for duty in schedule)  # C7: recompute the cost
    if claimed_cost is not None and abs(claimed_cost - cost) > config.COST_TOL:
        return CheckResult(False, None, [f"C7: claimed cost {claimed_cost} but recomputed {cost}"])
    return CheckResult(True, cost, [])
