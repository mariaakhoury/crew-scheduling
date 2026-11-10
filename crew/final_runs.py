"""Final runs, one command per night (task C8, Master Plan §10.8). Owner: Member C.

    python -m crew.final_runs --night 1 --dry-run     # every pre-flight check + time projection, runs nothing
    python -m crew.final_runs --night 1               # H, AF, AF+S, SP, SP+S, LP-AF, LP-SP on instances/final
    python -m crew.final_runs --night 2               # reruns (once) of crashed runs, then LP-AF-naive

Pre-flight (all must pass, else nothing runs): HEAD is the tag v1.0-final-run with no modified tracked file;
instances/final/MANIFEST.csv lists 15-20 files whose fingerprints match; this is the agreed run machine; the laptop
is on mains power; Gurobi has a full licence. After each night: qa.verify_results on the results (Q13, Q23).

Night 2 "rerun once" needs no special code: the runner's resume re-runs ERROR / KILLED-during-solve rows exactly
once (the first row is kept and marked superseded) and skips everything else.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Callable, Iterable, Optional

import pandas as pd

from crew import config
from crew.version import REPO_DIR, _git, file_sha256

TAG = "v1.0-final-run"
FINAL_MACHINE = "b8796c6e6bd7"          # Maria's laptop, agreed in issue #1 (proposal 1)
FINAL_DIR = os.path.join("instances", "final")
RUNS_CSV = os.path.join("results", "runs.csv")
MIN_INSTANCES, MAX_INSTANCES = 15, 20

REQUIRED = ("H", "AF", "AF+S", "SP", "SP+S")
NIGHTS: dict[int, list[tuple[str, tuple[str, ...]]]] = {
    1: [("required methods + LP bounds (P0 + P1)", REQUIRED + ("LP-AF", "LP-SP"))],
    2: [("reruns of crashed runs (once each)", REQUIRED + ("LP-AF", "LP-SP")),
        ("naive big-M LP (P1)", ("LP-AF-naive",))],
}


# ----------------------------------------------------------------------------------------------- pre-flight checks
def manifest_paths(final_dir: str = FINAL_DIR) -> tuple[list[str], list[str]]:
    """(instance paths in MANIFEST order, problems). Every listed file must exist with its frozen fingerprint."""
    man_path = os.path.join(final_dir, "MANIFEST.csv")
    if not os.path.exists(man_path):
        return [], [f"{man_path} not found: has B frozen the instances (select_and_freeze)?"]
    man = pd.read_csv(man_path, dtype=str)
    problems, paths = [], []
    if not MIN_INSTANCES <= len(man) <= MAX_INSTANCES:
        problems.append(f"MANIFEST lists {len(man)} instances (need {MIN_INSTANCES}-{MAX_INSTANCES})")
    if man["name"].duplicated().any():
        problems.append(f"duplicate names in MANIFEST: {sorted(man.loc[man['name'].duplicated(), 'name'])}")
    for _, r in man.iterrows():
        p = os.path.join(final_dir, r["file"])
        if not os.path.exists(p):
            problems.append(f"missing frozen file {p}")
        elif file_sha256(p) != r["sha256"]:
            problems.append(f"{p} changed after the freeze (fingerprint differs from MANIFEST)")
        paths.append(p)
    return paths, problems


def git_problems(tag: str = TAG, git: Callable[..., Optional[str]] = _git) -> list[str]:
    head, tagged = git("rev-parse", "HEAD"), git("rev-list", "-n", "1", tag)
    if head is None:
        return ["git not available: the final runs must record an exact commit"]
    problems = []
    if not tagged:
        problems.append(f"tag {tag} does not exist yet (set it at Gate 2: git tag {tag} && git push origin {tag})")
    elif tagged != head:
        problems.append(f"HEAD {head[:7]} is not {tag} ({tagged[:7]}): git checkout {tag}")
    if git("status", "--porcelain", "--untracked-files=no"):
        problems.append("tracked files are modified: rows would carry '-dirty' (commit or stash first)")
    return problems


def machine_problems(expected: str = FINAL_MACHINE) -> list[str]:
    from crew.runner import machine_id
    got = machine_id()
    return [] if got == expected else [f"this machine is {got}, the agreed run machine is {expected}"]


def power_problems() -> list[str]:
    import psutil
    bat = psutil.sensors_battery()
    if bat is not None and not bat.power_plugged:
        return [f"on battery ({bat.percent:.0f}%): plug in the charger (battery mode slows the CPU and skews times)"]
    return []


def licence_problems() -> list[str]:
    try:
        import gurobipy as gp
        with gp.Env(params={"OutputFlag": 0}) as env, gp.Model(env=env) as m:
            x = m.addVars(2001, ub=1.0)                     # above the size-limited pip licence (2000 vars)
            m.setObjective(x.sum())
            m.optimize()
        return []
    except Exception as exc:                              # noqa: BLE001 - any licence/import failure blocks the night
        return [f"Gurobi cannot solve a 2001-variable model (full licence needed): {exc}"]


def preflight(final_dir: str = FINAL_DIR, *, rehearsal: bool = False) -> tuple[list[str], list[str]]:
    """(instance paths, problems). A rehearsal skips only the tag check (code may be newer than the tag)."""
    paths, problems = manifest_paths(final_dir)
    if not rehearsal:
        problems += git_problems()
    problems += machine_problems() + power_problems() + licence_problems()
    return paths, problems


# ----------------------------------------------------------------------------------------------- time projection
def _per_run_seconds(confirm: pd.DataFrame, cfg: dict) -> dict[str, dict[str, float]]:
    """Expected seconds per (instance, method) from the confirmation runs (same machine, same limits)."""
    worst = cfg["GUROBI_TIME_LIMIT_S"] + cfg["BUILD_LIMIT_S"]
    out: dict[str, dict[str, float]] = {}
    for name, g in confirm.groupby("instance"):
        row = {m: g.loc[g["method"] == m].iloc[0] for m in ("AF", "SP") if (g["method"] == m).any()}
        af = float(row["AF"]["end_to_end_s"]) if "AF" in row else worst
        sp = float(row["SP"]["end_to_end_s"]) if "SP" in row else worst
        af_build = float(row["AF"]["t_build_s"]) if "AF" in row and pd.notna(row["AF"]["t_build_s"]) else worst / 2
        sp_pre = (sum(float(row["SP"][c]) for c in ("t_enum_s", "t_build_s") if pd.notna(row["SP"][c]))
                  if "SP" in row else worst)
        lp_af = af_build + 5.0                            # build + LP solve: seconds, never the 120 s MIP limit
        out[str(name)] = {"H": 2.0, "AF": af, "AF+S": af, "SP": sp, "SP+S": sp,
                          "LP-AF": lp_af, "LP-AF-naive": lp_af, "LP-SP": sp_pre + 5.0}
    return out


def project_minutes(names: Iterable[str], methods: Iterable[str], confirm_csv: str = "results/confirm.csv",
                    cfg: Optional[dict] = None) -> tuple[float, float]:
    """(expected minutes, worst-case minutes). Instances missing from confirm.csv count at the worst case."""
    cfg = cfg or config.config_snapshot()
    worst = cfg["GUROBI_TIME_LIMIT_S"] + cfg["BUILD_LIMIT_S"]
    per = _per_run_seconds(pd.read_csv(confirm_csv), cfg) if os.path.exists(confirm_csv) else {}
    methods, expected, worst_total = list(methods), 0.0, 0.0
    for name in names:
        for m in methods:
            expected += per.get(name, {}).get(m, worst) + 3.0          # + subprocess start-up per run
            worst_total += (5.0 if m == "H" else worst) + 3.0
    return expected / 60, worst_total / 60


# ----------------------------------------------------------------------------------------------- the nights
def run_night(night: int, paths: list[str], out: str, log=print) -> int:
    from crew.runner import run_all
    cfg = config.config_snapshot()
    for label, methods in NIGHTS[night]:
        log(f"=== night {night}: {label}: {', '.join(methods)}")
        run_all(paths, methods, cfg, out)
    log("=== verify every saved solution (qa.verify_results, Q13/Q23)")
    report = os.path.join(os.path.dirname(out) or ".", f"B8_night{night}_report.md")
    return subprocess.call([sys.executable, "-m", "qa.verify_results", out, "--report", report], cwd=REPO_DIR)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="C8 final runs with pre-flight checks.")
    ap.add_argument("--night", type=int, choices=sorted(NIGHTS), required=True)
    ap.add_argument("--final-dir", default=FINAL_DIR)
    ap.add_argument("--out", default=RUNS_CSV)
    ap.add_argument("--dry-run", action="store_true", help="checks + projection only")
    ap.add_argument("--rehearsal", action="store_true",
                    help="skip the tag check; refuses to write results/runs.csv (use --out elsewhere)")
    a = ap.parse_args(argv)
    if a.rehearsal and os.path.normcase(os.path.abspath(a.out)) == os.path.normcase(os.path.abspath(RUNS_CSV)):
        ap.error("--rehearsal must not write the real results/runs.csv")

    paths, problems = preflight(a.final_dir, rehearsal=a.rehearsal)
    names = [os.path.splitext(os.path.basename(p))[0] for p in paths]
    methods = [m for _, ms in NIGHTS[a.night] for m in ms if not (a.night == 2 and ms == NIGHTS[1][0][1])]
    exp, worst = project_minutes(names, methods)
    print(f"night {a.night}: {len(paths)} instances x {len(methods)} methods; "
          f"projected {exp:.0f} min (worst case {worst:.0f} min)")
    if problems:
        print("NOT STARTING - fix these first:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("pre-flight: all checks passed")
    if a.dry_run:
        return 0
    return run_night(a.night, paths, a.out)


if __name__ == "__main__":
    sys.exit(main())
