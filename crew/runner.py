"""Experiment runner (tasks C3/C4, C8). Owner: Member C.

    python -m crew.runner --instances instances/proto --methods H,AF,AF+S,SP,SP+S --out results/runs.csv

* One subprocess per (instance, method), killed after cfg["HARD_KILL_S"]: a crash or memory blow-up loses one run,
  never the night (status KILLED, with the phase it reached).
* One row per run in runs.csv (columns of Master Plan §10.7). The whole file is rewritten atomically after every
  run, so an interrupted batch never leaves a half-written row.
* Resume (§10.6): a run is skipped if a non-superseded row with the same (instance_sha256, method, config_hash)
  exists. ERROR rows and KILLED-during-solve rows are rerun ONCE; the first row is kept and marked superseded.
* Methods are ordered H first per instance, so '+S' methods find the heuristic cache.
"""
from __future__ import annotations

import argparse
import csv
import functools
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Iterable, Optional

from crew import config, sysinfo
from crew.instance import load_instance
from crew.run_child import METHODS
from crew.version import REPO_DIR, file_sha256, git_commit

COLUMNS = [
    # Master Plan §10.7
    "run_id", "timestamp", "git_commit", "instance_sha256", "config_hash", "gurobi_version", "machine_id",
    "instance", "generator", "seed", "n", "m", "L", "W", "n_arcs", "class", "method", "status",
    "gurobi_status_code", "feasible_checked", "objective", "best_bound", "gap_pct", "globally_proven",
    "solver_time_s", "end_to_end_s", "t_pre_s", "t_heur_s", "t_enum_s", "t_build_s", "n_vars", "n_constrs",
    "n_nonzeros", "nodes", "n_duties", "enumeration_complete", "start_given", "start_accepted", "heuristic_cost",
    "peak_rss_mb", "threads", "time_limit_s", "build_limit_s", "log_file", "solution_file",
    # added in v1.3 / v1.4.1
    "superseded", "lp_obj", "root_bound", "obj_bound_raw", "t_first_incumbent_s", "first_incumbent_obj",
    "n_incumbents", "int_vio", "constr_vio", "trajectory_file",
    # runner bookkeeping: the fifth timer (end_to_end_s = sum of all five), the phase of a KILLED run, errors
    "t_solve_s", "killed_phase", "error",
]
RERUN_ONCE = {"ERROR"}                       # plus KILLED with killed_phase == "solve" (infrastructure failure)
METHOD_ORDER = list(METHODS)                 # H first


def _slug(method: str) -> str:
    return method.replace("+", "p")


@functools.lru_cache(maxsize=1)
def _machine() -> dict:
    return sysinfo.machine_info()                  # imports gurobipy: compute once per process


