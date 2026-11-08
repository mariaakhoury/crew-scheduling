"""HiGHS development fallback (owner B): both models solved by HiGHS must reproduce the reference optima on P0..P5,
and the LP relaxations must keep Theorem 3 (LP-AF <= LP-SP). Skipped when the optional package highspy is missing.

    pytest -q tests/test_highs_fallback.py
"""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
pytest.importorskip("highspy", reason="optional: pip install highspy")
pytest.importorskip("gurobipy")

from crew import config                                  # noqa: E402
from crew.highs_fallback import solve_instance           # noqa: E402
from crew.instance import load_instance                  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
HAVE_AF = os.path.exists(os.path.join(ROOT, "crew", "model_arcflow.py"))


@pytest.mark.parametrize("path", PROTO, ids=lambda p: os.path.basename(p).split("_")[0])
@pytest.mark.parametrize("model", ["SP", "AF"])
def test_highs_reaches_reference_optimum(path, model):
    if model == "AF" and not HAVE_AF:
        pytest.skip("crew/model_arcflow.py (A2) not available")
    inst = load_instance(path)
    r = solve_instance(inst, model)
    assert r["status"] == "OPTIMAL", r
    assert r["check_ok"] is True
    assert abs(r["objective"] - inst.reference["cost"]) <= config.COST_TOL


@pytest.mark.parametrize("path", PROTO, ids=lambda p: os.path.basename(p).split("_")[0])
def test_highs_lp_dominance(path):
    if not HAVE_AF:
        pytest.skip("crew/model_arcflow.py (A2) not available")
    inst = load_instance(path)
    lp_af = solve_instance(inst, "AF", relax=True)["objective"]
    lp_sp = solve_instance(inst, "SP", relax=True)["objective"]
    assert lp_af <= lp_sp + 1e-6 <= inst.reference["cost"] + 2e-6
