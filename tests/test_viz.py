"""Tests for the pictures (task A7): they draw without errors and show one bar per trip."""
import matplotlib
matplotlib.use("Agg")      # draw without opening windows

from crew.instance import load_instance, make_instance
from crew.viz import gantt, plot_timetable


def _bars(fig):
    return sum(len(ax.patches) for ax in fig.axes)


def test_gantt_p0_one_bar_per_trip():
    inst = load_instance("instances/proto/P0_example8.json")
    fig = gantt(inst, inst.reference["schedule"])
    assert _bars(fig) == len(inst.trips)
    assert "$945.00" in fig.axes[0].get_title(loc="left")


def test_gantt_and_timetable_large_instance():
    inst = make_instance("R_n300_m3_L480_s200", 300, 3, 480, 360, 200)
    assert _bars(gantt(inst, inst.reference["schedule"])) == 300
    plot_timetable(inst)
