## Discussion: theory versus experiments

> Shared file: A writes H1-H4 (task A9), B writes H5 and H8 (B10), C writes H6 and the conclusions (C11). Numbers
> come from the final runs (`results/runs.csv`: 15 frozen instances, tag v1.0-final-run, verify_results PASS)
> unless marked *[pilot]*. Verdict rules are the ones fixed in Master Plan §10.9, written before the final runs. A
> "not confirmed" verdict with a good explanation is a valid result.

### Hypothesis register

| ID | Statement | Verdict | Evidence | Owner |
|---|---|---|---|---|
| H1 | LP-AF <= LP-SP on every instance where SP is built (Theorem 3) | **confirmed** (10/10; LP-SP = optimum on all 10) | LP-AF / LP-SP rows, `results/a12` | A |
| H2 | Naive big-M gives an LP bound at most as strong as the tight one; difference small | **confirmed** (identical on 15/15) | LP-AF-naive rows | A |
| H3 | Where both are built and solved, SP needs fewer nodes and less solver time | **confirmed** (SP faster on 6/7 = 86 %) | paired nodes / times | A |
| H4 | SP's end-to-end advantage shrinks as \|P\| grows (build share rises with \|P\|) | **not confirmed** (rho = -0.92) | SP timers, `results/b13` | A + B |
| H5 | SP becomes unbuildable for long duties and large n; AF is built on every instance | **confirmed** (SP not built on 5 of 15, AF on 15 of 15) | `results/b13` | **B** |
| H6 | The MIP start helps AF more than SP | **not confirmed** (median 2.6 % AF vs 2.6 % SP) | `results/b12` | C (B12 data) |
| H8 | Difficulty grows with trips per duty more than with n alone | **cannot be decided** (ρ 0.84 vs 0.83; n and trips per duty move together, ρ = 0.97) | `results/b13` | **B** |

H7 (reduced-cost fixing) was withdrawn in Master Plan v1.5 and its ID is not reused; H9 (L-sweep) and H10 (driver cut AF+C) were optional (P2) experiments that were not run, so they have no verdict.

### H5 - SP becomes unbuildable, AF is always built (B)

**Rule (§10.9).** Confirmed if at least 2 benchmark instances have SP not built (COLUMN_CAP, BUILD_LIMIT,
MEM_LIMIT_BUILD, KILLED_BUILD) and AF has 0 build failures. Build failures are never counted as time limits.

**Why we expected it.** \|P\| grows exponentially with the number of trips that fit in one duty: every legal duty
must be enumerated and stored before Gurobi starts, so long duties (large L, W) and dense timetables (many
connections per trip) explode the column count. Arc-flow has \|A\| + 4n variables, polynomial in n.

**Evidence (final runs, `results/b13/B13_summary.md`).** SP was **not built on 5 of the 15** benchmark instances,
all for the same reason: the duty list passed the 2,000,000-duty cap (COLUMN_CAP) while it was being enumerated
(after 3-75 s, inside the 120 s build limit). They are exactly the instances with the largest menus: every instance
with n >= 300 (n = 300 and the three n = 500), and already n = 100 when a duty may last 10 hours (L = 600). The
largest SP that could be built had 63,633 duties (n = 100, L = 8 h) and was solved in 0.6 s. **AF was built on all
15**, the largest (n = 500, 58,864 variables) in 2.2 s. Both rows show up as "not built" in the tables, never as a
time limit.

**Verdict: confirmed.** The prediction held for the reason we gave: \|P\| is exponential in the trips per duty,
\|A\| + 4n is polynomial in n. (In the pilot, one AF build ran past the 30 s pilot limit on the 7.7 GB pilot laptop -
memory swapping, not the model; on the final-run machine AF never needed more than 2.2 s.) This is also why the
benchmark has a "no model finishes" group at all: on those 5 instances the stronger model cannot even start, and the
weaker one runs out of time.

### H8 - difficulty and trips per duty (B)

**Rule (§10.9).** Judged from the feature charts and the rank correlations of difficulty (largest plain-model
solver time, unsolved or unbuilt runs counted at the time limit) with n, L and trips per duty. Stated as an
observation for this generator only.

**Limitation.** W = 0.75 L ties the two duty limits, so the effects of spread and driving time cannot be separated;
and the hardest instances are censored at the time limit, which is why a rank statistic is used.

**Evidence (final runs, `results/b13/h8_correlations.csv`).** Spearman rank correlation with difficulty over the 15
instances: **trips per duty 0.84, n 0.83, L 0.35**.

