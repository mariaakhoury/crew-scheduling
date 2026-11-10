"""B8 / B12 / B13 report logic (owner B) on small synthetic runs.csv tables - no solver needed."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import analysis_heuristic as AH  # noqa: E402
from crew import analysis_scaling as AS  # noqa: E402


def _row(inst, method, status, t=None, gap=None, nodes=1, n=50, duties=None, **kw):
    row = {"instance": inst, "method": method, "status": status, "solver_time_s": t, "gap_pct": gap,
           "nodes": nodes, "n": n, "L": 360, "n_arcs": 10, "n_duties": duties, "objective": 100.0,
           "best_bound": 100.0 if status == "OPTIMAL" else 90.0, "t_first_incumbent_s": 1.0,
           "start_accepted": "yes" if method.endswith("+S") else None, "heuristic_cost": 110.0,
           "feasible_checked": "yes", "end_to_end_s": (t or 0) + 1, "t_enum_s": 0.5, "t_build_s": 0.5,
           "time_limit_s": 120}
    row.update(kw)
    return row


RUNS = pd.DataFrame([
    _row("a", "AF", "OPTIMAL", 10), _row("a", "AF+S", "OPTIMAL", 5),                    # time: +0.5
    _row("b", "AF", "TIME_LIMIT", 120, gap=20), _row("b", "AF+S", "TIME_LIMIT", 120, gap=10),   # final gap: +0.5
    _row("c", "AF", "TIME_LIMIT", 120, gap=20), _row("c", "AF+S", "OPTIMAL", 60),       # solved only with start
    _row("a", "SP", "OPTIMAL", 0.2, duties=100), _row("a", "SP+S", "OPTIMAL", 0.2, duties=100),  # tie at root
    _row("b", "SP", "COLUMN_CAP", duties=2_000_001), _row("b", "SP+S", "COLUMN_CAP", duties=2_000_001),
    _row("c", "SP", "BUILD_LIMIT", duties=5000), _row("c", "SP+S", "BUILD_LIMIT", duties=5000),
])


def test_improvement_bases():
    p = AH.paired_effect(RUNS).set_index(["model", "instance"])
    assert p.loc[("AF", "a"), "basis"] == "time" and abs(p.loc[("AF", "a"), "improvement"] - 0.5) < 1e-9
    assert p.loc[("AF", "b"), "basis"] == "final gap" and abs(p.loc[("AF", "b"), "improvement"] - 0.5) < 1e-9
    assert p.loc[("AF", "c"), "basis"] == "solved only with start" and p.loc[("AF", "c"), "improvement"] == 1
    assert p.loc[("SP", "b"), "basis"] == "not comparable"


def test_h6_and_no_help_reasons():
    v = AH.h6_verdict(RUNS)
    assert v["verdict"] == "confirmed" and v["comparable_SP"] == 1
    nh = AH.no_help_list(RUNS).set_index(["model", "instance"])
    assert "root node" in nh.loc[("SP", "a"), "reason"]
    assert "not comparable" in nh.loc[("SP", "b"), "reason"]


def test_best_known_includes_the_heuristic_schedule():
    runs = pd.DataFrame([_row("z", "AF", "TIME_LIMIT", 120, gap=20, objective=120.0, best_bound=90.0),
                         _row("z", "H", "HEURISTIC", objective=110.0)])
    q = AH.heuristic_quality(runs).loc["z"]
    assert q["best_value"] == 110.0 and bool(q["ls_is_best_known"])      # never "worse than the best known"
    assert q["ls_gap_pct"] >= 0                                          # gap to the bound, upper bound only


def test_h5_counts_build_failures_never_as_timeouts():
    v = AS.h5_verdict(RUNS)
    assert v == {"SP_not_built": 2, "AF_build_failures": 0, "verdict": "confirmed"}


def test_reports_write_their_files(tmp_path):
    runs = tmp_path / "runs.csv"
    RUNS.to_csv(runs, index=False)
    AH.report(str(runs), None, str(tmp_path / "b12"))
    AS.report(str(runs), None, str(tmp_path / "b13"))
    for f in ("b12/B12_summary.md", "b12/paired_effect.png", "b13/B13_summary.md", "b13/status_map.png"):
        assert (tmp_path / f).exists(), f


def test_verify_reports_missing_instance_instead_of_crashing(tmp_path):
    from qa.verify_results import verify
    sol = tmp_path / "solutions"
    sol.mkdir()
    (sol / "r1.json").write_text('{"schedule": [[0]]}', encoding="utf-8")
    pd.DataFrame([{"run_id": "r1", "instance": "ghost", "method": "AF", "status": "OPTIMAL", "objective": 1.0,
                   "best_bound": 1.0, "solution_file": "solutions/r1.json"}]).to_csv(tmp_path / "runs.csv", index=False)
    problems = verify(str(tmp_path / "runs.csv"), None, str(tmp_path))
    assert any("ghost" in p and "cannot be loaded" in p for p in problems)
