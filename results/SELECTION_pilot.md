# Benchmark selection (Group M) - pilot stage

Source rows: `results/pilot.csv` + `results/pilot_small.csv` (pilot limits). Written by `pilot/classify.py`. Pilot classes are PRELIMINARY:
at the pilot limit a hard instance and a time-limit instance look the same (Master Plan §10.3 step 1).

## Rule (fixed before the confirmation runs)
1. Classes from the plain AF and SP runs, first rule wins: NOT_BUILT (neither model built) -> TIME_LIMIT
   (a built plain model hit the limit) -> HARD (max solver time > 24 s at the final
   limits) -> MEDIUM (both optimal and times differ x10, or only one model built) -> EASY.
2. Confirmation candidates = every HARD, TIME_LIMIT and NOT_BUILT instance + 2 spares per EASY/MEDIUM class, at most 24 files. Spread rule: order by
   (n, L, configuration id) and take evenly spaced positions from the smallest to the largest; if the cap
   binds, at least 2 SP_not_built instances are kept.
3. Final selection (after the confirmation runs): within each class, order by (n, L, configuration id) and
   take the targets {'EASY': 4, 'MEDIUM': 5, 'HARD': 5, 'TIME_LIMIT': 6} with the spread rule; at least 2 selected instances carry
   SP_not_built (places reserved in TIME_LIMIT, then HARD, then MEDIUM); missing TIME_LIMIT places are
   filled with HARD. If fewer than 15 are then selected, the remaining places up to 15 are filled from the
   unused TIME_LIMIT, then HARD, then EASY instances with the same spread rule (column selected_as).
   (Changed from 'smallest n first' on 9 Nov, issue #1, before the confirmation runs: smallest-first
   dropped every instance with n > 80 and every SP_not_built instance; the fill-up guarantees 15.)
4. No instance is hand-picked, replaced or removed after the final runs start.

## Selection procedure (exact, reproducible by hand; approved in issue #1, 9 Nov)

**A. Spread-take k instances from a pool of N** (used in every step below):
1. Order the pool by n, then L, then configuration id (the instance name), all ascending; number the
   positions 0 .. N-1.
2. If k >= N: take the whole pool. If k = 0: take nothing. If k = 1: take position floor(N / 2).
3. Otherwise take positions round(i * (N - 1) / (k - 1)) for i = 0, 1, ..., k - 1 (Python round: halves go
   to the nearest even integer), dropping duplicates. Position 0 (smallest) and N - 1 (largest) are
   always taken.

**B. Confirmation candidates (pilot stage, at most 24 files):**
1. Spares: spread-take 2 from the EASY pool and 2 from the MEDIUM pool.
2. Rechecks: the pool of all HARD, TIME_LIMIT and NOT_BUILT instances, k = 24 - number of spares.
   First spread-take min(2, k) from the SP_not_built instances of that pool, then spread-take the
   remaining places from the rest of the pool.

**C. Final selection (after the confirmation runs):**
1. Classes come from the confirmation rows; an instance without them keeps its pilot class only if that
   class is EASY or a both-optimal MEDIUM; anything else is UNCONFIRMED and never selected.
2. Go through the classes in the order TIME_LIMIT, HARD, MEDIUM, EASY with targets 6, 5, 5, 4; HARD's
   target is increased by TIME_LIMIT's shortfall (places TIME_LIMIT could not fill).
3. Keep a counter need = 2 (minimum number of SP_not_built instances). In TIME_LIMIT, HARD and MEDIUM:
   first spread-take min(need, target) from the class's SP_not_built instances, then spread-take the
   remaining places from the class's other instances. In EASY: spread-take the target directly.
   After each class, lower need by the number of SP_not_built instances taken.
4. Fill-up: if fewer than 15 are selected, take the missing number from the unused TIME_LIMIT
   instances (spread-take); if still fewer than 15, from the unused HARD, then the unused EASY ones.
   These rows are marked selected_as = 'fill-up to 15'.
5. NOT_BUILT, UNCONFIRMED and UNUSABLE instances are never selected. No instance is hand-picked,
   replaced or removed after the final runs start.

**Data note:** the rows come from 2 machine fingerprints: `a221bde82d6c` (96 rows), `9e28e4fab317` (76 rows). Allowed for the pilot (used only to choose candidates) when the difference is explained here; final rows must share one configuration and one machine.

**Explanation:** Both fingerprints are the same laptop (i5-13420H, 8 cores). The fingerprint includes the RAM size, which the runner reported as 8.3 GB in the morning and as 7.7 GiB after C's RAM-unit fix of 9 Nov. Both batches use the same configuration (757cdd8f3860: 30 s + 30 s, MemLimit 6 GB). The supplement (results/pilot_small.csv) was added on 9 Nov to fix the EASY/MEDIUM shortage; its first batch (MemLimit 5 GB) is kept there marked superseded.

