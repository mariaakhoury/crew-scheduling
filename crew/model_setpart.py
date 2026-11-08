"""Model 2: set partitioning over complete duties. Owner: Member B (task B3).

    min  sum_p c_p z_p
    s.t. sum_{p in P: i in p} z_p = 1     for every trip i      (8)  Gurobi name c8_cover[i]
         z_p in {0, 1}                    for every duty p in P

P is the COMPLETE set of legal duties from duties.enumerate_duties; c_p = F + c * spread(p).
Size (checked by Q28): |P| variables, n rows, sum_p |p| nonzeros.

The duty cost is computed here from the instance data on purpose, not imported from checker.py,
so the independent checker can catch a cost bug in the model.
"""
from __future__ import annotations

import gurobipy as gp
from gurobipy import GRB

from crew import config
from crew.instance import Instance, Schedule


def setpart_cost(inst: Instance, duty) -> float:
    """c_p = F + c_per_min * (end of last trip - start of first trip)."""
    T = inst.trips
    return inst.F + inst.c_per_min * (T[duty[-1]].end - T[duty[0]].start)


def apply_params(model: gp.Model) -> None:
    """Only for solve_setpart (tests / notebook demo): the same frozen parameters the runner sets."""
    params = config.GUROBI_PARAMS
    for name in sorted(params, key=lambda k: k != "LogToConsole"):   # silence the console first
        model.setParam(name, params[name])
    model.setParam("TimeLimit", config.GUROBI_TIME_LIMIT_S)


def build_setpart(inst: Instance, duties, relax: bool = False,
                  env: gp.Env | None = None) -> tuple[gp.Model, dict]:
    """Build Model 2 over the given (complete) list of duties, WITHOUT calling optimize().
    relax=True gives the LP relaxation (0 <= z <= 1), used for LP-SP and Theorem 3 / Q22.
    Sets NO Gurobi parameters: the runner sets them from config.py (repo rule, AGENTS.md).
    Returns (model, {"z": variables keyed by duty index, "cover": rows keyed by trip id})."""
    n = len(inst.trips)
    model = gp.Model(f"SP_{inst.name}", env=env) if env is not None else gp.Model(f"SP_{inst.name}")

    # Variables z_p: one per duty, objective coefficient c_p
    costs = [setpart_cost(inst, d) for d in duties]
    vtype = GRB.CONTINUOUS if relax else GRB.BINARY
    z = model.addVars(len(duties), lb=0.0, ub=1.0, obj=costs, vtype=vtype, name="z")
    model.ModelSense = GRB.MINIMIZE

    # Which duties contain trip i (column structure of the cover rows)
    covering: list[list[int]] = [[] for _ in range(n)]
    for p, duty in enumerate(duties):
        for i in duty:
            covering[i].append(p)

    # (8) every trip is covered by exactly one chosen duty
    cover = model.addConstrs((gp.quicksum(z[p] for p in covering[i]) == 1 for i in range(n)),
                             name=config.CONSTRAINT_NAMES[8])
    model.update()
    return model, {"z": z, "cover": cover}


def decode_setpart(inst: Instance, duties, vars: dict) -> Schedule:
    """Chosen duties (z_p > 0.5) as a schedule; trips inside each duty are already in start order."""
    z = vars["z"]
    return [list(duties[p]) for p in range(len(duties)) if z[p].X > 0.5]


def solve_setpart(inst: Instance, duties, relax: bool = False, log_file: str | None = None,
                  env: gp.Env | None = None) -> dict:
    """Convenience wrapper for tests and the notebook demo: build, optimise, decode.
    The experiment runner (Member C) does its own timing and status handling."""
    model, vars = build_setpart(inst, duties, relax=relax, env=env)
    apply_params(model)                    # same frozen parameters the runner uses
    if log_file:
        model.setParam("LogFile", log_file)
    model.optimize()
    out = {"status": model.Status, "num_vars": model.NumVars, "num_constrs": model.NumConstrs,
           "num_nz": model.NumNZs, "objective": None, "bound": None, "nodes": None, "schedule": None,
           "runtime": model.Runtime}
    if model.SolCount > 0:
        out["objective"] = model.ObjVal
        if not relax:
            out["bound"] = model.ObjBound
            out["nodes"] = model.NodeCount
            out["schedule"] = decode_setpart(inst, duties, vars)
    model.dispose()
    return out
