"""Benchmark freeze (task B9, owner B). Master Plan §10.1 stage C and §10.3 step 4.

    python -m pilot.freeze --selection results/selected.csv --from instances/candidates --to instances/final

Copies the selected instance files unchanged into instances/final/, then writes
  MANIFEST.csv : name, file, sha256, generator, seed, n, m, L, W, class_at_selection
  README.md    : where every instance came from and how sizes and parameters were chosen
                 (the professor's "document where each instance came from" requirement, §2.2).
Every file must already have a checked reference schedule (required for the final benchmark).
After the tag v1.0-final-run, files never change; a changed file gets a new name.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.checker import check_schedule  # noqa: E402
from crew.instance import instance_features, load_instance  # noqa: E402


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def freeze(selection: pd.DataFrame, src: str, dst: str) -> pd.DataFrame:
    os.makedirs(dst, exist_ok=True)
    rows = []
    for _, s in selection.iterrows():
        name = s["instance"]
        source, target = os.path.join(src, name + ".json"), os.path.join(dst, name + ".json")
        inst = load_instance(source)                                   # V1-V10, includes V9 on the reference
        if not inst.reference:
            raise ValueError(f"{name}: the final benchmark needs a checked reference schedule")
        res = check_schedule(inst, inst.reference["schedule"], inst.reference["cost"])
        assert res.ok, (name, res.errors)
        shutil.copyfile(source, target)
        f = instance_features(inst)
        rows.append({"name": name, "file": f"{name}.json", "sha256": sha256(target), "generator": inst.generator,
                     "seed": inst.seed, "n": f["n"], "m": f["m"], "L": inst.L, "W": inst.W, "arcs": f["arcs"],
                     "arcs_per_trip": round(f["arcs_per_trip"], 2), "trips_per_hour": round(f["trips_per_hour"], 2),
                     "trips_per_duty_ref": round(f["n"] / len(inst.reference["schedule"]), 2),
                     "reference_cost": inst.reference["cost"], "reference_kind": inst.reference.get("kind"),
                     "class_at_selection": s.get("class"), "params": inst.params})
    man = pd.DataFrame(rows)
    man.drop(columns=["params"]).to_csv(os.path.join(dst, "MANIFEST.csv"), index=False, quoting=csv.QUOTE_MINIMAL)
    write_readme(man, dst)
    return man


def write_readme(man: pd.DataFrame, dst: str) -> None:
    """Every number in the text is read from the data or from config.py (repo rule: no cost literals)."""
    from crew import config
    gens = ", ".join(sorted(set(map(str, man["generator"]))))
    w_ratios = sorted({round(w / l, 2) for w, l in zip(man["W"], man["L"])})
    lines = ["# Final benchmark (Group M, frozen)", "",
             f"Generator(s): {gens} (`crew.instance.make_instance`, Member A; see its docstring for the model of a",
             "timetable). Trips longer than W are redrawn, so every instance is feasible (one driver per trip is legal).",
             "Each file stores every generator argument in `params` and its seed, so it can be rebuilt exactly.", "",
             "## How sizes and parameters were chosen",
             f"- n from {man['n'].min()} to {man['n'].max()} trips; m in {sorted(set(man['m']))} terminals; "
             f"L in {sorted(set(man['L']))} min; W/L in {w_ratios}.",
             f"- Costs are frozen for every instance (config.py): F = ${config.F:.2f} per duty, "
             f"c = ${config.C_PER_MIN:.2f} per paid minute, tau = {config.TAU} min.",
             "- Instances were selected from the pilot population by the written rule in SELECTION.md (no hand-picking).",
             "- What makes an instance hard: more trips per duty (larger L, W) makes |P| explode; more connections per",
             "  trip (denser timetable, fewer terminals) and larger n make both models bigger.", "",
             "## Instances", "",
             "| name | n | m | L | W | arcs | arcs/trip | trips/duty (ref) | reference cost | seed | sha256 (first 12) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in man.iterrows():
        lines.append(f"| {r['name']} | {r['n']} | {r['m']} | {r['L']} | {r['W']} | {r['arcs']} | {r['arcs_per_trip']} | "
                     f"{r['trips_per_duty_ref']} | {r['reference_cost']} | {r['seed']} | {r['sha256'][:12]} |")
    lines += ["", "Full generator parameters are stored in each file's `params` field; full hashes in MANIFEST.csv.", ""]
    with open(os.path.join(dst, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True, help="CSV with at least 'instance' and 'class' columns")
    ap.add_argument("--from", dest="src", default=os.path.join(ROOT, "instances", "candidates"))
    ap.add_argument("--to", dest="dst", default=os.path.join(ROOT, "instances", "final"))
    a = ap.parse_args(argv)
    man = freeze(pd.read_csv(a.selection), a.src, a.dst)
    print(f"frozen {len(man)} instances -> {a.dst}/MANIFEST.csv")
    if len(man) < 15:
        print("WARNING: fewer than 15 instances (professor's minimum)")


if __name__ == "__main__":
    main()
