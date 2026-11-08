"""One run = one process (tasks C3/C4/C5). Owner: Member C.

Started only by crew.runner:   python -m crew.run_child <job.json>
The job file names the instance, the method, the frozen settings (cfg) and where to write. The child
  * writes its current phase to <run_id>.phase (so a hard kill can still report how far it got),
  * times the five phases with time.perf_counter(): t_pre (arcs), t_heur, t_enum, t_build, t_solve,
  * translates the outcome into the status taxonomy of Master Plan §10.6 (classify / certify below),
  * writes <run_id>.result.json, plus the solution file; the Gurobi log goes to results/logs/<run_id>.log.

Model code is imported lazily through the shared interfaces of Master Plan §7.3 (graph, model_arcflow, duties,
model_setpart, integration). A module that does not exist yet gives status ERROR with a clear message, never a
silent fallback. Every setting comes from cfg (= config.config_snapshot()), never from literals in this file.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from contextlib import contextmanager
from typing import Any, Iterator, NamedTuple, Optional

from crew import sysinfo
from crew.checker import check_schedule
from crew.instance import Instance, Schedule, load_instance


class MethodSpec(NamedTuple):
    model: Optional[str]      # None (heuristic only), "AF" or "SP"
    start: bool               # give the heuristic schedule to Gurobi as a MIP start
    relax: bool = False       # LP relaxation run
    naive_m: bool = False     # AF with one big-M per family (task A6)


METHODS: dict[str, MethodSpec] = {
    "H": MethodSpec(None, False),
    "AF": MethodSpec("AF", False),
    "AF+S": MethodSpec("AF", True),
    "SP": MethodSpec("SP", False),
    "SP+S": MethodSpec("SP", True),
    "LP-AF": MethodSpec("AF", False, relax=True),
    "LP-SP": MethodSpec("SP", False, relax=True),
    "LP-AF-naive": MethodSpec("AF", False, relax=True, naive_m=True),
}

# Gurobi Status codes (gurobipy.GRB.Status) -> taxonomy. Kept as numbers so this module imports without gurobipy.
GRB_OPTIMAL, GRB_INFEASIBLE, GRB_INF_OR_UNBD, GRB_TIME_LIMIT = 2, 3, 4, 9
GRB_NUMERIC, GRB_SUBOPTIMAL, GRB_MEM_LIMIT = 12, 13, 17
_OTHER_STATUS = {GRB_INFEASIBLE: "INFEASIBLE", GRB_INF_OR_UNBD: "INF_OR_UNBD",
                 GRB_NUMERIC: "NUMERIC", GRB_SUBOPTIMAL: "SUBOPTIMAL", GRB_MEM_LIMIT: "MEM_LIMIT_SOLVE"}


class BuildStop(Exception):
    """A build-phase outcome that is not an error: BUILD_LIMIT, COLUMN_CAP or MEM_LIMIT_BUILD."""
    def __init__(self, status: str, detail: str = ""):
        super().__init__(f"{status}: {detail}")
        self.status = status


# ------------------------------------------------------------------ pure status logic (unit-tested)

def classify(gurobi_code: int, sol_count: int) -> str:
    """Gurobi status code + number of solutions -> preliminary status (before the checker and certificate)."""
    if gurobi_code == GRB_OPTIMAL:
        return "OPTIMAL"
    if gurobi_code == GRB_TIME_LIMIT:
        return "TIME_LIMIT" if sol_count > 0 else "TIME_LIMIT_NOSOL"
    return _OTHER_STATUS.get(gurobi_code, "ERROR")


def certify(inst: Instance, schedule: Optional[Schedule], objective: float, bound: float,
            cfg: dict) -> tuple[bool, float | None, str]:
    """Optimality certificate of Master Plan §10.6 for a status-2 full-model run.
    Returns (proven, checker_cost, reason_if_not). All four conditions must hold:
    checker accepts the schedule; checker cost == objective (COST_TOL); objective is a multiple of COST_STEP;
    objective - bound <= MIPGapAbs."""
    tol, step = cfg["COST_TOL"], cfg["COST_STEP"]
    if schedule is None:
        return False, None, "no decoded schedule"
    res = check_schedule(inst, schedule)
    if not res.ok:
        return False, None, "checker rejected the schedule: " + "; ".join(res.errors[:3])
    if abs(res.cost - objective) > tol:
        return False, res.cost, f"checker cost {res.cost} != objective {objective}"
    if abs(objective / step - round(objective / step)) * step > tol:
        return False, res.cost, f"objective {objective} is not a multiple of {step}"
    if objective - bound > cfg["GUROBI_PARAMS"]["MIPGapAbs"] + 1e-9:
        return False, res.cost, f"objective - bound = {objective - bound} > MIPGapAbs"
    return True, res.cost, ""


def gap_pct(objective: Optional[float], bound: Optional[float]) -> Optional[float]:
    """100 x (value - bound) / value; only defined with an incumbent (never averaged as 0 or 100)."""
    if objective is None or bound is None or objective == 0:
        return None
    return 100.0 * (objective - bound) / objective


# ------------------------------------------------------------------ helpers

class _Phase:
    """Writes the current phase to disk (one tiny write per phase) and keeps the five timers."""
    def __init__(self, path: str):
        self.path, self.timers = path, {}

    def set(self, name: str) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(name)

    @contextmanager
    def timed(self, name: str) -> Iterator[None]:
        self.set(name)
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.timers[name] = self.timers.get(name, 0.0) + time.perf_counter() - t0


def _atomic_json(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(tmp, path)


def _arcs(inst: Instance):
    """A's trip network (A1). Until graph.py exists, the same rule computed here (identical to checker rule C4)."""
    try:
        from crew.graph import build_arcs
    except ModuleNotFoundError:
        from crew.greedy import can_follow
        T = inst.trips
        return [(a.id, b.id) for a in T for b in T if can_follow(inst, a, b)]
    return build_arcs(inst)


