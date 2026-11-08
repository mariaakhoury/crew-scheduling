"""Test fixtures ONLY: stand-ins for teammates' modules that do not exist yet.

Each helper uses the real module as soon as it exists (B2 crew.duties, B3 crew.model_setpart), so the tests that
use them automatically switch to the group's own code. Never import this file from crew/.
"""
import importlib.util
import time

from crew import config
from crew.checker import duty_cost, is_legal_duty
from crew.run_child import _arcs

HAVE_GUROBI = importlib.util.find_spec("gurobipy") is not None
HAVE_AF = importlib.util.find_spec("crew.model_arcflow") is not None
HAVE_SP = (importlib.util.find_spec("crew.model_setpart") is not None
           and importlib.util.find_spec("crew.duties") is not None)


def all_duties(inst) -> list[tuple[int, ...]]:
    """Every legal duty: B's enumerate_duties if it exists, else a DFS along the arcs."""
    if HAVE_SP:
        from crew.duties import enumerate_duties
        duties, status, _ = enumerate_duties(inst, _arcs(inst), config.COLUMN_CAP, time.perf_counter() + 60)
        assert status == "complete", status
        return [tuple(d) for d in duties]
    succ: dict[int, list[int]] = {}
    for a, b in _arcs(inst):
        succ.setdefault(a, []).append(b)
    out: list[tuple[int, ...]] = []

    def dfs(d: list[int]) -> None:
        out.append(tuple(d))
        for nxt in succ.get(d[-1], []):
            if is_legal_duty(inst, d + [nxt])[0]:
                dfs(d + [nxt])
    for t in range(len(inst.trips)):
        dfs([t])
    return out


def setpart_model(inst, duties):
    """B's build_setpart if it exists, else a minimal set-partitioning model with the shared row name c8_cover."""
    if HAVE_SP:
        from crew.model_setpart import build_setpart
        return build_setpart(inst, duties)
    import gurobipy as gp
    m = gp.Model()
    z = m.addVars(len(duties), vtype=gp.GRB.BINARY, obj=[duty_cost(inst, list(d)) for d in duties])
    for t in range(len(inst.trips)):
        m.addConstr(gp.quicksum(z[k] for k, d in enumerate(duties) if t in d) == 1, name=f"c8_cover[{t}]")
    return m, {"z": z}


def apply_params(model, logfile=None, **overrides) -> None:
    """The frozen Gurobi parameters from config.py (as the runner sets them), plus test overrides."""
    params = {**config.GUROBI_PARAMS, **overrides}
    for name in sorted(params, key=lambda k: k != "LogToConsole"):
        model.setParam(name, params[name])
    if logfile:
        model.setParam("LogFile", logfile)
