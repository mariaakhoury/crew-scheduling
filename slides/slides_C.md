# Slides 10-12 and 14 - Member C (Maria) - 5:00 in total

> Final numbers, 10 Nov: every number is recomputed from the final runs (`results/runs.csv`, 15 frozen instances,
> tag `v1.0-final-run`, 120 s + 120 s, one machine; `qa.verify_results` PASS) by `crew.analysis` (C9, tables in
> `results/report/`), B12 (`crew.analysis_heuristic`), B13 (`crew.analysis_scaling`), A12 (`crew.analysis_strength`).
> Order and times from Master Plan §12; titles state the **finding**. Script length: about 130 words per minute.
> Slide 9 (B) ends with the benchmark; slide 13 (B) sits between slides 12 and 14.

---

## Slide 10 - "Greedy strands trip 7; swap-then-merge saves a whole driver ($232.50)" (1:00)

**Key message:** the greedy choice that looks cheapest (shortest wait) can cost a whole extra driver; local search
repairs it with a move that is only good as a pair.

**Show:** the three Gantt charts of P0 from A11 (`case_study`): greedy $1,177.50 with trip 7 alone in red, after local
search $945.00, optimal $945.00. Under them the cost table: drivers −$300, paid minutes +$67.50, total −$232.50.
**Trip numbers:** trip ids 0-7, as on slide 6 (duties {0,1,4,5} and {2,3,6,7}); the Gantt bars show the same ids.

**Script (128 words):**
"Before any solver runs, we build a schedule by hand-style rules. Greedy takes the trips in time order and gives
each one to the driver who waits least. On our 8-trip example that looks clever until trip 6: greedy gives it to
driver 1, who is then at the 5-hour driving limit. Trip 7 now has nowhere to go, and greedy hires a third driver
for one single trip: $1,177.50. Local search fixes it with a pair of moves: first move trip 6 to driver 2 - alone
that costs *more* - then attach trip 7 to driver 2. One driver fewer: $945, the optimum. The lesson: a driver costs
$300, as much as 10 hours of paid waiting, so it is worth waiting a lot to save one."

**Likely questions:** *Why accept a move that makes things worse?* - only together with the merge that follows;
the pair is evaluated as one move and must save at least $0.50. *Does local search always reach the optimum?* - no:
on the benchmark it stays a median of 2.4 % above the optimum (10 instances where SP proves it; max 11.3 %); it stops
at the first schedule no single move can improve (a local optimum).

---

## Slide 11 - "The heuristic gives both models a complete start; it rarely changes the result" (1:10)

**Key message:** the heuristic is fast and always feasible, so it can be handed to Gurobi as a complete MIP start;
Gurobi accepted every start, but for Model 1 it was a clear gain only twice (2 wins, 10 ties, 3 losses by B12's
tie rule), it never mattered for Model 2, and it cannot fix Model 1's weak bound.

**Show:** left, a flow picture: timetable → greedy → local search → complete start (x, u, v, T, D for Model 1;
z for Model 2) → Gurobi log line "User MIP start produced solution". Right, the B12 paired chart
(`slides/figures/C_slide11_start_effect.png`: AF vs AF+S and SP vs SP+S).

**Numbers (final runs):**
- heuristic time: at most 0.43 s on every instance up to n = 500; all 15 schedules pass the checker
- heuristic cost: median 2.4 % above the optimum on the 10 instances where SP proves it (0 % on 2, max 11.3 % at
  n = 50 with L = 10 h); local search improved greedy on 2 of 15
- where SP cannot be built (5 instances), the 0.5 s heuristic is within 0.8-7.8 % of plain AF's 2-minute answer,
  and on the 500-trip instance with 3 terminals and 6 h duties it is **1.5 % cheaper** than it
- starts accepted: AF 15/15, SP 10/10; AF's first incumbent arrives at a median 0.16 of the time it takes without
  the start
- AF+S vs AF (B12 tie rule): **2 wins** - one clear gain on a large instance (n = 500, 3 terminals, 6 h: 3.9 %
  cheaper, $45,143.50 → $43,400.50) and one on a mid-size proof (n = 50, 3 terminals: 29 % faster, 3.7 → 2.6 s);
  **10 ties**, including the other three n = 300-500 instances (0.2-0.9 % cheaper: below the tie threshold);
  **3 losses** - two slower proofs (n = 60: 38.8 → 71.5 s and 7.3 → 9.7 s) and one worse proven gap with the same
  schedule (n = 50, 10 h: 4.7 → 6.0 %, a weaker bound at the time limit)