def machine_id() -> str:
    """Short, non-personal fingerprint of the hardware/software (no host or user names)."""
    blob = json.dumps(_machine(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


# ------------------------------------------------------------------ csv io

def read_rows(csv_path: str) -> list[dict]:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{csv_path} has different columns than this runner; refusing to mix formats")
        return list(reader)


def write_rows(csv_path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    tmp = csv_path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({k: "" if r.get(k) is None else r.get(k, "") for k in COLUMNS})
    os.replace(tmp, csv_path)


def write_env(results_dir: str, cfg: dict) -> str:
    """results/env.txt: the run machine and the frozen settings (task C8)."""
    path = os.path.join(results_dir, "env.txt")
    os.makedirs(results_dir, exist_ok=True)
    info = {**_machine(), "machine_id": machine_id(), "git_commit": git_commit(),
            "config_hash": config.config_hash(cfg), "settings": cfg}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1, sort_keys=True)
    return path


# ------------------------------------------------------------------ one run

def run_one(inst_path: str, method: str, cfg: dict, results_dir: str = "results", attempt: int = 1) -> dict:
    """Run one (instance, method) in its own process and return exactly one runs.csv row (Master Plan §7.3)."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {list(METHODS)}")
    inst = load_instance(inst_path)                      # validates V1-V10 before spending any solver time
    inst_sha, cfg_hash, code = file_sha256(inst_path), config.config_hash(cfg), git_commit()
    run_id = f"{inst.name}.{_slug(method)}.{cfg_hash[:8]}.{attempt}"
    tmp_dir = os.path.join(results_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    job_path = os.path.join(tmp_dir, run_id + ".job.json")
    result_path = os.path.join(tmp_dir, run_id + ".result.json")
    phase_path = os.path.join(tmp_dir, run_id + ".phase")
    for p in (result_path, phase_path):
        if os.path.exists(p):
            os.remove(p)
    job = {"run_id": run_id, "instance_path": os.path.abspath(inst_path), "method": method, "cfg": cfg,
           "results_dir": os.path.abspath(results_dir), "instance_sha256": inst_sha, "git_commit": code,
           "heuristic_cache": os.path.abspath(os.path.join(results_dir, "heuristic", inst.name + ".json"))}
    with open(job_path, "w", encoding="utf-8") as fh:
        json.dump(job, fh)

    env = {**os.environ, "PYTHONPATH": REPO_DIR + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result: dict
    try:
        proc = subprocess.run([sys.executable, "-m", "crew.run_child", job_path], cwd=REPO_DIR, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=cfg["HARD_KILL_S"])
        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as fh:
                result = json.load(fh)
        else:                                            # crashed without writing a result (e.g. segfault, OOM kill)
            result = {"status": "ERROR", "error": f"exit code {proc.returncode}: {proc.stderr[-500:]}"}
    except subprocess.TimeoutExpired:
        phase = "start"
        if os.path.exists(phase_path):
            with open(phase_path, encoding="utf-8") as fh:
                phase = fh.read().strip() or "start"
        # config.py: KILLED_BUILD (killed before the solve: not built) vs KILLED (during the solve: runner failure)
        result = {"status": "KILLED" if phase == "solve" else "KILLED_BUILD", "killed_phase": phase,
                  "error": f"hard kill after {cfg['HARD_KILL_S']} s in phase {phase!r}"}
    result.pop("traceback", None)

    info = _machine()
    row = {k: "" for k in COLUMNS}
    row.update({k: v for k, v in result.items() if k in row})
    row.update(run_id=run_id, timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               git_commit=code, instance_sha256=inst_sha, config_hash=cfg_hash,
               gurobi_version=info.get("gurobi") or "", machine_id=machine_id(), instance=inst.name,
               generator=inst.generator, seed="" if inst.seed is None else inst.seed, n=len(inst.trips),
               m=len(inst.terminals), L=inst.L, W=inst.W, method=method, threads=cfg["GUROBI_PARAMS"]["Threads"],
               time_limit_s=cfg["GUROBI_TIME_LIMIT_S"], build_limit_s=cfg["BUILD_LIMIT_S"], superseded="no")
    return row


# ------------------------------------------------------------------ batch with resume

def _needs_run(existing: list[dict]) -> tuple[bool, Optional[dict]]:
    """Decide from the rows already present for one (instance, method, config) key.
    Returns (run_it, row_to_mark_superseded)."""
    live = [r for r in existing if r["superseded"] != "yes"]
    if not existing:
        return True, None
    if len(existing) == 1 and len(live) == 1:
        r = live[0]
        infra_failure = r["status"] in RERUN_ONCE or (r["status"] == "KILLED" and r["killed_phase"] == "solve")
        if infra_failure:
            return True, r
    return False, None


def run_all(instance_paths: Iterable[str], methods: Iterable[str], cfg: dict, csv_path: str,
            results_dir: Optional[str] = None, log=print) -> None:
    """Resumable batch (Master Plan §7.3). Safe to stop and restart at any moment."""
    results_dir = results_dir or os.path.dirname(os.path.abspath(csv_path))
    methods = sorted(set(methods), key=METHOD_ORDER.index)
    unknown = [m for m in methods if m not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods {unknown}")
    write_env(results_dir, cfg)
    rows = read_rows(csv_path)
    cfg_hash = config.config_hash(cfg)

    for path in instance_paths:
        inst_sha = file_sha256(path)
        for method in methods:
            existing = [r for r in rows if (r["instance_sha256"], r["method"], r["config_hash"])
                        == (inst_sha, method, cfg_hash)]
            go, supersede = _needs_run(existing)
            if not go:
                continue
            row = run_one(path, method, cfg, results_dir, attempt=len(existing) + 1)
            if supersede is not None:
                supersede["superseded"] = "yes"
            rows.append(row)
            write_rows(csv_path, rows)
            log(f"{row['instance']:<28} {method:<12} {row['status']:<17} obj={row['objective']!s:<10} "
                f"e2e={_fmt(row['end_to_end_s'])} s")


def _fmt(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "-"


def _expand(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        out.extend(sorted(glob.glob(os.path.join(p, "*.json"))) if os.path.isdir(p) else [p])
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run every (instance, method) pair and append rows to runs.csv.")
    ap.add_argument("--instances", nargs="+", required=True, help="instance files and/or folders of *.json")
    ap.add_argument("--methods", required=True, help="comma-separated, e.g. H,AF,AF+S,SP,SP+S")
    ap.add_argument("--out", default=os.path.join("results", "runs.csv"))
    args = ap.parse_args(argv)
    run_all(_expand(args.instances), args.methods.split(","), config.config_snapshot(), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
