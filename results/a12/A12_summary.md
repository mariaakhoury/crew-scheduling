# A12 model strength - source `results/runs.csv`

- Chart 1 uses the **LP** gap.
- Q22, LP(AF) <= LP(SP): holds on all 10 instances.
- Q21 / H2, naive vs tight big-M: naive never stronger on all 15 instances; largest difference 1.8e-11.

## Per model

model  instances  built  median_lp_gap_pct  median_root_gap_pct  median_nodes  median_build_s  median_solve_s
   AF         15     15          12.031512            10.526316        2983.0        0.055921      120.005436
   SP         15     10           0.000000             0.000000           1.0        0.091019        0.057935

## Naive vs tight big-M (A8)

                      LP tight  LP naive  difference  gap tight %  gap naive %  Q21 ok
instance                                                                              
rt_n100_m2_L600_s201    7593.0    7593.0        -0.0        12.03        12.03    True
rt_n100_m3_L480_s201    7635.5    7635.5         0.0        14.65        14.65    True
rt_n20_m2_L360_s201     2233.0    2233.0         0.0         1.89         1.89    True
rt_n300_m3_L480_s201   21093.5   21093.5         0.0        17.71        17.71    True
rt_n30_m3_L360_s201     3138.0    3138.0         0.0        11.44        11.44    True
rt_n40_m2_L480_s201     3836.5    3836.5         0.0         9.46         9.46    True
rt_n500_m2_L480_s201   27184.0   27184.0        -0.0        23.08        23.08    True
rt_n500_m3_L360_s201   32867.5   32867.5         0.0        24.27        24.27    True
rt_n500_m3_L480_s201   32867.5   32867.5         0.0        18.76        18.76    True
rt_n50_m2_L600_s201     4395.0    4395.0         0.0         8.03         8.03    True
rt_n50_m3_L600_s201     4801.0    4801.0         0.0         5.38         5.38    True
rt_n60_m2_L360_s201     4881.5    4881.5         0.0         8.33         8.33    True
rt_n60_m2_L480_s201     4881.5    4881.5         0.0         8.23         8.23    True
rt_n60_m3_L360_s201     5077.0    5077.0         0.0        15.84        15.84    True
rt_n80_m2_L360_s201     6114.0    6114.0         0.0        12.72        12.72    True
