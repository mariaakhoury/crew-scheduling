"""Shared constants for the whole project. Owner: Member C. Starter kit v1.6 (matches Master Plan v1.5 + issue #1).
RULE: no other file may type a cost, wage, turnaround, limit or Gurobi setting. Import from here.
"""
SCHEMA_VERSION = "1.0"

# --- units: time in integer minutes, money in US dollars ---
# F, C_PER_MIN and TAU are FROZEN for every benchmark instance (rule V6). Difficulty is varied only through
# n, terminals m, timetable density (service window, headways), L and W - never through costs.
F = 300.0            # $ fixed cost per duty (per driver used)
C_PER_MIN = 0.50     # $ per paid minute (paid time = spread of the duty) = $30/h
TAU = 10             # minutes, minimum turnaround between two trips of one duty
COST_STEP = 0.50     # every schedule cost is a multiple of this (F and C_PER_MIN x integer minutes)
COST_TOL = 0.01      # $ tolerance when comparing two costs

# --- experiment limits (identical for every method) ---
# LIMITS RULE (Master Plan v1.5, §7.2): 120 s + 120 s for every method and instance, fixed at the kickoff.
# Never changed per method, per instance, or after seeing results. There is no fallback.
GUROBI_TIME_LIMIT_S = 120   # Gurobi TimeLimit, solve phase only
BUILD_LIMIT_S = 120         # preprocessing + heuristic + enumeration + model build
HARD_KILL_S = GUROBI_TIME_LIMIT_S + BUILD_LIMIT_S + 120   # = 360 s; subprocess killed after this (safety net)
COLUMN_CAP = 2_000_000      # max duties stored for set partitioning (memory guard)
CLOCK_CHECK_EVERY = 10_000  # enumeration checks the build clock every this many duties

# --- Gurobi parameters used for EVERY MIP run ---
GUROBI_PARAMS = {
    "Threads": 4,           # fixed for all runs; must not exceed physical cores of the run machine
    "Seed": 0,
    "MIPGap": 0.0,
    "MIPGapAbs": 0.49,      # < COST_STEP, so OPTIMAL means the exact optimum
    "MemLimit": 11,         # GB; about 75% of the run machine's RAM (15.4 GB laptop -> 11). Check: sysinfo.suggested_mem_limit_gb()
    "LogToConsole": 0,
}

# --- Gurobi numerical tolerances (issue #1, clarification 4) ---
# These are Gurobi's DEFAULTS. They are recorded here so every "optimal" claim can name them; they are
# never set or loosened. Wording: "proven optimal within Gurobi's numerical tolerances ... with the
# schedule and its cost confirmed by the independent checker".
GUROBI_DEFAULT_TOLERANCES = {
    "FeasibilityTol": 1e-6,
    "IntFeasTol": 1e-5,
    "OptimalityTol": 1e-6,
}

# --- shared constraint names (Master Plan v1.5, §7.3); (3) and (7) are variable bounds, not rows ---
CONSTRAINT_NAMES = {
    1: "c1_pred",
    2: "c2_succ",
    4: "c4_Tchain",
    5: "c5_spread",
    6: "c6_Dchain",
    8: "c8_cover",
}

# --- run statuses (Master Plan v1.5, §10.6; issue #1, clarification 2) ---
# Build outcomes are kept apart from solver outcomes: a build failure is never a timeout.
BUILD_FAILURE_STATUSES = ("BUILD_LIMIT", "COLUMN_CAP", "MEM_LIMIT_BUILD", "KILLED_BUILD")
SOLVE_STATUSES = ("OPTIMAL", "TIME_LIMIT", "TIME_LIMIT_NOSOL", "MEM_LIMIT_SOLVE", "KILLED", "CHECK_FAILED")
HARD_THRESHOLD_S = 24       # operational "hard" rule: largest solver time of a BUILT plain model > 24 s


# --- configuration fingerprint (Master Plan v1.5, §10.6 "stale-result protection") ---
# Every runs.csv row stores config_hash. A row whose hash differs from the frozen one is stale and never used.
FROZEN_SETTINGS = ("SCHEMA_VERSION", "F", "C_PER_MIN", "TAU", "COST_STEP", "COST_TOL",
                   "GUROBI_TIME_LIMIT_S", "BUILD_LIMIT_S", "HARD_KILL_S", "COLUMN_CAP", "CLOCK_CHECK_EVERY",
                   "GUROBI_PARAMS", "GUROBI_DEFAULT_TOLERANCES")


def config_snapshot(**overrides) -> dict:
    """The frozen settings as a plain dict (deep copy). Overrides are for tests only, e.g. a forced tiny time limit;
    they change config_hash, so such rows can never be mistaken for real results."""
    import copy
    snap = {k: copy.deepcopy(globals()[k]) for k in FROZEN_SETTINGS}
    unknown = set(overrides) - set(snap)
    if unknown:
        raise KeyError(f"not a frozen setting: {sorted(unknown)}")
    snap.update(overrides)
    return snap


def config_hash(snapshot: dict | None = None) -> str:
    """SHA-256 of the canonical JSON of the settings (sorted keys, no spaces): same settings -> same hash, any OS."""
    import hashlib
    import json
    canonical = json.dumps(config_snapshot() if snapshot is None else snapshot,
                           sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
