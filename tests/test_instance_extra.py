"""Extra loader tests (v1.4): V9 still runs when V7 fails, and non-English text loads as UTF-8.
    pytest -q tests/test_instance_extra.py
"""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance, load_instance_raw_errors, save_instance  # noqa: E402

INVALID = os.path.join(ROOT, "tests", "invalid_instances")


def test_v9_still_checked_when_name_is_wrong():
    # I17 has a wrong reference cost (V9). Copied under another file name it ALSO breaks V7.
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "renamed_copy.json")
        shutil.copy(os.path.join(INVALID, "I17_ref_wrong_cost.json"), path)
        errs = load_instance_raw_errors(path)
        assert any(e.startswith("V7:") for e in errs), errs
        assert any(e.startswith("V9:") for e in errs), errs


def test_non_english_names_round_trip_as_utf8():
    inst = load_instance(os.path.join(ROOT, "instances", "proto", "P0_example8.json"))
    inst.terminals = ["Beyrouth – Hamra", "جونية"]
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "P0_example8.json")
        raw = json.load(open(os.path.join(ROOT, "instances", "proto", "P0_example8.json"), encoding="utf-8"))
        raw["terminals"] = inst.terminals
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False)       # raw UTF-8 bytes, as an editor would save them
        assert load_instance(path).terminals == inst.terminals
        save_instance(inst, path)
        assert load_instance(path) == inst
