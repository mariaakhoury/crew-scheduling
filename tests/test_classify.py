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


def test_several_pilot_files_are_read_together(tmp_path):
    from pilot.classify import load_runs
    a, b = _rows({"e1": SPEC["e1"]}), _rows({"tl": SPEC["tl"]}).assign(superseded="no")
    b = pd.concat([b, b.assign(superseded="yes", status="ERROR")])          # superseded rows never count
    a.to_csv(tmp_path / "a.csv", index=False)
    b.to_csv(tmp_path / "b.csv", index=False)
    df = load_runs([str(tmp_path / "a.csv"), str(tmp_path / "b.csv")])
    assert sorted(df["instance"].unique()) == ["e1", "tl"] and "ERROR" not in set(df["status"])


def test_grid_exclusion():
    from pilot.run_pilot import configurations
    grid = {"n": [20], "m": [2, 3], "L_by_n": {"20": [360, 480]}, "w_ratio": 0.75, "seeds": [201],
            "exclude": ["rt_n20_m3_L480_s201"]}
    names = [c["name"] for c in configurations(grid)]
    assert len(names) == 3 and "rt_n20_m3_L480_s201" not in names


def test_confirmation_candidates_are_rechecks_plus_two_spares_per_class():
    cand = confirmation_candidates(classify_all(_rows(SPEC)))
    # spread spares: of the three EASY instances (e1 < e2 < e3 by n, L) the smallest and the largest are kept
    assert set(cand["instance"]) == {"e1", "e3", "md", "hd", "tl", "nb", "sp_only"}
    assert set(cand.loc[cand["instance"].isin(["e1", "e3", "md"]), "why_candidate"]) == {"spare"}


def test_spread_take_keeps_both_ends():
    from pilot.classify import spread_take
    pool = pd.DataFrame({"x": range(10)})
    assert list(spread_take(pool, 4)["x"]) == [0, 3, 6, 9]
    assert list(spread_take(pool, 1)["x"]) == [5]
    assert len(spread_take(pool, 20)) == 10 and spread_take(pool, 0).empty


def _many_time_limit(k, flagged_ns):
    spec = {}
    for i, n in enumerate(range(50, 50 + 50 * k, 50)):
        sp = ("COLUMN_CAP", None) if n in flagged_ns else ("OPTIMAL", 1.0)
        spec[f"t{i:02d}"] = (n, 360, "TIME_LIMIT", 30.0, *sp)
    return classify_all(_rows(spec))


def test_selection_is_spread_and_keeps_two_sp_not_built():
    from pilot.classify import select
    classes = _many_time_limit(12, flagged_ns={550, 600})      # only the two largest have SP not built
    sel = select(classes)
    tl = sel[(sel["class"] == "TIME_LIMIT") & (sel["selected_as"] == "class target")]   # fill-up adds the rest
    assert len(tl) == 6
    assert int(tl["SP_not_built"].sum()) >= 2                    # the reserve takes both flagged instances
    assert tl["n"].min() == 50 and tl["n"].max() == 600          # smallest and largest both present


def test_fill_up_to_15_from_unused_time_limit_then_hard_then_easy():
    from pilot.classify import select
    spec = {f"tl{i:02d}": (50 + 10 * i, 360, "TIME_LIMIT", 30.0, "OPTIMAL", 1.0) for i in range(10)}
    spec.update({f"e{i}": (20 + i, 360, "OPTIMAL", 0.1, "OPTIMAL", 0.1) for i in range(8)})
    spec["nb1"], spec["nb2"] = (400, 360, "TIME_LIMIT", 30.0, "COLUMN_CAP", None), (500, 360, "TIME_LIMIT", 30.0,
                                                                                    "COLUMN_CAP", None)
    sel = select(classify_all(_rows(spec)))          # targets: 6 TIME_LIMIT + 4 EASY = 10 -> 5 places to fill
    assert len(sel) == 15
    filled = sel[sel["selected_as"] == "fill-up to 15"]
    assert len(filled) == 5 and set(filled["class"]) == {"TIME_LIMIT"}      # 12 TL available: fill from TL first
    assert int(sel["SP_not_built"].sum()) >= 2


def test_no_fill_up_when_targets_reach_15():
    from pilot.classify import select
    spec = {f"tl{i:02d}": (50 + 10 * i, 360, "TIME_LIMIT", 30.0, "OPTIMAL", 1.0) for i in range(6)}
    spec.update({f"h{i}": (100 + i, 360, "OPTIMAL", 60.0, "OPTIMAL", 1.0) for i in range(5)})
    spec.update({f"m{i}": (60 + i, 360, "OPTIMAL", 5.0, "OPTIMAL", 0.1) for i in range(5)})
    spec.update({f"e{i}": (20 + i, 360, "OPTIMAL", 0.1, "OPTIMAL", 0.1) for i in range(4)})
    sel = select(classify_all(_rows(spec)))
    assert len(sel) == 20 and set(sel["selected_as"]) == {"class target"}


def test_cap_keeps_large_and_sp_not_built_candidates():
    from pilot import classify as C
    classes = _many_time_limit(30, flagged_ns={1450, 1500})
    cand = C.confirmation_candidates(classes)
    assert len(cand) == C.MAX_CONFIRM_FILES
    assert cand["n"].max() == 1500 and int(cand["SP_not_built"].sum()) >= 2
