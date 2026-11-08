"""MIP starts: the heuristic schedule as a complete starting solution for both models (task C2). Owner: Member C.

Shared interfaces (Master Plan §7.3):
    start_arcflow(model, vars, inst, schedule)   vars = {"x", "u", "v", "T", "D"} from build_arcflow
    start_setpart(model, vars, duties, schedule) vars = {"z"} from build_setpart, z keyed by index into `duties`
    start_accepted(logfile, expected_cost) -> bool

The starts are COMPLETE: every variable of the model gets a Start value (not only the ones equal to 1), so Gurobi
can accept the schedule without a repair heuristic. Arc-flow values are computed by the pure function
arcflow_start_values() and can be verified without Gurobi:

    x[i,j] = 1  iff  j directly follows i in a duty          u[j] = 1  iff  j is the first trip of its duty
    v[i]   = 1  iff  i is the last trip of its duty          T[j] = start time of j's duty (first trip's start)
    D[j]   = driving minutes of j's duty up to and including j

A start that cannot be expressed in the model (an arc missing from the network, a duty missing from the duty list)
is a bug upstream and raises ValueError; it is never silently dropped.
"""
from __future__ import annotations

import re

from crew import config
from crew.checker import check_schedule
from crew.instance import Instance, Schedule

# Gurobi log lines that report an accepted user start (wording of Gurobi 10-13).
_ACCEPTED = re.compile(r"(?:Loaded user MIP start with objective|User MIP start produced solution with objective)"
                       r"\s+([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)", re.IGNORECASE)


def arcflow_start_values(inst: Instance, schedule: Schedule) -> dict:
    """Values of x, u, v, T, D for a legal schedule. x is returned as the SET of arcs equal to 1."""
    res = check_schedule(inst, schedule)
    if not res.ok:
        raise ValueError(f"MIP start must be a legal schedule: {res.errors[:3]}")
    trips = inst.trips
    x: set[tuple[int, int]] = set()
    u = {t.id: 0 for t in trips}
    v = {t.id: 0 for t in trips}
    T: dict[int, int] = {}
    D: dict[int, int] = {}
    for duty in schedule:
        duty = [int(j) for j in duty]
        u[duty[0]], v[duty[-1]] = 1, 1
        start, driven = trips[duty[0]].start, 0
        for k, j in enumerate(duty):
            driven += trips[j].end - trips[j].start
            T[j], D[j] = start, driven
            if k > 0:
                x.add((duty[k - 1], j))
    return {"x": x, "u": u, "v": v, "T": T, "D": D}


def arcflow_objective(inst: Instance, values: dict) -> float:
    """Model 1's objective evaluated at the start values: F*sum(u) + c*total driving + c*sum(wait on used arcs).
    Equals the schedule's cost (sum of F + c*spread), which the tests use as a consistency check."""
    T = inst.trips
    driving = sum(t.end - t.start for t in T)
    waiting = sum(T[j].start - T[i].end for i, j in values["x"])
    return inst.F * sum(values["u"].values()) + inst.c_per_min * (driving + waiting)


def start_arcflow(model, vars: dict, inst: Instance, schedule: Schedule) -> None:
    """Set a complete MIP start on Model 1 (A2) from a legal schedule."""
    values = arcflow_start_values(inst, schedule)
    x = vars["x"]
    arc_keys = set(x.keys())
    missing = values["x"] - arc_keys
    if missing:
        raise ValueError(f"schedule uses arcs that are not in the model's network: {sorted(missing)[:5]}")
    for key in arc_keys:
        x[key].Start = 1.0 if key in values["x"] else 0.0
    for name in ("u", "v", "T", "D"):
        var = vars[name]
        for j in var.keys():
            var[j].Start = float(values[name][j])
    model.update()


def start_setpart(model, vars: dict, duties, schedule: Schedule) -> None:
    """Set a complete MIP start on Model 2 (B3): z = 1 for the schedule's duties, 0 for all others.
    The checker is not repeated here (no instance in the §7.3 signature); the runner only passes schedules that
    improve() has already verified, and this function checks that they form a partition of the listed duties."""
    index = {tuple(int(i) for i in d): k for k, d in enumerate(duties)}
    chosen: set[int] = set()
    covered: list[int] = []
    for duty in schedule:
        key = tuple(int(i) for i in duty)
        if key not in index:
            raise ValueError(f"duty {list(key)} is not in the duty list (enumeration incomplete or a bug)")
        chosen.add(index[key])
        covered.extend(key)
    if len(covered) != len(set(covered)):
        raise ValueError("MIP start covers a trip twice")
    z = vars["z"]
    for k in z.keys():
        z[k].Start = 1.0 if k in chosen else 0.0
    model.update()


def start_accepted(logfile: str, expected_cost: float) -> bool:
    """True if the Gurobi log reports a user start with objective == expected_cost.
    The log prints about 6 significant digits, so the tolerance is max(COST_TOL, 1e-5 * |cost|)."""
    try:
        with open(logfile, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return False
    tol = max(config.COST_TOL, 1e-5 * abs(expected_cost))
    return any(abs(float(m.group(1)) - expected_cost) <= tol for m in _ACCEPTED.finditer(text))
