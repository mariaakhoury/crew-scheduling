# B12 heuristic contribution - source `results/runs.csv`

- Instances with a heuristic: 15; proven optimum known for 10.
- LS equals the best known value on 2; median LS gap 4.99 % (exact on proven instances, upper bound otherwise).
- LS improved greedy on 2 of 15.
- H6 (start helps AF more than SP): **not confirmed** - median improvement AF 0.03 (15 pairs) vs SP 0.03 (10 pairs).

## Per model

model  pairs  comparable  median_improvement  min_improvement  max_improvement  win  tie  loss start_accepted  median_first_incumbent_ratio
   AF     15          15            0.025648        -0.844862         0.297296    2   10     3          15/15                      0.156246
   SP     15          10            0.026320        -0.393700         0.285723    0   10     0          10/10                      0.000000

## Did not help / not comparable (28 pairs)

            instance model     status   status_S          basis   improvement  wtl                                                                                                                 reason
rt_n100_m2_L600_s201    AF TIME_LIMIT TIME_LIMIT      final gap  2.628028e-14  tie time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
rt_n100_m3_L480_s201    AF TIME_LIMIT TIME_LIMIT      final gap -1.937984e-03  tie time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
 rt_n20_m2_L360_s201    AF    OPTIMAL    OPTIMAL           time  0.000000e+00  tie                                                       solved at the root node either way: the start had nothing to add
rt_n300_m3_L480_s201    AF TIME_LIMIT TIME_LIMIT      final gap  2.564813e-02  tie time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
 rt_n30_m3_L360_s201    AF    OPTIMAL    OPTIMAL           time  3.910600e-02  tie                                                                                         solved in under 1 s either way
 rt_n40_m2_L480_s201    AF    OPTIMAL    OPTIMAL           time  2.972956e-01  tie                                                       solved at the root node either way: the start had nothing to add
rt_n500_m2_L480_s201    AF TIME_LIMIT TIME_LIMIT      final gap  2.881381e-02  tie                                                       solved at the root node either way: the start had nothing to add
rt_n500_m3_L480_s201    AF TIME_LIMIT TIME_LIMIT      final gap  6.791379e-03  tie time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
 rt_n50_m2_L600_s201    AF TIME_LIMIT TIME_LIMIT      final gap -2.733333e-01 loss time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
 rt_n60_m2_L360_s201    AF    OPTIMAL    OPTIMAL           time  2.928289e-02  tie                                                                                         solved in under 1 s either way
 rt_n60_m2_L480_s201    AF    OPTIMAL    OPTIMAL           time -8.448618e-01 loss                                                                                                   check the Gurobi log
 rt_n60_m3_L360_s201    AF    OPTIMAL    OPTIMAL           time -3.426718e-01 loss                                                                                                   check the Gurobi log
 rt_n80_m2_L360_s201    AF TIME_LIMIT TIME_LIMIT      final gap  8.955224e-02  tie time limit either way: the start gave an incumbent early, but the bound (not the incumbent) is what keeps the gap open
rt_n100_m2_L600_s201    SP COLUMN_CAP COLUMN_CAP not comparable           NaN  n/a                                                                               not comparable (COLUMN_CAP / COLUMN_CAP)
rt_n100_m3_L480_s201    SP    OPTIMAL    OPTIMAL           time -5.409836e-02  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n20_m2_L360_s201    SP    OPTIMAL    OPTIMAL           time  0.000000e+00  tie                                                       solved at the root node either way: the start had nothing to add
rt_n300_m3_L480_s201    SP COLUMN_CAP COLUMN_CAP not comparable           NaN  n/a                                                                               not comparable (COLUMN_CAP / COLUMN_CAP)
 rt_n30_m3_L360_s201    SP    OPTIMAL    OPTIMAL           time  1.538349e-01  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n40_m2_L480_s201    SP    OPTIMAL    OPTIMAL           time  2.857233e-01  tie                                                       solved at the root node either way: the start had nothing to add
rt_n500_m2_L480_s201    SP COLUMN_CAP COLUMN_CAP not comparable           NaN  n/a                                                                               not comparable (COLUMN_CAP / COLUMN_CAP)
rt_n500_m3_L360_s201    SP COLUMN_CAP COLUMN_CAP not comparable           NaN  n/a                                                                               not comparable (COLUMN_CAP / COLUMN_CAP)
rt_n500_m3_L480_s201    SP COLUMN_CAP COLUMN_CAP not comparable           NaN  n/a                                                                               not comparable (COLUMN_CAP / COLUMN_CAP)
 rt_n50_m2_L600_s201    SP    OPTIMAL    OPTIMAL           time  9.090692e-02  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n50_m3_L600_s201    SP    OPTIMAL    OPTIMAL           time -1.384624e-01  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n60_m2_L360_s201    SP    OPTIMAL    OPTIMAL           time  1.607154e-01  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n60_m2_L480_s201    SP    OPTIMAL    OPTIMAL           time -3.937001e-01  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n60_m3_L360_s201    SP    OPTIMAL    OPTIMAL           time  5.264016e-02  tie                                                       solved at the root node either way: the start had nothing to add
 rt_n80_m2_L360_s201    SP    OPTIMAL    OPTIMAL           time  0.000000e+00  tie                                                       solved at the root node either way: the start had nothing to add
