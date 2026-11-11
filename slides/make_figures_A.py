"""Figures for slides 1-5 (Member A). Every number is computed here from the code and data.

    py slides/make_figures_A.py            # writes slides/figures/A_*.png and prints the numbers used

slide 3: the P0 timetable, and its optimal 2-driver schedule ($945)
slide 4: the P0 trip network (14 arcs); the arcs the optimal schedule uses are drawn bold
slide 5: (a) Model 1's LP bound with and without the duty-limit rules (4)-(7), P0-P5
         (b) model size: Model 1 variables vs Model 2 duties, from results/runs.csv (final runs, 15 instances)
"""
from __future__ import annotations

import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from crew import config
from crew.graph import build_arcs
from crew.instance import load_instance
from crew.model_arcflow import build_arcflow
from crew.viz import _COLORS, _hhmm, gantt

OUT = os.path.join(ROOT, "slides", "figures")
P0 = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))


def slide3_timetable():
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for t in P0.trips:
        ax.barh(t.id, t.end - t.start, left=t.start, height=0.6, color=_COLORS[t.origin % 10])
        ax.text((t.start + t.end) / 2, t.id, f"{t.id}: {P0.terminals[t.origin]}→{P0.terminals[t.dest]}",
                ha="center", va="center", color="white", fontsize=8)
    ax.set_ylim(len(P0.trips) - 0.5, -0.5)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(60))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_hhmm))
    ax.set_title(f"P0: 8 trips between A and B. Shift ≤ {P0.L // 60} h, driving ≤ {P0.W // 60} h, "
                 f"turnaround ≥ {P0.tau} min", loc="left", fontsize=10)
    ax.grid(axis="x", color="0.9")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "A_slide3_timetable.png"), dpi=200)
    fig = gantt(P0, P0.reference["schedule"], title="The optimal schedule: 2 drivers")
    fig.savefig(os.path.join(OUT, "A_slide3_optimal.png"), dpi=200)


def slide4_network():
    arcs = build_arcs(P0)
    used = {(d[k], d[k + 1]) for d in P0.reference["schedule"] for k in range(len(d) - 1)}
    pos = {t.id: ((t.start + t.end) / 2, 1.0 if t.origin == 0 else 0.0) for t in P0.trips}
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for i, j in arcs:
        (x1, y1), (x2, y2) = pos[i], pos[j]
        bold = (i, j) in used
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=2.6 if bold else 0.9, color="black" if bold else "0.7",
                                    shrinkA=14, shrinkB=14, connectionstyle="arc3,rad=0.25"))
    for t in P0.trips:
        x, y = pos[t.id]
        ax.scatter(x, y, s=650, color=_COLORS[t.origin % 10], zorder=3)
        ax.text(x, y, str(t.id), ha="center", va="center", color="white", fontsize=11, weight="bold", zorder=4)
    ax.set_yticks([0, 1], ["leaves B", "leaves A"])
    ax.set_ylim(-0.6, 1.6)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(60))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_hhmm))
    ax.set_title(f"P0's trip network: {len(arcs)} arcs \"j can follow i\". Bold = the 6 arcs the optimal "
                 f"schedule uses (x = 1)", loc="left", fontsize=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "A_slide4_network.png"), dpi=200)
    return len(arcs)


def _lp(inst, drop_limits: bool) -> float:
    model, _ = build_arcflow(inst, build_arcs(inst), relax=True)
    model.Params.OutputFlag = 0
    if drop_limits:     # remove rows (4), (5), (6); T and D then appear in no row, so bounds (3), (7) do nothing
        names = tuple(config.CONSTRAINT_NAMES[k] for k in (4, 5, 6))
        for c in model.getConstrs():
            if c.ConstrName.startswith(names):
                model.remove(c)
        model.update()
    model.optimize()
    value = model.ObjVal
    model.dispose()
    return value


def slide5_lp():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "P*.json"))):
        inst = load_instance(path)
        opt = inst.reference["cost"]
        full, free = _lp(inst, False), _lp(inst, True)
        rows.append({"instance": inst.name.split("_")[0], "optimum": opt,
                     "LP gap, with the duty rules (%)": 100 * (opt - full) / opt,
                     "LP gap, rules (4)-(7) deleted (%)": 100 * (opt - free) / opt})
    df = pd.DataFrame(rows).set_index("instance")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(df))
    ax.bar(x - 0.2, df.iloc[:, 1], 0.4, label="Model 1 LP, with the duty rules", color="tab:blue")
    ax.bar(x + 0.2, df.iloc[:, 2], 0.4, label="Model 1 LP, duty rules deleted", color="0.7")
    ax.set_xticks(x, df.index)
    ax.set_ylabel("gap to the optimum (%)")
    ax.set_title("Deleting the duty rules barely changes Model 1's LP bound", loc="left", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "A_slide5_lp.png"), dpi=200)
    return df


def slide5_size():
    path = os.path.join(ROOT, "results", "runs.csv")
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path)
    af = d[d["method"] == "AF"].set_index("instance")
    sp = d[d["method"] == "SP"].set_index("instance")
    t = pd.DataFrame({"n": af["n"], "AF variables": af["n_vars"], "SP duties": sp["n_duties"],
                      "SP status": sp["status"]}).sort_values(["n", "AF variables"])
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.scatter(t["n"], t["AF variables"], color="tab:blue", label="Model 1: variables (always built)")
    built = t["SP status"] != "COLUMN_CAP"
    ax.scatter(t.loc[built, "n"], t.loc[built, "SP duties"], color="tab:orange", marker="s",
               label="Model 2: duties listed")
    ax.scatter(t.loc[~built, "n"], [config.COLUMN_CAP] * int((~built).sum()), color="tab:red", marker="x", s=60,
               label=f"Model 2: stopped at the {config.COLUMN_CAP:,} cap (not built)")
    ax.set_yscale("log")
    ax.set_xlabel("trips n")
    ax.set_ylabel("size (log scale)")
    ax.set_title("Model 1 grows gently; Model 2's duty list explodes (final runs)", loc="left", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "A_slide5_size.png"), dpi=200)
    return t


def main():
    os.makedirs(OUT, exist_ok=True)
    slide3_timetable()
    print("slide 4: P0 arcs =", slide4_network())
    print("slide 5a:\n", slide5_lp().round(1).to_string())
    t = slide5_size()
    if t is not None:
        print("slide 5b: largest AF model =", int(t["AF variables"].max()), "variables; SP not built on",
              int((t["SP status"] == "COLUMN_CAP").sum()), "of", len(t))
    print("figures written to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
