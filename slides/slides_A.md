# Slides 1–5 (Member A) — Act 1: the trap, Act 2 begins

Speaking time 5:00. Figures: `py slides/make_figures_A.py` (writes `slides/figures/A_*.png`; every number on
these slides is printed by that script). Trip numbers are ids 0–7, as on every other slide.

---

## Slide 1 — Bus crews: cover every trip at the lowest cost (also airline crew pairing)  ·  0:50

**On the slide**
- Photo: a bus terminal at rush hour (find one with a free licence, e.g. Unsplash; credit it on the slide)
- One sentence: *A timetable of trips is fixed; we choose which driver does which trips, legally, as cheaply as possible.*
- Small line: same structure as airline crew pairing, train crew rostering, delivery-driver planning

**Script**
Every morning a bus company has a fixed timetable: hundreds of trips between its terminals. Each trip needs a
driver, and our job is to decide which driver does which trips. The rules are legal ones: shifts can't be too
long, and a driver can't drive for too long. Airlines solve exactly the same problem for pilots and cabin crew,
so what we show today carries over. We built two exact models and a fast heuristic, and tested them on
fifteen benchmark timetables.

---

## Slide 2 — One driver is worth 10 hours of waiting (F / c = 600 min)  ·  1:00

**On the slide** (one table)

| | |
|---|---|
| **Inputs** | trips (start, end, from, to); terminals |
| **A duty** | one driver's chain of trips: each leaves from where the last one arrived, ≥ 10 min later |
| **Rule 1: spread** | first departure to last arrival ≤ **L** (e.g. 7 h) |
| **Rule 2: driving** | total driving ≤ **W** = 0.75 L |
| **Cost of a duty** | **$300** + **$0.50 × spread minutes** (waiting is paid) |
| **Goal** | every trip covered exactly once, at minimum total cost |

Big line under the table: **$300 ÷ $0.50 per minute = 600 minutes = 10 hours**

**Script**
A duty is one driver's day: a chain of trips, each leaving from where the previous one arrived, with at least ten
minutes to turn around. Two legal limits: the whole shift, first departure to last arrival, is at most L, and the
driving inside it is at most W. Each duty costs three hundred dollars plus fifty cents for every minute of the
shift, so waiting time is paid. The key number is the ratio: one extra driver costs as much as six hundred paid
minutes, ten hours. So it is worth making drivers wait a lot to avoid hiring one more. Keep that in mind for the
next slide.

---

## Slide 3 — P0: can you find the 2-driver schedule? (1 driver is impossible)  ·  1:20

**On the slide**
- Left (show first): `A_slide3_timetable.png` — 8 trips between A and B, L = 7 h, W = 5 h
- Right (reveal after the pause): `A_slide3_optimal.png` — the optimal schedule, 2 drivers, **$945**
  (duty {0, 1, 4, 5} $442.50; duty {2, 3, 6, 7} $502.50)

**Script**
Here is our smallest example, P0: eight one-hour trips between terminals A and B. Take ten seconds: how few
drivers can cover them? *(pause)* One driver is impossible, for two reasons: trips 0 and 2 overlap, and the
eight trips add up to eight hours of driving, more than the five allowed. *(reveal)* Two drivers are enough.
The first does 0, 1, 4 and 5; the second does 2, 3, 6 and 7. Total cost nine hundred and forty-five dollars,
and that is proven optimal: both our models and a brute-force search agree. Even on eight trips, the obvious
greedy approach gets this wrong, as Maria will show you later.

---

## Slide 4 — Model 1 writes a schedule as chains of trips (arc-flow: x, u, v, T, D)  ·  1:00

**On the slide**
- `A_slide4_network.png` — P0's 14 arcs; the 6 arcs of the optimal schedule in bold
- Variables, one line each:
  - **x_ij** = 1 if the same driver does trip j right after trip i (one per arc)
  - **u_j / v_j** = 1 if trip j starts / ends a duty
  - **T_j** = when j's duty started  ·  **D_j** = driving so far, up to j
- Rules: every trip has one predecessor or starts a duty (1), one successor or ends a duty (2);
  T is carried along the chain (4) and limits the spread (5); D adds up the driving (6), at most W (7)

**Script**
Model 1 starts from the trip network. An arrow from i to j means j can follow i: it leaves from where i
arrives, at least ten minutes later. P0 has fourteen such arrows. For each arrow the model decides yes or no, and
every trip gets exactly one way in and one way out, either another trip or the start or end of a duty. The yes
arrows join into chains, and each chain is one driver. Here the six bold arrows form the two duties from the
previous slide. To enforce the legal limits, two numbers travel along each chain: T remembers when the duty
started, and D adds up the driving.

---

## Slide 5 — Model 1 is small and always buildable, but its LP almost forgets the duty limits  ·  0:50

**On the slide**
- Left: `A_slide5_size.png` — Model 1 stays below 60,000 variables up to 500 trips; Model 2's duty list
  passes 2 million and cannot be built on 5 of the 15 benchmark instances (final runs)
- Right: `A_slide5_lp.png` — Model 1's LP bound with the duty rules vs with rules (4)–(7) deleted (P0–P5):
  almost the same, identical on P3 and P4
- One line: the rules that make the problem hard only become active once the solver branches

**Script**
Model 1's strength is its size. It grows with the number of arrows, not with the number of possible duties, so
it can always be built: even at five hundred trips it has under sixty thousand variables. Its weakness is on the
right. If we solve its linear relaxation, the quick lower bound the solver relies on, and then delete the
duty-limit rules completely, the bound hardly moves. On two prototypes it does not move at all. In other words,
the relaxation almost forgets the shift and driving limits, and the solver has to recover them by branching. Amani
will now show a model that is the opposite: a much stronger bound, at the price of size.

---

### Backup (if asked)
- Why is (4) needed? Without it, T would not be tied to its duty's start, so a 14-hour duty would look legal.
- Why is the big-M s_j − ℓ_i valid? When the arc is unused, T_j ≤ s_j and T_i ≥ ℓ_i, so no real schedule is cut off (Theorem 2).
- Why not 1440? It is not always valid (it depends on the data); we compute valid constants per instance.
- Why no symmetry? Drivers have no index: a duty is a chain of arcs, not "driver k".
- **What next for Model 1? An exact arc reduction.** An arc i → j can never be in a legal duty if the pair alone
  breaks a limit: e_j − s_i > L (spread) or d_i + d_j > W (driving). On our benchmark that is 56,669 of 153,818
  arcs (36.8 %, Amani's count). Deleting them changes no integer solution, makes Model 1 about a third smaller,
  and the LP can no longer use them fractionally. We found this after the code freeze, so it is future work.
