"""HiGHS fallback for DEVELOPMENT without a full Gurobi licence. Owner: Member B.

NOT for graded results: the professor requires the models in Python with Gurobi, and every final run uses Gurobi
on one machine (Master Plan §10.5). The runner does not use this file. It exists so that anyone can build and
solve the real models on instances above the free licence's 2,000-variable limit while the licence is missing.

How it works: the model is built with gurobipy exactly as in the experiments (building needs no licence; only
optimize() is size-limited), its matrix is copied into HiGHS and solved there. Settings come from config.py
(time limit, MIPGap, MIPGapAbs = 0.49, seed), so OPTIMAL means the same exact-optimum certificate.
Decoding reuses the models' own decode functions through a solution view that carries the HiGHS values as `.X`.

    python -m crew.highs_fallback --instances instances/proto --models AF,SP      # P0-P5 check
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from types import SimpleNamespace

import gurobipy as gp
from gurobipy import GRB

from crew import config

try:
    import highspy
except ImportError:                                  # optional dependency: pip install highspy
    highspy = None

INF_GRB = GRB.INFINITY


def _require_highs() -> None:
    if highspy is None:
        raise ImportError("HiGHS fallback needs the optional package highspy: pip install highspy")


def _to_highs_lp(model: gp.Model):
    """Copy a gurobipy model (variables, bounds, types, linear rows, objective + constant) into a HighsLp."""
    model.update()
    vars_ = model.getVars()
    constrs = model.getConstrs()
    if model.NumQConstrs or model.NumSOS or model.NumGenConstrs or model.IsQP:
        raise ValueError("HiGHS fallback supports linear models only")
    col = {v.index: k for k, v in enumerate(vars_)}
    inf = highspy.kHighsInf

    def cap(x):
        return inf if x >= INF_GRB else (-inf if x <= -INF_GRB else x)

    lp = highspy.HighsLp()
    lp.num_col_ = len(vars_)
    lp.num_row_ = len(constrs)
    lp.col_cost_ = model.getAttr("Obj", vars_)
    lp.col_lower_ = [cap(x) for x in model.getAttr("LB", vars_)]
    lp.col_upper_ = [cap(x) for x in model.getAttr("UB", vars_)]
    lp.offset_ = model.ObjCon
    lp.sense_ = highspy.ObjSense.kMinimize if model.ModelSense == GRB.MINIMIZE else highspy.ObjSense.kMaximize
    vtypes = model.getAttr("VType", vars_)
    if any(t in "BI" for t in vtypes):
        lp.integrality_ = [highspy.HighsVarType.kInteger if t in "BI" else highspy.HighsVarType.kContinuous
                           for t in vtypes]
    lower, upper, start, index, value = [], [], [0], [], []
    for c, sense, rhs in zip(constrs, model.getAttr("Sense", constrs), model.getAttr("RHS", constrs)):
        row = model.getRow(c)
        for k in range(row.size()):
            index.append(col[row.getVar(k).index])
            value.append(row.getCoeff(k))
        start.append(len(index))
        lower.append(rhs if sense in ">=" else -inf)
        upper.append(rhs if sense in "<=" else inf)
    lp.row_lower_, lp.row_upper_ = lower, upper
    lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = start, index, value
    lp.a_matrix_.num_col_, lp.a_matrix_.num_row_ = lp.num_col_, lp.num_row_
    return lp, vars_


def solve_with_highs(model: gp.Model, time_limit_s: float | None = None, log_file: str | None = None) -> dict:
    """Solve a built (not optimized) gurobipy model with HiGHS. Returns status (runner vocabulary where it applies:
    OPTIMAL, TIME_LIMIT, TIME_LIMIT_NOSOL, INFEASIBLE, ERROR), objective, bound, gap_pct, nodes, runtime, and the
    variable values by name. The gurobipy model is left unsolved."""
    _require_highs()
    lp, vars_ = _to_highs_lp(model)
    h = highspy.Highs()
    h.setOptionValue("output_flag", bool(log_file))
    if log_file:
        h.setOptionValue("log_file", log_file)
        h.setOptionValue("log_to_console", False)
    p = config.GUROBI_PARAMS
    h.setOptionValue("time_limit", float(time_limit_s if time_limit_s is not None else config.GUROBI_TIME_LIMIT_S))
    h.setOptionValue("mip_rel_gap", float(p["MIPGap"]))
    h.setOptionValue("mip_abs_gap", float(p["MIPGapAbs"]))
    h.setOptionValue("random_seed", int(p["Seed"]))
    h.passModel(lp)
    t0 = time.perf_counter()
    h.run()
    runtime = time.perf_counter() - t0
    ms = h.getModelStatus()
    info = h.getInfo()
    is_mip = lp.integrality_ is not None and len(lp.integrality_) > 0
    has_sol = info.primal_solution_status == 2           # 2 = feasible point available
    S = highspy.HighsModelStatus
    if ms == S.kOptimal:
        status = "OPTIMAL"
    elif ms == S.kTimeLimit:
        status = "TIME_LIMIT" if has_sol else "TIME_LIMIT_NOSOL"
    elif ms in (S.kInfeasible, S.kUnboundedOrInfeasible):
        status = "INFEASIBLE"
    else:
        status = "ERROR"
    out = {"solver": "HiGHS " + h.version(), "status": status, "highs_status": h.modelStatusToString(ms),
           "objective": info.objective_function_value if has_sol else None,
           "bound": (info.mip_dual_bound if is_mip else (info.objective_function_value if has_sol else None)),
           "nodes": info.mip_node_count if is_mip else None, "runtime": runtime,
           "num_vars": lp.num_col_, "num_constrs": lp.num_row_, "num_nz": len(lp.a_matrix_.value_),
           "values": None}
    if has_sol:
        out["values"] = list(h.getSolution().col_value)        # position k = gurobipy Var.index k
        if out["bound"] is not None and out["objective"]:
            out["gap_pct"] = 100 * (out["objective"] - out["bound"]) / out["objective"]
    return out


def solution_view(vars: dict, values: list) -> dict:
    """Same structure as the models' variable dicts, but every variable is replaced by an object whose .X is the
    HiGHS value, so decode_setpart / decode_arcflow can be reused unchanged. Call it BEFORE disposing the model
    (Var.index is read from the live model)."""
    out = {}
    for key, td in vars.items():
        if hasattr(td, "items"):
            out[key] = {k: SimpleNamespace(X=values[v.index]) for k, v in td.items()}
        else:
            out[key] = td
    return out


def solve_instance(inst, model: str = "SP", relax: bool = False, time_limit_s: float | None = None) -> dict:
    """Build Model 1 (AF) or Model 2 (SP) for one instance, solve it with HiGHS, decode and check the schedule."""
    from crew.checker import check_schedule
    from crew.duties import COMPLETE, enumerate_duties, get_arcs
    arcs = get_arcs(inst)
    if model == "SP":
        from crew.model_setpart import build_setpart, decode_setpart
        duties, status, count = enumerate_duties(inst, arcs, config.COLUMN_CAP,
                                                 time.perf_counter() + config.BUILD_LIMIT_S)
        if status != COMPLETE:
            return {"status": "COLUMN_CAP" if status == "capped" else "BUILD_LIMIT", "n_duties": count}
        m, mvars = build_setpart(inst, duties, relax=relax)
        decode = lambda view: decode_setpart(inst, duties, view)   # noqa: E731
    elif model == "AF":
        from crew.model_arcflow import build_arcflow, decode_arcflow
        m, mvars = build_arcflow(inst, arcs, relax=relax)
        decode = lambda view: decode_arcflow(inst, view)           # noqa: E731
    else:
        raise ValueError("model must be 'AF' or 'SP'")
    res = solve_with_highs(m, time_limit_s=time_limit_s)
    res["schedule"] = res["check_ok"] = None
    if not relax and res["values"] is not None:
        res["schedule"] = decode(solution_view(mvars, res["values"]))
    m.dispose()                                               # only after decoding (the view reads Var.index)
    if res["schedule"] is not None:
        chk = check_schedule(inst, res["schedule"], res["objective"])
        res["check_ok"] = chk.ok
        if not chk.ok:
            res["status"] = "CHECK_FAILED"
            res["check_errors"] = chk.errors[:3]
    res.pop("values")
    return res


def main(argv=None) -> None:
    from crew.instance import load_instance
    ap = argparse.ArgumentParser(description="Solve AF / SP with HiGHS (development fallback, not graded).")
    ap.add_argument("--instances", nargs="+", required=True, help="files and/or folders of *.json")
    ap.add_argument("--models", default="AF,SP")
    ap.add_argument("--relax", action="store_true", help="solve the LP relaxations instead")
    ap.add_argument("--time-limit", type=float, default=None)
    a = ap.parse_args(argv)
    paths = []
    for p in a.instances:
        paths += sorted(glob.glob(os.path.join(p, "*.json"))) if os.path.isdir(p) else [p]
    print(f"{'instance':28s} {'model':5s} {'status':14s} {'objective':>10s} {'reference':>10s} {'match':>5s} "
          f"{'vars':>7s} {'nodes':>6s} {'time s':>7s} check")
    bad = 0
    for path in paths:
        inst = load_instance(path)
        ref = (inst.reference or {}).get("cost")
        for model in a.models.split(","):
            r = solve_instance(inst, model, relax=a.relax, time_limit_s=a.time_limit)
            obj = r.get("objective")
            obj = None if obj is None else round(obj, 2)             # display only (8945.999999 -> 8946.0)
            kind = (inst.reference or {}).get("kind")
            match = "" if obj is None or ref is None or a.relax else (
                "yes" if abs(obj - ref) <= config.COST_TOL else ("n/a" if kind != "optimal" else "NO"))
            bad += match == "NO" or r["status"] in ("CHECK_FAILED", "ERROR", "INFEASIBLE")
            print(f"{inst.name:28s} {model:5s} {r['status']:14s} {obj if obj is not None else '':>10} "
                  f"{ref if ref is not None else '':>10} {match:>5s} {r.get('num_vars', ''):>7} "
                  f"{r.get('nodes') if r.get('nodes') is not None else '':>6} {r.get('runtime', 0):7.2f} "
                  f"{'' if r.get('check_ok') is None else ('OK' if r['check_ok'] else 'FAILED')}", flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
