## Discussion: theory versus experiments

> **DRAFT (B, 9 Nov).** Shared file: A writes H1-H4 (task A9), B writes H5 and H8 (B10), C writes H6 and the
> conclusions (C11). Every number below marked *[pilot]* comes from the 30 s + 30 s pilot (`results/pilot.csv`,
> 24 candidates) and is **preliminary**; it is replaced by the final-run numbers after Gate 3 (Fri 13). Verdict rules
> are the ones fixed in Master Plan §10.9, written before the final runs. A "not confirmed" verdict with a good
> explanation is a valid result.

### Hypothesis register

| ID | Statement | Verdict | Evidence | Owner |
|---|---|---|---|---|
| H1 | LP-AF <= LP-SP on every instance where SP is built (Theorem 3) | _after Gate 3_ | LP-AF / LP-SP rows | A |
| H2 | Naive big-M gives an LP bound at most as strong as the tight one; difference small | _after Gate 3_ | LP-AF-naive rows | A |
| H3 | Where both are built and solved, SP needs fewer nodes and less solver time | _after Gate 3_ | paired nodes / times | A |
| H4 | SP's end-to-end advantage shrinks as \|P\| grows (build share rises with \|P\|) | _after Gate 3_ | `results/b13` | A + B |
| H5 | SP becomes unbuildable for long duties and large n; AF is built on every instance | _after Gate 3_ | `results/b13` | **B** |
| H6 | The MIP start helps AF more than SP | **not confirmed** (median 2.6 % AF vs 2.6 % SP) | `results/b12` | C (B12 data) |
| H8 | Difficulty grows with trips per duty more than with n alone | _after Gate 3_ | `results/b13` | **B** |

### H5 - SP becomes unbuildable, AF is always built (B)

**Rule (§10.9).** Confirmed if at least 2 benchmark instances have SP not built (COLUMN_CAP, BUILD_LIMIT,
MEM_LIMIT_BUILD, KILLED_BUILD) and AF has 0 build failures. Build failures are never counted as time limits.

**Why we expected it.** \|P\| grows exponentially with the number of trips that fit in one duty: every legal duty
must be enumerated and stored before Gurobi starts, so long duties (large L, W) and dense timetables (many
connections per trip) explode the column count. Arc-flow has \|A\| + 4n variables, polynomial in n.

**Pilot [pilot].** SP was not built on 13 of 24 candidates: 7 exceeded the 2,000,000-duty cap, 6 could not be
enumerated within the 30 s build limit (n = 400-500). AF was built on 23 of 24; the one failure
(rt_n400_m2_L480) took 38.8 s to build where same-size instances took about 2 s, which points to memory swapping on
the 7.7 GB pilot laptop rather than to the model. At the final 120 s build limit on the final-run machine we expect
0 AF build failures.

**Final verdict:** _fill from `results/b13/B13_summary.md` (H5 line) after Gate 3._

### H8 - difficulty and trips per duty (B)

**Rule (§10.9).** Judged from the feature charts and the rank correlations of difficulty (largest plain-model
solver time, unsolved or unbuilt runs counted at the time limit) with n, L and trips per duty. Stated as an
observation for this generator only.

**Limitation.** W = 0.75 L ties the two duty limits, so the effects of spread and driving time cannot be separated;
and the hardest instances are censored at the time limit, which is why a rank statistic is used.

**Pilot [pilot].** Spearman correlation with difficulty: n 0.55, trips per duty 0.54, L 0.11. At the pilot limit
almost every instance with n >= 100 is censored at 30 s, so the ranks cannot separate n from trips per duty yet.

**Final verdict:** _fill from `results/b13/h8_correlations.csv` after Gate 3; say which feature ranks higher and
whether the difference is large enough to call._

### H4 - build share of SP (A + B)

**Rule.** Build share = (enumeration + build) / end-to-end time of SP, against \|P\|; we read Spearman rho > 0.3 as
confirmed, 0 < rho <= 0.3 as partly confirmed (our reading rule, stated here before the final runs).

**Pilot [pilot].** rho = -0.54 over 11 built SP runs: **not confirmed** at the pilot limit. The likely reason: the
largest SP model that was built (1.7 million duties) hit the 30 s *solve* limit, so solve time, not build time,
dominated its end-to-end time - each node LP has 1.7 million columns. This is the "a stronger bound is not
automatically faster" argument of Master Plan §4.6. Re-check on the final runs before writing the verdict.

### Heuristic contribution - data for H6 (B12; C writes the verdict)

**Pilot [pilot].** Every start was accepted (AF 22/22, SP 11/11). With the start, the first incumbent appeared much
earlier (median time ratio 0.12 for AF, 0.27 for SP), but the final result changed little: on AF the time-limit gap
improved by a median of 7 %, on SP the solver time by 9 %. Where SP solved at the root node the start had nothing
to add. The bound, not the incumbent, keeps AF's gap open, so a better start cannot close it. Local search improved
greedy on 9 of 24 candidates.

