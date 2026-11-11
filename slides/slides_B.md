# Slides 6-9 and 13 - Member B (Amani) - 5:00 in total

> Final, 11 Nov. Order and times from Master Plan §12; titles state the **finding**, not the topic.
> Every number is from the final runs (`results/runs.csv`, tag `v1.0-final-run`), checked against `results/b13/`
> and `results/a12/`. Script length: about 130 words per minute.
> Slide 5 (A) ends with Model 1's weakness; slide 10 (C) starts with the heuristic. Handover lines are marked.

---

## Slide 6 - "Model 2 writes a schedule as a menu of whole working days" (0:50)

**Key message:** list every legal driver's day once; then the solver only has to pick days so that every trip is
covered exactly once.

**Show:** left, the 8-trip example P0 as a timetable; right, the "menu": a matrix with trips as rows and a few of
the 40 legal duties as columns (1 = the duty covers the trip). Highlight the 2 chosen columns {0, 1, 4, 5} and
{2, 3, 6, 7} = $945. Trips are numbered 0-7 on every slide, like the Gantt charts (A7) and slide 10 (group
decision, 10 Nov). Under it, the whole model in one line:
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

**Show:** left, "LP bound as % of the optimum" for both models on the 10 benchmark instances Model 2 could build
(Model 2: 100 % on all 10; Model 1: 84-98 %). Right, **|P| against n, one colour per L**, log scale; points on the
dashed 2-million line = Model 2 not built. n = 100 has 63,633 duties at L = 480 (3 terminals) but more than
2,000,000 at L = 600 (2 terminals).

**Script (152 words):**
"Why bother with a huge menu? Because its LP relaxation is much stronger. Theorem 3 says every LP solution of
Model 2 can be turned into an LP solution of Model 1 with the same cost - so Model 2's bound is never weaker. On
the example: Model 1's LP says 898 dollars, Model 2's says 945 - already the optimum. A bound that tight means the
solver barely has to branch: in our final runs, Model 2 solved every model it could build at the very first node.
The price is the menu itself. A longer working day fits more trips, and every extra trip multiplies the number of
possible days. With 100 trips, going from 8 to 10 hours of spread takes us from sixty thousand duties to more than
two million - past our memory guard, so the model cannot even be built. Model 1 never has this problem."

**Likely questions:** *Then why not always use Model 2?* - when |P| explodes it cannot be built at all, and building
it costs time before Gurobi even starts. *What if L doubles?* - |P| can only grow (every duty that was legal stays
legal), so Model 2 may become unbuildable; Model 1 only gets more arcs.

---

## Slide 8 - "Same optimum - and the stronger bound wins, until the menu cannot be built" (0:50)

**Key message:** both models always agree on the optimum (checked independently); where Model 2 can be built its
strong bound makes it fast, but on the largest instances it never gets to solve.

**Show:** "LP gap vs solver time" (same data as A12, `results/a12/gap_vs_time.png`, redrawn in the deck palette):
Model 2 at 0 % gap and under 1 s; Model 1 at 2-16 % (to the optimum) and up to the 120 s limit; hollow markers
= no optimum known, gap to the best schedule found (footnote). Two callouts: *10 of 10* built Model 2 models proven
optimal at the root node (at most 0.9 s end to end); *5 of 15* never built (3-75 s spent listing duties).
Backup if asked where the time goes: `results/a12/time_split.png`.

**Script (115 words):**
"First, correctness: on every instance both models solve, they give the same cost, and an independent checker -
written without looking at either model - confirms every schedule. Now bound against speed. Model 2's dots sit at
zero gap: its LP already equals the optimum, so all ten models it could build were solved at the first node, in
under a second. Model 1's LP is 2 to 16 percent below the optimum, so it must branch - on the larger instances
until the 120-second limit. The stronger bound wins - but only where the menu exists. On 5 of our 15 instances,
Model 2 spent up to 75 seconds listing duties and never started."

**Likely questions:** *Is it fair that Model 2 gets an extra build budget?* - both get the same two limits; the
equal-budget column shows who solves within 120 s end to end. *How do you know "optimal" is really optimal?* -
every cost is a multiple of $0.50, so a gap below $0.50 leaves no better schedule, and the checker recomputes it.

---

## Slide 9 - "Benchmark: realistic bus timetables, from instant to impossible, chosen by a written rule" (1:10)

**Key message:** 15-20 generated rotation timetables that cover the professor's three groups, selected by a rule
fixed before the final runs - no hand-picking.

**Show (done 10 Nov, from the frozen benchmark):** three cards for the professor's groups - *every model fast* 4,
*models differ clearly* 6 (medium 2, hard 1, and 3 time-limit instances Model 2 solves in under 0.6 s), *no model
finishes* 5 (Model 1 times out, Model 2 not built) - and a class summary table (instances, n, terminals, duty
length, |P|, Model 1 / Model 2 times). Footer: the rule, 15 of 43 candidates, 2 by the fill-up; limitation
W = 0.75 L. Full 15-row table: `notebook_src/benchmark.md`. Classes recomputed from the final runs (Master Plan
§10.3 step 5): identical to the selection on all 15 instances, so the cards and table stand.

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

## Slide 13 - "Two different failures: Model 1 runs out of time from 80 trips, Model 2's menu stops fitting from 100" (1:00)

> Master Plan: the L-sweep chart if the optional sweep ran, otherwise the B13 scalability chart (default). The
> sweep did not run, so this is the B13 outcome chart.

**Key message:** build failures and time-outs are different results; Model 2 fails by not being built (more than
2 million duties), Model 1 fails by not finishing (time limit).

**Show:** outcome per method on the 15 instances, stacked: optimal / time limit / not built. Model 1 (AF, AF+S):
7 optimal, 8 time limit (every n ≥ 80 and one n = 50 with 10 h duties; gaps 5-27 %). Model 2 (SP, SP+S): 10
optimal at the root node, 5 not built (n = 100 with 10 h duties and every n ≥ 300). The start (+S) changes no
outcome. Background chart: `results/b13/status_map.png`; verdicts in `results/b13/B13_summary.md` (H5 confirmed).

**Script (138 words):**
"This chart separates two kinds of failure that are easy to confuse. Orange means the model was built but did
not finish in time. Grey means the model could not even be built. Model 1 - always buildable - fails in orange:
from 80 trips, and once already at 50 trips with long duties, it runs out of time. Model 2 fails in grey: once
the menu passes two million duties, it never starts. Where Model 2 can be built, it wins - Model 1 was
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
| 7 | 1:10 | 152 | 1:10 |
| 8 | 0:50 | 115 | 0:53 |
| 9 | 1:10 | 147 | 1:08 |
| 13 | 1:00 | 138 | 1:04 |
| **Total** | **5:00** | **658** | **≈5:04** - no slack: speak calmly, and cut a sentence if a rehearsal runs over |

### Status
- [x] Every number from the final runs (slides 7, 8, 13 updated 11 Nov; slide 9 classes rechecked: unchanged)
- [x] Slide 8 built on A's A12 data (LP gap vs solver time), with the "best known" footnote
- [ ] Give `slides_B.pptx` to C for merging into one deck; rehearse twice with a timer (Mon 16)
