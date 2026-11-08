"""Pictures of timetables and schedules (task A7). Owner: Member A.

gantt:          one row per duty (driver), one bar per trip, coloured by the terminal the trip leaves from.
                Gaps between bars are waiting time.
plot_timetable: every trip of an instance over the day, plus how many trips start each hour (shows the peaks).
"""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

from crew.checker import check_schedule, duty_cost
from crew.instance import Instance

_COLORS = plt.get_cmap("tab10").colors


def _hhmm(x, _pos=None) -> str:
    """Minutes after midnight -> 'HH:MM' for the time axis."""
    x = int(round(x))
    return f"{x // 60:02d}:{x % 60:02d}"


def _time_axis(ax, lo: int, hi: int) -> None:
    span = hi - lo
    step = 60 if span <= 12 * 60 else 120
    ax.set_xlim(lo - 10, hi + 10)
    ax.xaxis.set_major_locator(MultipleLocator(step))
    ax.xaxis.set_major_formatter(FuncFormatter(_hhmm))
    ax.grid(axis="x", color="0.85", linewidth=0.6)
    ax.set_axisbelow(True)


def _legend(ax, inst: Instance) -> None:
    handles = [Patch(color=_COLORS[k % 10], label=f"leaves {name}") for k, name in enumerate(inst.terminals)]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=8)


def gantt(inst: Instance, schedule: list[list[int]], title: str | None = None, ax=None) -> matplotlib.figure.Figure:
    """Draw a schedule: row k = duty k, bars = its trips. The right margin shows each duty's cost.
    The title adds the number of duties and the total cost, recomputed by the checker."""
    n_duties = len(schedule)
    if ax is None:
        fig, ax = plt.subplots(figsize=(11, max(2.5, 0.32 * n_duties + 1.2)))
    else:
        fig = ax.figure
    small = n_duties <= 30                       # write labels and costs only when they stay readable
    for row, duty in enumerate(schedule):
        for i in duty:
            t = inst.trips[i]
            ax.barh(row, t.end - t.start, left=t.start, height=0.7,
                    color=_COLORS[t.origin % 10], edgecolor="white", linewidth=0.5)
            if small:
                ax.text((t.start + t.end) / 2, row, t.label or str(t.id),
                        ha="center", va="center", fontsize=7, color="white")
        if small:
            last_end = inst.trips[duty[-1]].end
            ax.text(last_end + 8, row, f"${duty_cost(inst, duty):,.2f}", va="center", fontsize=7, color="0.3")
    lo = min(t.start for t in inst.trips)
    hi = max(t.end for t in inst.trips) + (60 if small else 0)
    _time_axis(ax, lo, hi)
    ax.set_ylim(n_duties - 0.5, -0.5)           # duty 1 at the top
    ax.set_yticks(range(n_duties))
    ax.set_yticklabels([f"duty {k + 1}" for k in range(n_duties)] if small else [""] * n_duties)
    if not small:
        ax.tick_params(axis="y", length=0)
        ax.set_ylabel(f"{n_duties} duties (one row each)")
    result = check_schedule(inst, schedule)
    head = title or inst.name
    status = f"{n_duties} duties, total ${result.cost:,.2f}" if result.ok else "ILLEGAL schedule (see checker)"
    ax.set_title(f"{head}\n{status}", fontsize=10, loc="left")
    _legend(ax, inst)
    fig.tight_layout()
    return fig


def plot_timetable(inst: Instance) -> matplotlib.figure.Figure:
    """Top: every trip as a bar (row = trip id). Bottom: trips starting in each hour."""
    n = len(inst.trips)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True,
                                      gridspec_kw={"height_ratios": [3, 1]})
    for t in inst.trips:
        top.barh(t.id, t.end - t.start, left=t.start, height=0.8, color=_COLORS[t.origin % 10], linewidth=0)
    top.set_ylim(n - 0.5, -0.5)
    top.set_ylabel("trip id")
    top.set_title(f"{inst.name}: {n} trips, {len(inst.terminals)} terminals, L = {inst.L}, W = {inst.W} min",
                  fontsize=10, loc="left")
    _legend(top, inst)

    lo = min(t.start for t in inst.trips)
    hi = max(t.end for t in inst.trips)
    first_hour, last_hour = lo // 60, hi // 60
    hours = list(range(first_hour, last_hour + 1))
    counts = [sum(1 for t in inst.trips if t.start // 60 == h) for h in hours]
    bottom.bar([h * 60 + 30 for h in hours], counts, width=54, color="0.55")
    bottom.set_ylabel("trips starting\nthis hour")
    _time_axis(bottom, lo, hi)
    fig.tight_layout()
    return fig