def load_or_run_heuristic(inst: Instance, inst_sha: str, code_version: str, cache_path: str,
                          time_limit_s: float) -> dict:
    """Heuristic cache (Master Plan §10.5): H runs once per instance and code version; '+S' methods reuse it,
    including its measured time t_heur_s."""
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("instance_sha256") == inst_sha and cached.get("git_commit") == code_version:
            return cached
    from crew.greedy import greedy_insertion
    from crew.localsearch import improve
    t0 = time.perf_counter()
    g = greedy_insertion(inst)
    res = improve(inst, g, time_limit_s=max(time_limit_s - (time.perf_counter() - t0), 0.0))
    entry = {"instance": inst.name, "instance_sha256": inst_sha, "git_commit": code_version,
             "greedy_cost": res.start_cost, "cost": res.cost, "schedule": res.schedule,
             "t_heur_s": time.perf_counter() - t0, "stopped_by": res.stopped_by, "moves": res.moves}
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    _atomic_json(cache_path, entry)
    return entry


# ------------------------------------------------------------------ the run

def run(job: dict) -> dict:
    cfg, spec = job["cfg"], METHODS[job["method"]]
    run_id, results = job["run_id"], job["results_dir"]
    tmp_dir = os.path.join(results, "tmp")
    ph = _Phase(os.path.join(tmp_dir, run_id + ".phase"))
    out: dict[str, Any] = {"status": "ERROR", "start_given": "yes" if spec.start else "no"}
    t_start = time.perf_counter()
    deadline = t_start + cfg["BUILD_LIMIT_S"]                       # build budget: pre + heur + enum + build

    try:
        ph.set("load")
        inst = load_instance(job["instance_path"])

        with ph.timed("pre"):
            arcs = _arcs(inst)
        out["n_arcs"] = len(arcs)

        heur = None
        if spec.model is None or spec.start:
            with ph.timed("heur"):
                heur = load_or_run_heuristic(inst, job["instance_sha256"], job["git_commit"],
                                             job["heuristic_cache"], deadline - time.perf_counter())
            ph.timers["heur"] = heur["t_heur_s"]                    # stored time counts, also when loaded from cache
            out["heuristic_cost"] = heur["cost"]

        if spec.model is None:                                      # method H: heuristic only
            res = check_schedule(inst, heur["schedule"], heur["cost"])
            out.update(status="HEURISTIC" if res.ok else "CHECK_FAILED", objective=heur["cost"],
                       feasible_checked="yes" if res.ok else "no", globally_proven="no")
            out["solution_file"] = _save_solution(results, run_id, heur["schedule"], heur["cost"])
        else:
            _solve_mip(inst, arcs, heur, spec, cfg, job, ph, deadline, out)

    except BuildStop as stop:
        out.update(status=stop.status, error=str(stop))
    except MemoryError:
        out.update(status="MEM_LIMIT_BUILD", error="MemoryError before the solve")
    except ModuleNotFoundError as exc:
        out.update(status="ERROR", error=f"missing module {exc.name!r} (not written yet?)")
    except Exception as exc:                                         # noqa: BLE001 - every failure becomes a row
        out.update(status="ERROR", error=f"{type(exc).__name__}: {exc}"[:500],
                   traceback=traceback.format_exc()[-2000:])

    t = ph.timers
    out.update(t_pre_s=t.get("pre"), t_heur_s=t.get("heur"), t_enum_s=t.get("enum"),
               t_build_s=t.get("build"), t_solve_s=t.get("solve"),
               end_to_end_s=sum(v for v in (t.get(k) for k in ("pre", "heur", "enum", "build", "solve")) if v),
               peak_rss_mb=round(sysinfo.peak_memory_mb(), 1))
    return out


