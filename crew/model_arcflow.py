"""Model 1: arc-flow MILP (tasks A2 and A6). Owner: Member A.

Plain words: x[i,j] = 1 means one driver does trip j right after trip i. Every trip either starts a duty (u = 1)
or has exactly one predecessor, and either ends a duty (v = 1) or has exactly one successor, so the chosen arcs
cut the trips into chains = duties. T carries each duty's start time along the chain (spread rule) and D adds up
the driving minutes (driving rule). Constraint numbers (1)-(7) and names follow Master Plan §3.1.

    build_arcflow(inst, arcs, relax=False, naive_m=False) -> (model, {"x", "u", "v", "T", "D"})
    decode_arcflow(inst, vars) -> schedule
"""
from __future__ import annotations

import gurobipy as gp
from gurobipy import GRB

from crew import config
from crew.graph import big_m_bounds
from crew.instance import Instance, Schedule

N = config.CONSTRAINT_NAMES


def build_arcflow(inst: Instance, arcs, relax: bool = False, naive_m: bool = False):
    """Build Model 1. relax=True makes x, u, v continuous in [0, 1] (LP relaxation).
    naive_m=True (task A6) uses one big constant per family instead of the tight per-arc constants."""
    trips = inst.trips
    n = len(trips)
    arcs = [tuple(a) for a in arcs]
    ell, U = big_m_bounds(inst)
    s = [t.start for t in trips]
    e = [t.end for t in trips]
    d = [t.end - t.start for t in trips]

    # Big-M constants. Tight (default): per arc, from the variable bounds (Theorem 2).
    # Naive (A6): one constant per family, valid for every arc (checked below, Q21).
    if naive_m:
        MT_glob, MD_glob = max(s) - min(ell), inst.W
        assert all(MT_glob >= s[j] - ell[i] and MD_glob >= U[i] for i, j in arcs), "naive M not valid"
        MT = {(i, j): MT_glob for i, j in arcs}
        MD = {(i, j): MD_glob for i, j in arcs}
    else:
        MT = {(i, j): s[j] - ell[i] for i, j in arcs}
        MD = {(i, j): U[i] for i, j in arcs}

    model = gp.Model(f"arcflow_{inst.name}")
    vtype = GRB.CONTINUOUS if relax else GRB.BINARY
    J = range(n)
    x = model.addVars(arcs, lb=0.0, ub=1.0, vtype=vtype, name="x")
    u = model.addVars(J, lb=0.0, ub=1.0, vtype=vtype, name="u")
    v = model.addVars(J, lb=0.0, ub=1.0, vtype=vtype, name="v")
    T = model.addVars(J, lb=ell, ub=s, name="T")          # (3) c3_Tbound: ell_j <= T_j <= s_j (bounds, not rows)
    D = model.addVars(J, lb=d, ub=U, name="D")            # (7) c7_Dbound: d_j <= D_j <= U_j (bounds, not rows)

    # Objective: F * (number of duties) + c * (total driving, a constant) + c * (waiting on used arcs)
    model.setObjective(inst.F * u.sum() + inst.c_per_min * sum(d)
                       + inst.c_per_min * gp.quicksum((s[j] - e[i]) * x[i, j] for i, j in arcs), GRB.MINIMIZE)

    preds = {j: [] for j in J}
    succs = {i: [] for i in J}
    for i, j in arcs:
        preds[j].append(i)
        succs[i].append(j)

    # (1) each trip is first in its duty or has exactly one predecessor
    model.addConstrs((u[j] + gp.quicksum(x[i, j] for i in preds[j]) == 1 for j in J), name=N[1])
    # (2) each trip is last in its duty or has exactly one successor
    model.addConstrs((v[i] + gp.quicksum(x[i, j] for j in succs[i]) == 1 for i in J), name=N[2])
    # (4) the duty start time is carried along the chain
    model.addConstrs((T[j] <= T[i] + MT[i, j] * (1 - x[i, j]) for i, j in arcs), name=N[4])
    # (5) spread rule (redundant given (3)-(4); kept for readability, presolve removes it)
    model.addConstrs((e[j] - T[j] <= inst.L for j in J), name=N[5])
    # (6) driving adds up along the chain
    model.addConstrs((D[j] >= D[i] + d[j] - MD[i, j] * (1 - x[i, j]) for i, j in arcs), name=N[6])

    model.update()
    return model, {"x": x, "u": u, "v": v, "T": T, "D": D}


def decode_arcflow(inst: Instance, vars: dict) -> Schedule:
    """Turn a solved model into duties: start at every trip with u = 1 and follow arcs with x >= 0.5."""
    nxt = {i: j for (i, j), var in vars["x"].items() if var.X >= 0.5}
    schedule = []
    for j in range(len(inst.trips)):
        if vars["u"][j].X >= 0.5:
            duty = [j]
            while duty[-1] in nxt:
                duty.append(nxt[duty[-1]])
            schedule.append(duty)
    return schedule
