"""Tests for crew/sysinfo.py (v1.6): peak memory works on every OS, and machine facts are recorded.
    pytest -q tests/test_sysinfo.py
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from crew import config  # noqa: E402
from crew.sysinfo import machine_info, peak_memory_mb, suggested_mem_limit_gb  # noqa: E402


def test_peak_memory_sees_a_200_mb_block():
    # Fresh process fills a 200 MB block: the peak must then be at least ~190 MB and never go down.
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from crew.sysinfo import peak_memory_mb as p;"
            "a = p(); x = b'1' * 200_000_000; print(a, p())")
    out = subprocess.run([sys.executable, "-c", code, ROOT], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    before, after = map(float, out.split())
    assert after >= 190 and after >= before, (before, after)


def test_peak_memory_is_positive_here():
    assert peak_memory_mb() > 1


def test_machine_info_has_cpu_and_ram():
    info = machine_info()
    assert info["cpu"] and info["ram_gb"] > 0 and info["logical_cores"] >= 1


def test_threads_fit_the_machine():
    assert isinstance(config.GUROBI_PARAMS["Threads"], int)
    assert config.GUROBI_PARAMS["Threads"] <= machine_info()["physical_cores"]      # plan 10.5: threads <= cores
    assert suggested_mem_limit_gb() >= 1


def test_machine_id_ignores_display_formatting_and_software_versions(monkeypatch):
    import crew.sysinfo as si
    from crew import runner
    from crew.sysinfo import fingerprint_facts
    runner.machine_id.cache_clear()
    before = runner.machine_id()
    facts = fingerprint_facts()
    assert set(facts) == {"v", "cpu", "physical_cores", "logical_cores", "os", "ram_gib"}   # no python/gurobi
    assert isinstance(facts["ram_gib"], int) and facts["ram_gib"] >= 1
    # a change in how machine_info() DISPLAYS things (units, rounding, versions) must not change the id
    monkeypatch.setattr(si, "machine_info", lambda: {"ram_gb": 999.9, "python": "9.9", "gurobi": "99"})
    runner.machine_id.cache_clear()
    assert runner.machine_id() == before
    runner.machine_id.cache_clear()
