# Data dictionary - Group M crew scheduling (schema 1.0)

Owner: Member A (instance fields) and Member B (validation rules C1-C7). Approved at the kickoff (Thu 5 Nov) by all three members; the rules below are unchanged since v1.1.
Machine-readable version: `instance.schema.json` (JSON Schema 2020-12).

## Units (the same in every file, formula, test and slide)
| Quantity | Unit | Type |
|---|---|---|
| time (start, end, L, W, tau, waits) | minutes after 00:00 of the service day; may exceed 1440 for after-midnight trips | integer |
| money (F, costs, objective, bounds) | US dollars | float, always a multiple of $0.50 |
| wage | dollars per paid minute (`c_per_min = 0.5`); "per hour" is never used in data or code | float |

## Instance file `instances/<set>/<name>.json`
| Field | Required | Type | Meaning / rule |
|---|---|---|---|
| `schema_version` | yes | string | must be `"1.0"` |
| `name` | yes | string `[A-Za-z0-9_]+` | must equal the file name without `.json` |
| `generator` | yes | `"hand"`, `"timetable"`, `"planted"`, `"routes"` | how the instance was made |
| `seed` | yes | integer or null | random seed (null for hand-made) |
| `params` | yes | object | every generator argument needed to rebuild the file (e.g. `n`, `m`, window, headways) |
| `units` | yes | object with `time`, `money` | documentation only |
| `L` | yes | integer > 0 | max spread of a duty, minutes |
| `W` | yes | integer > 0, W <= L | max driving time of a duty, minutes |
| `tau` | yes | integer >= 0 | turnaround, minutes; must equal `config.TAU` |
| `F` | yes | number | $ per duty; must equal `config.F` |
| `c_per_min` | yes | number | $ per paid minute; must equal `config.C_PER_MIN` |
| `terminals` | yes | list of strings | terminal names; trips refer to them by index |
| `trips` | yes | list of trip objects | see below |
| `reference` | no (yes for benchmark files) | object or null | a checked schedule, see below |

### Trip object
| Field | Required | Type | Rule |
|---|---|---|---|
| `id` | yes | integer | 0..n-1, and equal to the trip's position in the list |
| `label` | no | string | display only (e.g. "T1"); never used by any algorithm |
| `start` | yes | integer >= 0 | minutes |
| `end` | yes | integer > start | minutes |
| `origin` | yes | integer | index into `terminals` |
| `dest` | yes | integer | index into `terminals`, different from `origin` |

Trips do **not** have to be sorted by start time (planted instances are not). Every algorithm that needs time order sorts by `(start, id)` itself.

### Reference object
| Field | Type | Rule |
|---|---|---|
| `schedule` | list of duties; a duty is a list of trip ids in increasing start time | must pass the checker |
| `cost` | number | must equal the checker's recomputed cost within $0.01 |
| `kind` | `"optimal"`, `"heuristic"`, `"planted"` | `"optimal"` only if proved by a full model (status OPTIMAL with the exact gap settings), i.e. proven optimal within Gurobi's numerical tolerances and confirmed by the checker (issue #1, clarification 4) |
| `verified_by` | string | what produced and checked it, e.g. `"greedy+LS; checker"` |

## Instance validation rules (`instance.validate_instance` / `load_instance_raw_errors`, Member A)
Every error message starts with its code and a colon, e.g. `"V5: trip 6 lasts 301 min > W = 300"`. JSON Schema covers V1 only.
Test data: `tests/invalid_instances/` (21 files, one broken rule each, listed in `EXPECTED.csv`).
- V1: `schema_version == "1.0"`, and no unknown fields (JSON Schema `additionalProperties: false`).
- V2: trip ids are exactly 0..n-1 in list order.
- V3: `start` and `end` are Python `int` after `json.load` (a float such as `360.0` is invalid, although JSON Schema accepts it), and 0 <= start < end.
- V4: `origin` and `dest` are valid terminal indices, origin != dest.
- V5: every trip has `end - start <= W`, and `W <= L`. (This guarantees feasibility: one driver per trip is always legal.)
- V6: `tau`, `F`, `c_per_min` equal the values in `config.py`.
- V7: `name` equals the file name.
- V8: labels, if present, are unique.
- V9: if `reference` is present, it passes `check_schedule` and its `cost` matches.
- V10: `params` contains `n` equal to the number of trips (generated instances only).

## Schedule validation rules (`checker.check_schedule`, Member B)
- C1: every id in the schedule is an existing trip id.
- C2: every trip appears exactly once (no missing trip, no duplicate).
- C3: no empty duty; each duty is listed in strictly increasing start time.
- C4: consecutive trips a, b in a duty: `dest(a) == origin(b)` and `end(a) + tau <= start(b)`.
- C5: spread `end(last) - start(first) <= L`.
- C6: driving `sum(end - start) <= W`.
- C7: cost = sum over duties of `F + c_per_min * spread`; if a claimed cost is given, |claimed - recomputed| <= $0.01.

## Results file `results/runs.csv`
See Master Plan v1.5, §10.6–§10.7 for the column list (one row per run), plus `git_commit` in the resume key and `obj_bound_raw`, `int_vio`, `constr_vio`, `bound_vio` (issue #1, clarifications 1 and 4).
