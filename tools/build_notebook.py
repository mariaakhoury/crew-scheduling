"""Notebook builder (task A10, owner A). Master Plan §11.2 (architecture) and §11.3 (submission package).

    python tools/build_notebook.py            # writes dist/ (notebook + data folders)
    python tools/build_notebook.py --zip      # also writes dist/groupM_data.zip

Every module of crew/ appears IN FULL in its own %%writefile cell under a short explanation, so the notebook
contains all the code and recreates the package next to itself. Then the notebook imports it, checks it, runs the
P0 demo and P0-P5 check, and loads the saved results (RUN_MODE = "demo") for the tables and charts.

Rules kept: modules are copied unchanged (the `from crew.x import y` lines are never rewritten); only relative
paths; every crew module is included (a new module goes to "Other code" automatically, never silently dropped);
the build fails if the notebook would contain a personal path.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys
import zipfile

import nbformat as nbf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_NAME = "crew_scheduling_groupM.ipynb"

# Which modules go in which code section (Master Plan §11.2, sections 3-11). Any crew module not listed here is
# added under "Other code", so nothing is ever left out.
CODE_SECTIONS = [
    ("3. Code: settings", "Every fixed number of the project lives in `config.py` and nowhere else.",
     ["__init__.py", "config.py", "version.py", "sysinfo.py"]),
    ("4. Code: data and trip network",
     "`instance.py` loads and validates timetables (rules V1-V10) and generates new ones (rotation generator). "
     "`graph.py` builds the trip network: which trip can follow which, and the big-M numbers.",
     ["instance.py", "graph.py"]),
    ("5. Code: the independent checker and brute force",
     "`checker.py` decides whether a schedule is legal and what it costs. It imports no model or heuristic code, "
     "which makes it an independent referee. `brute.py` is the ground truth for tiny cases (n <= 10).",
     ["checker.py", "brute.py"]),
    ("6. Model 1: arc-flow", None, ["model_arcflow.py"]),
    ("7. Model 2: set partitioning", None, ["duties.py", "model_setpart.py"]),
    ("9. Heuristic: greedy insertion + local search",
     "Greedy gives each trip, in start order, to the open duty where it adds the least cost. Local search then "
     "improves the schedule with tail swaps, merges and swap-then-merge, accepting only legal moves that save "
     "at least $0.50.",
     ["greedy.py", "localsearch.py"]),
    ("10. Integration: the heuristic as a MIP start",
     "The heuristic schedule is given to Gurobi as a complete starting solution for both models (+S methods).",
     ["integration.py"]),
    ("11. Experiment and analysis code",
     "The runner solves every (instance, method) pair in its own process and writes one row per run to "
     "`results/runs.csv`. Every table and chart below is recomputed from that file by the analysis modules.",
     ["runner.py", "run_child.py", "final_runs.py", "highs_fallback.py", "analysis.py", "analysis_heuristic.py",
      "analysis_scaling.py", "analysis_strength.py", "analysis_profiles.py", "viz.py"]),
]

# Data the notebook needs next to itself (relative paths). Missing optional items are skipped by the builder.
DATA_REQUIRED = ["instances/proto", "instance.schema.json", "requirements.txt"]
DATA_OPTIONAL = ["instances/final", "results/runs.csv", "results/heuristic", "results/solutions",
                 "results/env.txt", "results/final_classes.csv", "results/confirm.csv", "data_dictionary.md"]

PERSONAL_PATH = re.compile(r"(/Users/|/home/|/tmp/|[A-Za-z]:\\\\)")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _md_file(name: str) -> str | None:
    p = os.path.join(ROOT, "notebook_src", name)
    return _read(p) if os.path.exists(p) else None


def _code_cells() -> list:
    """Markdown explanation + one %%writefile cell per module, for every module in crew/."""
    cells = []
    all_mods = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "crew", "*.py")))
    placed = set()
    sections = list(CODE_SECTIONS)
    missing = [m for m in all_mods if not any(m in s[2] for s in sections)]
    if missing:
        sections.append(("Other code", "Modules added after the notebook layout was written.", missing))
    for title, text, mods in sections:
        mods = [m for m in mods if m in all_mods]
        if not mods:
            continue
        cells.append(nbf.v4.new_markdown_cell(f"## {title}" + (f"\n\n{text}" if text else "")))
        if title.startswith("6."):
            md = _md_file("model1.md")
            if md:
                cells.append(nbf.v4.new_markdown_cell(md))
        if title.startswith("7."):
            md = _md_file("model2.md")
            if md:
                cells.append(nbf.v4.new_markdown_cell(md))
        for m in mods:
            cells.append(nbf.v4.new_code_cell(f"%%writefile crew/{m}\n" + _read(os.path.join(ROOT, "crew", m))))
            placed.add(m)
    assert placed == set(all_mods), f"modules not placed in the notebook: {set(all_mods) - placed}"
    return cells, sorted(m[:-3] for m in all_mods if m != "__init__.py")


INTRO = """# Bus driver scheduling: two exact models and a heuristic (Group M)