## Preliminary classes: {'EASY': 14, 'MEDIUM': 2, 'HARD': 0, 'TIME_LIMIT': 26, 'NOT_BUILT': 1, 'UNCONFIRMED': 0, 'UNUSABLE': 0}

| class | target | in this population |
|---|---|---|
| EASY | 4 | 14 |
| MEDIUM | 5 | 2 |
| HARD | 5 | 0 |
| TIME_LIMIT | 6 | 26 |

**WARNING:** too few MEDIUM instances in this population for the targets. Add smaller configurations to the candidate pool (same generator, same rule) and pilot them before the freeze; record the addition here.

## Confirmation candidates (24 files, 48 runs: plain AF and SP at the final limits)

| instance | class | why_candidate | reason | SP_not_built | n | m | L | W | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n20_m2_L360_s201 | EASY | spare | both fast / similar | False | 20 | 2 | 360 | 270 | 371 | OPTIMAL | 0.00600004 | OPTIMAL | 0.00899982 |
| rt_n50_m2_L600_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 50 | 2 | 600 | 450 | 14599 | TIME_LIMIT | 30.01 | OPTIMAL | 0.172 |
| rt_n50_m3_L600_s201 | MEDIUM | spare | SP faster by x43.6 | False | 50 | 3 | 600 | 450 | 9982 | OPTIMAL | 4.537 | OPTIMAL | 0.104 |
| rt_n60_m2_L360_s201 | EASY | spare | both fast / similar | False | 60 | 2 | 360 | 270 | 6650 | OPTIMAL | 0.704 | OPTIMAL | 0.0420001 |
| rt_n60_m3_L360_s201 | MEDIUM | spare | SP faster by x71.3 | False | 60 | 3 | 360 | 270 | 1911 | OPTIMAL | 7.126 | OPTIMAL | 0.0309999 |
| rt_n60_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 60 | 2 | 480 | 360 | 16064 | TIME_LIMIT | 30.008 | OPTIMAL | 0.138 |
| rt_n80_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 80 | 2 | 360 | 270 | 22644 | TIME_LIMIT | 30.028 | OPTIMAL | 0.211 |
| rt_n80_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 80 | 3 | 360 | 270 | 5044 | TIME_LIMIT | 30.114 | OPTIMAL | 0.644 |
| rt_n80_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 80 | 3 | 480 | 360 | 22968 | TIME_LIMIT | 30.576 | OPTIMAL | 0.23 |
| rt_n100_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 100 | 2 | 480 | 360 | 297266 | TIME_LIMIT | 30.004 | OPTIMAL | 3.428 |
| rt_n100_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 100 | 3 | 480 | 360 | 63633 | TIME_LIMIT | 30.022 | OPTIMAL | 1.179 |
| rt_n100_m2_L600_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 100 | 2 | 600 | 450 | 2e+06 | TIME_LIMIT | 30.018 | COLUMN_CAP |  |
| rt_n200_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF/SP hit the time limit | False | 200 | 2 | 360 | 270 | 1.72403e+06 | TIME_LIMIT | 30.027 | TIME_LIMIT | 30.433 |
| rt_n200_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 200 | 3 | 360 | 270 | 113958 | TIME_LIMIT | 30.028 | OPTIMAL | 1.492 |
| rt_n200_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 200 | 3 | 480 | 360 | 1.20719e+06 | TIME_LIMIT | 30.039 | OPTIMAL | 12.19 |
| rt_n300_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 2 | 360 | 270 | 2e+06 | TIME_LIMIT | 30.047 | COLUMN_CAP |  |
| rt_n300_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 2 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.347 | COLUMN_CAP |  |
| rt_n300_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 3 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.054 | COLUMN_CAP |  |
| rt_n400_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 400 | 2 | 360 | 270 | 1.32e+06 | TIME_LIMIT | 30.11 | BUILD_LIMIT |  |
| rt_n400_m2_L480_s201 | NOT_BUILT | recheck at 120 s | neither model built (AF:BUILD_LIMIT, SP:BUILD_LIMIT); recheck at the final limits | True | 400 | 2 | 480 | 360 | 190000 | BUILD_LIMIT |  | BUILD_LIMIT |  |
| rt_n400_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 400 | 3 | 480 | 360 | 1.83e+06 | TIME_LIMIT | 30.745 | BUILD_LIMIT |  |
| rt_n500_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 3 | 360 | 270 | 2e+06 | TIME_LIMIT | 30.734 | COLUMN_CAP |  |
| rt_n500_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 2 | 480 | 360 | 1.75e+06 | TIME_LIMIT | 30.132 | BUILD_LIMIT |  |
| rt_n500_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 3 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.11 | COLUMN_CAP |  |

