# Slides 10-12 and 14 - Member C (Maria) - 5:00 in total

> Draft, 10 Nov. Order and times from Master Plan §12; titles state the **finding**, not the topic.
> *[confirm]* = preliminary number from the confirmation runs on the final machine (`results/confirm.csv`,
> 24 candidates, plain AF and SP, 120 s + 120 s). *[pilot]* = 30 s pilot (B12 draft). *[H-preview]* = the heuristic
> run on the 24 candidates (seconds, no solver). All are replaced after Gate 3 by numbers recomputed from
> `results/runs.csv`. Titles in [brackets] are filled in only after Gate 3. Script length: about 130 words per minute.
> Slide 9 (B) ends with the benchmark; slide 13 (B) sits between slides 12 and 14.

---

## Slide 10 - "Greedy strands trip 7; swap-then-merge saves a whole driver ($232.50)" (1:00)

**Key message:** the greedy choice that looks cheapest (shortest wait) can cost a whole extra driver; local search
repairs it with a move that is only good as a pair.

**Show:** the three Gantt charts of P0 from A11 (`case_study`): greedy $1,177.50 with trip 7 alone in red, after local
search $945.00, optimal $945.00. Under them the cost table: drivers −$300, paid minutes +$67.50, total −$232.50.
**Trip numbers:** trip ids 0-7, as on slide 6 (duties {0,1,4,5} and {2,3,6,7}). The Gantt bars carry the file's
labels T1-T8 (T8 = trip 7): before merging, relabel the bars with the ids (or say "T8, trip 7") so slides 6 and 10 match.

**Script (128 words):**
"Before any solver runs, we build a schedule by hand-style rules. Greedy takes the trips in time order and gives
each one to the driver who waits least. On our 8-trip example that looks clever until trip 6: greedy gives it to
driver 1, who is then at the 5-hour driving limit. Trip 7 now has nowhere to go, and greedy hires a third driver
for one single trip: $1,177.50. Local search fixes it with a pair of moves: first move trip 6 to driver 2 - alone
that costs *more* - then attach trip 7 to driver 2. One driver fewer: $945, the optimum. The lesson: a driver costs
$300, as much as 10 hours of paid waiting, so it is worth waiting a lot to save one."

**Likely questions:** *Why accept a move that makes things worse?* - only together with the merge that follows;
the pair is evaluated as one move and must save at least $0.50. *Does local search always reach the optimum?* - no:
on the benchmark it stays a median of 2.5 % above the optimum *[H-preview]*; it stops at the first schedule no
single move can improve (a local optimum).

---

## Slide 11 - "The heuristic gives both models a complete start [where it helped, and where it did not]" (1:10)

**Key message:** the heuristic is fast and always feasible, so it can be handed to Gurobi as a complete MIP start;
it makes the first solution appear much earlier, but it cannot fix a weak bound.

**Show:** left, a flow picture: timetable → greedy → local search → complete start (x, u, v, T, D for Model 1;
z for Model 2) → Gurobi log line "User MIP start produced solution". Right, the B12 paired chart (AF vs AF+S and
SP vs SP+S: time to first incumbent, final gap).

**Numbers to use (replace after Gate 3):**
- heuristic time: under 0.5 s on every candidate up to n = 500; all 24 schedules pass the checker *[H-preview]*
- heuristic cost: median 2.5 % above the optimum where SP proves it (max 11.3 %, n = 50 with L = 10 h) *[H-preview]*
- on two of the largest candidates (n = 400 and 500) the 0.5 s heuristic is **cheaper than plain AF's answer after
  2 minutes** (−2.2 % and −1.4 %) *[H-preview vs confirm]*
- starts accepted: AF 22/22, SP 11/11; first incumbent much earlier (median time ratio 0.12 AF, 0.27 SP); final
  AF gap improved by a median of 7 % *[pilot]*

**Script (152 words):**
"Why build a heuristic if we have two exact models? Because it is almost free - under half a second even with 500
trips - and it is always a legal schedule. That lets us give Gurobi a *complete* start: for Model 1 we translate
the duties into every variable - arcs, start and end markers, spread and driving times; for Model 2 we switch on
exactly the duty columns we used. Gurobi's log confirms it accepted the start every time. Did it help? It made the
first good solution appear much earlier, and on two of the largest instances our half-second heuristic was already better
than what plain Model 1 found in two minutes. But the start mostly changes the *upper* side. Model 1's gap stays
open because its *lower* bound is weak - a better start cannot fix that. And where Model 2 solves at the root node,
there is nothing left for a start to do."

**Likely questions:** *How do you know Gurobi used the start?* - we read the log line and compare its objective with
the heuristic cost (`start_accepted`). *Why does the start not help SP?* - SP's LP bound is already (almost) the
optimum, so it finds and proves the optimum at the root. *Why a complete start, not a partial one?* - a partial
start makes Gurobi solve a sub-MIP to complete it, which can fail; a complete one is checked in one step.

---

## Slide 12 - "[Which model wins on the benchmark, and when]" (1:20)

**Draft title (if the final runs agree):** "Model 2 wins whenever it can be built; Model 1 is the only option
beyond that"

**Key message:** where SP is built it proves the optimum in seconds; AF reaches the time limit from n = 50 on;
where SP cannot be built, AF still returns a feasible schedule with a proven gap.

