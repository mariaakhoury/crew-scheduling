## Benchmark: where the instances come from and what makes them hard

> **Owner: B (tasks B5, B6, B9, B16).** Numbers marked *[pilot]* come from the 30 s + 30 s pilot on 43 candidate
> instances (`results/pilot.csv` + `results/pilot_small.csv`) and are preliminary. The final counts, classes and
> table below are filled in from `instances/final/MANIFEST.csv` and `instances/final/SELECTION.md` after the freeze
> on Wed 11 Nov. *[final]* marks those places.

### Source of the instances
No public data set of bus timetables with our exact rules (terminal changes, 10-minute turnaround, spread and
driving limits) is available, so every instance is **generated** by our rotation generator
(`crew.instance.make_instance`, generator `routes`). It imitates how a real bus timetable arises:

1. The *m* terminals are connected by routes (every pair of terminals); each route gets a typical one-way trip
   length of 30-70 minutes.
2. Buses leave the depot between 05:00 and 22:00, three times as often in the morning (07:00-09:00) and evening
   (16:00-19:00) peaks. A regular bus stays in service 4-10 hours, an extra rush-hour bus 1.5-3.5 hours.
3. Each bus shuttles back and forth on its route: trip, layover of at least tau = 10 minutes (plus 0-15 random
   minutes), return trip, and so on, until its block ends. Single trips vary by +/- 5 minutes.
4. All buses' trips are **pooled** and numbered by start time: drivers are not tied to buses, so a driver may
   change bus and route at a terminal. That is the scheduling freedom the models exploit.

Every generator setting and the random seed are stored in each instance file (`params`, `seed`), so any instance
can be rebuilt exactly. Each file also holds a **reference schedule** made by our heuristic (greedy + local search)
and accepted by the independent checker.

**Feasibility is guaranteed:** a trip longer than the driving limit W is redrawn, so "one driver per trip" is
always a legal schedule and every instance has a solution.

### How sizes and parameters were chosen
| Parameter | Values | Why |
|---|---|---|
| trips n | 20, 30, 40, 50, 60, 80, 100, 200, 300, 400, 500 | from instances every model solves instantly to instances no model can finish |
| terminals m | 2, 3 | fewer terminals = more connections per trip = harder |
| spread limit L | 360, 480, 600 min (6, 8, 10 h) | longer duties = more trips per duty = more possible duties |
| driving limit W | 0.75 L | a fixed ratio, so a duty is limited by both rules |
| costs, tau | F = $300, c = $0.50/min, tau = 10 min | **fixed** for every instance (data rule V6): difficulty comes from the timetable, not from the prices |
| seed | 201 | the final seeds (the pilot files are the candidate instances) |

The grid was built in two steps, both before any final run:
- **Main pilot** (`pilot/grid.json`, 24 configurations, n = 50-500). It gave only 2 easy and 1 medium instances
  *[pilot]*, too few for the targets.
- **Small supplement** (`pilot/grid_small.json`, 19 configurations, n = 20-80), added on 9 Nov with the group's
  agreement (issue #1). One configuration (n = 20, m = 3, L = 480) was left out because its reference schedule has
  a median of 2.5 trips per duty, below our density rule of 3.

Every candidate passes the **density rule** (median trips per duty in the reference schedule >= 3; range 3-7
*[pilot]*), so duties are real chains of trips and not mostly single trips.

### What makes an instance hard
| Feature | Effect | Pilot evidence *[pilot]* |
|---|---|---|
| **trips per duty** (set by L and W against the trip lengths) | the number of possible duties \|P\| grows exponentially with it: Model 2 has one variable per duty | n = 100: 63,633 duties at L = 480 with 3 terminals, more than 2,000,000 at L = 600 with 2 terminals |
| **connections per trip** (fewer terminals, denser timetable) | more arcs for Model 1, more duty combinations for Model 2 | 7.7 arcs per trip (n = 50, m = 3) up to 113.7 (n = 500, m = 2) |
| **number of trips n** | both models grow; Model 1 polynomially (\|A\| + 4n variables), Model 2 exponentially | main pilot (24 instances): Model 1 built on 23 (one build ran past the 30 s pilot limit while the laptop was swapping memory); Model 2 not built on 13 |
| cost structure | fixed here (F / c = 600 minutes: one driver is worth 10 hours of paid time) | not varied - stated as a limitation |

What this means for each model *[pilot]*: Model 2 (set partitioning) solved **29 of the 30 instances it could
build**, almost always at the first node, because its LP bound is so strong. The exception had 1.7 million duties:
each LP was so large that it hit the time limit anyway (a strong bound is not automatically fast). Otherwise it
fails only when the list of duties cannot be built (more than 2 million duties, or more than the build time). Model 1 (arc-flow) is always built but its weak
LP bound makes it slow: it already hit the 30 s limit at n = 50 with long duties.

### The classes and how the instances were selected
Each instance is classified from the plain Model 1 and Model 2 runs at the final limits (120 s + 120 s), first
rule wins: **time limit** (a built model hit the limit) > **hard** (slowest built model > 24 s) > **medium** (both
optimal, times differ x10, or only one model built) > **easy**. Instances where Model 2 could not be built carry
the flag **SP not built**; a build failure is never counted as a time limit.

The final benchmark is chosen by a **written rule, fixed before the confirmation runs** (issue #1): within each
class, instances are ordered by size and taken at evenly spaced positions from the smallest to the largest; at
least 2 SP-not-built instances are kept; if fewer than 15 are selected, the remaining places are filled by the same
rule. The exact step-by-step procedure is in `instances/final/SELECTION.md`; no instance is hand-picked, replaced or
removed after the final runs start.

**[final]** Selected: _N_ instances (target 20, minimum 15): easy _a_, medium _b_, hard _c_, time limit _d_;
SP not built _e_; n from _x_ to _y_. Fill-up used: _yes/no_ (why). Full table: `instances/final/README.md`;
fingerprints: `instances/final/MANIFEST.csv`.

This covers the professor's three required groups:
- **instances every model solves quickly**: the easy class (both models optimal in under a second *[pilot]*);
- **instances where the models differ clearly**: medium and hard (Model 2 up to 71x faster at n = 60 *[pilot]*);
- **instances Gurobi cannot solve within the time limit**: the time-limit class.

### Limitations
- One generator family: conclusions hold for rotation timetables of this kind, not for every real network.
- W = 0.75 L ties the two duty limits, so their effects cannot be separated.
- Costs are fixed, so the cost structure's effect on difficulty is not measured.
- Pilot classes come from a different laptop than the final runs; the final classes are recomputed from the final
  runs on the final-run machine.
