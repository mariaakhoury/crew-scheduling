"""Machine facts and peak memory, the same way on Windows, macOS and Linux. Owner: Member C.

Course rule: all final runs happen on ONE computer, and the notebook states its CPU and RAM (machine_info()).
peak_memory_mb() replaces resource.getrusage, which does not exist on Windows.

IMPORTANT: a process's peak memory only goes up, never down. So measure ONE run per Python process
(the runner already starts one subprocess per run). Two runs in the same process would share one peak.
"""
from __future__ import annotations

import os
import platform
import sys

MB = 1_000_000   # bytes per MB (decimal, like Windows Task Manager)
GIB = 2 ** 30    # bytes per GiB: the unit Windows "Installed RAM" and config.MemLimit use (15.4 on a 16 GB laptop)


def peak_memory_mb() -> float:
    """Highest memory this Python process has used so far, in MB, Gurobi included (gurobipy runs inside it)."""
    if sys.platform == "win32":
        import psutil
        return psutil.Process().memory_info().peak_wset / MB      # Windows "peak working set"
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / MB if sys.platform == "darwin" else peak * 1024 / MB   # macOS: bytes, Linux: KB


def _cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or platform.machine()


def machine_info() -> dict:
    """CPU, cores, RAM, OS, Python and Gurobi version of this computer, for the notebook's 'Setup' section."""
    import psutil
    info = {
        "cpu": _cpu_name(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / GIB, 1),   # GiB
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
    }
    try:
        import gurobipy
        info["gurobi"] = ".".join(map(str, gurobipy.gurobi.version()))
    except Exception:            # gurobipy missing or no licence: still report the rest
        info["gurobi"] = None
    return info


def suggested_mem_limit_gb() -> int:
    """About 75% of this computer's RAM in GiB, rounded down (15.4 GiB -> 11). Use for config.GUROBI_PARAMS['MemLimit'];
    rounding down and binary units keep Gurobi's limit on the safe side whichever GB definition it applies."""
    import psutil
    return int(0.75 * psutil.virtual_memory().total / GIB)


def fingerprint_facts() -> dict:
    """The facts behind runs.csv machine_id: hardware and OS identity only, each with its own fixed definition.

    Deliberately independent of machine_info() (a display dict whose rounding/units may change) and of software
    versions (Python, Gurobi: recorded in their own columns and in env.txt), so the same computer keeps the same id
    across code changes and software updates. RAM is whole GiB of installed memory, so two laptops with the same CPU
    model are still told apart. "v" versions the definition itself; changing it is a deliberate, one-time event."""
    import psutil
    return {"v": 2, "cpu": _cpu_name(), "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True), "os": platform.system(),
            "ram_gib": int(round(psutil.virtual_memory().total / GIB))}
