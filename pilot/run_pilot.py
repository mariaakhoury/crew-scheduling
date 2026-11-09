"""Pilot grid (task B5, owner B). Master Plan §10.1, stage B (Mon 9 night).

    python -m pilot.run_pilot --grid pilot/grid.json --out results/pilot.csv

1. Generates one candidate instance per grid configuration with Member A's rotation generator
   (crew.instance.make_instance, task A4) into instances/candidates/. Each file is checked with
   load_instance (rules V1-V10) right after it is written.
2. Runs AF, AF+S, SP, SP+S on every candidate through Member C's runner (crew.runner.run_all)
   at the PILOT limits from the grid file (30 s + 30 s). Pilot rows are never reported as final results.

Needs: A4 (make_instance) and C3/C4 (runner). Until they exist this script stops with a clear message.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance, save_instance  # noqa: E402


def configurations(grid: dict) -> list[dict]:
    """Expand the grid: every n with its allowed L values, every m, W = round(w_ratio * L), every seed.
    Names listed in grid["exclude"] are skipped (each exclusion must be justified in the grid's _comment)."""
    out = []
    excluded = set(grid.get("exclude", []))
    for n, m, seed in itertools.product(grid["n"], grid["m"], grid["seeds"]):
        for L in grid["L_by_n"][str(n)]:
            W = int(round(grid["w_ratio"] * L))
            name = f"rt_n{n}_m{m}_L{L}_s{seed}"
            if name not in excluded:
                out.append({"n": n, "m": m, "L": L, "W": W, "seed": seed, "name": name})
    return out


def generate(grid: dict, folder: str) -> list[str]:
    """Write one instance per configuration (skips files that already exist, so a restart is safe)."""
    from crew.instance import make_instance
    from crew.localsearch import heuristic           # C's greedy + local search builds the reference (AGENTS.md)

    def greedy_plus_local_search(inst):              # the name is stored in reference.verified_by
        return heuristic(inst).schedule

    os.makedirs(folder, exist_ok=True)
    paths = []
    for cfg in configurations(grid):
        path = os.path.join(folder, cfg["name"] + ".json")
        if not os.path.exists(path):
            inst = make_instance(cfg["name"], cfg["n"], cfg["m"], cfg["L"], cfg["W"], cfg["seed"],
                                 schedule_fn=greedy_plus_local_search, **grid.get("generator_params", {}))
            save_instance(inst, path)
        load_instance(path)                      # V1-V10 must pass, otherwise stop here
        paths.append(path)
    return paths


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default=os.path.join(ROOT, "pilot", "grid.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "pilot.csv"))
    ap.add_argument("--folder", default=os.path.join(ROOT, "instances", "candidates"))
    ap.add_argument("--generate-only", action="store_true")
    a = ap.parse_args(argv)
    with open(a.grid, encoding="utf-8") as fh:
        grid = json.load(fh)
    try:
        paths = generate(grid, a.folder)
    except NotImplementedError as exc:
        sys.exit(f"Cannot generate the pilot instances yet: {exc} (waiting for Member A, task A4)")
    print(f"{len(paths)} candidate instances in {a.folder}")
    if a.generate_only:
        return
    try:
        from crew import runner
    except ImportError:
        sys.exit("crew.runner is not available yet (waiting for Member C, tasks C3/C4)")
    # Pilot limits (30 s + 30 s) as overrides of the frozen config: they change config_hash, so pilot rows can
    # never be mistaken for final rows. The kill margin stays the same as in config.py (limits + 120 s).
    from crew import config
    t, b = grid["pilot_time_limit_s"], grid["pilot_build_limit_s"]
    margin = config.HARD_KILL_S - config.GUROBI_TIME_LIMIT_S - config.BUILD_LIMIT_S
    cfg = config.config_snapshot(GUROBI_TIME_LIMIT_S=t, BUILD_LIMIT_S=b, HARD_KILL_S=t + b + margin)
    # Gurobi's MemLimit must fit THIS machine (config.py: "about 75% of the run machine's RAM"). On a laptop with
    # less RAM than config assumes, cap it for the pilot so a big model fails cleanly (MEM_LIMIT) instead of swapping.
    from crew.sysinfo import suggested_mem_limit_gb
    fit = suggested_mem_limit_gb()
    if fit < cfg["GUROBI_PARAMS"]["MemLimit"]:
        print(f"MemLimit {cfg['GUROBI_PARAMS']['MemLimit']} GB > 75% of this machine's RAM: using {fit} GB for the pilot")
        cfg["GUROBI_PARAMS"]["MemLimit"] = fit
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    runner.run_all(paths, grid["methods"], cfg, a.out)
    print(f"pilot rows -> {a.out}; next: python -m pilot.classify --runs {a.out} --stage pilot "
          f"--out instances/final/SELECTION.md --classes-csv results/pilot_classes.csv")


if __name__ == "__main__":
    main()
