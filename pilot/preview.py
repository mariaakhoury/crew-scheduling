"""Pilot preview (task B5, owner B) - needs NO Gurobi licence.

    python -m pilot.preview --folder instances/candidates --out results/pilot_preview.csv

For every candidate instance: size (n, m, L, W), arcs |A| and arcs per trip, the reference schedule's drivers and
median trips per duty (density rule Q2: >= 3), the number of legal duties |P| counted with the same cap and build
limit the pilot uses, whether set partitioning can be built, and arc-flow's size (|A| + 4n variables, 3n + 2|A| rows).
Run it before the pilot night to predict SP_not_built cases and the night's length; nothing here is a solver result.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.duties import count_duties, get_arcs  # noqa: E402
from crew.instance import load_instance  # noqa: E402


def preview(folder: str, build_limit_s: float) -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        inst = load_instance(path)
        n = len(inst.trips)
        arcs = get_arcs(inst)
        per_duty = [len(d) for d in inst.reference["schedule"]]
        count, stopped, secs = count_duties(inst, arcs, cap=config.COLUMN_CAP,
                                            deadline=time.perf_counter() + build_limit_s)
        if not stopped:
            sp = "yes"
        elif count > config.COLUMN_CAP:
            sp = "no: COLUMN_CAP"
        else:
            sp = "no: BUILD_LIMIT"
        rows.append({"instance": inst.name, "n": n, "m": len(inst.terminals), "L": inst.L, "W": inst.W,
                     "arcs": len(arcs), "arcs_per_trip": round(len(arcs) / n, 1),
                     "ref_drivers": len(per_duty), "median_trips_per_duty": statistics.median(per_duty),
                     "duties_counted": count, "count_stopped_early": stopped, "SP_buildable": sp,
                     "enum_s": round(secs, 1), "AF_vars": len(arcs) + 4 * n, "AF_rows": 3 * n + 2 * len(arcs)})
        print(f"{inst.name:28s} |P| {'>' if stopped else ' '}{count:>10,}  SP: {sp}", flush=True)
    return pd.DataFrame(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=os.path.join(ROOT, "instances", "candidates"))
    ap.add_argument("--grid", default=os.path.join(ROOT, "pilot", "grid.json"),
                    help="the build limit is read from here (pilot_build_limit_s)")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "pilot_preview.csv"))
    a = ap.parse_args(argv)
    with open(a.grid, encoding="utf-8") as fh:
        limit = json.load(fh)["pilot_build_limit_s"]
    df = preview(a.folder, limit)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_csv(a.out, index=False)
    med = df["median_trips_per_duty"]
    print(f"\nQ2 density (median trips per duty >= 3): {'PASS' if (med >= 3).all() else 'FAIL'} "
          f"(range {med.min()}-{med.max()}); SP not buildable at {limit} s: "
          f"{int((df['SP_buildable'] != 'yes').sum())} of {len(df)}; preview -> {a.out}")


if __name__ == "__main__":
    main()
