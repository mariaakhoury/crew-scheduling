## Model 1: arc-flow (plain words)

**The idea in one sentence.** For every pair of trips that one driver could do back to back, the model decides
yes or no; the "yes" links join trips into chains, and each chain is one driver's duty.

### When can trip j follow trip i? (the trip network)

Trip *j* can come right after trip *i* in the same duty if *j* leaves from the terminal where *i* arrives, and at
least τ = 10 minutes after *i* ends. Each such pair is an **arc** (*i*, *j*). Arcs always point forward in time,
so a chain can never loop back on itself. On P0 there are 14 arcs (`graph.build_arcs`).

### Variables

| Variable | Type | Meaning |
|---|---|---|
| x<sub>ij</sub> | yes/no, one per arc | the same driver does trip *j* right after trip *i* |
| u<sub>j</sub> | yes/no | trip *j* is the **first** trip of a duty |
| v<sub>i</sub> | yes/no | trip *i* is the **last** trip of a duty |
| T<sub>j</sub> | number in [ℓ<sub>j</sub>, s<sub>j</sub>] | when the duty containing *j* started |
| D<sub>j</sub> | number in [d<sub>j</sub>, U<sub>j</sub>] | minutes driven in that duty up to and including *j* |

T and D are "memories" carried along each chain: T remembers when the duty began, D adds up the driving.

### Cost

Total = \$300 × (number of duties) + \$0.50 × (all driving minutes) + \$0.50 × (waiting minutes on used arcs).
Driving is the same in every schedule, so the model really trades **drivers against waiting**.
This equals the official cost, Σ (\$300 + \$0.50 × spread), because each duty's spread is its driving plus its waits.

### Rules (constraints)

| # | Name | Rule in words |
|---|---|---|
| (1) | `c1_pred` | every trip either starts a duty or comes after exactly one trip |
| (2) | `c2_succ` | every trip either ends a duty or is followed by exactly one trip |
| (3) | bound on T | a duty starts no later than each of its trips, and no earlier than ℓ<sub>j</sub> |
| (4) | `c4_Tchain` | if *j* follows *i*, T cannot increase: T<sub>j</sub> ≤ T<sub>i</sub>, so every T in a duty is at most its first trip's start |
| (5) | `c5_spread` | trip *j* ends at most L minutes after its duty started |
| (6) | `c6_Dchain` | if *j* follows *i*, driving grows by *j*'s length: D<sub>j</sub> ≥ D<sub>i</sub> + d<sub>j</sub> |
| (7) | bound on D | driving up to *j* is at most U<sub>j</sub> ≤ W |

(1) and (2) cut the trips into chains. (3) and (4) together enforce the spread limit L; (6) and (7) enforce the
driving limit W. Rule (5) is already implied by the bound ℓ<sub>j</sub> ≥ e<sub>j</sub> − L, so it changes nothing; we keep it
because it is easy to read, and Gurobi removes it. Without (4), however, a 14-hour duty would look legal.

### Full mathematical formulation

**Sets and data.** Trips $J = \{0, \dots, n-1\}$; trip $j$ starts at $s_j$, ends at $e_j$ and drives
$d_j = e_j - s_j$ minutes. Arcs $A = \{(i, j) : \text{dest}_i = \text{origin}_j,\ e_i + \tau \le s_j\}$.
Costs $F = 300$ per duty and $c = 0.5$ per minute; limits $L$ (spread) and $W$ (driving).
With $s_{\min} = \min_k s_k$: $\ell_j = \max(s_{\min},\, e_j - L)$ and $U_j = \min(W,\, e_j - s_{\min})$.
Big-M constants per arc: $M^T_{ij} = s_j - \ell_i$ and $M^D_{ij} = U_i$.

**Variables.** $x_{ij} \in \{0,1\}$ for $(i,j) \in A$; $u_j, v_j \in \{0,1\}$; $T_j$ and $D_j$ continuous, $j \in J$.

$$
\min \; F \sum_{j \in J} u_j \;+\; c \sum_{j \in J} d_j \;+\; c \sum_{(i,j) \in A} (s_j - e_i)\, x_{ij}
$$

subject to

