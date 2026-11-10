## The P0 story: why a cheap-looking choice costs a whole driver

P0 has 8 one-hour trips between terminals A and B (L = 420, W = 300, turnaround 10 min).
Trips are numbered by id, 0–7, in the text, the charts and the slides.

**Greedy ($1,177.50, 3 drivers).** Greedy takes the trips in start order and gives each one to the driver
where it waits least. Trips 0 and 2 overlap, so it opens two drivers. When trip 6 arrives, both drivers could take it;
greedy picks the shorter wait (driver 1). Driver 1 now has 300 minutes of driving, the limit W.
Then trip 7 has nowhere to go: driver 1 is full, and driver 2 is at terminal A while trip 7 leaves from B.
Greedy hires a **third driver for one trip** (trip 7, outlined in red).

**Local search ($945.00, 2 drivers).** It moves trip 6 from driver 1 to driver 2 (a tail swap), then appends
trip 7 to driver 2 (a merge). The swap alone makes things worse ($1,237.50), so it is only accepted together
with the merge: this is the *swap-then-merge* move. On P0 local search reaches the optimum.

**Optimal ($945.00).** Model 1, Model 2 and brute force all agree.

| | Greedy | Optimal | Difference |
|---|---:|---:|---:|
| Drivers × $300 | 3 × 300 = 900.00 | 2 × 300 = 600.00 | −300.00 |
| Paid minutes × $0.50 | 555 × 0.5 = 277.50 | 690 × 0.5 = 345.00 | +67.50 |
| **Total** | **1,177.50** | **945.00** | **−232.50** |

**The lesson.** The optimum pays for 135 more minutes of waiting to save one driver. One driver ($300)
costs as much as 600 paid minutes ($0.50 each), so it is worth waiting up to 10 hours in total to avoid hiring
another driver, and a short wait now can be very expensive later.

```python
from crew.greedy import greedy_insertion
from crew.localsearch import heuristic
from crew.viz import case_study, cost_table
P0 = load_instance("instances/proto/P0_example8.json")
schedules = {"Greedy": greedy_insertion(P0), "After local search": heuristic(P0).schedule,
             "Optimal": P0.reference["schedule"]}
case_study(P0, schedules, highlight=[7])
cost_table(P0, schedules)
```
