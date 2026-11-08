"""Result verification (task B8, owner B): tests Q13 and Q23 plus the fingerprint check. Master Plan §10.6.

    python -m qa.verify_results results/runs.csv [--manifest instances/final/MANIFEST.csv]

For every non-superseded row:
  Q13  every saved solution passes the independent checker, and its recomputed cost equals the row's objective;
       no INFEASIBLE / INF_OR_UNBD / CHECK_FAILED row is left unexplained (they are listed).
  Q23  every OPTIMAL row: value - raw bound <= MIPGapAbs (0.49); value is a multiple of $0.50 (+-0.01);
       checker cost = value (+-0.01); a full model (not an LP row).
  Fingerprints: instance_sha256 matches MANIFEST.csv, a single config_hash is used, and no stale row is used.
Exit code 0 only if everything passes, so it can be used as a gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.checker import check_schedule  # noqa: E402
from crew.instance import load_instance  # noqa: E402

BUG_STATUSES = ("INFEASIBLE", "INF_OR_UNBD", "CHECK_FAILED")


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def load_solution(path: str):
    """A solution file is either {"schedule": [...], ...} or the schedule list itself."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["schedule"] if isinstance(data, dict) else data


def _resolve(path: str, base: str) -> str:
    return path if os.path.isabs(path) else os.path.join(base, path)


def verify(runs_path: str, manifest_path: str | None, inst_dir: str) -> list[str]:
    problems: list[str] = []
    df = pd.read_csv(runs_path)
    if "superseded" in df.columns:
        df = df[~df["superseded"].map(_truthy)]
    results_dir = os.path.dirname(os.path.abspath(runs_path))                 # results/
    base = os.path.dirname(results_dir)                                       # repo root

    # ---- fingerprints
    manifest = None
    if manifest_path and os.path.exists(manifest_path):
        manifest = pd.read_csv(manifest_path).set_index("name")["sha256"].to_dict()
        missing = set(manifest) - set(df["instance"])
        if missing:
            problems.append(f"FINGERPRINT: instances in MANIFEST without rows: {sorted(missing)}")
    if "config_hash" in df.columns and df["config_hash"].nunique() > 1:
        problems.append(f"FINGERPRINT: {df['config_hash'].nunique()} different config_hash values (stale rows?)")
    if manifest is not None and "instance_sha256" in df.columns:
        stale = df[df.apply(lambda r: manifest.get(r["instance"]) != r["instance_sha256"], axis=1)]
        for _, r in stale.iterrows():
            problems.append(f"FINGERPRINT: stale row {r.get('run_id')} ({r['instance']}, {r['method']})")

    # ---- per row
    cache: dict[str, object] = {}
    for _, r in df.iterrows():
        rid, status, method = r.get("run_id"), str(r["status"]), str(r["method"])
        tag = f"{rid} {r['instance']} {method}"
        if status in BUG_STATUSES:
            problems.append(f"Q13: {tag} has status {status} (bug: must be investigated and explained)")
            continue
        if method.startswith("LP"):
            continue                                                          # LP rows have no schedule
        sol = r.get("solution_file")
        has_obj = pd.notna(r.get("objective"))
        if not has_obj:
            continue
        # The runner stores solution_file relative to the results folder ("solutions/<run_id>.json");
        # an older layout may store it relative to the repo root. Accept both.
        sol_path = None
        if isinstance(sol, str):
            for b in (results_dir, base):
                if os.path.exists(_resolve(sol, b)):
                    sol_path = _resolve(sol, b)
                    break
        if sol_path is None:
            problems.append(f"Q13: {tag} has an objective but no solution file")
            continue
        if r["instance"] not in cache:
            cache[r["instance"]] = load_instance(os.path.join(inst_dir, r["instance"] + ".json"))
        inst = cache[r["instance"]]
        res = check_schedule(inst, load_solution(sol_path), float(r["objective"]))
        if not res.ok:
            problems.append(f"Q13: {tag} solution rejected: {res.errors[:3]}")
            continue
        if status == "OPTIMAL":                                               # Q23 certificate
            value = float(r["objective"])
            bound = float(r["obj_bound_raw"]) if pd.notna(r.get("obj_bound_raw")) else float(r["best_bound"])
            if value - bound > config.GUROBI_PARAMS["MIPGapAbs"] + 1e-9:
                problems.append(f"Q23: {tag} value - bound = {value - bound:.4f} > 0.49")
            steps = value / config.COST_STEP
            if abs(steps - round(steps)) * config.COST_STEP > config.COST_TOL:
                problems.append(f"Q23: {tag} value {value} is not a multiple of ${config.COST_STEP}")
            if "globally_proven" in r and not _truthy(r["globally_proven"]):
                problems.append(f"Q23: {tag} is OPTIMAL but globally_proven is not yes")
        elif "globally_proven" in r and _truthy(r["globally_proven"]):
            problems.append(f"Q10: {tag} has status {status} but globally_proven = yes")
    return problems


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--manifest", default=os.path.join(ROOT, "instances", "final", "MANIFEST.csv"))
    ap.add_argument("--instances", default=os.path.join(ROOT, "instances", "final"))
    a = ap.parse_args(argv)
    problems = verify(a.runs, a.manifest, a.instances)
    for p in problems:
        print(p)
    print(f"verify_results: {'PASS' if not problems else f'{len(problems)} problem(s)'}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
