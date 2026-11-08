"""Acceptance test for rules V1-V10 (now implemented in crew/instance.py; should pass).
Acceptance test for rules V1-V10:
  - every prototype file -> no errors
  - every file in tests/invalid_instances -> at least one error message starting with its expected rule code
    pytest -q tests/test_instance_validation.py
"""
import csv, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.instance import load_instance_raw_errors  # noqa: E402  (see instance.py)


def test_prototype_instances_valid():
    for f in sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json"))):
        assert load_instance_raw_errors(f) == [], f


def test_invalid_instances_rejected_with_right_rule():
    for row in csv.DictReader(open(os.path.join(ROOT, "tests", "invalid_instances", "EXPECTED.csv"), encoding="utf-8")):
        errs = load_instance_raw_errors(os.path.join(ROOT, "tests", "invalid_instances", row["file"]))
        assert any(e.startswith(row["expected_rule"] + ":") for e in errs), (row["file"], errs)
