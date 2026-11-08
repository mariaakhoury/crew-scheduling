"""Tests for the C0 fingerprints and the C3/C4 runner (status logic, rows, resume, kill, rerun-once).
    pytest -q tests/test_runner.py
"""
import glob, importlib.util, json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.checker import check_schedule  # noqa: E402
from crew.instance import load_instance  # noqa: E402
from crew.run_child import certify, classify, gap_pct  # noqa: E402
from crew.runner import COLUMNS, read_rows, run_all, run_one  # noqa: E402
from crew.version import file_sha256, git_commit, source_fingerprint  # noqa: E402

PROTO = sorted(glob.glob(os.path.join(ROOT, "instances", "proto", "*.json")))
P0_PATH = os.path.join(ROOT, "instances", "proto", "P0_example8.json")
P0 = load_instance(P0_PATH)
CFG = config.config_snapshot()
quiet = lambda *a, **k: None  # noqa: E731


# ------------------------------------------------------------------ C0 fingerprints

def test_config_hash_is_stable_and_sensitive():
    assert config.config_hash() == config.config_hash(config.config_snapshot())
    assert len(config.config_hash()) == 64
    assert config.config_hash(config.config_snapshot(GUROBI_TIME_LIMIT_S=1)) != config.config_hash()


def test_config_snapshot_is_a_copy_and_rejects_unknown_keys():
    snap = config.config_snapshot()
    snap["GUROBI_PARAMS"]["Threads"] = 99
    assert config.GUROBI_PARAMS["Threads"] != 99
    try:
        config.config_snapshot(NOT_A_SETTING=1)
    except KeyError:
        return
    raise AssertionError("unknown override must raise KeyError")


def test_code_and_file_fingerprints():
    assert git_commit() and source_fingerprint() == source_fingerprint()
    assert file_sha256(P0_PATH) == file_sha256(P0_PATH) and len(file_sha256(P0_PATH)) == 64


def test_file_sha256_ignores_windows_line_endings():
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        with open(a, "wb") as fh:  # binary write (no text encoding involved)
            fh.write(b'{"x": 1}\n')
        with open(b, "wb") as fh:  # binary write (no text encoding involved)
            fh.write(b'{"x": 1}\r\n')
        assert file_sha256(a) == file_sha256(b)


# ------------------------------------------------------------------ overnight safety

def test_keep_awake_is_active_during_a_batch_and_released_after():
    from crew.runner import keep_awake
    if sys.platform != "win32":
        with keep_awake():                       # no-op elsewhere, must not fail
            return
    import ctypes
    k32 = ctypes.windll.kernel32
    CONT, SYS = 0x80000000, 0x00000001

    def current():                               # SetThreadExecutionState returns the PREVIOUS state; set it back
        prev = k32.SetThreadExecutionState(CONT) & 0xFFFFFFFF
        k32.SetThreadExecutionState(prev)
        return prev

    with keep_awake():
        assert current() & SYS, "system-required flag not set during the batch"
    assert not current() & SYS, "flag not released after the batch"


# ------------------------------------------------------------------ pure status logic (Master Plan §10.6)

def test_classify_maps_every_gurobi_outcome():
    assert classify(2, 1) == "OPTIMAL"
    assert classify(9, 3) == "TIME_LIMIT"
    assert classify(9, 0) == "TIME_LIMIT_NOSOL"
    assert classify(17, 0) == "MEM_LIMIT_SOLVE"
    assert classify(3, 0) == "INFEASIBLE" and classify(4, 0) == "INF_OR_UNBD"
    assert classify(12, 0) == "NUMERIC" and classify(13, 1) == "SUBOPTIMAL"
    assert classify(999, 0) == "ERROR"


def test_certificate_accepts_a_true_optimum_and_rejects_every_failure():
    opt = P0.reference["schedule"]
    assert certify(P0, opt, 945.0, 944.6, CFG)[0]                       # value - bound = 0.4 <= 0.49
    assert not certify(P0, opt, 945.0, 944.0, CFG)[0]                   # gap 1.0 > MIPGapAbs
    assert not certify(P0, opt, 945.25, 945.25, CFG)[0]                 # not a multiple of $0.50 / != checker
    assert not certify(P0, [[0, 1, 4, 5]], 945.0, 945.0, CFG)[0]        # checker rejects (trips missing)
    assert not certify(P0, None, 945.0, 945.0, CFG)[0]


def test_gap_only_with_an_incumbent():
    assert gap_pct(1000.0, 900.0) == 10.0
    assert gap_pct(None, 900.0) is None


# ------------------------------------------------------------------ the runner, end to end (real subprocesses)

def test_H_rows_resume_and_cache():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "runs.csv")
        run_all(PROTO, ["H"], CFG, out, log=quiet)
        rows = read_rows(out)
        assert len(rows) == len(PROTO)
        for r in rows:
            inst = load_instance(os.path.join(ROOT, "instances", "proto", r["instance"] + ".json"))
            assert r["status"] == "HEURISTIC" and r["feasible_checked"] == "yes" and r["globally_proven"] == "no"
            assert r["config_hash"] == config.config_hash(CFG) and r["instance_sha256"]
            with open(os.path.join(d, r["solution_file"]), encoding="utf-8") as fh:
                sol = json.load(fh)
            assert check_schedule(inst, sol["schedule"], float(r["objective"])).ok
            assert float(r["end_to_end_s"]) >= 0 and float(r["peak_rss_mb"]) > 0
            assert os.path.exists(os.path.join(d, "heuristic", r["instance"] + ".json"))
        p0 = next(r for r in rows if r["instance"] == "P0_example8")
        assert float(p0["objective"]) == 945.0 and float(p0["heuristic_cost"]) == 945.0

        run_all(PROTO, ["H"], CFG, out, log=quiet)                     # resume: nothing new
        assert len(read_rows(out)) == len(PROTO)
        assert os.path.exists(os.path.join(d, "env.txt"))


def test_changed_settings_never_reuse_old_rows():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "runs.csv")
        run_all([P0_PATH], ["H"], CFG, out, log=quiet)
        run_all([P0_PATH], ["H"], config.config_snapshot(GUROBI_TIME_LIMIT_S=60), out, log=quiet)
        rows = read_rows(out)
        assert len(rows) == 2 and len({r["config_hash"] for r in rows}) == 2


def test_forced_kill_before_the_solve_gives_KILLED_BUILD_with_phase():
    with tempfile.TemporaryDirectory() as d:
        row = run_one(P0_PATH, "H", config.config_snapshot(HARD_KILL_S=0.001), d)
        assert row["status"] == "KILLED_BUILD" and row["killed_phase"] != "solve", row
        assert list(row) == COLUMNS


def test_missing_model_is_an_honest_error_rerun_once_then_kept():
    if importlib.util.find_spec("crew.model_arcflow") is not None:
        return                                                          # Model 1 exists: nothing to test here
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "runs.csv")
        for _ in range(3):
            run_all([P0_PATH], ["AF"], CFG, out, log=quiet)
        rows = read_rows(out)
        assert [r["status"] for r in rows] == ["ERROR", "ERROR"]          # first run + exactly one rerun
        assert [r["superseded"] for r in rows] == ["yes", "no"]          # never deleted, only marked
        assert "model_arcflow" in rows[1]["error"]
