"""Tests for crew/final_runs.py (C8 pre-flight checks and time projection). Owner: Member C."""
import os
import shutil

import pandas as pd
import pytest

from crew import config, final_runs
from crew.version import file_sha256

CAND = os.path.join(os.path.dirname(__file__), "..", "instances", "candidates")


def _freeze(tmp_path, k=15):
    """A fake instances/final with k frozen candidate files and a matching MANIFEST.csv."""
    files = sorted(f for f in os.listdir(CAND) if f.endswith(".json"))[:k]
    rows = []
    for f in files:
        shutil.copy(os.path.join(CAND, f), tmp_path / f)
        rows.append({"name": f[:-5], "file": f, "sha256": file_sha256(str(tmp_path / f))})
    pd.DataFrame(rows).to_csv(tmp_path / "MANIFEST.csv", index=False)
    return files


def test_manifest_ok(tmp_path):
    files = _freeze(tmp_path)
    paths, problems = final_runs.manifest_paths(str(tmp_path))
    assert problems == [] and [os.path.basename(p) for p in paths] == files


def test_manifest_missing(tmp_path):
    paths, problems = final_runs.manifest_paths(str(tmp_path))
    assert paths == [] and "not found" in problems[0]


def test_manifest_detects_changed_missing_and_too_few(tmp_path):
    files = _freeze(tmp_path, k=15)
    with open(tmp_path / files[0], "a", encoding="utf-8") as fh:
        fh.write(" ")
    os.remove(tmp_path / files[1])
    man = pd.read_csv(tmp_path / "MANIFEST.csv").iloc[:-1]       # 14 rows: below the course minimum
    man.to_csv(tmp_path / "MANIFEST.csv", index=False)
    _, problems = final_runs.manifest_paths(str(tmp_path))
    text = " | ".join(problems)
    assert "lists 14 instances" in text and "changed after the freeze" in text and "missing frozen file" in text


def _fake_git(head="a" * 40, tag="a" * 40, dirty=""):
    def git(*args):
        if args[:1] == ("rev-parse",):
            return head
        if args[:1] == ("rev-list",):
            return tag
        if args[:1] == ("status",):
            return dirty
        raise AssertionError(args)
    return git


def test_git_checks():
    assert final_runs.git_problems(git=_fake_git()) == []
    assert "does not exist yet" in final_runs.git_problems(git=_fake_git(tag=None))[0]
    assert "is not v1.0-final-run" in final_runs.git_problems(git=_fake_git(tag="b" * 40))[0]
    assert "-dirty" in final_runs.git_problems(git=_fake_git(dirty=" M crew/runner.py"))[0]
    assert "git not available" in final_runs.git_problems(git=_fake_git(head=None))[0]


def test_projection_uses_confirmation_times(tmp_path):
    cfg = config.config_snapshot()
    confirm = pd.DataFrame([
        {"instance": "a", "method": "AF", "end_to_end_s": 120.0, "t_build_s": 1.0, "t_enum_s": None},
        {"instance": "a", "method": "SP", "end_to_end_s": 10.0, "t_build_s": 2.0, "t_enum_s": 3.0},
    ])
    confirm.to_csv(tmp_path / "confirm.csv", index=False)
    exp, worst = final_runs.project_minutes(["a"], ["AF", "SP"], str(tmp_path / "confirm.csv"), cfg)
    assert exp == pytest.approx((120 + 3 + 10 + 3) / 60)
    limit = cfg["GUROBI_TIME_LIMIT_S"] + cfg["BUILD_LIMIT_S"]
    assert worst == pytest.approx(2 * (limit + 3) / 60)
    exp_unknown, _ = final_runs.project_minutes(["not-run"], ["AF"], str(tmp_path / "confirm.csv"), cfg)
    assert exp_unknown == pytest.approx((limit + 3) / 60)         # unknown instance: worst case, never optimistic


def test_nights_cover_the_plan():
    night1 = set(final_runs.NIGHTS[1][0][1])
    assert night1 == {"H", "AF", "AF+S", "SP", "SP+S", "LP-AF", "LP-SP"}
    assert final_runs.NIGHTS[2][0][1] == final_runs.NIGHTS[1][0][1]   # rerun pass = same set (resume reruns once)
    assert final_runs.NIGHTS[2][-1][1] == ("LP-AF-naive",)


def test_rehearsal_refuses_real_runs_csv():
    with pytest.raises(SystemExit):
        final_runs.main(["--night", "1", "--rehearsal", "--dry-run"])


def test_dry_run_stops_without_manifest(tmp_path, capsys):
    assert final_runs.main(["--night", "1", "--dry-run", "--final-dir", str(tmp_path)]) == 1
    assert "NOT STARTING" in capsys.readouterr().out