- SP+S vs SP: 10 ties - solved at the root node with or without the start

**Script (156 words):**
"Why build a heuristic if we have two exact models? Because it is almost free - under half a second even with 500
trips - and it is always a legal schedule. That lets us give Gurobi a *complete* start: for Model 1 we translate
the duties into every variable - arcs, start and end markers, spread and driving times; for Model 2 we switch on
exactly the duty columns we used. Gurobi accepted the start every time. Did it help? Rarely. Model 1 gained
clearly twice: a 500-trip instance ended 4 percent cheaper, and one 50-trip proof was 29 percent faster. Most runs
were ties, and three were worse - two proofs took longer because the start sent the search down a different path.
On one 500-trip instance the half-second heuristic alone beat two minutes of plain Model 1. But a start only improves
the *upper* side. Model 1's gap stays open because its *lower* bound is weak, and Model 2 is solved at
the root node anyway - there is nothing left for a start to do."

**Likely questions:** *How do you know Gurobi used the start?* - we read the log line and compare its objective with
the heuristic cost (`start_accepted`, 25 of 25). *Why was AF+S worse on three instances?* - a different first
incumbent sends branch-and-bound down a different tree; on instances that are proved in seconds that variation is
larger than the benefit of the start (performance variability, one seed); on the third, the schedule was the same
but the bound at the time limit was weaker for the same reason. *Why a complete start, not a partial
one?* - a partial start makes Gurobi solve a sub-MIP to complete it, which can fail; a complete one is checked in
one step.

---

## Slide 12 - "Model 2 wins whenever it can be built; Model 1 is the only option beyond that" (1:20)

**Key message:** where SP is built it proves the optimum in under a second; AF reaches the time limit from n = 50
on; where SP cannot be built, AF still returns a feasible schedule with a proven gap - and AF's gap is the bound,
not the schedule.

**Show:** the comparison table (C9, `results/report/tables.md`, methods in rows) and the performance profile (A16,
`slides/figures/C_slide12_profile.png`).
Highlight three numbers: SP optimal 10 / 15, AF optimal 7 / 15, SP not built 5 / 15 (the profile curves end at
67 % and 47 %: the share of all 15 instances each model solved).

**Numbers (final runs):**
- SP: optimal on all 10 instances it could build, every one in under 1 s end-to-end (max 0.9 s, n = 100,
  63,633 duties), at the root node (1 node), because its LP bound **equals** the optimum on all 10
- SP not built on 5 (more than 2,000,000 duties): every instance with n ≥ 300, and n = 100 when duties may last 10 h
- AF: optimal on 7 of 15 (n ≤ 60); time limit on 8, from n = 50 with L = 10 h on, with proven gaps of 4.7-27.2 %
  growing with n
- on the 3 instances where AF stopped at the time limit and SP knows the optimum, **AF's schedule already was the
  optimum** - the whole 4.7-14.4 % gap is AF's weak lower bound
- example: n = 100 (3 terminals, 8 h): SP optimal in 0.9 s; AF stopped after 2 minutes with a 14.4 % gap on a
  schedule that was in fact optimal

**Script (170 words):**
"So which model wins? On our benchmark, the answer depends on one question: can Model 2 be built? When it can,
it wins clearly. It proved the optimum on every instance it could build, each in under a second, because its LP
bound already *is* the optimum - Gurobi does not need to branch at all. Model 1 proved optimality only up to 60
trips; from 50 trips on it can hit the 2-minute limit, with gaps from 5 to 27 percent that grow with size. But look
closer: where we know the true optimum, Model 1 had already *found* it - it just could not *prove* it. The gap is the
weak bound, not a bad schedule. And Model 2 has a cliff: with long duties or many trips the menu passes two million
duties and we cannot even build it. There Model 1 is the only exact model that still runs. So the practical rule:
try Model 2 first; if the menu explodes, use Model 1 with the heuristic start and report its gap honestly."