**How to run.** Unzip `groupM_data.zip`, create a fresh Python environment, run
`pip install -r requirements.txt`, open this notebook in the unzipped folder and run all cells from the top.
`RUN_MODE = "demo"` (default) solves P0-P5 live and **loads** the saved final results; `"full"` re-runs every
experiment (Gurobi academic licence, about 2 hours, only on the run machine).

## 1. The problem

A bus company runs a timetable of trips between terminals. Each trip needs one driver. A driver's **duty** is a
chain of trips: each trip must leave from the terminal where the previous one arrived, at least 10 minutes later.
A duty may last at most **L** minutes from first departure to last arrival (its *spread*), and contain at most
**W** minutes of driving. Every duty costs **$300** plus **$0.50 per minute of spread**. We want the cheapest set
of duties that covers every trip exactly once. The same structure appears in airline crew pairing, train crew
rostering and delivery-route driver planning.

## 2. The data

Each timetable is a JSON file (schema 1.0, `instance.schema.json`, described in `data_dictionary.md`): the limits
L, W, the turnaround τ, the costs, the terminals and the trips (id, start, end, origin, destination; times in
minutes after midnight). Small hand-made prototypes P0-P5 test correctness. The benchmark instances come from a
**rotation generator**: buses shuttle back and forth between terminals all day, with more buses at rush hour,
and their rotations are cut into single trips. Every trip is shorter than W, so one driver per trip is always
legal: every instance is feasible."""

SETUP = """import os, sys, importlib
RUN_MODE = "demo"          # "demo": solve P0-P5 live, load saved results.  "full": re-run all experiments.
HERE = os.path.abspath(os.getcwd())
os.makedirs("crew", exist_ok=True)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for f in ["instances/proto/P0_example8.json", "instance.schema.json"]:
    assert os.path.exists(f), f"missing data file: {f} (unzip the submission next to the notebook)"
print("working folder ready; RUN_MODE =", RUN_MODE)"""


def _import_cell(modules: list[str]) -> str:
    return f"""importlib.invalidate_caches()
import crew
MODULES = {modules!r}
for name in MODULES:
    importlib.reload(importlib.import_module("crew." + name))
importlib.reload(crew)
assert os.path.dirname(os.path.abspath(crew.__file__)) == os.path.join(HERE, "crew"), crew.__file__

# self-check: the package next to this notebook is the one in use, and the checker agrees with P0's reference
from crew import config
from crew.instance import load_instance
from crew.checker import check_schedule
P0 = load_instance("instances/proto/P0_example8.json")
assert check_schedule(P0, P0.reference["schedule"], P0.reference["cost"]).cost == 945.0
from crew.sysinfo import machine_info
print("crew loaded from", os.path.relpath(crew.__file__, HERE), "|", len(MODULES), "modules")
print("this machine:", {{k: v for k, v in machine_info().items() if k in ("cpu", "physical_cores", "ram_gb", "os")}})
print("limits: Gurobi", config.GUROBI_TIME_LIMIT_S, "s + build", config.BUILD_LIMIT_S, "s;",
      "Gurobi params", config.GUROBI_PARAMS)"""


SOLVE_HELPERS = """import math
import matplotlib.pyplot as plt
import pandas as pd
from crew.graph import build_arcs
from crew.model_arcflow import build_arcflow, decode_arcflow
from crew.duties import enumerate_duties
from crew.model_setpart import build_setpart, decode_setpart
from crew.greedy import greedy_insertion
from crew.localsearch import heuristic
from crew.viz import case_study, cost_table, gantt, plot_timetable


def _solve(model):
    for k, v in config.GUROBI_PARAMS.items():
        model.setParam(k, v)
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", config.GUROBI_TIME_LIMIT_S)
    model.optimize()
    return model


def solve_af(inst):
    model, mv = build_arcflow(inst, build_arcs(inst))
    _solve(model)
    return model.ObjVal, decode_arcflow(inst, mv)


