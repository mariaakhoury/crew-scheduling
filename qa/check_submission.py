"""Submission checklist - automatic part (owner B; Master Plan §14.5, professor's checklist §7, Q18/Q19).

    python -m qa.check_submission --notebook dist/crew_scheduling_groupM.ipynb --slides slides/slides_groupM.pdf \
        --zip dist/groupM_data.zip

Prints PASS / FAIL / MISSING per item and exits 1 unless every automatic item passes. The items that need a human
(teaching quality, rehearsals, every member presents...) are in SUBMISSION_CHECKLIST.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MIP_METHODS = ("AF", "AF+S", "SP", "SP+S")
PERSONAL_PATH = re.compile(r"(/Users/|/home/|/tmp/|[A-Za-z]:\\\\Users\\\\)")
RESULTS_ARE = ("objective", "best_bound", "gap_pct", "solver_time_s", "n_vars", "n_constrs", "nodes")


class Checklist:
    def __init__(self):
        self.items: list[tuple[str, str, str]] = []

    def add(self, item: str, ok: bool | None, detail: str = "") -> None:
        self.items.append(("MISSING" if ok is None else "PASS" if ok else "FAIL", item, detail))

    def print(self) -> bool:
        for status, item, detail in self.items:
            print(f"[{status:7s}] {item}" + (f" - {detail}" if detail else ""))
        bad = [s for s, _, _ in self.items if s != "PASS"]
        print(f"\n{len(self.items) - len(bad)}/{len(self.items)} automatic items pass")
        return not bad


def check_notebook(c: Checklist, path: str) -> None:
    if not os.path.exists(path):
        c.add("Notebook exists (.ipynb)", None, path)
        return
    with open(path, encoding="utf-8") as fh:
        nb = json.load(fh)
    cells = nb.get("cells", [])
    code = [x for x in cells if x.get("cell_type") == "code"]
    c.add("Notebook exists (.ipynb)", True, f"{len(cells)} cells")
    c.add("Notebook was executed (outputs saved)", bool(code) and all(x.get("execution_count") for x in code),
          f"{sum(1 for x in code if x.get('execution_count'))}/{len(code)} code cells executed")
    errors = [x for x in code for o in x.get("outputs", []) if o.get("output_type") == "error"]
    c.add("No error cells", not errors, f"{len(errors)} error output(s)")
    text = json.dumps(nb)
    c.add("No personal file paths in the notebook (§11.3)", not PERSONAL_PATH.search(text))
    src = "\n".join("".join(x.get("source", "")) for x in cells).lower()
    for item, words in [("Problem description and application", ("application", "bus")),
                        ("Both models written (constraints (1)-(8))", ("c1_pred", "c8_cover")),
                        ("Heuristic code (greedy + local search)", ("greedy", "local search")),
                        ("Independent checker used", ("check_schedule",)),
                        ("Summary tables + comparison table", ("summary_table", "comparison_table")),
                        ("Small and large instance visualised (Gantt)", ("gantt",)),
                        ("Hardware, threads and time limits stated", ("threads", "time limit"))]:
        missing = [w for w in words if w not in src]
        c.add(f"Notebook: {item}", not missing, f"missing keyword(s): {missing}" if missing else "")
    comments = sum(line.strip().startswith("#") for x in code for line in "".join(x.get("source", "")).splitlines())
    c.add("Code is commented (professor §3)", comments >= 50, f"{comments} comment lines")


def check_benchmark_and_results(c: Checklist, final_dir: str, runs: str) -> None:
    from crew.version import file_sha256
    man_path = os.path.join(final_dir, "MANIFEST.csv")
    if not os.path.exists(man_path):
        c.add("Frozen benchmark with MANIFEST.csv", None, man_path)
        return
    man = pd.read_csv(man_path)
    c.add("At least 15 benchmark instances (professor §2.2)", len(man) >= 15, f"{len(man)} instances")
    bad = [r["name"] for _, r in man.iterrows()
           if not os.path.exists(os.path.join(final_dir, r["file"]))
           or file_sha256(os.path.join(final_dir, r["file"])) != r["sha256"]]
    c.add("Every instance file matches its MANIFEST fingerprint", not bad, f"mismatch: {bad}" if bad else "")
    c.add("Instance documentation (README.md)", os.path.exists(os.path.join(final_dir, "README.md")))
    c.add("SELECTION.md (how instances were chosen)", os.path.exists(os.path.join(final_dir, "SELECTION.md"))
          or os.path.exists(os.path.join(ROOT, "SELECTION.md")))
    if not os.path.exists(runs):
        c.add("Final results runs.csv", None, runs)
        return
    df = pd.read_csv(runs)
    if "superseded" in df.columns:
        df = df[~df["superseded"].astype(str).str.lower().isin(["true", "1", "yes"])]
    have = set(zip(df["instance"], df["method"]))
    missing = [(i, m) for i in man["name"] for m in (*MIP_METHODS, "H") if (i, m) not in have]
    c.add("All methods run on all instances (professor §2.5)", not missing, f"{len(missing)} missing row(s)")
    c.add("One configuration for every row (same limits/threads)", df["config_hash"].nunique() == 1,
          f"{df['config_hash'].nunique()} config hash(es)")
    c.add("Every result column recorded (professor §2.5)", all(col in df for col in RESULTS_ARE))
    plain = df[df["method"].isin(["AF", "SP"])]
    tl = plain[plain["status"].isin(["TIME_LIMIT", "TIME_LIMIT_NOSOL"])]["instance"].nunique()
    solved_by_both = (plain[plain["status"] == "OPTIMAL"].groupby("instance")["method"].nunique() == 2).sum()
    c.add("Instances Gurobi cannot solve within the limit (>= 3)", tl >= 3, f"{tl}")
    c.add("Instances every model solves (>= 1)", solved_by_both >= 1, f"{solved_by_both}")
    from qa.verify_results import verify
    problems = verify(runs, man_path, final_dir)
    c.add("verify_results PASS (checker on every solution, Q13/Q23, fingerprints)", not problems,
          f"{len(problems)} problem(s)" if problems else "")


def check_files(c: Checklist, slides: str, zip_path: str) -> None:
    ok = os.path.exists(slides) and slides.lower().endswith((".pdf", ".pptx"))
    c.add("Slides file (PDF or PPTX)", ok if os.path.exists(slides) else None, slides)
    if not os.path.exists(zip_path):
        c.add("Data zip", None, zip_path)
        return
    names = zipfile.ZipFile(zip_path).namelist()
    for item, pattern in [("zip: final instances + MANIFEST", "instances/final/MANIFEST.csv"),
                          ("zip: results/runs.csv", "results/runs.csv"),
                          ("zip: requirements.txt", "requirements.txt")]:
        c.add(item, any(n.endswith(pattern) for n in names))
    c.add("zip: no licence file (never ship gurobi.lic)", not any(n.endswith(".lic") for n in names))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook", default=os.path.join(ROOT, "dist", "crew_scheduling_groupM.ipynb"))
    ap.add_argument("--slides", default=os.path.join(ROOT, "slides", "slides_groupM.pdf"))
    ap.add_argument("--zip", default=os.path.join(ROOT, "dist", "groupM_data.zip"))
    ap.add_argument("--final", default=os.path.join(ROOT, "instances", "final"))
    ap.add_argument("--runs", default=os.path.join(ROOT, "results", "runs.csv"))
    a = ap.parse_args(argv)
    c = Checklist()
    check_notebook(c, a.notebook)
    check_benchmark_and_results(c, a.final, a.runs)
    check_files(c, a.slides, a.zip)
    sys.exit(0 if c.print() else 1)


if __name__ == "__main__":
    main()
