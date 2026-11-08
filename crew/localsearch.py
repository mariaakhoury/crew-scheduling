"""Local search (task C14). Owner: Member C.

Improves a legal schedule with three moves, first-improvement, until no move saves money:

  1. tail_swap        duties A, B exchange their tails:  A[:p] + B[q:]  and  B[:q] + A[p:]   (a part may be empty)
  2. merge            duty Y is appended to duty X:      X + Y
  3. swap_then_merge  a legal tail swap (possibly worse on its own) followed by a merge that involves one of the
                      two new duties; accepted only if the two together save money.

A move is accepted only if the total cost drops by at least config.COST_STEP ($0.50). Every schedule cost is a
multiple of COST_STEP, so each accepted move lowers the cost by >= one step: the search cannot cycle, always stops,
and never returns anything worse than its input.

Speed: candidate duties are screened in O(1) from cached per-duty facts (first trip, last trip, driving minutes,
prefix sums of driving). Only an ACCEPTED move is re-checked in full with B's independent is_legal_duty; a
disagreement means a bug here and raises immediately instead of producing an illegal schedule.

Determinism: duties and split points are scanned in a fixed order and the first improving move is taken, so the
same input always gives the same output (no randomness, no dict/set ordering in decisions).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator, NamedTuple, Optional

from crew import config
from crew.checker import check_schedule, is_legal_duty
from crew.greedy import can_follow, greedy_insertion
from crew.instance import Instance, Schedule

_EPS = 1e-9
MOVE_KINDS = ("tail_swap", "merge", "swap_then_merge")


class _Facts(NamedTuple):
    """What a merge test needs to know about a (possibly hypothetical) duty."""
    first: int      # trip id of the first trip
    last: int       # trip id of the last trip
    driving: int    # total driving minutes


class _Move(NamedTuple):
    kind: str
    removed: tuple[int, ...]        # indices of the duties that disappear
    added: tuple[tuple[int, ...], ...]  # the new (non-empty) duties that replace them
    delta: float                    # change in total cost (negative = saving)


@dataclass
class LocalSearchResult:
    schedule: Schedule
    cost: float                     # cost of the returned schedule (recomputed by the checker)
    start_cost: float               # cost of the input schedule
    moves: dict[str, int] = field(default_factory=lambda: dict.fromkeys(MOVE_KINDS, 0))
    stopped_by: str = "local_optimum"   # "local_optimum" | "max_rounds" | "time_limit" (result legal in every case)
    seconds: float = 0.0

    @property
    def timed_out(self) -> bool:
        return self.stopped_by == "time_limit"


class _Searcher:
    def __init__(self, inst: Instance, schedule: Schedule, deadline: Optional[float]):
        self.inst = inst
        self.T = inst.trips
        self.dur = [t.end - t.start for t in inst.trips]
        self.duties: list[list[int]] = [list(d) for d in schedule]
        self.deadline = deadline
        self.step = config.COST_STEP - _EPS
        self._refresh()

    # ------------------------------------------------------------------ cached facts

    def _refresh(self) -> None:
        """Recompute per-duty facts after the schedule changed."""
        self.facts = [_Facts(d[0], d[-1], sum(self.dur[i] for i in d)) for d in self.duties]
        self.prefix = []                                   # prefix[k][m] = driving of the first m trips of duty k
        for d in self.duties:
            acc, row = 0, [0]
            for i in d:
                acc += self.dur[i]
                row.append(acc)
            self.prefix.append(row)
        self.costs = [self._cost(f.first, f.last) for f in self.facts]

    def _cost(self, first: int, last: int) -> float:
        return self.inst.F + self.inst.c_per_min * (self.T[last].end - self.T[first].start)

    def _out_of_time(self) -> bool:
        return self.deadline is not None and time.perf_counter() > self.deadline

    # ------------------------------------------------------------------ O(1) legality screens

    def _joined(self, a: int, p: int, b: int, q: int) -> Optional[Optional[_Facts]]:
        """Facts of the duty A[:p] + B[q:] (A = duty a, B = duty b).
        Returns None if illegal, _Facts if legal, and the sentinel () if the result is empty."""
        A, B = self.duties[a], self.duties[b]
        if p == 0 and q == len(B):
            return ()                                      # empty duty: simply disappears
        if p == 0:                                         # a suffix of a legal duty is legal
            return _Facts(B[q], B[-1], self.prefix[b][-1] - self.prefix[b][q])
        if q == len(B):                                    # a prefix of a legal duty is legal
            return _Facts(A[0], A[p - 1], self.prefix[a][p])
        if not can_follow(self.inst, self.T[A[p - 1]], self.T[B[q]]):
            return None                                    # C4: terminal or turnaround
        if self.T[B[-1]].end - self.T[A[0]].start > self.inst.L:
            return None                                    # C5: spread
        driving = self.prefix[a][p] + self.prefix[b][-1] - self.prefix[b][q]
        if driving > self.inst.W:
            return None                                    # C6: driving
        return _Facts(A[0], B[-1], driving)

    def _merge_facts(self, x: _Facts, y: _Facts) -> Optional[_Facts]:
        """Facts of duty X + Y, or None if illegal."""
        if not can_follow(self.inst, self.T[x.last], self.T[y.first]):
            return None
        if self.T[y.last].end - self.T[x.first].start > self.inst.L:
            return None
        if x.driving + y.driving > self.inst.W:
            return None
        return _Facts(x.first, y.last, x.driving + y.driving)

    def _fcost(self, f) -> float:
        return 0.0 if f == () else self._cost(f.first, f.last)

    # ------------------------------------------------------------------ move generators

    def _tail_swaps(self) -> Iterator[tuple[int, int, int, int, object, object, float]]:
        """Every legal tail swap (a < b), with the facts of both new duties and the cost change."""
        n_d = len(self.duties)
        for a in range(n_d):
            for b in range(a + 1, n_d):
                if self._out_of_time():
                    return
                la, lb = len(self.duties[a]), len(self.duties[b])
                base = self.costs[a] + self.costs[b]
                for p in range(la + 1):
                    for q in range(lb + 1):
                        if (p == 0 and q == 0) or (p == la and q == lb):
                            continue                       # identity (or a pure relabelling of the two duties)
                        na = self._joined(a, p, b, q)      # A[:p] + B[q:]
                        if na is None:
                            continue
                        nb = self._joined(b, q, a, p)      # B[:q] + A[p:]
                        if nb is None:
                            continue
                        yield a, b, p, q, na, nb, self._fcost(na) + self._fcost(nb) - base

    def _parts(self, a: int, b: int, p: int, q: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
        A, B = self.duties[a], self.duties[b]
        return tuple(A[:p] + B[q:]), tuple(B[:q] + A[p:])

    def find_tail_swap(self) -> Optional[_Move]:
        for a, b, p, q, _na, _nb, delta in self._tail_swaps():
            if delta <= -self.step:
                new = tuple(d for d in self._parts(a, b, p, q) if d)
                return _Move("tail_swap", (a, b), new, delta)
        return None

    def find_merge(self) -> Optional[_Move]:
        n_d = len(self.duties)
        for x in range(n_d):
            if self._out_of_time():
                return None
            for y in range(n_d):
                if x == y:
                    continue
                m = self._merge_facts(self.facts[x], self.facts[y])
                if m is None:
                    continue
                delta = self._fcost(m) - self.costs[x] - self.costs[y]
                if delta <= -self.step:
                    return _Move("merge", (x, y), (tuple(self.duties[x] + self.duties[y]),), delta)
        return None

    def find_swap_then_merge(self) -> Optional[_Move]:
        n_d = len(self.duties)
        for a, b, p, q, na, nb, d_swap in self._tail_swaps():
            new_a, new_b = self._parts(a, b, p, q)
            parts = [(na, new_a), (nb, new_b)]
            for k, (fx, dx) in enumerate(parts):
                if fx == ():
                    continue
                other_f, other_d = parts[1 - k]
                # merge partners: every untouched duty, plus the other new duty
                partners = [(self.facts[y], tuple(self.duties[y]), self.costs[y], y)
                            for y in range(n_d) if y not in (a, b)]
                if other_f != ():
                    partners.append((other_f, other_d, self._fcost(other_f), None))
                for fy, dy, cy, y in partners:
                    for first_f, first_d, second_f, second_d in ((fx, dx, fy, dy), (fy, dy, fx, dx)):
                        m = self._merge_facts(first_f, second_f)
                        if m is None:
                            continue
                        delta = d_swap + self._fcost(m) - self._fcost(fx) - cy
                        if delta <= -self.step:
                            merged = first_d + second_d
                            if y is None:                  # merged the two new duties with each other
                                return _Move("swap_then_merge", (a, b), (merged,), delta)
                            rest = other_d
                            new = tuple(d for d in (merged, rest) if d)
                            return _Move("swap_then_merge", tuple(sorted((a, b, y))), new, delta)
        return None

    # ------------------------------------------------------------------ apply

    def apply(self, move: _Move) -> None:
        for duty in move.added:                            # full, independent re-check of every new duty
            ok, why = is_legal_duty(self.inst, list(duty))
            if not ok:
                raise AssertionError(f"local search produced an illegal duty in a {move.kind} move: {why}")
        removed = set(move.removed)
        pos = min(removed)
        kept = [d for k, d in enumerate(self.duties) if k not in removed]
        insert_at = sum(1 for k in range(pos) if k not in removed)
        self.duties = kept[:insert_at] + [list(d) for d in move.added] + kept[insert_at:]
        self._refresh()


def improve(inst: Instance, schedule: Schedule, max_rounds: int = 1000,
            time_limit_s: Optional[float] = None) -> LocalSearchResult:
    """Improve a legal schedule and report how. Never returns a worse or illegal schedule.
    max_rounds: maximum number of accepted moves. time_limit_s: optional wall-clock budget.
    When either stops the search, the best schedule so far is returned and stopped_by says why."""
    t0 = time.perf_counter()
    start = check_schedule(inst, schedule)
    if not start.ok:
        raise ValueError(f"local search needs a legal starting schedule: {start.errors}")

    s = _Searcher(inst, schedule, None if time_limit_s is None else t0 + time_limit_s)
    moves = dict.fromkeys(MOVE_KINDS, 0)
    stopped_by = "local_optimum"
    while True:
        if sum(moves.values()) >= max_rounds:
            stopped_by = "max_rounds"
            break
        move = s.find_tail_swap() or s.find_merge() or s.find_swap_then_merge()
        if s._out_of_time():
            stopped_by = "time_limit"             # scans abort at the deadline; a move already found is still safe to apply
        if move is None:
            break
        s.apply(move)
        moves[move.kind] += 1

    final = check_schedule(inst, s.duties)
    if not final.ok or final.cost > start.cost + config.COST_TOL:
        raise AssertionError(f"local search broke its guarantees: ok={final.ok}, {start.cost} -> {final.cost}")
    return LocalSearchResult(schedule=s.duties, cost=final.cost, start_cost=start.cost, moves=moves,
                             stopped_by=stopped_by, seconds=time.perf_counter() - t0)


def local_search(inst: Instance, schedule: Schedule, max_rounds: int = 1000,
                 time_limit_s: Optional[float] = None) -> Schedule:
    """Shared interface (Master Plan §7.3): the improved schedule only. See improve() for the details."""
    return improve(inst, schedule, max_rounds, time_limit_s).schedule


def heuristic(inst: Instance, time_limit_s: Optional[float] = None) -> LocalSearchResult:
    """Method H: greedy insertion (C1) followed by local search (C14)."""
    return improve(inst, greedy_insertion(inst), time_limit_s=time_limit_s)