def solve_sp(inst):
    duties, status, count = enumerate_duties(inst, build_arcs(inst), config.COLUMN_CAP, math.inf)
    model, mv = build_setpart(inst, duties)
    _solve(model)
    return model.ObjVal, decode_setpart(inst, duties, mv), count"""

P0_DEMO = """af_cost, af_sched = solve_af(P0)
sp_cost, sp_sched, n_duties = solve_sp(P0)
g = greedy_insertion(P0)
h = heuristic(P0)
print(f"Model 1 (arc-flow):          ${af_cost:,.2f}  {af_sched}")
print(f"Model 2 (set partitioning):  ${sp_cost:,.2f}  {sp_sched}   ({n_duties} legal duties listed)")
print(f"greedy:                      ${check_schedule(P0, g).cost:,.2f}")
print(f"greedy + local search:       ${h.cost:,.2f}")
assert abs(af_cost - 945) < 0.01 and abs(sp_cost - 945) < 0.01 and n_duties == 40
assert abs(check_schedule(P0, g).cost - 1177.5) < 0.01 and abs(h.cost - 945) < 0.01
schedules = {"Greedy": g, "After local search": h.schedule, "Optimal": P0.reference["schedule"]}
case_study(P0, schedules, highlight=[7]); plt.show()
cost_table(P0, schedules)"""

PROTO_CHECK = """import glob
rows = []
for path in sorted(glob.glob("instances/proto/P*.json")):
    inst = load_instance(path)
    af_cost, af_sched = solve_af(inst)
    sp_cost, sp_sched, _ = solve_sp(inst)
    ref = inst.reference["cost"]
    ok = (abs(af_cost - ref) < 0.01 and abs(sp_cost - ref) < 0.01
          and check_schedule(inst, af_sched).ok and check_schedule(inst, sp_sched).ok)
    rows.append({"instance": inst.name, "n": len(inst.trips), "reference": ref, "Model 1": af_cost,
                 "Model 2": sp_cost, "both equal the reference and pass the checker": ok})
proto = pd.DataFrame(rows).set_index("instance")
assert proto.iloc[:, -1].all(), proto
proto"""

BENCHMARK = """from crew.instance import instance_features
final_paths = sorted(glob.glob("instances/final/*.json"))
if final_paths:
    features = pd.DataFrame([instance_features(load_instance(p)) for p in final_paths],
                            index=[os.path.basename(p)[:-5] for p in final_paths])
    display(features)
else:
    print("instances/final/ is not in this folder")"""

RESULTS_LOAD = """RUNS_CSV = "results/runs.csv"
if RUN_MODE == "full":
    import subprocess
    env = dict(os.environ, PYTHONPATH=HERE)
    for night in ("1", "2"):
        subprocess.run([sys.executable, "-m", "crew.final_runs", "--night", night], cwd=HERE, env=env, check=True)
runs = pd.read_csv(RUNS_CSV) if os.path.exists(RUNS_CSV) else None
print(f"{len(runs)} rows loaded from {RUNS_CSV}" if runs is not None else f"{RUNS_CSV} not found: results cells are skipped")"""

RESULTS_TABLES = """from crew.analysis import summary_table, comparison_table
if runs is not None:
    for method in ["H", "AF", "AF+S", "SP", "SP+S"]:
        if (runs["method"] == method).any():
            print("Summary table:", method)
            display(summary_table(runs, method))
    print("Comparison table")
    display(comparison_table(runs))"""

CHARTS = """from crew import analysis_strength, analysis_profiles, analysis_heuristic
os.makedirs("figures", exist_ok=True)
if runs is not None:
    q22 = analysis_strength.report(RUNS_CSV, "figures/a12")
    assert q22["ok"].all(), q22              # Theorem 3: LP(AF) <= LP(SP) on every instance
    display(analysis_strength.summary(runs))
    display(analysis_profiles.report(RUNS_CSV, "figures/a16"))
    display(analysis_profiles.win_tie_loss(runs))
    print("H6:", analysis_heuristic.report(RUNS_CSV, "results/heuristic", "figures/b12")["verdict"])
    from IPython.display import Image
    for png in ["a12/gap_vs_time.png", "a12/time_split.png", "a16/performance_profile.png", "b12/paired_effect.png"]:
        display(Image(os.path.join("figures", png)))"""

SCALING = """from crew import analysis_scaling
if runs is not None:
    b13 = analysis_scaling.report(RUNS_CSV, "instances/final/MANIFEST.csv", "figures/b13")
    print("H4:", b13["H4"]["verdict"], "| H5:", b13["H5"]["verdict"])
    display(b13["H8"])                        # rank correlations of difficulty with n, L, trips per duty
    from IPython.display import Image
    for f in ("sizes", "build_cost", "status_map"):
        display(Image(f"figures/b13/{f}.png"))"""

LARGE_GANTT = """if final_paths:
    big = max((load_instance(p) for p in final_paths), key=lambda i: len(i.trips))
    plot_timetable(big); plt.show()
    gantt(big, heuristic(big).schedule, title=f"{big.name}: heuristic schedule"); plt.show()"""

REPRO = """for f in ["results/env.txt"]:
    if os.path.exists(f):
        print(open(f, encoding="utf-8").read())
