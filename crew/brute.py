"""Brute-force oracle for tiny instances (n <= 10). Owner: Member B (task B1).

Deliberately independent of duties.py and of both MILP models: it tries every way of splitting
the trips into groups (set partitions) and uses only the checker to judge legality and cost.
If the models and this oracle agree, a shared bug is very unlikely.

Method: take the trips in (start, id) order and put each one either into an existing group or
into a new group. Because trips are added in start order, each group is always in increasing
start time, and every prefix of a legal duty is legal, so a branch is cut as soon as one group
becomes illegal. Bell(10) = 115,975 partitions at most, so this is fast for n <= 10.
"""
from __future__ import annotations

from crew.checker import check_schedule, duty_cost, is_legal_duty
from crew.instance import Instance, Schedule


def brute_force(inst: Instance, max_n: int = 10) -> tuple[float, Schedule]:
    """Return (optimal cost, an optimal schedule). Raises ValueError if n > max_n."""
    n = len(inst.trips)
    if n > max_n:
        raise ValueError(f"brute_force is limited to n <= {max_n} (got n = {n})")
    order = [t.id for t in sorted(inst.trips, key=lambda t: (t.start, t.id))]
    best = [float("inf"), None]
    groups: list[list[int]] = []

    def cost_so_far() -> float:
        return sum(duty_cost(inst, g) for g in groups)

    def place(k: int) -> None:
        if k == n:                                   # every trip placed: a complete schedule
            c = cost_so_far()
            if c < best[0] - 1e-9:
                best[0], best[1] = c, [list(g) for g in groups]
            return
        if cost_so_far() >= best[0]:                 # bound: costs only grow as trips are added
            return
        trip = order[k]
        for g in groups:                             # option 1: append to an existing group
            g.append(trip)
            if is_legal_duty(inst, g)[0]:
                place(k + 1)
            g.pop()
        groups.append([trip])                        # option 2: start a new group (always legal, rule V5)
        place(k + 1)
        groups.pop()

    place(0)
    cost, schedule = best
    res = check_schedule(inst, schedule, cost)        # final independent confirmation
    assert res.ok, res.errors
    return cost, schedule


def count_legal_duties_brute(inst: Instance, max_n: int = 10) -> int:
    """Count legal duties by checking EVERY subset of trips (2^n) with the checker.
    Used by Q12 to confirm the DFS count of duties.py independently."""
    n = len(inst.trips)
    if n > max_n:
        raise ValueError(f"limited to n <= {max_n}")
    order = sorted(range(n), key=lambda i: (inst.trips[i].start, i))
    count = 0
    for mask in range(1, 1 << n):
        duty = [i for i in order if mask >> i & 1]
        if is_legal_duty(inst, duty)[0]:
            count += 1
    return count
