"""Tests for the rotation generator (task A4, Q1 and Q2)."""
import os
import statistics

import pytest

from crew.instance import load_instance, make_instance, save_instance, validate_instance

# A few of the pilot configurations (n, m, L); W = 0.75 L
CONFIGS = [(50, 2, 360), (100, 3, 480), (200, 2, 600), (300, 3, 360), (500, 3, 600)]


def _make(n, m, L, seed=200):
    return make_instance(f"R_n{n}_m{m}_L{L}_s{seed}", n, m, L, int(0.75 * L), seed)


@pytest.mark.parametrize("n,m,L", CONFIGS)
def test_valid_and_exact_size(n, m, L):
    inst = _make(n, m, L)
    assert len(inst.trips) == n
    assert validate_instance(inst) == []          # rules V1-V10, including the checked reference schedule


@pytest.mark.parametrize("n,m,L", CONFIGS)
def test_every_trip_fits_one_driver(n, m, L):     # Q1: d_i <= W <= L
    inst = _make(n, m, L)
    assert inst.W <= inst.L
    assert all(t.end - t.start <= inst.W for t in inst.trips)


@pytest.mark.parametrize("n,m,L", CONFIGS)
def test_median_three_trips_per_duty(n, m, L):    # Q2
    inst = _make(n, m, L)
    assert statistics.median(len(d) for d in inst.reference["schedule"]) >= 3


def test_same_seed_same_file():
    a, b = _make(100, 3, 480), _make(100, 3, 480)
    assert a.trips == b.trips


def test_save_and_load_back(tmp_path):
    inst = _make(100, 3, 480)
    path = os.path.join(tmp_path, inst.name + ".json")
    save_instance(inst, path)
    assert load_instance(path).trips == inst.trips
