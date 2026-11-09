"""Tests for crew/analysis.py (task C7). The hand-made rows below exist ONLY in this test file: each one checks
a reporting rule against an answer computed by hand. Real tables are always built from results/runs.csv.
    pytest -q tests/test_analysis.py
"""
import glob, math, os, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.analysis import comparison_table, load_runs, summary_table, to_display  # noqa: E402
from crew.runner import COLUMNS, run_all, write_rows  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))


def row(instance, method, status, n=100, proven="no", **values):
    r = {c: "" for c in COLUMNS}
    r.update(run_id=f"{instance}.{method}", instance=instance, method=method, status=status, n=n, m=3, L=480,
             W=360, n_arcs=10 * n, config_hash="h1", instance_sha256="s-" + instance, superseded="no",
             globally_proven=proven)
    r.update(values)
    return r


# AF on three instances: proven / time limit with incumbent / time limit without incumbent; SP: one build failure.
ROWS = [
    row("i1", "AF", "OPTIMAL", n=50, proven="yes", objective=1000, best_bound=1000, gap_pct=0,
        solver_time_s=10, end_to_end_s=12, n_vars=100, n_constrs=50, nodes=5),
    row("i2", "AF", "TIME_LIMIT", n=100, objective=2000, best_bound=1800, gap_pct=10,
        solver_time_s=120, end_to_end_s=125, n_vars=200, n_constrs=100, nodes=900),
    row("i3", "AF", "TIME_LIMIT_NOSOL", n=200, best_bound=3000, solver_time_s=120, end_to_end_s=130,
        n_vars=400, n_constrs=200, nodes=50),
    row("i1", "SP", "OPTIMAL", n=50, proven="yes", objective=1000, best_bound=1000, gap_pct=0,
        solver_time_s=1, end_to_end_s=3, n_vars=40, n_constrs=8, nodes=1),
    row("i2", "SP", "COLUMN_CAP", n=100, end_to_end_s=60),
    row("i3", "SP", "CHECK_FAILED", n=200, objective=2999, best_bound=3000, solver_time_s=5,
        end_to_end_s=7, n_vars=900, n_constrs=200, nodes=3),
    row("i1", "SP", "ERROR", superseded="yes"),            # superseded rows are history only
]


@pytest.fixture
def df(tmp_path):
    path = tmp_path / "runs.csv"
    write_rows(str(path), ROWS)
    return load_runs(str(path))


def test_summary_table_averages_follow_the_rules(df):
    t = summary_table(df, "AF")
    assert list(t.index) == ["i1", "i2", "i3", "Average", "Sum"]           # sorted by n
    assert t.at["Average", "gap_pct"] == 5                                 # (0 + 10) / 2: NOSOL not averaged
    assert math.isclose(t.at["Average", "solver_time_s"], (10 + 120 + 120) / 3)
    assert t.at["Sum", "objective"] == 3000 and t.at["Sum", "n_vars"] == 700
    assert ("Average", "solver_time_s") in t.attrs["censored"]             # includes time-limit runs -> "≥"
    shown = to_display(t)
    assert shown.at["Average", "solver_time_s"].startswith("≥ ") and shown.at["i1", "gap_pct"] == "0"
    assert shown.at["i3", "objective"] == "–"


def test_uncensored_average_has_no_marker(df):
    t = summary_table(df[df["instance"] == "i1"], "AF")
    assert not t.attrs["censored"] and not to_display(t).at["Average", "solver_time_s"].startswith("≥")


def test_comparison_table_counts_and_built_only_averages(df):
    c = comparison_table(df)
    assert list(c.index) == ["AF", "SP"]
    af, sp = c.loc["AF"], c.loc["SP"]
    assert (af["OPTIMAL (proven)"], af["TIME_LIMIT"], af["TIME_LIMIT_NOSOL"], af["not built"]) == (1, 1, 1, 0)
    assert af["avg gap %"] == 5 and af["max gap %"] == 10
    assert ("AF", "avg solver time (s)") in c.attrs["censored"]
    # SP: superseded row ignored; COLUMN_CAP is "not built"; CHECK_FAILED is never "optimal"
    assert sp["runs"] == 3 and sp["OPTIMAL (proven)"] == 1 and sp["not built"] == 1 and sp["other (see rows)"] == 1
    assert sp["built runs"] == 2 and sp["avg #vars"] == (40 + 900) / 2       # over built runs only
    assert ("SP", "avg solver time (s)") not in c.attrs["censored"]


def test_equal_budget_column(df):
    c = comparison_table(df, budget_s=5)
    assert c.loc["AF", "proven within 5 s end-to-end"] == 0 and c.loc["SP", "proven within 5 s end-to-end"] == 1


def test_stale_and_ambiguous_data_are_refused(tmp_path):
    path = str(tmp_path / "runs.csv")
    write_rows(path, ROWS[:2] + [row("i9", "AF", "OPTIMAL", config_hash="h2")])
    with pytest.raises(ValueError, match="mixes"):
        load_runs(path)
    with pytest.raises(ValueError, match="stale"):
        load_runs(path, expected_config_hash="h1")
    write_rows(path, ROWS[:2] + [row("i1", "AF", "OPTIMAL")])                 # two live rows for (i1, AF)
    with pytest.raises(ValueError, match="duplicate"):
        load_runs(path)
    write_rows(path, ROWS[:1])
    with pytest.raises(ValueError, match="MANIFEST"):
        load_runs(path, manifest={"i1": "another-sha"})


def test_tables_on_real_heuristic_runs():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "runs.csv")
        run_all(PROTO, ["H"], config.config_snapshot(), out, log=lambda *a: None)
        df = load_runs(out, expected_config_hash=config.config_hash())
        t = summary_table(df, "H")
        assert len(t) == len(PROTO) + 2 and set(t["status"].iloc[:-2]) == {"HEURISTIC"}
        assert t.at["P0_example8", "objective"] == 945.0
        assert t.at["Sum", "objective"] == df["objective"].sum()
        c = comparison_table(df)
        assert c.loc["H", "heuristic only"] == len(PROTO) and c.loc["H", "OPTIMAL (proven)"] == 0
        assert to_display(c).shape == c.shape


def test_lp_rows_are_left_out_of_the_comparison_table_unless_asked(tmp_path):
    path = str(tmp_path / "runs.csv")
    write_rows(path, ROWS[:3] + [row("i1", "LP-AF", "OPTIMAL", lp_obj=900, solver_time_s=0.1, n_vars=100)])
    df = load_runs(path)
    assert list(comparison_table(df).index) == ["AF"]
    assert list(comparison_table(df, ["AF", "LP-AF"]).index) == ["AF", "LP-AF"]
