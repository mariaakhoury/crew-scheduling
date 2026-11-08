import glob
from crew.instance import load_instance
from crew.graph import build_arcs, big_m_bounds

FILES = sorted(glob.glob("instances/proto/P*.json"))


def brute_force_arcs(inst):
    # independent re-check of every pair, written differently on purpose
    out = set()
    n = len(inst.trips)
    for a in range(n):
        for b in range(n):
            ti, tj = inst.trips[a], inst.trips[b]
            if ti.dest == tj.origin and tj.start - ti.end >= inst.tau:
                out.add((a, b))
    return out


def test_p0_has_14_arcs():
    inst = load_instance("instances/proto/P0_example8.json")
    assert len(build_arcs(inst)) == 14


def test_arcs_equal_brute_force():
    for f in FILES:
        inst = load_instance(f)
        assert set(build_arcs(inst)) == brute_force_arcs(inst), f


def test_bounds_are_sensible():
    for f in FILES:
        inst = load_instance(f)
        ell, U = big_m_bounds(inst)
        for t in inst.trips:
            assert ell[t.id] <= t.start          # duty can start no later than the trip itself
            assert t.end - t.start <= U[t.id] <= inst.W