**Likely questions:** *Is the comparison fair?* - same machine, same 120 s + 120 s limits, 4 threads, same
parameters, recorded in env.txt and in every row. *Why is the gap of AF large even when its schedule is good?* -
the gap is (incumbent − bound) / incumbent; AF's LP is 1.9-15.8 % below the optimum (A12), so the gap overstates
how far the schedule is from optimal. *What about the equal-budget column?* - end-to-end time counts SP's
enumeration and build too: SP's worst end-to-end is still 0.9 s where it is built; where it is not, it spends
3-76 s discovering that the menu is too big.

---

## Slide 14 - "Theory held for the bounds and the cliff; the start and the build share surprised us. Next: column generation" (1:30)

**Show:** left, the hypothesis table below. Right, the Gantt chart of the largest final instance with a verified
schedule (A7 `viz`, `slides/figures/C_slide14_gantt.png`): `rt_n500_m2_L480_s201`, AF+S, 77 duties,
$35,342.00, 500 trips, time limit with a proven gap of 23.1 %, re-checked by the checker before drawing.
Bottom line: limitations and "what next" in one sentence each.

**Verdict table (final runs, rules of Master Plan §10.9):**

| ID | Statement | Verdict | Evidence |
|---|---|---|---|
| H1 | Model 1's LP ≤ Model 2's LP (Theorem 3) | **confirmed** | held on all 10 built instances; LP-SP = optimum on all 10, LP-AF 1.9-15.8 % lower |
| H2 | Naive big-M is weaker, but only a little | **confirmed** (no difference at all) | LP-AF-naive = LP-AF on all 15 instances |
| H3 | SP needs fewer nodes and less solver time | **confirmed** | 7 instances both proved: SP 1 node each (AF up to 77,832); faster on 6, n = 20 tie (solver time 0.005 vs 0.006 s) |
| H4 | SP's build share grows with \|P\| | **not confirmed** | Spearman ρ = −0.92 over 10 built SP runs: build share falls from 72 % to 32 % (median 48 %) |
| H5 | SP becomes unbuildable; AF always built | **confirmed** | SP not built on 5 of 15, AF build failures 0 |
| H6 | The MIP start helps AF more than SP | **not confirmed** | median improvement 2.6 % AF vs 2.6 % SP; AF: 2 wins, 10 ties, 3 losses |
| H8 | Difficulty grows with trips per duty more than with n | **too close to call** | rank correlation with difficulty: trips per duty 0.84, n 0.83 |

**Script (186 words):**
"Here is what the theory predicted and what we measured. First, the bounds: Theorem 3 says Model 2's LP is at least
as strong as Model 1's - it held on every instance, and Model 2's LP was exactly the optimum every time. The naive
big-M version gave the very same LP bound as our tight one. Second, size: Model 2 failed to build on 5 of 15
instances, Model 1 never. Third, speed: where both proved the optimum, Model 2 needed one node and was faster on 6
of 7. Two predictions failed. The heuristic start did not help Model 1 more than Model 2: it was a clear gain
only twice, and mostly a tie. On the right is the largest one: 500 trips covered by one legal schedule, checked
trip by trip. Limits of our study: one generator family, one machine, one seed per configuration, and the driving
limit tied to the spread. What next? Instead of writing Model 2's whole menu, generate only the duties that can
improve the solution - column generation. Its pricing problem is a shortest path with two resources on our trip
network: Model 2's strength without its explosion."

**Likely questions:** *Why is H4 not confirmed?* - the build share *falls* as \|P\| grows (72 % → 32 %, median 48 %),
because the root LP grows faster than the build: from 371 to 63,633 duties the solve time grows about 100 times
(0.006 → 0.61 s), the enumeration + build only about 9 times (0.03 → 0.29 s). The build cost shows its weight only
as the cliff (H5), not as a rising share (B13). *Would the conclusions change with another seed?* - possibly in the
numbers, not in the direction; we used one seed per configuration (§10.10 limitation). *Do the results hold for
real timetables?* - only for this generator's family; we say so. *Why column generation and not a bigger computer?* -
\|P\| grows exponentially with trips per duty; more memory buys only a little more n.

---

### Before Gate 3 - what is left
1. A and B check the H1-H5 and H8 wording against their own write-ups (`notebook_src/discussion.md`).
2. Figures: `py slides/make_figures_C.py` (done; slide 12 profile redrawn 11 Nov after A's fix 1e7c726: SP ends at 67 % = 10/15, AF at 47 % = 7/15).
3. Merge: A's slides 1-5 + B's `slides_B.pptx` (6-9, 13) + these four into `slides_groupM.pptx` / `.pdf`.
