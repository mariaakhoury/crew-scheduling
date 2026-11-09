"""Classification and confirmation-candidate rules (pilot/classify.py, owner B; Master Plan §10.3)."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pilot.classify import classify_all, confirmation_candidates  # noqa: E402


def _rows(spec):
    """spec: instance -> (n, L, AF status, AF time, SP status, SP time)."""
    out = []
    for name, (n, L, afs, aft, sps, spt) in spec.items():
        for m, st, t in (("AF", afs, aft), ("SP", sps, spt)):
            out.append({"instance": name, "method": m, "status": st, "solver_time_s": t, "n": n, "m": 2, "L": L,
                        "W": int(0.75 * L), "n_arcs": 10, "n_duties": 5 if m == "SP" else None})
    return pd.DataFrame(out)


SPEC = {
    "e1": (50, 360, "OPTIMAL", 0.1, "OPTIMAL", 0.1),
    "e2": (50, 480, "OPTIMAL", 0.2, "OPTIMAL", 0.1),
    "e3": (60, 360, "OPTIMAL", 0.2, "OPTIMAL", 0.2),
    "md": (50, 600, "OPTIMAL", 4.5, "OPTIMAL", 0.1),
    "hd": (100, 480, "OPTIMAL", 60.0, "OPTIMAL", 1.0),
    "tl": (200, 360, "TIME_LIMIT", 30.0, "OPTIMAL", 2.0),
    "nb": (400, 480, "BUILD_LIMIT", None, "BUILD_LIMIT", None),
    "sp_only": (300, 480, "TIME_LIMIT", 30.0, "COLUMN_CAP", None),
}


def test_classes_follow_the_rule_order():
    c = classify_all(_rows(SPEC)).set_index("instance")["class"].to_dict()
    assert c == {"e1": "EASY", "e2": "EASY", "e3": "EASY", "md": "MEDIUM", "hd": "HARD",
                 "tl": "TIME_LIMIT", "nb": "NOT_BUILT", "sp_only": "TIME_LIMIT"}


def test_neither_model_built_is_never_easy():
    c = classify_all(_rows({"nb": SPEC["nb"]})).iloc[0]
    assert c["class"] == "NOT_BUILT" and bool(c["SP_not_built"])


def test_confirm_stage_keeps_only_stable_pilot_classes():
    from pilot.classify import merge_with_pilot
    pilot = classify_all(_rows(SPEC))
    spec_only_buildable = {"bm": (100, 600, "TIME_LIMIT", 30.0, "COLUMN_CAP", None)}   # not re-run
    pilot = pd.concat([pilot, classify_all(_rows({"b1": (60, 360, "OPTIMAL", 3.0, "BUILD_LIMIT", None)}))])
    confirm = classify_all(_rows({"tl": (200, 360, "OPTIMAL", 80.0, "OPTIMAL", 2.0)}))      # TL at 30 s -> HARD
    merged = merge_with_pilot(confirm, pilot).set_index("instance")
    assert merged.loc["tl", "class"] == "HARD" and merged.loc["tl", "class_source"] == "confirmation"
    assert merged.loc["e1", "class"] == "EASY" and merged.loc["md", "class"] == "MEDIUM"     # stable pilot classes
    assert merged.loc["b1", "class"] == "UNCONFIRMED"           # MEDIUM only because SP was not built in 30 s
    assert merged.loc["nb", "class"] == "UNCONFIRMED" and merged.loc["sp_only", "class"] == "UNCONFIRMED"
    assert not spec_only_buildable.keys() & set(merged.index)


def test_grid_exclusion():
    from pilot.run_pilot import configurations
    grid = {"n": [20], "m": [2, 3], "L_by_n": {"20": [360, 480]}, "w_ratio": 0.75, "seeds": [201],
            "exclude": ["rt_n20_m3_L480_s201"]}
    names = [c["name"] for c in configurations(grid)]
    assert len(names) == 3 and "rt_n20_m3_L480_s201" not in names


def test_confirmation_candidates_are_rechecks_plus_two_spares_per_class():
    cand = confirmation_candidates(classify_all(_rows(SPEC)))
    assert set(cand["instance"]) == {"e1", "e2", "md", "hd", "tl", "nb", "sp_only"}   # e3 = third EASY: not a spare
    assert set(cand.loc[cand["instance"].isin(["e1", "e2", "md"]), "why_candidate"]) == {"spare"}
