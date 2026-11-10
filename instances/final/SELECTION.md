# Benchmark selection (Group M)

Source rows: `results/confirm.csv` (stage: confirm). Written by `pilot/classify.py`.

## Rule (fixed before the confirmation runs)
1. Classes from the plain AF and SP runs, first rule wins: TIME_LIMIT (a built plain model hit the limit) ->
   HARD (max solver time > 24 s) -> MEDIUM (both optimal and times differ x10, or only one
   model built) -> EASY.
2. Within each class, candidates are ordered by (n, L, configuration id) and the targets
   {'EASY': 4, 'MEDIUM': 5, 'HARD': 5, 'TIME_LIMIT': 6} are taken at evenly spaced positions (spread rule, issue #1, 9 Nov); at least
   2 selected instances carry SP_not_built. Missing TIME_LIMIT places are filled with HARD.
   If fewer than 15 are selected, the remaining places are filled from the unused TIME_LIMIT, then
   HARD, then EASY instances with the spread rule (column selected_as = 'fill-up to 15').
3. No instance is hand-picked, replaced or removed after the final runs start.

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

## Selected instances

Counts: {'EASY': 4, 'MEDIUM': 2, 'HARD': 1, 'TIME_LIMIT': 8, 'NOT_BUILT': 0, 'UNCONFIRMED': 0, 'UNUSABLE': 0} (total 15); SP_not_built inside the classes: 5.

| class | target | selected |
|---|---|---|
| EASY | 4 | 4 |
| MEDIUM | 5 | 2 |
| HARD | 5 | 1 |
| TIME_LIMIT | 6 | 8 |

**Fill-up used:** 2 place(s), taken from TIME_LIMIT (2), because these classes had fewer instances than their targets: MEDIUM 2/5, HARD 1/5. The course minimum of 15 instances is therefore met with a heavier share of the classes that had spare instances; the results discussion reports this mix.


Classes come from the confirmation runs at the final limits; instances that were not re-run keep their pilot class only if it is EASY or a both-optimal MEDIUM (column class_source).

| instance | class | selected_as | class_source | reason | SP_not_built | n | m | L | W | n_arcs | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n20_m2_L360_s201 | EASY | class target | confirmation | both fast / similar | False | 20 | 2 | 360 | 270 | 84 | 371 | OPTIMAL | 0 | OPTIMAL | 0.0150001 |
| rt_n30_m3_L360_s201 | EASY | class target | pilot (both solved below the hard threshold) | both fast / similar | False | 30 | 3 | 360 | 270 | 143 | 525 | OPTIMAL | 0.146 | OPTIMAL | 0.0120001 |
| rt_n40_m2_L480_s201 | EASY | class target | pilot (both solved below the hard threshold) | both fast / similar | False | 40 | 2 | 480 | 360 | 350 | 922 | OPTIMAL | 0.04 | OPTIMAL | 0.0280001 |
| rt_n50_m2_L600_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | False | 50 | 2 | 600 | 450 | 560 | 14599 | TIME_LIMIT | 120.006 | OPTIMAL | 0.111 |
| rt_n50_m3_L600_s201 | MEDIUM | class target | confirmation | SP faster by x35.3 | False | 50 | 3 | 600 | 450 | 386 | 9982 | OPTIMAL | 3.525 | OPTIMAL | 0.0640001 |
| rt_n60_m2_L360_s201 | EASY | class target | confirmation | both fast / similar | False | 60 | 2 | 360 | 270 | 818 | 6650 | OPTIMAL | 0.707 | OPTIMAL | 0.0469999 |
| rt_n60_m3_L360_s201 | MEDIUM | class target | confirmation | SP faster by x66.7 | False | 60 | 3 | 360 | 270 | 559 | 1911 | OPTIMAL | 6.666 | OPTIMAL | 0.0189998 |
| rt_n60_m2_L480_s201 | HARD | class target | confirmation | max solver time 38.6 s > 24 s | False | 60 | 2 | 480 | 360 | 818 | 16064 | OPTIMAL | 38.588 | OPTIMAL | 0.117 |
| rt_n80_m2_L360_s201 | TIME_LIMIT | fill-up to 15 | confirmation | AF hit the time limit | False | 80 | 2 | 360 | 270 | 1456 | 22644 | TIME_LIMIT | 120.03 | OPTIMAL | 0.141 |
| rt_n100_m3_L480_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | False | 100 | 3 | 480 | 360 | 1539 | 63633 | TIME_LIMIT | 120.025 | OPTIMAL | 0.598 |
| rt_n100_m2_L600_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | True | 100 | 2 | 600 | 450 | 2245 | 2e+06 | TIME_LIMIT | 120.035 | COLUMN_CAP |  |
| rt_n300_m3_L480_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | True | 300 | 3 | 480 | 360 | 13392 | 2e+06 | TIME_LIMIT | 120.299 | COLUMN_CAP |  |
| rt_n500_m3_L360_s201 | TIME_LIMIT | fill-up to 15 | confirmation | AF hit the time limit | True | 500 | 3 | 360 | 270 | 37302 | 2e+06 | TIME_LIMIT | 120.078 | COLUMN_CAP |  |
| rt_n500_m2_L480_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | True | 500 | 2 | 480 | 360 | 56864 | 2e+06 | TIME_LIMIT | 120.227 | COLUMN_CAP |  |
| rt_n500_m3_L480_s201 | TIME_LIMIT | class target | confirmation | AF hit the time limit | True | 500 | 3 | 480 | 360 | 37302 | 2e+06 | TIME_LIMIT | 120.087 | COLUMN_CAP |  |

## Every candidate considered

| instance | class | class_source | reason | SP_not_built | n | m | L | W | n_arcs | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n20_m2_L360_s201 | EASY | confirmation | both fast / similar | False | 20 | 2 | 360 | 270 | 84 | 371 | OPTIMAL | 0 | OPTIMAL | 0.0150001 |
| rt_n20_m3_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 20 | 3 | 360 | 270 | 66 | 224 | OPTIMAL | 0.049 | OPTIMAL | 0.0079999 |
| rt_n20_m2_L480_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 20 | 2 | 480 | 360 | 84 | 475 | OPTIMAL | 0.00899982 | OPTIMAL | 0.017 |
| rt_n30_m2_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 30 | 2 | 360 | 270 | 199 | 442 | OPTIMAL | 0.0109999 | OPTIMAL | 0.0140002 |
| rt_n30_m3_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 30 | 3 | 360 | 270 | 143 | 525 | OPTIMAL | 0.146 | OPTIMAL | 0.0120001 |
| rt_n30_m2_L480_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 30 | 2 | 480 | 360 | 199 | 558 | OPTIMAL | 0.0150001 | OPTIMAL | 0.0140002 |
| rt_n30_m3_L480_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 30 | 3 | 480 | 360 | 143 | 1563 | OPTIMAL | 0.0349998 | OPTIMAL | 0.017 |
| rt_n40_m2_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 40 | 2 | 360 | 270 | 350 | 792 | OPTIMAL | 0.0159998 | OPTIMAL | 0.0249999 |
| rt_n40_m3_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 40 | 3 | 360 | 270 | 245 | 854 | OPTIMAL | 0.288 | OPTIMAL | 0.016 |
| rt_n40_m2_L480_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 40 | 2 | 480 | 360 | 350 | 922 | OPTIMAL | 0.04 | OPTIMAL | 0.0280001 |
| rt_n40_m3_L480_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 40 | 3 | 480 | 360 | 245 | 2678 | OPTIMAL | 0.202 | OPTIMAL | 0.023 |
| rt_n50_m2_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 50 | 2 | 360 | 270 | 560 | 3718 | OPTIMAL | 0.095 | OPTIMAL | 0.0479999 |
| rt_n50_m3_L360_s201 | EASY | pilot (both solved below the hard threshold) | both fast / similar | False | 50 | 3 | 360 | 270 | 386 | 1180 | OPTIMAL | 0.823 | OPTIMAL | 0.0309999 |
| rt_n60_m2_L360_s201 | EASY | confirmation | both fast / similar | False | 60 | 2 | 360 | 270 | 818 | 6650 | OPTIMAL | 0.707 | OPTIMAL | 0.0469999 |
| rt_n60_m2_L480_s201 | HARD | confirmation | max solver time 38.6 s > 24 s | False | 60 | 2 | 480 | 360 | 818 | 16064 | OPTIMAL | 38.588 | OPTIMAL | 0.117 |
| rt_n50_m3_L600_s201 | MEDIUM | confirmation | SP faster by x35.3 | False | 50 | 3 | 600 | 450 | 386 | 9982 | OPTIMAL | 3.525 | OPTIMAL | 0.0640001 |
| rt_n60_m3_L360_s201 | MEDIUM | confirmation | SP faster by x66.7 | False | 60 | 3 | 360 | 270 | 559 | 1911 | OPTIMAL | 6.666 | OPTIMAL | 0.0189998 |
| rt_n50_m2_L600_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 50 | 2 | 600 | 450 | 560 | 14599 | TIME_LIMIT | 120.006 | OPTIMAL | 0.111 |
| rt_n80_m2_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 80 | 2 | 360 | 270 | 1456 | 22644 | TIME_LIMIT | 120.03 | OPTIMAL | 0.141 |
| rt_n80_m3_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 80 | 3 | 360 | 270 | 981 | 5044 | TIME_LIMIT | 120 | OPTIMAL | 0.0480001 |
| rt_n80_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 80 | 3 | 480 | 360 | 981 | 22968 | TIME_LIMIT | 120.018 | OPTIMAL | 0.174 |
| rt_n100_m2_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 100 | 2 | 480 | 360 | 2245 | 297266 | TIME_LIMIT | 120.028 | OPTIMAL | 3.747 |
| rt_n100_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 100 | 3 | 480 | 360 | 1539 | 63633 | TIME_LIMIT | 120.025 | OPTIMAL | 0.598 |
| rt_n100_m2_L600_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 100 | 2 | 600 | 450 | 2245 | 2e+06 | TIME_LIMIT | 120.035 | COLUMN_CAP |  |
| rt_n200_m2_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 200 | 2 | 360 | 270 | 9009 | 1.72403e+06 | TIME_LIMIT | 120.064 | OPTIMAL | 64.028 |
| rt_n200_m3_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 200 | 3 | 360 | 270 | 5993 | 113958 | TIME_LIMIT | 120.031 | OPTIMAL | 0.924 |
| rt_n200_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | False | 200 | 3 | 480 | 360 | 5993 | 1.20719e+06 | TIME_LIMIT | 120.021 | OPTIMAL | 9.649 |
| rt_n300_m2_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 300 | 2 | 360 | 270 | 20425 | 2e+06 | TIME_LIMIT | 120.096 | COLUMN_CAP |  |
| rt_n300_m2_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 300 | 2 | 480 | 360 | 20425 | 2e+06 | TIME_LIMIT | 120.046 | COLUMN_CAP |  |
| rt_n300_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 300 | 3 | 480 | 360 | 13392 | 2e+06 | TIME_LIMIT | 120.299 | COLUMN_CAP |  |
| rt_n400_m2_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 400 | 2 | 360 | 270 | 36270 | 2e+06 | TIME_LIMIT | 120.132 | COLUMN_CAP |  |
| rt_n400_m2_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 400 | 2 | 480 | 360 | 36270 | 2e+06 | TIME_LIMIT | 120.096 | COLUMN_CAP |  |
| rt_n400_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 400 | 3 | 480 | 360 | 23745 | 2e+06 | TIME_LIMIT | 120.082 | COLUMN_CAP |  |
| rt_n500_m3_L360_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 500 | 3 | 360 | 270 | 37302 | 2e+06 | TIME_LIMIT | 120.078 | COLUMN_CAP |  |
| rt_n500_m2_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 500 | 2 | 480 | 360 | 56864 | 2e+06 | TIME_LIMIT | 120.227 | COLUMN_CAP |  |
| rt_n500_m3_L480_s201 | TIME_LIMIT | confirmation | AF hit the time limit | True | 500 | 3 | 480 | 360 | 37302 | 2e+06 | TIME_LIMIT | 120.087 | COLUMN_CAP |  |
| rt_n60_m3_L480_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | False | 60 | 3 | 480 | 360 | 559 | 6974 | TIME_LIMIT | 30.001 | OPTIMAL | 0.075 |
| rt_n80_m2_L480_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | False | 80 | 2 | 480 | 360 | 1456 | 98476 | TIME_LIMIT | 30.023 | OPTIMAL | 1.142 |
| rt_n100_m3_L600_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | False | 100 | 3 | 600 | 450 | 1539 | 298815 | TIME_LIMIT | 30.013 | OPTIMAL | 2.631 |
| rt_n200_m2_L480_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | True | 200 | 2 | 480 | 360 | 9009 | 2e+06 | TIME_LIMIT | 30.045 | COLUMN_CAP |  |
| rt_n300_m3_L360_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | False | 300 | 3 | 360 | 270 | 13392 | 870192 | TIME_LIMIT | 30.025 | OPTIMAL | 17.214 |
| rt_n400_m3_L360_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | True | 400 | 3 | 360 | 270 | 23745 | 300000 | TIME_LIMIT | 30.381 | BUILD_LIMIT |  |
| rt_n500_m2_L360_s201 | UNCONFIRMED | pilot only | not confirmed at the final limits (pilot: TIME_LIMIT) | True | 500 | 2 | 360 | 270 | 56864 | 1.77e+06 | TIME_LIMIT | 30.092 | BUILD_LIMIT |  |
