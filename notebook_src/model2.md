## Model 2: set partitioning over complete duties

**Idea.** Instead of deciding trip by trip which trip a driver does next (Model 1), we first write down
*every* legal working day a driver could have — every **duty** — and then let the solver pick a set of
duties that covers each trip exactly once at minimum cost. It is the "menu of whole days" model.

### Sets and parameters
| Symbol | Meaning |
|---|---|
| $I = \{0,\dots,n-1\}$ | trips |
| $P$ | set of **all** legal duties (chains of trips that respect turnaround, spread $\le L$ and driving $\le W$) |
| $a_{ip}\in\{0,1\}$ | 1 if trip $i$ belongs to duty $p$ |
| $\sigma_p$ | spread of duty $p$: end of its last trip − start of its first trip (minutes) |
| $c_p = F + c\,\sigma_p$ | cost of duty $p$ ($F = \$300$, $c = \$0.50$ per minute) |

### Decision variables
$z_p \in \{0,1\}$ for every $p \in P$: 1 if duty $p$ is used (one driver works it).

### Formulation
$$\min \sum_{p\in P} c_p\, z_p$$
$$\text{s.t.}\quad \sum_{p\in P} a_{ip}\, z_p = 1 \qquad \forall i \in I \qquad (8)\ \texttt{c8\_cover}$$
$$z_p \in \{0,1\} \qquad \forall p \in P$$

Constraint (8) says: every trip is driven by exactly one chosen duty. All the work rules (same terminal,
10-minute turnaround, spread $\le L$, driving $\le W$) are **inside the columns**: a duty is only in $P$
if it is legal, so the model itself needs no big-M constraints and no time variables.

### Size as a function of the instance
* variables: $|P|$  ·  constraint rows: $n$  ·  nonzeros: $\sum_{p} |p|$ (checked against Gurobi by test Q28)
* $|P|$ grows **exponentially** with the number of trips that fit in one duty. Longer duties (larger $L$, $W$)
  and denser timetables make it explode: with the *old* pilot generator (planted, seed 1), $n = 200$ went from
  66,393 duties at $L = 360$ to 14.5 million at $L = 600$ (Master Plan §3.2; the counts for the final rotation
  generator are measured again and reported in the scalability section). That is why the code stops at `COLUMN_CAP` = 2,000,000 duties or after the
  120 s build limit, and reports the instance as **not built** (a build result, never a timeout).

### How the duties are generated (duties.py) — and why none is missed
Depth-first search: start a duty at every trip; extend it by any trip that can follow the last one
(an arc of the compatibility graph) as long as spread $\le L$ and driving $\le W$.

*Completeness.* Adding a trip can only increase the spread and the driving time, so every prefix of a legal
duty is itself legal. The search extends every legal prefix, therefore it reaches every legal duty.
Trips inside a duty are ordered by time, so each duty is produced exactly once. (Test Q12: on P0 the search
finds 40 duties, and on P0–P2 the count equals a brute-force check of all $2^n$ subsets of trips.)

### Theoretical argument: why it should be fast — and when it is not
**Strengths**
* **Strongest LP bound.** Theorem 3: every LP solution of set partitioning can be turned into an LP solution of
  the arc-flow model with the same cost, so $z_{LP}(\text{AF}) \le z_{LP}(\text{SP})$. In the pilot the SP LP
  equalled the integer optimum on 23 of 23 tiny instances; arc-flow's LP was lower on 20 of 23 (up to 17.3 %).
  In the final runs it equalled the optimum on all 10 benchmark instances where SP was built (H1).
  A tighter bound means fewer branch-and-bound nodes.
* **No big-M constants**, so the LP does not "forget" the duty limits the way arc-flow's relaxation does.
* **No symmetry**: a duty is a set of trips, not "driver $k$", so swapping drivers gives the same solution.

**Weaknesses**
* **Exponential number of columns.** Every duty must be enumerated and stored *before* Gurobi starts, so the
  fair comparison is end-to-end time (enumeration + build + solve), not solver time alone.
* **Bigger LP per node**: each node LP has $|P|$ columns (possibly millions), versus $|A| + 4n$ for arc-flow.
* **Memory**: the model may not be buildable at all for long duties and large $n$.

**Expected (to be tested, hypotheses H3–H5).** Where it can be built, SP needs fewer nodes and less solver
time than arc-flow; its advantage in end-to-end time shrinks as $|P|$ grows; and for long duties and large $n$
it cannot be built while arc-flow always can. A stronger bound is not automatically faster.
What the experiments showed is in §20 (Discussion): H3 and H5 confirmed, H4 not confirmed.

### Warm start (used by SP+S)
The heuristic schedule is a set of legal duties, so all of them are in the complete $P$. We set the start value
$z_p = 1$ for those duties and 0 for all others; Gurobi logs "Loaded user MIP start with objective X".

### What if…? (questions to be ready for)
* *Remove (8)?* The objective is minimised with nothing to cover, so the optimum is "no drivers" at \$0.
* *Use $\ge 1$ instead of $= 1$ (set covering)?* Valid here only if dropping a repeated trip from a duty keeps
  it legal and not more expensive — not true in general (removing a middle trip can break the terminal chain),
  so we keep set partitioning.
* *What if $L$ doubles?* More trips fit in a duty, $|P|$ can only grow (every duty that was legal stays legal)
  and SP may become unbuildable; arc-flow is unaffected in size.
* *Next step:* column generation — start with a few duties and add only those with negative reduced cost; the
  pricing problem is a resource-constrained shortest path (resources: spread and driving) on the acyclic trip graph.