**Verdict: cannot be decided with this benchmark.** 0.84 against 0.83 is no difference, and the data cannot produce
one: in our benchmark the number of trips and the trips per duty rise together (rank correlation **0.97** between n
and trips per duty: larger rotation timetables also give longer chains per driver), so their effects are
confounded. In addition, 8 of the 15 instances are censored at the 120 s limit, which ties their difficulty at the
top. What the data does show: difficulty follows the *size of the problem* (n, or equivalently trips per duty)
much more than the duty length L alone (0.35). Separating n from trips per duty would need instances with the same
n and different trips per duty (for example, the same timetable with only L changed: the optional L-sweep, task A14,
which we did not run).

### H1 - LP dominance, Theorem 3 (A)

**Rule (§10.9).** LP-AF <= LP-SP within 10^-6 on every final instance where SP is built; a violation is a bug (Q22).

**Final verdict: confirmed.** On all 10 instances where SP was built, LP-AF <= LP-SP (Q22 green, `crew.analysis_strength`).
The gap between the two is large: **LP-SP equals the proven optimum on all 10** (0 % LP gap), while LP-AF is
1.9-15.8 % below it (median 8.9 %). So SP's LP already "knows" the answer, which is why SP solves every one of
them at the root node (H3).

### H2 - naive versus tight big-M (A, task A8)

**Rule (§10.9).** The naive constants (one M per family: M_T = latest start - smallest l, M_D = W) must give an LP
bound no stronger than the tight per-arc constants (Q21); the size of the difference is reported as measured.

**Final verdict: confirmed, with a difference of zero.** LP-AF-naive and LP-AF are identical on all 15 instances
(largest difference 2 x 10^-11, rounding). The direction holds; the size we expected ("small") is in fact nothing.
**Why:** the big-M constants only appear in the chain rows (4) and (6), and Model 1's LP barely uses those rows:
on P0-P5, deleting rows (4)-(7) altogether moves the LP bound by at most 1.3 points, and not at all on P3 and P4
(slide 5, `slides/make_figures_A.py`). The LP solution spreads x fractionally so that the chain rows are slack
whatever M is. Tight constants are still the right choice (they cost nothing), but they are not where Model 1's
weakness comes from: the weakness is the formulation, not the constants.

### H3 - SP needs fewer nodes and less solver time (A)

**Rule (§10.9).** On the instances both plain models solve to proven optimality: confirmed if SP is faster on at
least 75 % of them, not confirmed below 50 %.

**Final verdict: confirmed.** Both models proved the optimum on 7 instances (n = 20-60). SP was faster on 6 of 7
(86 %) and never needed more nodes: always 1, against 1 to 77,832 for AF (strictly fewer on 5, tied at 1 node on
the two smallest). The one "loss" is n = 20: 0.006 s against 0.005 s, a tie in practice. The gap widens fast:
at n = 60, L = 480, AF needed 38.8 s and 77,832 nodes, SP 0.13 s at the root. Beyond these 7, SP also proved the
optimum on 3 instances where AF stopped at the time limit (n = 50-100), and on those 3 AF's schedule already was
the optimum: AF lacks the proof, not the schedule.

### H4 - build share of SP (A + B)

**Rule.** Build share = (enumeration + build) / end-to-end time of SP, against \|P\|; we read Spearman rho > 0.3 as
confirmed, 0 < rho <= 0.3 as partly confirmed (our reading rule, stated here before the final runs).

**Final verdict: not confirmed.** Over the 10 SP runs that were built, the build share *falls* as \|P\| grows,
from 72 % (371 duties) to 32 % (63,633 duties): rho = -0.92. At this size, building is cheap (at most 0.3 s) and
the root LP, which has one column per duty, grows faster than the build. This repeats the pilot (rho = -0.54) and
is the "a stronger bound is not automatically faster" argument of Master Plan §4.6.

**But the advantage does disappear, abruptly.** The 5 instances with more than 2,000,000 duties (n >= 300, and
n = 100 with L = 600) were never built: there SP's advantage drops from "best method" to "no answer" in one step,
at the cap, instead of shrinking gradually. So H4's mechanism (enumeration cost grows with \|P\|) is real, but on
this benchmark it shows up as a cliff, not as a slope.

### Heuristic contribution - data for H6 (B12; C writes the verdict)