$$
\begin{aligned}
& u_j + \sum_{i:(i,j) \in A} x_{ij} = 1 && \forall j \in J && (1)\ \texttt{c1\_pred}\\
& v_i + \sum_{j:(i,j) \in A} x_{ij} = 1 && \forall i \in J && (2)\ \texttt{c2\_succ}\\
& \ell_j \le T_j \le s_j && \forall j \in J && (3)\ \text{variable bounds}\\
& T_j \le T_i + M^T_{ij}\,(1 - x_{ij}) && \forall (i,j) \in A && (4)\ \texttt{c4\_Tchain}\\
& e_j - T_j \le L && \forall j \in J && (5)\ \texttt{c5\_spread}\\
& D_j \ge D_i + d_j - M^D_{ij}\,(1 - x_{ij}) && \forall (i,j) \in A && (6)\ \texttt{c6\_Dchain}\\
& d_j \le D_j \le U_j && \forall j \in J && (7)\ \text{variable bounds}\\
& x_{ij},\, u_j,\, v_j \in \{0, 1\}
\end{aligned}
$$

**Why it is correct, in one line each.** (1)-(2) cut the trips into chains (each trip one way in, one way out);
(3)-(5): $T$ can only decrease along a chain and starts at most at the first trip's start $s_{\text{first}}$, so
$T_{\text{last}} \le s_{\text{first}}$ and (5) gives $e_{\text{last}} - s_{\text{first}} \le L$; (6)-(7) add up the driving along the chain and cap it at $U_j \le W$.
The second term of the objective is a constant (total driving); together with the waiting term it equals
$\sum_{\text{duties}} (F + c \cdot \text{spread})$, the official cost. Rows: $3n + 2|A|$; variables: $|A| + 4n$.
LP relaxation (`relax=True`): $x, u, v \in [0, 1]$. Naive big-M variant (A6): $M^T = \max_j s_j - \min_i \ell_i$
and $M^D = W$ for every arc.

### The big-M numbers

Rules (4) and (6) should only apply when *j* really follows *i* (x<sub>ij</sub> = 1). When x<sub>ij</sub> = 0, a constant "M"
switches the rule off:

- (4): T<sub>j</sub> ≤ T<sub>i</sub> + M<sup>T</sup><sub>ij</sub> (1 − x<sub>ij</sub>), with M<sup>T</sup><sub>ij</sub> = s<sub>j</sub> − ℓ<sub>i</sub>
- (6): D<sub>j</sub> ≥ D<sub>i</sub> + d<sub>j</sub> − M<sup>D</sup><sub>ij</sub> (1 − x<sub>ij</sub>), with M<sup>D</sup><sub>ij</sub> = U<sub>i</sub>

Here ℓ<sub>j</sub> = max(earliest start, e<sub>j</sub> − L) is the earliest any duty containing *j* could start, and
U<sub>j</sub> = min(W, e<sub>j</sub> − earliest start) is the most driving possible up to *j* (`graph.big_m_bounds`).
These are the smallest numbers that are always big enough, using only the variable bounds.
**Smaller M = tighter model:** the LP relaxation gives a better lower bound. The "naive" version (task A6) uses one
big number per rule instead (M<sup>T</sup> = latest start − smallest ℓ, M<sup>D</sup> = W): same best schedule, weaker bound.

### Size

|A| + 4n variables and 3n + 2|A| constraints (|A| = number of arcs). The model grows with the number of arcs,
not with the number of possible duties, so it can always be built, even when Model 2's duty list explodes.

### Theorems 1–3 in plain words

**Theorem 1 (model → schedule).** Every solution of Model 1 is a real, legal schedule with the same cost.
Rules (1)–(2) cut the trips into chains; (3)–(4) keep each chain within L; (6)–(7) keep its driving within W.

**Theorem 2 (schedule → model).** Every legal schedule can be written as a solution of Model 1 with the same cost:
set x, u, v from the duties, T = each duty's start, D = driving so far. The big-M values are large enough that
unused arcs never block a real schedule. So Model 1 never cuts off a good schedule, and Models 1 and 2 always
have the **same optimum**.

**Theorem 3 (bounds).** The LP bound of Model 1 is never higher than Model 2's: LP(AF) ≤ LP(SP).
Any fractional Model 2 solution can be turned into a fractional Model 1 solution with the same cost, but not the
other way round. Model 2 is "stronger"; Model 1 is smaller. Which one solves faster is measured, not assumed.

### Where it is in the code

`crew/model_arcflow.py`: `build_arcflow(inst, arcs, relax=False, naive_m=False)` returns the model and its
variables; `decode_arcflow(inst, vars)` turns the solution back into duties: start at each trip with u = 1 and
follow the chosen arcs. On P0 it gives \$945 with duties {0, 1, 4, 5} and {2, 3, 6, 7}.
