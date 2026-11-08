"""Duty counting and enumeration for set partitioning (Model 2). Owner: Member B (task B2).

A duty is a chain of trips (i1, ..., ir) where every consecutive pair is a connection arc
(same terminal, at least tau minutes of turnaround), the spread e_ir - s_i1 is at most L and
the driving sum(d_ik) is at most W.

Enumeration completeness (Master Plan §3.2): appending a trip can only increase spread and
driving, so every prefix of a legal duty is legal. A depth-first search that starts at every
trip and only extends legal prefixes therefore reaches every legal duty, and because the trip
order inside a duty is fixed by time, each duty is produced exactly once.
"""
from __future__ import annotations

import time
from typing import Iterator, Optional

from crew import config
from crew.instance import Instance

Duty = tuple[int, ...]

# Status strings returned by enumerate_duties (agreed with the runner, AGENTS.md / issue #1):
# the runner maps "capped" -> COLUMN_CAP and anything other than "complete" -> BUILD_LIMIT.
COMPLETE = "complete"
CAPPED = "capped"
OUT_OF_TIME = "out_of_time"


def temp_build_arcs(inst: Instance) -> list[tuple[int, int]]:
    """Temporary arc builder (plan §8.6) used only until graph.build_arcs (Member A, task A1) exists.
    Arc (i, j): trip j can follow trip i in the same duty (same terminal, turnaround >= tau)."""
    T = inst.trips
    return [(a.id, b.id) for a in T for b in T
            if a.dest == b.origin and a.end + inst.tau <= b.start]


def get_arcs(inst: Instance) -> list[tuple[int, int]]:
    """Use Member A's graph.build_arcs if it exists, otherwise the temporary builder above."""
    try:
        from crew.graph import build_arcs          # A1
        return build_arcs(inst)
    except (ImportError, NotImplementedError):
        return temp_build_arcs(inst)


def _successors(inst: Instance, arcs) -> dict[int, list[int]]:
    """Adjacency list: succ[i] = trips that may follow trip i, sorted by id for a deterministic order."""
    succ: dict[int, list[int]] = {t.id: [] for t in inst.trips}
    for i, j in arcs:
        succ[i].append(j)
    for i in succ:
        succ[i].sort()
    return succ


def _dfs(inst: Instance, arcs) -> Iterator[Duty]:
    """Yield every legal duty exactly once (iterative DFS, so long duties never hit the recursion limit)."""
    T = inst.trips
    succ = _successors(inst, arcs)
    for t in sorted(T, key=lambda t: (t.start, t.id)):          # one search tree per first trip
        if t.end - t.start > inst.W:                             # cannot happen on valid data (rule V5)
            continue
        stack: list[tuple[Duty, int]] = [((t.id,), t.end - t.start)]   # (duty so far, driving so far)
        while stack:
            duty, drive = stack.pop()
            yield duty
            first_start = T[duty[0]].start
            for j in reversed(succ[duty[-1]]):                  # reversed -> pops in increasing id order
                tj = T[j]
                new_drive = drive + (tj.end - tj.start)
                if tj.end - first_start <= inst.L and new_drive <= inst.W:   # spread and driving rules
                    stack.append((duty + (j,), new_drive))


def count_duties(inst: Instance, arcs, cap: Optional[int] = None,
                 deadline: Optional[float] = None) -> tuple[int, bool, float]:
    """Count legal duties without storing them.
    cap: stop after this many duties; deadline: a time.perf_counter() value after which we stop.
    Returns (count, stopped_early, seconds)."""
    t0 = time.perf_counter()
    count = 0
    for _ in _dfs(inst, arcs):
        count += 1
        if cap is not None and count > cap:
            return count, True, time.perf_counter() - t0
        if deadline is not None and count % config.CLOCK_CHECK_EVERY == 0 and time.perf_counter() > deadline:
            return count, True, time.perf_counter() - t0
    return count, False, time.perf_counter() - t0


def enumerate_duties(inst: Instance, arcs, cap: int = config.COLUMN_CAP,
                     deadline: Optional[float] = None) -> tuple[Optional[list[Duty]], str, int]:
    """Store every legal duty (the complete set P for Model 2).
    deadline is an ABSOLUTE time.perf_counter() value (the runner passes start + BUILD_LIMIT_S).
    Returns (duties, status, count):
      (list, "complete", |P|)        all duties found
      (None, "capped", count)        more than `cap` duties (memory guard)  -> runner status COLUMN_CAP
      (None, "out_of_time", count)   the deadline passed (checked every config.CLOCK_CHECK_EVERY duties)
                                                                             -> runner status BUILD_LIMIT
    A capped or timed-out list is never returned, so SP is always built over the COMPLETE P."""
    duties: list[Duty] = []
    for duty in _dfs(inst, arcs):
        duties.append(duty)
        if len(duties) > cap:
            return None, CAPPED, len(duties)
        if deadline is not None and len(duties) % config.CLOCK_CHECK_EVERY == 0 \
                and time.perf_counter() > deadline:
            return None, OUT_OF_TIME, len(duties)
    return duties, COMPLETE, len(duties)