def _save_solution(results: str, run_id: str, schedule: Schedule, cost: float) -> str:
    rel = os.path.join("solutions", run_id + ".json")
    os.makedirs(os.path.join(results, "solutions"), exist_ok=True)
    _atomic_json(os.path.join(results, rel), {"run_id": run_id, "cost": cost, "schedule": schedule})
    return rel.replace(os.sep, "/")


def _solve_mip(inst, arcs, heur, spec: MethodSpec, cfg, job, ph: _Phase, deadline: float, out: dict) -> None:
    run_id, results = job["run_id"], job["results_dir"]
    duties = None

    if spec.model == "SP":
        from crew.duties import enumerate_duties
        with ph.timed("enum"):
            duties, enum_status, count = enumerate_duties(inst, arcs, cfg["COLUMN_CAP"], deadline)
        out.update(n_duties=count, enumeration_complete="yes" if enum_status == "complete" else "no")
        if enum_status == "capped":
            raise BuildStop("COLUMN_CAP", f"{count} duties > cap {cfg['COLUMN_CAP']}")
        if enum_status != "complete":
            raise BuildStop("BUILD_LIMIT", f"enumeration stopped ({enum_status}) after {count} duties")

    with ph.timed("build"):
        if spec.model == "AF":
            from crew.model_arcflow import build_arcflow
            model, mvars = build_arcflow(inst, arcs, relax=spec.relax, naive_m=spec.naive_m)
        else:
            from crew.model_setpart import build_setpart
            model, mvars = build_setpart(inst, duties, relax=spec.relax)
        params = cfg["GUROBI_PARAMS"]
        for name in sorted(params, key=lambda k: k != "LogToConsole"):   # silence the console first
            model.setParam(name, params[name])
        model.setParam("TimeLimit", cfg["GUROBI_TIME_LIMIT_S"])
        log_rel = os.path.join("logs", run_id + ".log")
        os.makedirs(os.path.join(results, "logs"), exist_ok=True)
        model.setParam("LogFile", os.path.join(results, log_rel))
        if spec.start:
            from crew import integration
            if spec.model == "AF":
                integration.start_arcflow(model, mvars, inst, heur["schedule"])
            else:
                integration.start_setpart(model, mvars, duties, heur["schedule"])
        model.update()
    out.update(log_file=log_rel.replace(os.sep, "/"), n_vars=model.NumVars, n_constrs=model.NumConstrs,
               n_nonzeros=model.NumNZs)
    if time.perf_counter() > deadline:
        raise BuildStop("BUILD_LIMIT", "model build finished after the build limit")

    with ph.timed("solve"):
        model.optimize()

    code, sols = model.Status, model.SolCount
    status = classify(code, sols)
    out.update(gurobi_status_code=code, solver_time_s=model.Runtime)
    if not spec.relax:
        out["nodes"] = model.NodeCount
    bound = _attr(model, "ObjBound")
    objective = model.ObjVal if sols > 0 else None
    out.update(best_bound=bound, obj_bound_raw=bound, objective=objective, gap_pct=gap_pct(objective, bound),
               int_vio=_attr(model, "IntVio"), constr_vio=_attr(model, "ConstrVio"), globally_proven="no")

    if spec.relax:
        out.update(status=status, lp_obj=objective)
        return
    if spec.start:
        from crew.integration import start_accepted
        out["start_accepted"] = "yes" if start_accepted(os.path.join(results, out["log_file"]), heur["cost"]) else "no"

    if sols > 0:
        if spec.model == "AF":
            from crew.model_arcflow import decode_arcflow
            schedule = decode_arcflow(inst, mvars)
        else:
            from crew.model_setpart import decode_setpart
            schedule = decode_setpart(inst, duties, mvars)
        res = check_schedule(inst, schedule)
        out["feasible_checked"] = "yes" if res.ok else "no"
        if not res.ok:
            out.update(status="CHECK_FAILED", error="; ".join(res.errors[:3]))
            return
        out["solution_file"] = _save_solution(results, run_id, schedule, objective)
        if status == "OPTIMAL":
            proven, _, why = certify(inst, schedule, objective, bound, cfg)
            if not proven:
                out.update(status="CHECK_FAILED", error=why)
                return
            out["globally_proven"] = "yes"
    out["status"] = status


def _attr(model, name: str) -> Optional[float]:
    """A Gurobi attribute as a finite float, else None (absent for this status, or +-inf such as 'no bound yet')."""
    try:
        value = float(getattr(model, name))
    except Exception:                                                # noqa: BLE001 - attribute absent for this status
        return None
    return value if math.isfinite(value) else None


def main(argv: list[str]) -> int:
    with open(argv[1], encoding="utf-8") as fh:
        job = json.load(fh)
    result = run(job)
    _atomic_json(os.path.join(job["results_dir"], "tmp", job["run_id"] + ".result.json"), result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