**Final runs (`results/b12/B12_summary.md`).** Every start was accepted (AF 15/15, SP 10/10). With the start, AF's
first incumbent came at a median 0.16 of the time without it (SP's at once: it starts from the start). Paired
outcome: AF 2 wins, 10 ties, 3 losses; SP 0 wins, 10 ties, 0 losses (tie = within 10 % or 1 s). Local search
improved greedy on 2 of 15. The verdict and its explanation are in H6 below.

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
10/10) and AF's first incumbent came at a median 0.16 of the time without the start, but by B12's tie rule
AF+S vs AF gives 2 wins, 10 ties and 3 losses, and SP+S vs SP 10 ties:
- **Where it helped (2):** one clear gain on a large instance, `rt_n500_m3_L360` (time limit either way): 3.9 %
  cheaper, $45,143.50 → $43,400.50 - there AF is still searching for good schedules at the time limit, so a
  ready-made one is worth something; and one mid-size proof, `rt_n50_m3_L600`, 29 % faster (3.7 → 2.6 s).
- **Ties (10):** the other three n = 300-500 instances ended 0.2-0.9 % cheaper, below the tie threshold; the other
  time-limit instances ended with the same schedule (on the 3 where SP knows the optimum, AF had already found it:
  the open gap is the bound, which a start cannot move). SP is solved at the root node with or without the start;
  its differences are hundredths of a second.
- **Where it hurt (3):** two AF instances that are proved in seconds took longer with the start (`rt_n60_m2_L480`
  38.8 → 71.5 s, `rt_n60_m3_L360` 7.3 → 9.7 s), and `rt_n50_m2_L600` ended with the same schedule but a weaker bound
  (gap 4.7 → 6.0 %). A different first incumbent sends branch-and-bound down a different tree; with one seed this
  is performance variability, not a bad start.

So the expectation was right about *why* SP needs no help, but wrong about AF: on most instances AF either proves
the optimum quickly by itself or is stuck on its bound, and it is short of good schedules only on the largest ones, where the start gave its one clear gain.

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
   always legal, a median 2.4 % above the optimum; as a complete start it was a clear gain for Model 1 only twice
   (3.9 % cheaper at n = 500, a 29 % faster proof at n = 50), mostly a tie, and never changed Model 2 (H6 not
   confirmed).
5. **Practical rule for this problem family:** count the duties first; if the menu fits, solve Model 2; otherwise
   solve Model 1 with the heuristic start and report its proven gap, knowing the gap mostly measures the bound.

**What the group learned.** A stronger formulation is worth more than a faster solver, until it no longer fits in
memory; a "gap" is a statement about the bound as much as about the schedule; two of our predictions (H4, H6) were
wrong, and finding out why taught us more than the ones that held; and every result we report is checked by code
that shares nothing with the models (the independent checker).

### Negative and surprising results (all members)

| Result | Explanation |
|---|---|
| Naive and tight big-M give exactly the same LP bound (H2) | Model 1's LP leaves the chain rows (4), (6) slack, so the size of M never matters; its weakness is the formulation |
| SP's build share falls as \|P\| grows (H4) | building is cheap up to 63,633 duties; the root LP grows faster. The advantage ends at the 2,000,000 cap, as a cliff |
| H8 cannot be decided (n 0.83 vs trips per duty 0.84) | n and trips per duty are almost perfectly correlated in our benchmark (ρ = 0.97), so their effects cannot be separated; 8 of 15 instances censored at 120 s |
| AF stopped at the time limit with gaps of 4.7-14.4 % on 3 instances where its schedule already was the optimum (SP proves it) | the gap measures AF's weak lower bound, not its schedule: AF lacks the proof, not the answer (C) |
| The MIP start made two quick AF proofs slower (n = 60: 38.8 → 71.5 s, 7.3 → 9.7 s) | a different first incumbent sends branch-and-bound down a different tree; with one seed this is performance variability (H6, C) |
| SP not built already at n = 100 when duties may last 10 h | 10-hour duties fit many more trips, and \|P\| is exponential in the trips per duty (H5) |
| [pilot] SP time limit at n = 200 with 1.7 M duties; solved at the final 120 s limit in 64 s | each node LP has 1.7 M columns: a strong bound but a slow LP (§4.6) |
| [pilot] one AF build took 38.8 s | memory swapping on the 7.7 GB pilot laptop; on the final-run machine every AF build took at most 2.2 s |

### What we would try next
- Column generation for SP: price duties with a resource-constrained shortest path (spread, driving) on the
  acyclic trip graph instead of enumerating \|P\|.
- An exact arc reduction for Model 1: delete every arc i -> j whose two trips alone break a limit
  (e_j - s_i > L or d_i + d_j > W). That is 56,669 of 153,818 arcs (36.8 %) on our benchmark (B's count): Model 1
  becomes about a third smaller with the same integer optimum. Found after the code freeze, so not in the runs.
- Several seeds per configuration, to separate the effect of the MIP start from performance variability (H6: 3 of
  15 AF pairs got worse with the start, which one seed cannot explain away) (C).
- Separate the effect of n from trips per duty (H8): the L-sweep (one timetable, only L changed).