**Show:** the comparison table (C9, `comparison_table`, methods in rows) and the performance profile (A16). Highlight
three numbers: SP optimal count, AF optimal count, SP not built count.

**Numbers to use (replace after Gate 3):** *[confirm]*
- SP: optimal on 14 of 24 candidates, mostly under 1 s (worst 93 s at n = 200 with 1.7 M duties); not built on 10
  (more than 2,000,000 duties: all n ≥ 300, and n = 100 with L = 10 h)
- AF: optimal on only 5 of 24; time limit on 19, from n = 50 on, with proven gaps of 5-27 % growing with n
- wherever both returned a value, SP's optimum ≤ AF's incumbent; at n = 200 AF's incumbent was up to 1.7 % above
  the optimum after 2 minutes
- example: n = 200 (3 terminals, 6 h): SP optimal in 1.5 s; AF 2 minutes, 19 % gap

**Script (166 words):**
"So which model wins? On our benchmark, the answer depends on one question: can Model 2 be built? When it can,
it wins clearly. It proved the optimum on every instance it could build, usually in under a second, because its
LP bound is already the optimum - Gurobi barely branches. Model 1 proved optimality on only the smallest instances;
from 50 trips on it hit the 2-minute limit with gaps between 5 and 27 percent, and the gap grows with size. But
Model 2 has a cliff: with long duties or many trips the menu passes two million duties and we cannot even build
it. There Model 1 is the only exact model that still runs - it always gives a legal schedule and a proven bound.
So the practical rule is: try Model 2 first; if the menu explodes, fall back to Model 1 with the heuristic start.
The gap you see there is mostly Model 1's weak bound, not a bad schedule."

**Likely questions:** *Is the comparison fair?* - same machine, same 120 s + 120 s limits, 4 threads, same
parameters, recorded in env.txt and in every row. *Why is the gap of AF large even when its schedule is good?* -
the gap is (incumbent − bound) / incumbent; AF's bound is weak (its LP ignores most of the duty limits), so the gap
overstates how far the schedule is from optimal. *What about the equal-budget column?* - end-to-end time counts
SP's enumeration and build too; read it from the comparison table.

---

## Slide 14 - "[Verdicts for the hypotheses tested], limitations, and next: column generation" (1:30)

**Show:** left, the hypothesis table (ID, one-line statement, verdict: confirmed / partly / not confirmed, one
number of evidence each). Right, the Gantt chart of one large final instance (A7, `viz`), best known schedule.
Bottom line: limitations and "what next" in one sentence each.

**Verdict table (filled after Gate 3; preliminary reading in brackets):**

| ID | Statement | Verdict | Evidence |
|---|---|---|---|
| H1 | Model 1's LP ≤ Model 2's LP (Theorem 3) | _after Gate 3_ | LP-AF vs LP-SP on every built instance |
| H2 | Naive big-M is weaker, but only a little | _after Gate 3_ | LP-AF-naive vs LP-AF |
| H3 | SP needs fewer nodes and less solver time | _after Gate 3_ (likely confirmed: SP faster end-to-end on 4 of the 5 candidates both solved; the 5th, n = 20, both under 0.1 s *[confirm]*) | paired times |
| H4 | SP's build share grows with \|P\| | _after Gate 3_ | time breakdown vs \|P\| |
| H5 | SP becomes unbuildable; AF always built | _after Gate 3_ (likely confirmed: 10 not built, 0 AF failures *[confirm]*) | build statuses |
| H6 | The MIP start helps AF more than SP | _after Gate 3_ | paired AF/AF+S, SP/SP+S medians (B12) |
| H8 | Difficulty grows with trips per duty more than with n | _after Gate 3_ | feature charts (B13) |

**Script (184 words, adjust to the final verdicts):**
"Here is what the theory predicted and what we measured. First, the bounds: Theorem 3 says Model 2's LP is at least
as strong as Model 1's - [it held on every instance]. Second, size: we expected Model 2 to explode with long duties
while Model 1 is always built - [confirmed: Model 2 failed to build on N instances, Model 1 never]. Third, speed:
where both are built, Model 2 was faster [on X of Y]. And the heuristic start [helped Model 1 more than Model 2],
because Model 2 usually needs no help at all. On the right is a real large instance: [n] trips covered by [k]
drivers, every duty within its spread and driving limits [instance's L and W]. Limits of our study: one generator family,
one machine, one seed per configuration, and the driving limit tied to the spread, so we cannot separate the two
effects. What next? Instead of writing Model 2's whole menu, generate only the duties that can improve the
solution - column generation. The pricing problem is a shortest path with two resources on our trip network, so
Model 2's strength without its explosion."

**Likely questions:** *Would the conclusions change with another seed?* - possibly in the numbers, not in the
direction; we used one seed per configuration (§10.10 limitation). *Do the results hold for real timetables?* - only
for this generator's family; we say so. *Why column generation and not a bigger computer?* - \|P\| grows
exponentially with trips per duty; more memory buys only a little more n.

---

### Before Gate 3 - what to fill in
1. Titles of slides 11, 12, 14 (brackets) from the final verdicts.
2. Every *[confirm]*, *[pilot]* and *[H-preview]* number from `results/runs.csv` via `crew.analysis` / B12 / A16.
3. Slide 14 Gantt: the largest final instance with a verified schedule; state its cost and status.
4. Merge: A's slides 1-5 + B's `slides_B.pptx` (6-9, 13) + these four into `slides_groupM.pptx` / `.pdf`.
