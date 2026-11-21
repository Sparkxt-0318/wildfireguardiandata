# Downstream check: fixed reach margin vs verified_S1 labels

**Commands.** GOFER.zip fetched from the Zenodo URL in `resources.json` (sha256 96eca2e1... matches) into `/home/user/wildfire 3 (1)/firewitness_raw/downstream/`. Ran the repo's `score_gofer.py` unchanged, then the repo's `calibrate.lofo / summarise_lofo / conformal_R` (class "all", alpha 0.10). The label step is `scratchpad/downstream/labels_check.py`, which reuses the repo's `component_reach` and 5 km rule. Numbers are in `downstream_numbers.csv`. No repo or data files were modified.

**Baseline: reproduced.** 28 fires, LOFO miss (fire-weighted, Clopper-Pearson 95%): 5 h R = 3.75 km, 6.2% [0.6, 22.1]; 8 h R = 5.03 km, 6.6% [0.7, 22.8]. Both match the published values. Fixed R applied to all 28 fires: 5.7% (5 h) and 6.0% (8 h).

**Method.** Labels were rasterised (cell-centre) onto each fire's 375 m grid, padded by 6 km. Their cells are added to the newly burned set N when they are not already in K_t. Components of N more than 5 km from K_t are dropped, as in the repo. Label intervals run from label_t0 00:00 to label_t1 24:00 America/Los_Angeles, converted to UTC.

| h | version | fixed R: miss [95% CI] | re-derived R (km): LOFO miss |
|---|---|---|---|
| 5 | baseline | 5.7% [0.5, 21.4] | 3.75: 6.2% |
| 5 | (a) lower | 5.7% (unchanged) | 3.75: 6.2% |
| 5 | (b) upper | **50.9%** [31.5, 70.2] | 19.29: 6.1% |
| 8 | baseline | 6.0% [0.5, 21.9] | 5.03: 6.6% |
| 8 | (a) lower | 6.0% (unchanged) | 5.03: 6.6% |
| 8 | (b) upper | **39.9%** [22.0, 60.1] | 19.29: 6.2% |

n = 28 fires, 20,161 (5 h) and 20,077 (8 h) fire-hours.

**What changed.**
- Lower bound: no (fire, issue-hour) cell changed. The result is empty by construction. Every label interval is at least 24 h, so none can lie inside a 5 h or 8 h window.
- Upper bound: 9,313 of 20,161 cells changed at 5 h and 9,222 of 20,077 at 8 h, across 15 fires. Of these, 8,835 (5 h) and 6,338 (8 h) newly exceed the published R.
- 70 labels lie within 5 km of some GOFER fire's final footprint during that fire's span. 64 of them add cells under the upper bound. Zero add cells under the lower bound. August Complex alone has 31.

**What it does not show.**
- The upper bound is not a realistic estimate. Median label interval is 3 days and 25% run 50 days or longer. A label is therefore treated as burning in every window it overlaps. That puts cells with unknown hour of burning into thousands of windows, and the rise to 40-51% is mostly this artefact.
- Without hour-level timing, the data cannot say whether the margin fails. The truth lies somewhere between "no change" and the upper bound, and neither is informative.
- The re-derived R (19.3 km) is simply the margin the upper-bound assumption would require. It is not a recommended value.
- Rasterisation is cell-centre, so sub-cell labels may vanish. Labels may also be a separate or earlier fire inside the 5 km zone.
- n = 28 fires, wide intervals, one random-hour calibration. The labels are mostly small fires outside GOFER's tracked fires.
