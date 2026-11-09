# Benchmark selection (Group M) - pilot stage

Source rows: `results/pilot.csv` (pilot limits). Written by `pilot/classify.py`. Pilot classes are PRELIMINARY:
at the pilot limit a hard instance and a time-limit instance look the same (Master Plan §10.3 step 1).

## Rule (fixed before the confirmation runs)
1. Classes from the plain AF and SP runs, first rule wins: NOT_BUILT (neither model built) -> TIME_LIMIT
   (a built plain model hit the limit) -> HARD (max solver time > 24 s at the final
   limits) -> MEDIUM (both optimal and times differ x10, or only one model built) -> EASY.
2. Confirmation candidates = every HARD, TIME_LIMIT and NOT_BUILT instance + 2 spares per EASY/MEDIUM class, at most 24 files, in increasing n, L, id.
3. Final selection (after the confirmation runs): within each class take candidates in increasing n, then L,
   then configuration id, up to the targets {'EASY': 4, 'MEDIUM': 5, 'HARD': 5, 'TIME_LIMIT': 6}; missing TIME_LIMIT places are filled with HARD.
4. No instance is hand-picked, replaced or removed after the final runs start.

## Preliminary classes: {'EASY': 2, 'MEDIUM': 1, 'HARD': 0, 'TIME_LIMIT': 20, 'NOT_BUILT': 1, 'UNUSABLE': 0}

| class | target | in this population |
|---|---|---|
| EASY | 4 | 2 |
| MEDIUM | 5 | 1 |
| HARD | 5 | 0 |
| TIME_LIMIT | 6 | 20 |

**WARNING:** too few EASY/MEDIUM instances in this population for the targets. Add smaller configurations to the candidate pool (same generator, same rule) and pilot them before the freeze; record the addition here.

## Confirmation candidates (24 files, 48 runs: plain AF and SP at the final limits)

| instance | class | why_candidate | reason | SP_not_built | n | m | L | W | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n50_m2_L360_s201 | EASY | spare | both fast / similar | False | 50 | 2 | 360 | 270 | 3718 | OPTIMAL | 0.095 | OPTIMAL | 0.0479999 |
| rt_n50_m3_L360_s201 | EASY | spare | both fast / similar | False | 50 | 3 | 360 | 270 | 1180 | OPTIMAL | 0.823 | OPTIMAL | 0.0309999 |
| rt_n50_m2_L600_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 50 | 2 | 600 | 450 | 14599 | TIME_LIMIT | 30.01 | OPTIMAL | 0.172 |
| rt_n50_m3_L600_s201 | MEDIUM | spare | SP faster by x43.6 | False | 50 | 3 | 600 | 450 | 9982 | OPTIMAL | 4.537 | OPTIMAL | 0.104 |
| rt_n100_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 100 | 2 | 480 | 360 | 297266 | TIME_LIMIT | 30.004 | OPTIMAL | 3.428 |
| rt_n100_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 100 | 3 | 480 | 360 | 63633 | TIME_LIMIT | 30.022 | OPTIMAL | 1.179 |
| rt_n100_m2_L600_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 100 | 2 | 600 | 450 | 2e+06 | TIME_LIMIT | 30.018 | COLUMN_CAP |  |
| rt_n100_m3_L600_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 100 | 3 | 600 | 450 | 298815 | TIME_LIMIT | 30.013 | OPTIMAL | 2.631 |
| rt_n200_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF/SP hit the time limit | False | 200 | 2 | 360 | 270 | 1.72403e+06 | TIME_LIMIT | 30.027 | TIME_LIMIT | 30.433 |
| rt_n200_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 200 | 3 | 360 | 270 | 113958 | TIME_LIMIT | 30.028 | OPTIMAL | 1.492 |
| rt_n200_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 200 | 2 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.045 | COLUMN_CAP |  |
| rt_n200_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 200 | 3 | 480 | 360 | 1.20719e+06 | TIME_LIMIT | 30.039 | OPTIMAL | 12.19 |
| rt_n300_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 2 | 360 | 270 | 2e+06 | TIME_LIMIT | 30.047 | COLUMN_CAP |  |
| rt_n300_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | False | 300 | 3 | 360 | 270 | 870192 | TIME_LIMIT | 30.025 | OPTIMAL | 17.214 |
| rt_n300_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 2 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.347 | COLUMN_CAP |  |
| rt_n300_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 300 | 3 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.054 | COLUMN_CAP |  |
| rt_n400_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 400 | 2 | 360 | 270 | 1.32e+06 | TIME_LIMIT | 30.11 | BUILD_LIMIT |  |
| rt_n400_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 400 | 3 | 360 | 270 | 300000 | TIME_LIMIT | 30.381 | BUILD_LIMIT |  |
| rt_n400_m2_L480_s201 | NOT_BUILT | recheck at 120 s | neither model built (AF:BUILD_LIMIT, SP:BUILD_LIMIT); recheck at the final limits | True | 400 | 2 | 480 | 360 | 190000 | BUILD_LIMIT |  | BUILD_LIMIT |  |
| rt_n400_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 400 | 3 | 480 | 360 | 1.83e+06 | TIME_LIMIT | 30.745 | BUILD_LIMIT |  |
| rt_n500_m2_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 2 | 360 | 270 | 1.77e+06 | TIME_LIMIT | 30.092 | BUILD_LIMIT |  |
| rt_n500_m3_L360_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 3 | 360 | 270 | 2e+06 | TIME_LIMIT | 30.734 | COLUMN_CAP |  |
| rt_n500_m2_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 2 | 480 | 360 | 1.75e+06 | TIME_LIMIT | 30.132 | BUILD_LIMIT |  |
| rt_n500_m3_L480_s201 | TIME_LIMIT | recheck at 120 s | AF hit the time limit | True | 500 | 3 | 480 | 360 | 2e+06 | TIME_LIMIT | 30.11 | COLUMN_CAP |  |

## Whole pilot population

| instance | class | reason | SP_not_built | n | m | L | W | n_arcs | n_duties | AF_status | AF_time | SP_status | SP_time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt_n50_m2_L360_s201 | EASY | both fast / similar | False | 50 | 2 | 360 | 270 | 560 | 3718 | OPTIMAL | 0.095 | OPTIMAL | 0.0479999 |
| rt_n50_m3_L360_s201 | EASY | both fast / similar | False | 50 | 3 | 360 | 270 | 386 | 1180 | OPTIMAL | 0.823 | OPTIMAL | 0.0309999 |
| rt_n50_m3_L600_s201 | MEDIUM | SP faster by x43.6 | False | 50 | 3 | 600 | 450 | 386 | 9982 | OPTIMAL | 4.537 | OPTIMAL | 0.104 |
| rt_n400_m2_L480_s201 | NOT_BUILT | neither model built (AF:BUILD_LIMIT, SP:BUILD_LIMIT); recheck at the final limits | True | 400 | 2 | 480 | 360 | 36270 | 190000 | BUILD_LIMIT |  | BUILD_LIMIT |  |
| rt_n50_m2_L600_s201 | TIME_LIMIT | AF hit the time limit | False | 50 | 2 | 600 | 450 | 560 | 14599 | TIME_LIMIT | 30.01 | OPTIMAL | 0.172 |
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