### H6 - the MIP start helps AF more than SP (C)

**Rule (§10.9).** Confirmed if the median AF improvement (AF+S vs AF) is larger than the median SP improvement
(SP+S vs SP), measured on time to first incumbent, solver time, and final gap on time-limit instances.

**Why we expected it.** A start helps a MIP by giving it a good incumbent early. Model 2's LP bound is (almost)
the optimum, so Gurobi usually finds and proves the optimum at the root node: a start has little left to do.
Model 1's LP is weak, so Gurobi searches a long time for good solutions, and a ready-made one is worth more.

**Heuristic quality (final runs).** Greedy + local search on the 15 benchmark instances: at most 0.43 s each up
to n = 500, every schedule passes the checker; median 2.4 % above the optimum on the 10 instances where SP proves
it (0 % on 2, max 11.3 % at n = 50 with L = 600); local search improved greedy on 2 of 15. Where SP cannot be built,
the heuristic is within 0.8-7.8 % of plain AF's 120 s incumbent and 1.5 % cheaper than it on `rt_n500_m3_L360`.

**Verdict: not confirmed.** B12 (`crew.analysis_heuristic`, rule §10.9): median improvement AF+S vs AF 2.6 % (15
pairs), SP+S vs SP 2.6 % (10 comparable pairs; 5 not built either way). Gurobi accepted every start (AF 15/15, SP
10/10) and AF's first incumbent came at a median 0.16 of the time without the start, but the final result moved
only in one place:
- **Where it helped:** AF on the 4 largest instances (n = 300-500, time limit either way): the final schedule was
  0.2-3.9 % cheaper with the start (`rt_n500_m3_L360`: $45,143.50 → $43,400.50). There AF is still searching for
  good schedules at the time limit, so a ready-made one is worth something.
- **Where it did not:** the other 4 AF time-limit instances ended with the same schedule (on the 3 where SP knows
  the optimum, AF had already found it: the open gap is the bound, which a start cannot move). SP is solved at the
  root node with or without the start; its differences are hundredths of a second.
- **Where it hurt:** two AF instances that are proved in seconds took longer with the start (`rt_n60_m2_L480`
  38.8 → 71.5 s, `rt_n60_m3_L360` 7.3 → 9.7 s). A different first incumbent sends branch-and-bound down a
  different tree; with one seed this is performance variability, not a bad start.

So the expectation was right about *why* SP needs no help, but wrong about AF: on most instances AF either proves
the optimum quickly by itself or is stuck on its bound, and only on the largest ones is it short of good schedules.

### Conclusions (C11)

> From the final runs (`results/runs.csv`, 15 instances, verify PASS).

1. **Model 2 wins whenever it can be built.** It proved the optimum on all 10 instances it could build, each in
   under a second at the root node, because its LP bound equals the optimum on every one of them.
2. **Model 1 is the fallback that always runs.** It was built on all 15, but proved optimality only on 7 (n ≤ 60);
   from n = 50 on it can stop at the time limit, with proven gaps of 4.7-27.2 % growing with n. Its gap is a weak
   bound, not a bad schedule: on all 3 time-limit instances where SP knows the optimum, AF's schedule *was* the
   optimum.
3. **The menu explodes.** Model 2 could not be built on 5 of 15 instances (more than 2,000,000 duties): every
   instance with n ≥ 300, and already n = 100 when duties may last 10 hours.
4. **The heuristic is cheap and useful as a start for big instances, not as an answer.** Under half a second,
   always legal, a median 2.4 % above the optimum; as a complete start it improved Model 1 only on the largest
   instances (up to 3.9 %) and never changed Model 2 (H6 not confirmed).
5. **Practical rule for this problem family:** count the duties first; if the menu fits, solve Model 2; otherwise
   solve Model 1 with the heuristic start and report its proven gap, knowing the gap mostly measures the bound.

**What the group learned.** A stronger formulation is worth more than a faster solver, until it no longer fits in
memory; a "gap" is a statement about the bound as much as about the schedule; two of our predictions (H4, H6) were
wrong, and finding out why taught us more than the ones that held; and every result we report is checked by code
that shares nothing with the models (the independent checker).

### Negative and surprising results (all members)

| Result | Explanation |
|---|---|
| _e.g. SP time limit at n = 200 with 1.7 M duties [pilot]_ | _each node LP has 1.7 M columns: a strong bound but a slow LP (§4.6)_ |
| _e.g. AF build 38.8 s on one instance [pilot]_ | _memory swapping on the 7.7 GB pilot laptop; not seen on same-size instances_ |
| | |

### What we would try next
- Column generation for SP: price duties with a resource-constrained shortest path (spread, driving) on the
  acyclic trip graph instead of enumerating \|P\|.
- _add from the final results_
