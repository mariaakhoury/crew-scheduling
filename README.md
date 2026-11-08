# Group M crew scheduling - working repository (built on starter kit v1.6, schema 1.0)

## Added by Member C (8 Nov), on top of starter kit v1.6
| File | Task | What it is |
|---|---|---|
| `crew/greedy.py` | C1 | `greedy_insertion(inst)`: P0 -> $1177.50 |
| `crew/localsearch.py` | C14 | `local_search(inst, schedule, max_rounds)` (+ `improve`, `heuristic` = method H): P0 -> $945 |
| `crew/config.py` | C0 | added `config_snapshot()` and `config_hash()` (nothing else changed) |
| `crew/version.py` | C0 | `git_commit()` (falls back to a source fingerprint without git), `file_sha256()` for MANIFEST.csv |
| `crew/runner.py`, `crew/run_child.py` | C3/C4 | runner: one subprocess per run, runs.csv, statuses, resume, rerun-once, env.txt |
| `crew/integration.py` | C2 | `start_arcflow`, `start_setpart` (complete MIP starts), `start_accepted(log, cost)` |
| `tests/test_greedy.py`, `test_localsearch.py`, `test_runner.py`, `test_integration.py` | | 28 new tests; whole suite: 53 passed, 1 skipped (Model 1 start acceptance: activates when A2 exists) |

Proposals for issue #1: H rows use status `HEURISTIC`; extra columns `t_solve_s`, `killed_phase`, `error`;
`enumerate_duties` returns status `"complete"` / `"capped"` (else out of time) and takes an absolute `time.perf_counter()` deadline.

---
# Starter kit v1.6 (original README)

**Matches Master Plan v1.5 (frozen) and GitHub issue #1.** No rule, data file or reference optimum changed since v1.2.

Changes in v1.6 (Windows can be the run machine; needs the group's OK in issue #1, because v1.5 said "no psutil"):
- New `crew/sysinfo.py`: `peak_memory_mb()` (Windows: psutil peak working set; Mac/Linux: resource.getrusage),
  `machine_info()` (CPU, cores, RAM, OS, Python, Gurobi version for the notebook) and `suggested_mem_limit_gb()`.
  A process's peak never goes down, so measure one run per process (the runner uses one subprocess per run).
- `requirements.txt`: `psutil` added back. `config.py`: `MemLimit` 12 -> 11 GB (75% of a 15.4 GB laptop).
- Course rule: ALL final runs on ONE computer; print `machine_info()` in the notebook.
- New `tests/test_sysinfo.py`; the smoke notebook also writes `crew/sysinfo.py`.

Changes in v1.5 (no rule, model, data file or reference optimum changed):
- `tools/build_notebook_smoke.py`: reads the crew files as UTF-8 (on Windows the "§" in `config.py` used to come out as "Â§"),
  also writes `instance.schema.json` into the notebook (the loader needs it for rule V1), and its last cell now loads P0 with
  `load_instance` and lets the checker recompute the reference cost ($945).
- New `tests/test_encoding.py`: fails if any `open(...)` in the kit forgets `encoding="utf-8"`, and checks that the smoke
  notebook copies every crew file and the schema byte for byte.

Changes in v1.4 (since v1.2):
- `crew/instance.py` (A): loading, saving and validation **implemented** (rules V1-V10). The checker is imported inside
  the V9 check, so there is no circular import. V9 still runs when only V7 (name) or V8 (labels) fails.
  Files are opened with `encoding="utf-8"` (safe on Windows).
- `crew/checker.py` (B): rules C1-C7 **implemented**. Accepts numpy trip ids from Gurobi. Odd ids (`"7"`, `7.0`, `True`)
  and badly shaped schedules (`None`, `[[0,1,4,5], 7]`) get a C1 error instead of a crash.
- `crew/__init__.py` added.
- New tests: `tests/test_checker.py`, `tests/test_checker_extra.py`.

Still to be written: `make_instance` (A4, rotation generator), `config_snapshot()` / `config_hash()` and
`crew/version.py` (C). Peak memory now works on Windows too (`crew/sysinfo.py`, v1.6).

This folder is the **shared data contract**. **It is not a solver** (no models or heuristic yet).

## What is in the kit
| File | Owner | Status |
|---|---|---|
| `crew/config.py` | C | **complete** (constants only) |
| `crew/instance.py` | A | **implemented**: load, save, validate (V1-V10), features. `make_instance` still to do (A4) |
| `crew/checker.py` | B | **implemented**: C1-C7 |
| `instance.schema.json` | A | **complete**; checks rule V1 only (see below) |
| `data_dictionary.md` | A + B | **complete** |
| `instances/proto/P0..P5.json` | A | **complete data**; validated; reference optima from the pilot-audit models |
| `tests/invalid_instances/` (21 files + `EXPECTED.csv`) | A + B | **complete test data**; each file breaks exactly one rule (V1-V10) |
| `tests/` | A + B | schema, validation, checker, encoding and extra tests |
| `tools/build_notebook_smoke.py` | C | architecture smoke test only (not the project notebook builder) |
| `requirements.txt` | C | draft pins |

Status when packaged: `pytest -q tests/` gives **26 passed, 0 failed**.
First time on a new laptop: `pip install -r requirements.txt` (in a venv), then `pytest -q tests/`.

## JSON Schema is not enough
JSON Schema checks field names, types and the schema version (V1). It **cannot** check ids 0..n-1 in order (V2), start < end and
integer times (V3; it accepts `360.0` as an integer), terminal indices and origin != dest (V4), d_i <= W <= L (V5), cost constants
equal to `config.py` (V6), name = file name (V7), unique labels (V8), a legal reference schedule with the right cost (V9),
or params.n = number of trips (V10). On the 21 broken test files, the schema caught only 2 (both V1). Those rules live in
`validate_instance` / `load_instance_raw_errors`.

## Prototype instances (Stage A data)
| File | Trips | L / W (min) | Reference optimum ($) | How it was verified |
|---|---:|---|---:|---|
| P0_example8 | 8 | 420 / 300 | 945.0 | set partitioning = arc-flow = brute force |
| P1_tt_n10_m3_L360_s0 | 10 | 360 / 270 | 2625.0 | SP = AF = brute force |
| P2_tt_n10_m3_L360_s1 | 10 | 360 / 270 | 2416.5 | SP = AF = brute force |
| P3_tt_n30_m3_L360_s1 | 30 | 360 / 270 | 6549.5 | SP = AF (same as pilot row timetable_n30_L360_s1) |
| P4_tt_n30_m3_L480_s3 | 30 | 480 / 360 | 6068.5 | SP = AF (pilot row timetable_n30_L480_s3) |
| P5_planted_n25_m3_L360_s3 | 25 | 360 / 270 | 2719.5 | SP = AF (pilot row planted_n25_L360_s3) |

These values come from the throwaway pilot-audit script. They are **targets for the group's own code to reproduce**, not results of the group's code.
P0 is the **demonstration instance** (small worked example). It is not one of the 20 final benchmark instances.

## How to load an instance
```python
from crew.instance import load_instance
from crew.checker import check_schedule
inst = load_instance("instances/proto/P0_example8.json")
print(inst.name, len(inst.trips), "trips, L =", inst.L, "W =", inst.W)
print(check_schedule(inst, inst.reference["schedule"]))   # ok=True, cost=945.0
```

## Validate the files against the schema
```bash
pip install jsonschema
python -c "import json,glob,jsonschema; S=json.load(open('instance.schema.json')); [jsonschema.validate(json.load(open(f)),S) for f in glob.glob('instances/proto/*.json')]; print('all valid')"
```
