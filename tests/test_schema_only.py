"""Runs today (no project code needed). Shows what JSON Schema alone can and cannot catch.
    pytest -q tests/test_schema_only.py
"""
import csv, glob, json, os
import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = json.load(open(os.path.join(ROOT, "instance.schema.json"), encoding="utf-8"))


def schema_ok(path):
    try:
        jsonschema.validate(json.load(open(path, encoding="utf-8")), SCHEMA)
        return True
    except jsonschema.ValidationError:
        return False


def test_prototype_files_pass_schema():
    files = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
    assert len(files) == 6
    assert all(schema_ok(f) for f in files)


def test_schema_catches_only_what_expected_csv_says():
    # Most rules (V2-V10) are NOT checkable by JSON Schema; validate_instance must check them.
    for row in csv.DictReader(open(os.path.join(ROOT, "tests", "invalid_instances", "EXPECTED.csv"), encoding="utf-8")):
        path = os.path.join(ROOT, "tests", "invalid_instances", row["file"])
        assert schema_ok(path) == (row["caught_by_json_schema"] == "no"), row["file"]
