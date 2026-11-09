"""Benchmark freeze (pilot/freeze.py, owner B): MANIFEST fingerprints must equal the runner's instance_sha256,
whatever the line endings of the local copy (a Windows CRLF copy and the repo's LF copy are the same instance)."""
import os
import shutil
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew.version import file_sha256  # noqa: E402
from pilot import freeze  # noqa: E402

P0 = os.path.join(ROOT, "instances", "proto", "P0_example8.json")


def test_manifest_hash_ignores_line_endings(tmp_path):
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    from pathlib import Path
    data = Path(P0).read_bytes().replace(b"\r\n", b"\n")
    lf.write_bytes(data)
    crlf.write_bytes(data.replace(b"\n", b"\r\n"))
    assert freeze.sha256(str(lf)) == freeze.sha256(str(crlf)) == file_sha256(str(lf))


def test_freeze_writes_runner_compatible_manifest(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(P0, src / "P0_example8.json")
    man = freeze.freeze(pd.DataFrame({"instance": ["P0_example8"], "class": ["EASY"]}), str(src), str(tmp_path / "final"))
    written = pd.read_csv(tmp_path / "final" / "MANIFEST.csv")
    assert written["sha256"].iloc[0] == file_sha256(P0) == man["sha256"].iloc[0]
    assert (tmp_path / "final" / "README.md").exists()
