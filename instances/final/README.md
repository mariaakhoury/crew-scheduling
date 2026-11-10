# Final benchmark (Group M, frozen)

Generator(s): routes (`crew.instance.make_instance`, Member A; see its docstring for the model of a
timetable). Trips longer than W are redrawn, so every instance is feasible (one driver per trip is legal).
Each file stores every generator argument in `params` and its seed, so it can be rebuilt exactly.

## How sizes and parameters were chosen
- n from 20 to 500 trips; m in [2, 3] terminals; L in [360, 480, 600] min; W/L in [0.75].
- Costs are frozen for every instance (config.py): F = $300.00 per duty, c = $0.50 per paid minute, tau = 10 min.
- Instances were selected from the pilot population by the written rule in SELECTION.md (no hand-picking).
- What makes an instance hard: more trips per duty (larger L, W) makes |P| explode; more connections per
  trip (denser timetable, fewer terminals) and larger n make both models bigger.

## Instances

| name | n | m | L | W | arcs | arcs/trip | trips/duty (ref) | reference cost | seed | sha256 (first 12) |
|---|---|---|---|---|---|---|---|---|---|---|
| rt_n20_m2_L360_s201 | 20 | 2 | 360 | 270 | 84 | 4.2 | 3.33 | 2276.0 | 201 | fa1cf4e31b4b |
| rt_n30_m3_L360_s201 | 30 | 3 | 360 | 270 | 143 | 4.77 | 3.33 | 3641.5 | 201 | 5fd56175b1fe |
| rt_n40_m2_L480_s201 | 40 | 2 | 480 | 360 | 350 | 8.75 | 3.64 | 4237.5 | 201 | b1c4c6bc80b6 |
| rt_n50_m2_L600_s201 | 50 | 2 | 600 | 450 | 560 | 11.2 | 4.17 | 5319.5 | 201 | 9825ea8cc66f |
| rt_n50_m3_L600_s201 | 50 | 3 | 600 | 450 | 386 | 7.72 | 4.17 | 5529.5 | 201 | fcf912b0fe6e |
| rt_n60_m2_L360_s201 | 60 | 2 | 360 | 270 | 818 | 13.63 | 4.62 | 5512.0 | 201 | e0ce41e0f597 |
| rt_n60_m3_L360_s201 | 60 | 3 | 360 | 270 | 559 | 9.32 | 4.0 | 6349.5 | 201 | 2488d16978c0 |
| rt_n60_m2_L480_s201 | 60 | 2 | 480 | 360 | 818 | 13.63 | 4.62 | 5423.5 | 201 | b68ec1a60d94 |
| rt_n80_m2_L360_s201 | 80 | 2 | 360 | 270 | 1456 | 18.2 | 4.71 | 7145.5 | 201 | 81f1472c0f48 |
| rt_n100_m3_L480_s201 | 100 | 3 | 480 | 360 | 1539 | 15.39 | 5.0 | 9116.5 | 201 | 7ae29307b138 |
| rt_n100_m2_L600_s201 | 100 | 2 | 600 | 450 | 2245 | 22.45 | 4.76 | 9306.5 | 201 | 9d44c4412e06 |
| rt_n300_m3_L480_s201 | 300 | 3 | 480 | 360 | 13392 | 44.64 | 5.36 | 26286.5 | 201 | cb74a1554248 |
| rt_n500_m3_L360_s201 | 500 | 3 | 360 | 270 | 37302 | 74.6 | 5.1 | 44476.5 | 201 | a560c05a255e |
| rt_n500_m2_L480_s201 | 500 | 2 | 480 | 360 | 56864 | 113.73 | 6.49 | 35941.0 | 201 | 0cf66d1fa441 |
| rt_n500_m3_L480_s201 | 500 | 3 | 480 | 360 | 37302 | 74.6 | 5.88 | 41013.5 | 201 | b74e19884435 |

Full generator parameters are stored in each file's `params` field; full hashes in MANIFEST.csv.
