# Instructions for AI coding assistants (and humans) working in this repository

MSBA 320 group project, Group M: bus crew scheduling (cover every trip with duties at minimum cost).
Three members: **A** = data + Model 1 (arc-flow), **B** = checker + Model 2 (set partitioning), **C** = heuristic +
runner + experiments. Source of truth: *Master Plan v1.5* (frozen) and the *Detailed Task Guide*; the professor's
instructions win over both. Read the section for the member you are helping before writing code.

## Hard rules
1. **Edit only files owned by the member you are helping** (table below). If another member's file needs a change,
   say so and stop; do not "fix" it. Shared files (README, AGENTS.md, requirements.txt) change only by agreement.
2. **Use the exact interfaces below.** The runner (`crew/runner.py`, `crew/run_child.py`) imports A's and B's
   modules by these names and signatures. Renaming a function breaks the experiments.
3. **Every fixed number lives in `crew/config.py`** (costs, tau, limits, Gurobi parameters). Never type 300, 0.5,
   10, 120, ... anywhere else. Models must NOT set Gurobi parameters; the runner sets them from config.
4. **Constraint names are shared:** `c1_pred`, `c2_succ`, `c4_Tchain`, `c5_spread`, `c6_Dchain` (arc-flow),
   `c8_cover` (set partitioning). (3) and (7) are variable bounds of T and D, not rows.
5. **`crew/checker.py` must stay independent:** it imports only `crew.config` and the data classes in
   `crew.instance`, never models, the heuristic or Gurobi.
6. **Run `pytest -q tests/` before every push; never push a failing test.** A skipped test is fine and expected
   while a teammate's module is missing (it activates by itself when the module appears).
7. Never commit `gurobi.lic`, `.venv/`, `results/tmp/` or personal file paths.

## NOT real implementations (do not copy them into crew/)
- `tests/standins.py` is a **test fixture**: a tiny duty list + set-partitioning model used ONLY so C's tests can
  run before B2/B3 exist. It switches to `crew.duties` / `crew.model_setpart` automatically once they exist.
  **Model 2 is still B's task (B2, B3); Model 1 is still A's task (A1, A2).**
- `instance._temporary_greedy` only builds generated files' reference schedules until `make_instance` is called with
  `schedule_fn=lambda inst: crew.localsearch.heuristic(inst).schedule` (C's greedy + local search, task A4 step 5).

## Who owns what
| Member | Files (create them with exactly these names) |
|---|---|
| A | `crew/instance.py` (incl. `make_instance`, task A4), `crew/graph.py` (A1), `crew/model_arcflow.py` (A2, A6), `crew/viz.py` (A7), `analysis_strength.py` (A12), `tools/build_notebook.py` (A10), `notebook_src/model1.md` (A5) |
| B | `crew/checker.py` (B0), `crew/brute.py` (B1), `crew/duties.py` (B2), `crew/model_setpart.py` (B3), `tests/test_gate1.py` (B4), `pilot/run_pilot.py` (B5), `SELECTION.md`, `instances/final/` + `MANIFEST.csv` (B9), `qa/verify_results.py` (B8), `analysis_heuristic.py` (B12), `analysis_scaling.py` (B13), `notebook_src/model2.md` (B7) |
| C | `crew/config.py`, `requirements.txt`, `crew/version.py`, `crew/sysinfo.py`, `crew/greedy.py` (C1), `crew/localsearch.py` (C14), `crew/integration.py` (C2), `crew/runner.py` + `crew/run_child.py` (C3, C4, C12), `crew/analysis.py` (C7, C9; A adds the A16 profile functions there by agreement) |

## Interfaces (Master Plan §7.3) — status as of 8 Nov
```python
Schedule = list[list[int]]   # duties of trip ids, increasing start time
# instance.py (A)      load_instance, save_instance, validate_instance, load_instance_raw_errors   DONE
#                      make_instance(name, n, m, L, W, seed, schedule_fn=None, **gen_params)      DONE (A4)
# graph.py (A)         build_arcs(inst) -> list[tuple[int, int]]                                    DONE (A1)
#                      big_m_bounds(inst) -> tuple[list[int], list[int]]   # (ell, U)              DONE (A1)
# model_arcflow.py (A) build_arcflow(inst, arcs, relax=False, naive_m=False) -> (gp.Model, {"x","u","v","T","D"})  TODO
#                      decode_arcflow(inst, vars) -> Schedule
# checker.py (B)       check_schedule, is_legal_duty, duty_cost                                     DONE
# brute.py (B)         brute_force(inst, max_n=10) -> tuple[float, Schedule]                         TODO
# duties.py (B)        enumerate_duties(inst, arcs, cap, deadline) -> (list[tuple[int,...]] | None, status, count)  TODO
#                      count_duties(inst, arcs, cap, deadline) -> (count, stopped_early, seconds)
# model_setpart.py (B) build_setpart(inst, duties, relax=False) -> (gp.Model, {"z"})   z keyed by index in duties  TODO
#                      decode_setpart(inst, duties, vars) -> Schedule
# greedy.py (C)        greedy_insertion(inst) -> Schedule                                           DONE
# localsearch.py (C)   local_search(inst, schedule, max_rounds=1000) -> Schedule                    DONE
# integration.py (C)   start_arcflow, start_setpart, start_accepted                                 DONE
# runner.py (C)        run_one(inst_path, method, cfg) -> dict ; run_all(paths, methods, cfg, csv)  DONE
```
What the runner additionally assumes (proposed in issue #1, confirm there):
- `build_arcflow` / `build_setpart` return the model **before** `optimize()`, with variables keyed as above
  (`x` by arc tuple `(i, j)`, `u v T D` by trip id, `z` by duty index); they set no Gurobi parameters.
- `enumerate_duties` returns status `"complete"`, `"capped"` (more than `cap` duties) or anything else = out of
  time; `deadline` is an absolute `time.perf_counter()` value.
- Rows of `runs.csv`: heuristic-only runs have status `HEURISTIC`; extra columns `t_solve_s`, `killed_phase`, `error`.

## Setup and daily commands
```
python -m venv .venv && .venv\Scripts\activate      # macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest -q tests/                                      # before every push
python -m crew.runner --instances instances/proto --methods H,AF,AF+S,SP,SP+S --out results/runs.csv
```
Everyone pushes to `main`; `git pull` before starting work. Line endings are LF everywhere (`.gitattributes`).