## Whole pilot population

| instance | class | reason | SP_not_built | n | m | L | W | n_arcs | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n20_m2_L360_s201 | EASY | both fast / similar | False | 20 | 2 | 360 | 270 | 84 | 371 | OPTIMAL | 0.00600004 | OPTIMAL | 0.00899982 |
| rt_n20_m3_L360_s201 | EASY | both fast / similar | False | 20 | 3 | 360 | 270 | 66 | 224 | OPTIMAL | 0.049 | OPTIMAL | 0.0079999 |
| rt_n20_m2_L480_s201 | EASY | both fast / similar | False | 20 | 2 | 480 | 360 | 84 | 475 | OPTIMAL | 0.00899982 | OPTIMAL | 0.017 |
| rt_n30_m2_L360_s201 | EASY | both fast / similar | False | 30 | 2 | 360 | 270 | 199 | 442 | OPTIMAL | 0.0109999 | OPTIMAL | 0.0140002 |
| rt_n30_m3_L360_s201 | EASY | both fast / similar | False | 30 | 3 | 360 | 270 | 143 | 525 | OPTIMAL | 0.146 | OPTIMAL | 0.0120001 |
| rt_n30_m2_L480_s201 | EASY | both fast / similar | False | 30 | 2 | 480 | 360 | 199 | 558 | OPTIMAL | 0.0150001 | OPTIMAL | 0.0140002 |
| rt_n30_m3_L480_s201 | EASY | both fast / similar | False | 30 | 3 | 480 | 360 | 143 | 1563 | OPTIMAL | 0.0349998 | OPTIMAL | 0.017 |
| rt_n40_m2_L360_s201 | EASY | both fast / similar | False | 40 | 2 | 360 | 270 | 350 | 792 | OPTIMAL | 0.0159998 | OPTIMAL | 0.0249999 |
| rt_n40_m3_L360_s201 | EASY | both fast / similar | False | 40 | 3 | 360 | 270 | 245 | 854 | OPTIMAL | 0.288 | OPTIMAL | 0.016 |
| rt_n40_m2_L480_s201 | EASY | both fast / similar | False | 40 | 2 | 480 | 360 | 350 | 922 | OPTIMAL | 0.04 | OPTIMAL | 0.0280001 |
| rt_n40_m3_L480_s201 | EASY | both fast / similar | False | 40 | 3 | 480 | 360 | 245 | 2678 | OPTIMAL | 0.202 | OPTIMAL | 0.023 |
| rt_n50_m2_L360_s201 | EASY | both fast / similar | False | 50 | 2 | 360 | 270 | 560 | 3718 | OPTIMAL | 0.095 | OPTIMAL | 0.0479999 |
| rt_n50_m3_L360_s201 | EASY | both fast / similar | False | 50 | 3 | 360 | 270 | 386 | 1180 | OPTIMAL | 0.823 | OPTIMAL | 0.0309999 |
| rt_n60_m2_L360_s201 | EASY | both fast / similar | False | 60 | 2 | 360 | 270 | 818 | 6650 | OPTIMAL | 0.704 | OPTIMAL | 0.0420001 |
| rt_n50_m3_L600_s201 | MEDIUM | SP faster by x43.6 | False | 50 | 3 | 600 | 450 | 386 | 9982 | OPTIMAL | 4.537 | OPTIMAL | 0.104 |
| rt_n60_m3_L360_s201 | MEDIUM | SP faster by x71.3 | False | 60 | 3 | 360 | 270 | 559 | 1911 | OPTIMAL | 7.126 | OPTIMAL | 0.0309999 |
| rt_n400_m2_L480_s201 | NOT_BUILT | neither model built (AF:BUILD_LIMIT, SP:BUILD_LIMIT); recheck at the final limits | True | 400 | 2 | 480 | 360 | 36270 | 190000 | BUILD_LIMIT |  | BUILD_LIMIT |  |
| rt_n50_m2_L600_s201 | TIME_LIMIT | AF hit the time limit | False | 50 | 2 | 600 | 450 | 560 | 14599 | TIME_LIMIT | 30.01 | OPTIMAL | 0.172 |
| rt_n60_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 60 | 2 | 480 | 360 | 818 | 16064 | TIME_LIMIT | 30.008 | OPTIMAL | 0.138 |
| rt_n60_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 60 | 3 | 480 | 360 | 559 | 6974 | TIME_LIMIT | 30.001 | OPTIMAL | 0.075 |
| rt_n80_m2_L360_s201 | TIME_LIMIT | AF hit the time limit | False | 80 | 2 | 360 | 270 | 1456 | 22644 | TIME_LIMIT | 30.028 | OPTIMAL | 0.211 |
| rt_n80_m3_L360_s201 | TIME_LIMIT | AF hit the time limit | False | 80 | 3 | 360 | 270 | 981 | 5044 | TIME_LIMIT | 30.114 | OPTIMAL | 0.644 |
| rt_n80_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 80 | 2 | 480 | 360 | 1456 | 98476 | TIME_LIMIT | 30.023 | OPTIMAL | 1.142 |
| rt_n80_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 80 | 3 | 480 | 360 | 981 | 22968 | TIME_LIMIT | 30.576 | OPTIMAL | 0.23 |
| rt_n100_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 100 | 2 | 480 | 360 | 2245 | 297266 | TIME_LIMIT | 30.004 | OPTIMAL | 3.428 |
| rt_n100_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 100 | 3 | 480 | 360 | 1539 | 63633 | TIME_LIMIT | 30.022 | OPTIMAL | 1.179 |
| rt_n100_m2_L600_s201 | TIME_LIMIT | AF hit the time limit | True | 100 | 2 | 600 | 450 | 2245 | 2e+06 | TIME_LIMIT | 30.018 | COLUMN_CAP |  |
| rt_n100_m3_L600_s201 | TIME_LIMIT | AF hit the time limit | False | 100 | 3 | 600 | 450 | 1539 | 298815 | TIME_LIMIT | 30.013 | OPTIMAL | 2.631 |
| rt_n200_m2_L360_s201 | TIME_LIMIT | AF/SP hit the time limit | False | 200 | 2 | 360 | 270 | 9009 | 1.72403e+06 | TIME_LIMIT | 30.027 | TIME_LIMIT | 30.433 |
| rt_n200_m3_L360_s201 | TIME_LIMIT | AF hit the time limit | False | 200 | 3 | 360 | 270 | 5993 | 113958 | TIME_LIMIT | 30.028 | OPTIMAL | 1.492 |
| rt_n200_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 200 | 2 | 480 | 360 | 9009 | 2e+06 | TIME_LIMIT | 30.045 | COLUMN_CAP |  |
| rt_n200_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | False | 200 | 3 | 480 | 360 | 5993 | 1.20719e+06 | TIME_LIMIT | 30.039 | OPTIMAL | 12.19 |
| rt_n300_m2_L360_s201 | TIME_LIMIT | AF hit the time limit | True | 300 | 2 | 360 | 270 | 20425 | 2e+06 | TIME_LIMIT | 30.047 | COLUMN_CAP |  |
| rt_n300_m3_L360_s201 | TIME_LIMIT | AF hit the time limit | False | 300 | 3 | 360 | 270 | 13392 | 870192 | TIME_LIMIT | 30.025 | OPTIMAL | 17.214 |
| rt_n300_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 300 | 2 | 480 | 360 | 20425 | 2e+06 | TIME_LIMIT | 30.347 | COLUMN_CAP |  |
| rt_n300_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 300 | 3 | 480 | 360 | 13392 | 2e+06 | TIME_LIMIT | 30.054 | COLUMN_CAP |  |
| rt_n400_m2_L360_s201 | TIME_LIMIT | AF hit the time limit | True | 400 | 2 | 360 | 270 | 36270 | 1.32e+06 | TIME_LIMIT | 30.11 | BUILD_LIMIT |  |
| rt_n400_m3_L360_s201 | TIME_LIMIT | AF hit the time limit | True | 400 | 3 | 360 | 270 | 23745 | 300000 | TIME_LIMIT | 30.381 | BUILD_LIMIT |  |
| rt_n400_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 400 | 3 | 480 | 360 | 23745 | 1.83e+06 | TIME_LIMIT | 30.745 | BUILD_LIMIT |  |
| rt_n500_m2_L360_s201 | TIME_LIMIT | AF hit the time limit | True | 500 | 2 | 360 | 270 | 56864 | 1.77e+06 | TIME_LIMIT | 30.092 | BUILD_LIMIT |  |
| rt_n500_m3_L360_s201 | TIME_LIMIT | AF hit the time limit | True | 500 | 3 | 360 | 270 | 37302 | 2e+06 | TIME_LIMIT | 30.734 | COLUMN_CAP |  |
| rt_n500_m2_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 500 | 2 | 480 | 360 | 56864 | 1.75e+06 | TIME_LIMIT | 30.132 | BUILD_LIMIT |  |
| rt_n500_m3_L480_s201 | TIME_LIMIT | AF hit the time limit | True | 500 | 3 | 480 | 360 | 37302 | 2e+06 | TIME_LIMIT | 30.11 | COLUMN_CAP |  |
