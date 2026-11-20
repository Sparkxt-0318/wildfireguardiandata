# ROUNDS_fuel

Dev areas only (10 tiles, 1,935 plots), map M22. Keep a change only if the F1 ratio rises and the F2 false-alarm share does not rise (n_c >= 25).
Protocol section 9. Numbers are pooled over the dev areas; interval = cluster bootstrap. The code hash of each run is in results/dev_<label>_M22.json.

| round | cause (read in dev wrong verdicts) | change | numbers (dev, M22, pooled) | decision |
|---|---|---|---|---|
| 0 | baseline | version 1 exactly as the protocol | F1 10.59 [8.29,13.58] n_c 64 (73% disagree) n_k 1615 (6.9%); F2 0.0098 (17 false alarms of 1743 agreeing plots, Wilson hi 0.0156); stale/consistent 1.60 [0.57,2.88] n_s 72; spatial placebo 0.57 [0.12,1.12] | gates F1 pass, F2 pass |
| 1 | 10 of the 17 false alarms were R1.9a: map says grass (GR), NLCD and WorldCover both say shrub, the plot has >=10 % shrub but grass >= 2x shrub, which the protocol crosswalk counts as compatible with GR | switch off R1.9a (grass -> shrub); keep R1.9b | F1 10.59 -> 10.60 (n_c 64 -> 39; share of contradicted plots that disagree 0.73 -> 0.82; interval [8.11,13.68]); F2 0.0098 -> 0.0040 (17 -> 7 false alarms) | KEPT (the F1 rise is within noise; the gain is in precision and F2) |
| 2 | R1.1 (timber without canopy) hits 14 plots with 93% disagreement; consistent timber cells with weak tree evidence (S=-2) may hold more | R1.1 max_S -3 -> -2 | F1 10.60 -> 10.71 (n_c 39->41, interval [8.30,13.74]); F2 0.0040 -> 0.0040 (7->7 false alarms) | KEPT |
| 3 | R1.7 (unburnable on vegetation) hits 7 plots at 86% disagreement; natural-vegetation share threshold 70 may be too strict | R1.7 wc_natural 70 -> 50 | F1 10.71 -> 10.86 (n_c 41->44, interval [8.42,13.67]); F2 0.0040 -> 0.0040 (7->7 false alarms) | KEPT |
| 4 | R1.9b (SH vs grass) hits 19 plots at 74% disagreement; the WorldCover grass share threshold may be too strict | R1.9 wc_lifeform 60 -> 50 (affects R1.9b only after round 1) | F1 10.86 -> 10.98 (n_c 44->45, interval [8.49,13.74]); F2 0.0040 -> 0.0040 (7->7 false alarms) | KEPT |
| 5 | R1.1 still hits 93% disagreement; weak tree evidence S=-1 (one layer shows some tree) may still be a timber class without canopy | R1.1 max_S -2 -> -1 | F1 10.98 -> 11.07 (n_c 45->47, interval [8.66,13.82]); F2 0.0040 -> 0.0040 (7->7 false alarms) | KEPT |
| 6 | R1.9b precision stayed high when its threshold was relaxed (round 4) | R1.9 wc_lifeform 50 -> 40 | F1 11.07 -> 10.83 (n_c 47->48, interval [8.41,13.59]); F2 0.0040 -> 0.0046 (7->8 false alarms) | REVERTED |
| 7 | R1.7 precision stayed high when relaxed (round 3) | R1.7 wc_natural 50 -> 30 | F1 11.07 -> 11.07 (n_c 47->47, interval [8.66,13.82]); F2 0.0040 -> 0.0040 (7->7 false alarms) | REVERTED |
| 8 | cells with only 2 available independent layers are never judged by R1.1 | R1.1 min_n 3 -> 2 | F1 11.07 -> 11.07 (n_c 47->47, interval [8.66,13.82]); F2 0.0040 -> 0.0040 (7->7 false alarms) | REVERTED |
| 9 | R1.2 (non-timber under dense forest) rarely fires in dev (interior West); thresholds may be too strict | R1.2 tcc_min 50->40 and canopy max 15->10 m (one rule, two thresholds) | F1 11.07 -> 10.41 (n_c 47->50, interval [7.94,13.07]); F2 0.0040 -> 0.0057 (7->10 false alarms) | REVERTED |
| 10 | R1.9b requires TCC<5; shrubland with sparse tree cover is excluded | R1.9 tcc_lt 5 -> 10 | F1 11.07 -> 11.19 (n_c 47->48, interval [8.78,14.01]); F2 0.0040 -> 0.0040 (7->7 false alarms) | KEPT |
| 11 | R1.6 (burnable on bare ground) fires on few plots; bare share threshold 70 may be too strict | R1.6 wc_bare 70 -> 50 | F1 11.19 -> 11.19 (n_c 48->48, interval [8.78,14.01]); F2 0.0040 -> 0.0040 (7->7 false alarms) | REVERTED |
| 12 | stale cells (S1 mostly) disagree with plots only slightly more than consistent ones; S2 tree-cover-loss rule may miss sparse woodland loss | S2 tc2000_min 25 -> 10 | F1 11.19 -> 11.19 (n_c 48->48, interval [8.78,14.01]); F2 0.0040 -> 0.0040 (7->7 false alarms) | REVERTED |
