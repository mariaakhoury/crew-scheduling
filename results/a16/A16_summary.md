# A16 performance profiles - source `results/runs.csv`, metric: end_to_end time

## Per method

        runs  solved  fastest_on  solved_within_120s_end_to_end  sgm_end_to_end_s
method                                                                           
AF        15       7           0                              7         55.991534
AF+S      15       7           0                              7         58.521591
SP        15      10           8                             10         19.622311
SP+S      15      10           2                             10         19.681338

## Win / tie / loss

   A    B  A_wins  ties  A_losses
  AF AF+S       2    12         1
  AF   SP       0     9         6
  AF SP+S       0     9         6
AF+S   SP       0     9         6
AF+S SP+S       0     9         6
  SP SP+S       0    15         0
