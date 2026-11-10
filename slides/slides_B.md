# Slides 6-9 and 13 - Member B (Amani) - 5:00 in total

> Draft, 10 Nov. Order and times from Master Plan §12; titles state the **finding**, not the topic.
> *[pilot]* = preliminary number (30 s pilot): replace on Sun 15 with the final runs (`results/b13/`,
> `instances/final/SELECTION.md`). Script length: about 130 words per minute.
> Slide 5 (A) ends with Model 1's weakness; slide 10 (C) starts with the heuristic. Handover lines are marked.

---

## Slide 6 - "Model 2 writes a schedule as a menu of whole working days" (0:50)

**Key message:** list every legal driver's day once; then the solver only has to pick days so that every trip is
covered exactly once.

**Show:** left, the 8-trip example P0 as a timetable; right, the "menu": a matrix with trips as rows and a few of
the 40 legal duties as columns (1 = the duty covers the trip). Highlight the 2 chosen columns {0,1,4,5} and
{2,3,6,7} = $945. Under it, the whole model in one line:
min Σ c_p z_p subject to Σ_{p ∋ i} z_p = 1 for every trip i, z_p ∈ {0, 1}.

**Script (106 words):**
"Model 1 builds each driver's day step by step. Model 2 does the opposite: first we write down *every* legal
working day - every chain of trips that respects the work rules. For our 8-trip example there are exactly 40. Each day becomes one yes/no variable with its cost:
300 dollars for the driver plus 50 cents per minute. The only constraint says: every trip is in exactly one chosen
day - constraint (8). All the work rules are inside the menu, so there are no big-M constraints and no time
variables. Here Gurobi picks these two days: 945 dollars, the same optimum as Model 1."

**Likely questions:** *What if you remove constraint (8)?* - nothing has to be covered, so the optimum is no drivers
at $0. *How do you know no duty is missing?* - every shorter piece of a legal duty is legal, so a search that
extends legal pieces trip by trip reaches every duty exactly once (we check: 40 on P0, equal to brute force).

---

## Slide 7 - "Model 2 has the stronger bound, but its menu explodes with longer duties" (1:10)

**Key message:** Model 2's LP bound is at least as strong as Model 1's (Theorem 3) and in practice equals the
optimum; but the number of possible duties grows exponentially with how many trips fit in one duty.

**Show:** left, a two-bar picture "LP bound vs optimum" for both models on one instance (from LP-AF / LP-SP; P0:
Model 1 897.6, Model 2 945.0 = optimum). Right, the B13 chart **|P| against n, one colour per L**, log scale, with
crosses where Model 2 could not be built (`results/b13/sizes.png`).
*[pilot]*: n = 100 has 63,633 duties at L = 480 (3 terminals) but more than 2,000,000 at L = 600 (2 terminals).

**Script (151 words):**
"Why bother with a huge menu? Because its LP relaxation is much stronger. Theorem 3 says every LP solution of
Model 2 can be turned into an LP solution of Model 1 with the same cost - so Model 2's bound is never weaker. On
the example: Model 1's LP says 898 dollars, Model 2's says 945 - already the optimum. A bound that tight means the
solver barely has to branch: in our pilot, Model 2 solved almost everything it could build at the very first node.
The price is the menu itself. A longer working day fits more trips, and every extra trip multiplies the number of
possible days. With 100 trips, going from 8 to 10 hours of spread takes us from sixty thousand duties to more than
two million - past our memory guard, so the model cannot even be built. Model 1 never has this problem."

**Likely questions:** *Then why not always use Model 2?* - when |P| explodes it cannot be built at all, and building
it costs time before Gurobi even starts. *What if L doubles?* - |P| can only grow (every duty that was legal stays
legal), so Model 2 may become unbuildable; Model 1 only gets more arcs.

---

## Slide 8 - "Same problem, same optimum - but a stronger bound is not automatically faster" (0:50)

**Key message:** both models always agree on the optimum (checked independently); where Model 2 is large, its
strong bound does not save it - each LP is huge, and enumeration plus building costs time first.

**Show:** the A12 chart "LP gap vs solver time, one marker per model" (from Member A, Thu-Fri); if not ready, the
stacked bars "enumerate / build / solve" for Model 2 from `results/b13/build_cost.png`.
*[pilot]*: the largest Model 2 that could be built had 1.7 million duties and still hit the time limit.

**Script (106 words):**
"First, correctness: on every instance both models solve, they give the same cost, and an independent checker -
written without looking at either model - confirms every schedule. But a stronger bound is not automatically
faster. Total time is enumeration plus building plus solving, and Model 2 pays for every duty before Gurobi starts.
And every node of its search solves an LP with as many columns as there are duties. Our largest buildable case had
1.7 million duties: a near-perfect bound, but it still ran out of time. So the winner depends on the instance -
which is what our benchmark is built to show."