print("instances:", len(final_paths), "final files; MANIFEST:", os.path.exists("instances/final/MANIFEST.csv"))"""


def build_notebook() -> nbf.NotebookNode:
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    code_cells, modules = _code_cells()
    C = [md(INTRO), code(SETUP)]
    C += code_cells
    C += [md("Schema used by the loader (rule V1); written next to the notebook so it needs no extra file."),
          code("%%writefile instance.schema.json\n" + _read(os.path.join(ROOT, "instance.schema.json")))]
    C += [md("## 12. Import the package and self-check"), code(_import_cell(modules))]
    C += [md("## 13. Small worked example: P0\n\nBoth models, brute force agree on $945; greedy strands trip 7 "
             "($1,177.50) and local search repairs it."), code(SOLVE_HELPERS), code(P0_DEMO)]
    case = _md_file("case_p0.md")
    if case:
        C.append(md(re.sub(r"```python.*?```", "", case, flags=re.S).strip()))
    C += [md("## 14. Prototype check: P0 to P5\n\nBoth models must equal the reference optimum and pass the checker."),
          code(PROTO_CHECK)]
    bench = _md_file("benchmark.md")
    C += [md("## 15. Benchmark" + ("\n\n" + bench if bench else "")), code(BENCHMARK)]
    C += [md("## 16. Experiments\n\nIn demo mode the saved `results/runs.csv` of the final runs is loaded."),
          code(RESULTS_LOAD)]
    C += [md("## 17. Results: summary tables and the comparison table\n\nAverages over time-limit runs are "
             "lower bounds and are marked with ≥."), code(RESULTS_TABLES)]
    C += [md("## 18. Charts\n\nModel strength (A12), performance profiles (A16) and the heuristic's effect "
             "(B12), all recomputed from `results/runs.csv`."), code(CHARTS),
          md("Scalability (B13): model sizes, build cost and status by instance."), code(SCALING)]
    C += [md("## 19. A large instance"), code(LARGE_GANTT)]
    disc = _md_file("discussion.md")
    C += [md("## 20. Discussion" + ("\n\n" + disc if disc else ""))]
    C += [md("## 21. Reproducibility"), code(REPRO)]
    nb = nbf.v4.new_notebook()
    nb["cells"] = C
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


def check_no_personal_paths(nb) -> None:
    for k, cell in enumerate(nb["cells"]):
        m = PERSONAL_PATH.search(cell["source"])
        if m:
            raise SystemExit(f"cell {k} contains a personal path ({m.group(0)!r}); remove it before submitting")


def copy_data(dist: str) -> list[str]:
    copied = []
    for rel in DATA_REQUIRED + DATA_OPTIONAL:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            if rel in DATA_REQUIRED:
                raise SystemExit(f"required file missing: {rel}")
            continue
        dst = os.path.join(dist, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        copied.append(rel)
    with open(os.path.join(dist, "README.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("Group M - bus driver scheduling\n\n1. Unzip this folder.\n2. python -m venv venv, then activate "
                 "it.\n3. pip install -r requirements.txt\n4. Open crew_scheduling_groupM.ipynb here and run all "
                 "cells (RUN_MODE = \"demo\").\n")
    return copied


def make_zip(dist: str) -> str:
    out = os.path.join(dist, "groupM_data.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, files in os.walk(dist):
            for f in files:
                p = os.path.join(folder, f)
                if p == out or "__pycache__" in p:
                    continue
                z.write(p, os.path.relpath(p, dist))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args(argv)
    nb = build_notebook()
    check_no_personal_paths(nb)
    os.makedirs(a.out, exist_ok=True)
    nbf.validate(nb)
    nbf.write(nb, os.path.join(a.out, NB_NAME))
    copied = copy_data(a.out)
    print(f"wrote {os.path.join(a.out, NB_NAME)} ({len(nb['cells'])} cells); data: {', '.join(copied)}")
    if a.zip:
        print("zip:", make_zip(a.out))


if __name__ == "__main__":
    main()
