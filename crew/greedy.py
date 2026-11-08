"""Greedy heuristic (task C1). Owner: Member C.

Idea: go through the trips in order of start time and give each trip to the open duty (driver)
that can take it most cheaply. If no duty can take it legally, open a new duty (hire a driver).

Cost of adding trip j to a duty = c_per_min x (wait before j + duration of j),
because the duty's paid time (its spread) grows by exactly that much.
Costs, turnaround, L and W are read from the instance (which must equal config.py, rule V6),
so no number is typed here.

Expected result on P0: [[0, 1, 4, 5, 6], [2, 3], [7]], cost $1177.50.
"""
from __future__ import annotations

from crew.instance import Instance, Schedule, Trip


def can_follow(inst: Instance, a: Trip, b: Trip) -> bool:
    """True if one driver can do trip b right after trip a: same terminal and at least tau minutes break.
    (Stand-in for A's trip network, A1; same rule as checker rule C4.)"""
    return a.dest == b.origin and a.end + inst.tau <= b.start


def greedy_insertion(inst: Instance) -> Schedule:
    """Build a legal schedule (list of duties, each a list of trip ids in start order). Deterministic."""
    trips = inst.trips
    order = sorted(range(len(trips)), key=lambda i: (trips[i].start, i))   # by start time, ties by id

    duties: list[list[int]] = []      # trip ids of each duty
    driving: list[int] = []           # minutes driven so far in each duty

    for j in order:
        tj = trips[j]
        dur = tj.end - tj.start
        best_k, best_cost = None, None

        for k, duty in enumerate(duties):                      # every open duty, lowest number first
            first, last = trips[duty[0]], trips[duty[-1]]
            if not can_follow(inst, last, tj):
                continue                                       # wrong terminal or break too short
            if tj.end - first.start > inst.L:
                continue                                       # workday (spread) would exceed L
            if driving[k] + dur > inst.W:
                continue                                       # driving would exceed W
            add_cost = inst.c_per_min * ((tj.start - last.end) + dur)
            if best_cost is None or add_cost < best_cost:      # strict "<": ties keep the lowest duty number
                best_k, best_cost = k, add_cost

        new_duty_cost = inst.F + inst.c_per_min * dur
        if best_k is None or new_duty_cost < best_cost:        # nothing fits (or a new driver is cheaper)
            duties.append([j])
            driving.append(dur)
        else:
            duties[best_k].append(j)
            driving[best_k] += dur

    return duties