**Likely questions:** *Is it fair that Model 2 gets an extra build budget?* - both get the same two limits; the
equal-budget column shows who solves within 120 s end to end. *How do you know "optimal" is really optimal?* -
every cost is a multiple of $0.50, so a gap below $0.50 leaves no better schedule, and the checker recomputes it.

---

## Slide 9 - "Benchmark: realistic bus timetables, from instant to impossible, chosen by a written rule" (1:10)

**Key message:** 15-20 generated rotation timetables that cover the professor's three groups, selected by a rule
fixed before the final runs - no hand-picking.

**Show:** left, a small feature table (n, terminals, L, duties, class) of the final benchmark
(`instances/final/README.md`); right, the class counts against the targets (from `SELECTION.md`) and the three
groups: *every model fast* (easy), *models differ clearly* (medium + hard), *no model finishes* (time limit).
Footnote: limitation - W = 0.75 L ties the two duty limits.
**[final]**: _N_ instances; easy _a_ / medium _b_ / hard _c_ / time limit _d_; SP not built _e_; n from _x_ to _y_.

**Script (147 words):**
"Our instances imitate real timetables: buses shuttle between terminals all day, busier in the morning and evening
peaks, and their trips are pooled so drivers can change bus; each instance can be rebuilt from its seed. We vary
the number of trips, the number of terminals and the length of a working day, and keep prices fixed, so
difficulty comes from the timetable. A pilot run sorted the candidates into easy, medium, hard and time-limit; it
showed too few easy ones, so we added smaller timetables before any final run. Then a written rule - fixed in our decision log before any final run - picked the final set: spread across
sizes, at least two instances where Model 2 cannot be built, and at least 15 in total. So the benchmark contains
instances both models solve instantly, instances where they differ clearly, and instances no model finishes."

**Likely questions:** *Did you pick instances to make your models look good?* - no: a rule fixed before the final
runs picked them; every candidate and its class is listed in `SELECTION.md`. *What makes an instance hard?* -
mostly trips per duty (set by L and W), then connections per trip and n (H8).

---

## Slide 13 - "Longer duties: Model 2's menu outgrows the computer before Model 1 runs out of time" (1:00)

> Master Plan: the L-sweep chart if the optional sweep ran, otherwise the B13 scalability chart (default).

**Key message:** build failures and time-outs are different results; Model 2 fails by not being built (memory /
build time), Model 1 fails by not finishing (time limit).

**Show:** `results/b13/status_map.png` - solver time against n for all four methods; triangles = time limit,
crosses = not built. Verdicts H4 and H5 in one line each (from `results/b13/B13_summary.md`).
*[pilot]*: Model 2 not built on 13 of 24 main-pilot instances; Model 1 hit the time limit on 20 of 24.

**Script (139 words):**
"This chart separates two kinds of failure that are easy to confuse. A triangle means the model was built but did
not finish in time. A cross means the model could not even be built. Model 1 - always buildable - fails with
triangles: from about 60 trips with long duties, it runs out of time. Model 2 fails with crosses: once the menu
passes two million duties or the build time, it never starts. Where Model 2 can be built, it wins - Model 1 was
faster only on the tiniest timetables, by thousandths of a second. So our recommendation is simple: use the menu while it fits; when it does not, you need Model 1 - or, as a next
step, column generation, which builds only the duties that are worth adding instead of all of them."
*→ handover to C (slide 14, verdicts and conclusions).*

**Likely questions:** *Why are build failures not counted as timeouts?* - they are different causes and different
fixes (memory vs search); mixing them would make Model 2 look slow when it was never run. *What is column
generation?* - start with a few duties and add only those with negative reduced cost; the pricing problem is a
shortest path with spread and driving limits on the acyclic trip graph.

---

### Timing check
| Slide | Planned | Script words | Spoken (≈130 wpm) |
|---|---|---|---|
| 6 | 0:50 | 106 | 0:49 |
| 7 | 1:10 | 151 | 1:10 |
| 8 | 0:50 | 106 | 0:49 |
| 9 | 1:10 | 147 | 1:08 |
| 13 | 1:00 | 139 | 1:04 |
| **Total** | **5:00** | **649** | **≈5:00** - no slack: speak calmly, and cut a sentence if a rehearsal runs over |

### To finish on Sun 15
- [ ] Replace every *[pilot]* number with the final one; fill every **[final]** blank
- [ ] Slide 7 right chart: `results/b13/sizes.png` from the final runs
- [ ] Slide 8 chart: ask A for the A12 chart; fallback `results/b13/build_cost.png`
- [ ] Slide 13 chart: `results/b13/status_map.png`; H4/H5 verdicts from `B13_summary.md`
- [ ] Give the slides to C for merging into one deck; rehearse twice with a timer (Mon 16)
