"""Trip network (task A1). Owner: Member A.

build_arcs:    which trip can directly follow which (same terminal, >= tau minutes gap).
big_m_bounds:  ell[j] = earliest possible duty start for trip j,
               U[j]   = most driving possible up to and including trip j.
"""
from __future__ import annotations

from crew.instance import Instance


def build_arcs(inst: Instance) -> list[tuple[int, int]]:
    """Arc (i, j) if j starts where i ends and at least tau minutes after i ends."""
    arcs = []
    for i in inst.trips:
        for j in inst.trips:
            if i.dest == j.origin and i.end + inst.tau <= j.start:
                arcs.append((i.id, j.id))
    return arcs


def big_m_bounds(inst: Instance) -> tuple[list[int], list[int]]:
    """Return (ell, U), one value per trip, used as big-M numbers in Model 1."""
    s_min = min(t.start for t in inst.trips)
    ell = [max(s_min, t.end - inst.L) for t in inst.trips]
    U = [min(inst.W, t.end - s_min) for t in inst.trips]
    return ell, U
