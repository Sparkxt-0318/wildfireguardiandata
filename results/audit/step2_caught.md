# Step 2, track caught: recompute of results/CAUGHT_RESULTS.md (main at 3fc6ab0) from release caught-v0.1 only

Release files used (S/rel_v01/x/caught-v0.1/caught-v0.1/, inner SHA256SUMS all OK): `caught_labels_v0.1_{2018,2019,2020}.parquet`
(220,975 rows), `caught_states_v0.1_{2018,2019,2020}.parquet`, `heat_floors_m2.json`, `scar_pairs/`, `DATA_CARD.md`, `NOTES.md`.
Scripts: S/work_caught/scripts/ (`load.py`, `counts.py`, `geom_states.py`, `extras.py`, `floors.py`); outputs
S/work_caught/counts_out.txt, geom_out.txt, extras_out.txt.

## 1. Summary

Counted per distinct numeric value (a value repeated later in the text is counted once; a table cell counts once, a
"rate (CI)" pair counts once): **MATCH 282, MISMATCH 2, MISMATCH-MC 0, CANNOT RECOMPUTE 382, PARAMETER 25.**
**Mismatches:** (1) line 73: "PERIM in 1,126 of the 4,795 verified records" (S2). Among all 4,795 S2 verified records
2,528 carry PERIM; 1,126 is the count among the 1,648 verified records *with no standard label*. The numerator and the
denominator come from different sets. (The S3 equivalent, line 129, "5,169 of the 13,793", is correct over all verified.)
(2) lines 362-363: Landsat scar floor "5,277 m2". With the frozen formula (N_min 8, T 0.10, dNBR_ref 0.25, p 30 m) it
is 5,276.47 m2, which rounds to 5,276. The release field `scar_floor_m2` stores 5276.5, and rounding that again gives 5,277,
so this is a double-rounding slip of 1 m2. Everything recomputable on the headline page matches exactly. That covers:
the S1, S2 and S3 tables by class (records, standard label, no standard label, verified with Clopper-Pearson CI,
probable, record-only), the S3 by-year table, searched counts, the witness counts, the record-only reasons, and the
16-vertex disc (2.55 %). The S1 and S2 numbers are reproduced from the S3 release rows: the release has `slice` = "S3"
on every row, so there is no S1 or S2 column. S1 is selected as STATE == CA and FIRE_YEAR == 2020, and S2 as
FIRE_YEAR == 2020. The release contains no S1 or S2 run, so the claim that S2 and S1 came from separate runs equal to S3 cannot be tested
from the release (a side check against the repo's non-release `verified_S1.csv`/`verified_S2.csv` gives identical rid
sets: 378 and 4,795). **CANNOT RECOMPUTE (main groups):** all placebo counts and rates (C1, by slice and year; no
placebo rows are in the release, and the states files hold FOD record ids only); C2 sealed recall (the sealed truth
fires are not released: FRAP wildfire and Rx perimeters, NIFC perimeter history, the sealed split ids, per-truth-fire labels and
standard footprints, cluster cell x year ids, and `results/caught/C2_sealed_*.csv`, which is in the repo, not the
release); recall by fuel and the scar/mapped ratio by fuel (these need the dev and sealed truth runs and the WorldCover fuel at the
polygon point); scar floors by fuel (inputs T and dNBR medians come from the dev truth run); the downstream GOFER check (GOFER
v0.2 and wildfireguardian code are not in the release); all v0.2 numbers (caught-v0.2 is not v0.1); and wall times.

## 2. Table

Status counts per row are given as [n] when a row covers several values.

| line | quantity (short) | published | recomputed | status | source file and field / how |
|---|---|---|---|---|---|
| 3 | frozen commit | 530a3d5 | - | PARAMETER | |
| 8 | 95 % CI, 0.5-degree cell x year | - | - | PARAMETER [2] | |
| 17 | S1 records; searched; scar floor | 10,360; 4,037; 2,345 m2 | 10,360; 4,037; 2,345.1 | MATCH [3] | labels: STATE=CA & FIRE_YEAR=2020; `searched`; `scar_floor_m2` (s2, T=0.10) = 2345.1 |
| 20 | S1 wall time | 0.9 h | - | CANNOT RECOMPUTE | no run log in release |
| 24-31 | S1 table, 8 rows x 7 values (records, std, no-std, verified + CP CI, probable, record-only) | see file | identical in every cell (e.g. all: 10,360 / 397 / 9,963 / 92 (0.75-1.13) / 522 / 9,349) | MATCH [56] | `FIRE_SIZE_CLASS`, `std_label`, `tier`; CI = Clopper-Pearson (scipy beta) of verified / no-std |
| 33-34 | S1 headline verified no-std, by class | 92 (A1 B26 C45 D16 E3 G1) | same | MATCH [7] | as above |
| 37-38 | S1 placebo verified 9/3,526 0.26 % (0.12-0.48); 10/9,251 0.11 % (0.05-0.20); probable 178/3,526 5.05 % (4.35-5.82); dev rate 4.44 % | - | not in release (CP from the published k/n reproduces the intervals) | CANNOT RECOMPUTE [4] | needs placebo rows / S1_placebo.csv (repo only) and dev rounds |
| 39 | records with matched placebo 9,251 of 10,360 (89 %) | 9,251; 10,360; 89 % | 10,360 | MATCH [1], CANNOT [1] | 9,251 needs placebo data; 9,251/10,360 = 89.3 % |
| 39 | gates 1 %, 5 % | - | - | PARAMETER [2] | |
| 42-43 | S1 probable labels; searched windows; about 200 false | 633; 4,037; ~200 | 633; 4,037; 5 % x 4,037 = 202 | MATCH [3] | `tier`=probable (all, incl. std) |
| 48 | S2 records; searched | 74,530; 32,340 | 74,530; 32,340 | MATCH [2] | FIRE_YEAR=2020 |
| 48 | S2 matched placebos; searched placebos | 70,163; 30,992 | - | CANNOT RECOMPUTE [2] | no placebo rows |
| 52 | S2 wall time | 2.1 h; ~7 h | - | CANNOT RECOMPUTE [2] | |
| 56-63 | S2 table, 8 x 7 | see file | identical (all: 74,530 / 4,363 / 70,167 / 1,648 (2.24-2.46) / 7,128 / 61,391) | MATCH [56] | as S1 |
| 65-66 | S2 headline 1,648 by class | A5 B612 C765 D169 E90 F6 G1 | same | MATCH [8] | |
| 68-69 | S2 placebo verified 0.16 % (0.12-0.22), 0.08 % (0.06-0.10); probable 4.92 % (4.68-5.16) | - | - (CP from published k/n consistent) | CANNOT RECOMPUTE [3] | no placebo rows |
| 73 | S2 verified records | 4,795 | 4,795 | MATCH | `tier`=verified, 2020 |
| 73 | PERIM in 1,126 of the 4,795 verified | 1,126 of 4,795 | 2,528 of 4,795 (1,126 is of the 1,648 no-std verified) | **MISMATCH** | `witnesses` contains PERIM (same with `kinds` PERIMETER) |
| 74 | S2 probable labels; ~1,600 false | 8,344; ~1,600 | 8,344; 4.92 % x 32,340 = 1,591 | MATCH [2] | arithmetic on recomputed searched count |
| 79 | S3 records; searched | 220,975; 94,330 | 220,975; 94,330 | MATCH [2] | all rows |
| 79 | S3 matched placebos 209,000 (94.6 %); 91,224 searched | - | 209,000/220,975 = 94.58 % (arithmetic only) | CANNOT RECOMPUTE [3] | no placebo rows |
| 81 | S3 2020 rows equal S2 exactly | claim | every published S2 number reproduced from S3 2020 rows | (not counted) | S2 run not in release; see section 3 |
| 83 | S3 verified records | 13,793 | 13,793 | MATCH | |
| 83 | geometry 0.00005 deg / 5 decimals | - | - | PARAMETER | |
| 83 | S3 wall time | 6.7 h; ~14 h | - | CANNOT RECOMPUTE [2] | |
| 88-95 | S3 table, 8 x 7 | see file | identical (all: 220,975 / 13,467 / 207,508 / 4,343 (2.03-2.16) / 20,913 / 182,252; G: 540/525/15/1 (0.17-31.95)/10/4) | MATCH [56] | |
| 101-103 | S3 by year (records, std, no-std, verified + class split, probable, record-only, searched) | see file | identical (2018: 81,733 / 5,161 / 76,572 / 1,680 / 7,908 / 66,984 / 34,526; 2019: 64,712 / 3,943 / 60,769 / 1,015 / 5,877 / 53,877 / 27,464; 2020 as S2) | MATCH [40] | `FIRE_YEAR` |
| 105-106 | S3 headline 4,343 by class | A16 B1,522 C2,104 D449 E232 F19 G1 | same | MATCH [8] | |
| 106-107 | verified no-std resting on S2 scar / perimeter / HMS analyst / GOES | 4,001 / 2,113 / 1,212 / 1,039 | 4,001 / 2,113 / 1,212 / 1,039 | MATCH [4] | token in `witnesses` (restricted to agreeing `pairs`: 3,999 / 2,112 / 1,162 / 1,028) |
| 109-111 | S3 placebo verified 191/91,224 0.21 % (0.18-0.24); 205/209,000 0.10 % (0.09-0.11); by year 0.30, 0.14, 0.16 % | - | - (CP from published k/n consistent) | CANNOT RECOMPUTE [5] | no placebo rows |
| 113-115 | S3 probable placebo 4,837/91,224 5.30 % (5.16-5.45); by year 5.67, 5.28, 4.92 %; dev 4.44 % | - | - | CANNOT RECOMPUTE [5] | |
| 116-118 | S3 probable labels; searched | 24,930; 94,330 | 24,930; 94,330 | MATCH [2] | |
| 116-118 | 1 false per 19; ~5,000 false | - | 1/0.053 = 18.9; 5.3 % x 94,330 = 5,000 (arithmetic only; rate from placebo) | CANNOT RECOMPUTE [2] | |
| 121 | disc-geometry labels: record-only; probable smoke-only | 182,252; 410 | 182,252; 410 | MATCH [2] | `pixel_label`=False; probable with `kinds`=SMOKE = 410 |
| 122 | 16 vertices; 2.55 % less area | 16; 2.55 % | all 182,662 non-pixel geometries have 16 vertices; geodesic area / (pi r_m^2) = 0.97450 (1,500-row sample per year) | MATCH [2] | shapely + pyproj Geod |
| 122 | S1/S2 discs 256 vertices; 0.01 % less | 256; 0.01 % | 256-gon deficit 0.010 % (geometry) | MATCH [1] (0.01 %), CANNOT [1] (S1/S2 runs not released) | |
| 124-125 | code line 143; 2 % of radius | - | - | PARAMETER [2] | |
| 129 | PERIM in 5,169 of 13,793 verified | 5,169 / 13,793 | 5,169 / 13,793 | MATCH | `witnesses` PERIM |
| 130 | class-A record-only below floor | 105,065 of 105,381 | 105,065 of 105,381 | MATCH [2] | `reason`=below_floor |
| 131 | clear look nothing found, classes B-G | 56,469 | 56,469 (class A has 0) | MATCH | |
| 134 | C2 run time 21:48-22:53Z | - | - | CANNOT RECOMPUTE | |
| 134-140 | date, commit, 300 acres, mod 10 in 3-9, 250 m, +30 m, 2,000 resamples, 0.5 deg | - | - | PARAMETER [7] | |
| 145-150 | C2 sealed small-fire table, 6 rows (n, labelled, standard, diff + CI, verified-only, verified - std + CI, gate) | all 3711 / 0.639 / 0.306 / +0.333 (0.308-0.358) / 0.299 / -0.008 (-0.020 to 0.004); A 206 ... E 1 | - | CANNOT RECOMPUTE [35] | sealed truth set not released (FRAP/NIFC sealed perimeters, truth-run labels, standard footprints per truth fire, cluster ids; C2_sealed_primary_small.csv is repo-only). Arithmetic: differences equal labelled - standard per row; class n sum 206+1029+1857+618+1 = 3711 |
| 152 | class A "fires under 0.26 acre" | - | release: A max 0.25, B min 0.251 acres; line 365 says "under 0.25 acre" | PARAMETER (text inconsistency) | `FIRE_SIZE` |
| 153 | scar floor 2,345 m2 = 0.58 acre | 2,345; 0.58 | 2,345.1; 0.5795 | MATCH [2] | `scar_floor_m2`; formula |
| 160-161 | reference n 1,008, 0.940 vs 0.852; FACTS n 1,497, 0.816 vs 0.670 | - | - | CANNOT RECOMPUTE [6] | truth sets not released |
| 166-184 | downstream GOFER check: 28 fires, 6.2 % (0.6-22.1), 6.6 % (0.7-22.8), R 3.75 / 5.03 km, 70 labels, 31 at August Complex, table rows (5.7 %, 0 issue-hours, 50.9 % (31.5-70.2), 19.3 km, 6.1 %, 6.0 %, 39.9 % (22.0-60.1), 6.2 %), 20,161 and 20,077 fire-hours | - | - | CANNOT RECOMPUTE [23] | GOFER v0.2 and wildfireguardian research/kcf-margin are not in the release |
| 167 | 5 km, 5 h, 8 h | - | - | PARAMETER | |
| 181-182 | label interval at least one day; median 3 days; a quarter 50 days or more | >= 1 d; 3; 25 % >= 50 | S1 verified labels (n 378), inclusive days `label_t1 - label_t0 + 1`: min 1, median 3, share >= 50 days 25.1 % | MATCH [3] | assumes inclusive day count (exclusive: median 2) |
| 199 | citation years | - | - | PARAMETER | |
| 209, 214 | dev split mod 10 in 0-2; rule 0.2 / 0.25 / n >= 10 | - | - | PARAMETER [2] | |
| 218-226 | scar/mapped ratio by fuel, 9 rows x 7 (clear looks, scars found, median (quartiles), below 0.2 count, share, Wilson CI, inside median) | - | - (shares k/found consistent: 65/703 = 9.2 %, 105/360 = 29.2 %, 39/95 = 41.1 %, ...) | CANNOT RECOMPUTE [63] | needs dev truth fires, truth_dev_r3 run, WorldCover fuel |
| 229-232 | timber scar found in 57 % of clear looks vs 86 % grass | 57 %; 86 % | 360/628 = 57.3 %, 703/822 = 85.5 % (from published table) | CANNOT RECOMPUTE [2] | as above |
| 239 | N_min 8 | - | - | PARAMETER | |
| 245-250 | scar floor by fuel (T, dNBR median, m2, acre) x 6 | 2,335 / 5,253 / 2,569 / 5,781 / 2,968 / 6,679 m2 | formula on the printed rounded inputs: 2,336 / 5,255 / 2,571 / 5,786 / 2,969 / 6,681 (differences within input rounding) | CANNOT RECOMPUTE [24] | T and dNBR medians come from dev truth run (not released) |
| 257-276 | sealed recall by fuel, 20 rows x (n, labelled, standard, verified) | e.g. grass all 1650 / 0.762 / 0.292 / 0.316 | - (n sums: per fuel and per class add up to the C2 table: A 206, B 1029, C 1857, D 618, all 3711) | CANNOT RECOMPUTE [80] | sealed truth set + fuel at polygon point not released |
| 284-285 | v0.2 commits | - | - | PARAMETER | |
| 291-292 | 10-60 days, half the pixels | - | - | PARAMETER | |
| 293 | v0.2 record windows looked at | 15,584 | 15,584 | MATCH | v0.1 S3 probable with `scar_status`=scar (the v0.2 input set; derivable from v0.1) |
| 293 | v0.2 placebo windows | 3,698 | - | CANNOT RECOMPUTE | |
| 299-301 | v0.2 C1 table, 3 rows x 6 (searched placebos, v0.1 verified rate, v0.2 any, second only, persistence, both) | - | - | CANNOT RECOMPUTE [18] | placebos not in release; v0.2 not v0.1 |
| 304-306 | persistence 47 % / 34 %, second sensor 33 % / 10 % | - | - | CANNOT RECOMPUTE [4] | caught-v0.2 |
| 315-317 | v0.2 counts table: records, no-std, v0.1 verified, record-only | S1 10,360 / 9,963 / 92 / 9,349; S2 74,530 / 70,167 / 1,648 / 61,391; S3 220,975 / 207,508 / 4,343 / 182,252 | same | MATCH [12] | |
| 315-317 | v0.2 verified (any), second-sensor only, v0.2 probable | 275/176/339; 4,486/3,155/4,290; 13,538/9,419/11,718 | - (arithmetic: v0.1 probable no-std - (v0.2 verified - v0.1 verified) = 339 / 4,290 / 11,718, consistent) | CANNOT RECOMPUTE [9] | caught-v0.2 |
| 319 | v0.2 S3 by class (any route; second only) | A16 B7,648 ... | - | CANNOT RECOMPUTE [14] | caught-v0.2 |
| 324-326 | 1.80 % -> ~1,700; ~200 under v0.1; ~585 second sensor | - | arithmetic on 94,330 consistent (1,698; 198; 585) | CANNOT RECOMPUTE [4] | rates from placebo/v0.2 |
| 330-338 | v0.2 sealed set: 50, 795 (A211 B385 C129 D70; 736/59), 3,855, 3,061, 794, 1,500, tiers 179/229/387, lifted 121 (35/18/68), 27 | - | - | CANNOT RECOMPUTE [20] | v0.2 sealed set not in v0.1 |
| 344-348 | C2 v0.2 table, 5 rows x 7 | - | - | CANNOT RECOMPUTE [35] | |
| 356-357 | protocol subset 47 of 50, 3; recalls 0.319 / 0.064 / 0.085 / 0.149 / 0.234 | - | - | CANNOT RECOMPUTE [8] | |
| 362-363 | S2 scar floor 2,345 m2 (0.58 acre); Landsat 1.30 acres | 2,345; 0.58; 1.30 | 2,345.10; 0.5795; 5,276.47/4,046.86 = 1.304 | MATCH [3] | `scar_floor_m2` and formula (independent and repo `floor.scar_floor_m2(0.10, p, n_min=8)`) |
| 362 | Landsat scar floor | 5,277 m2 | 5,276.47 m2 -> 5,276 (release field 5276.5) | **MISMATCH** (rounding) | as above |
| 363 | T = 0.10 | - | - | PARAMETER | |
| 363-364 | by-fuel range 0.58-0.73 acre (S2), 1.30-1.65 (Landsat) | - | - | CANNOT RECOMPUTE [2] | dev truth inputs |
| 365 | class A under 0.25 acre | - | - | PARAMETER | |
| 375 | California 107, Maine 27 perimeters | - | - | CANNOT RECOMPUTE [2] | v0.2 sealed set |
| (release) | heat floors (heat_floors_m2.json): MODIS 1921.2 / 3421.6, VIIRS 327.5 / 65.4, AVHRR 3037.7 / 3516.8, GOES 4018.8 / 3489.8 m2 day/night | not quoted in CAUGHT_RESULTS.md | identical from repo code `firewitness.caught.run.heat_floors(0)` | (not counted; MATCH vs code) | repo code import, not independent |
| (release) | DATA_CARD counts 220,975 / 13,793 / 24,930 / 182,252 / 207,508 / 4,343 / 20,913 | - | same | (not counted; MATCH) | |

## 3. Data problems and observations

- **Integrity holds:** 220,975 rows, rid and FOD_ID unique, FIRE_YEAR equals the file year, every row has exactly one tier
  (verified 13,793, probable 24,930, record-only 182,252; no nulls), no record dropped relative to the stated totals.
  Every record-only row has a reason and no labelled row has one. Every verified row has at least one agreeing pair,
  and no probable row has a pair. FIRE_SIZE_CLASS agrees with FIRE_SIZE (NWCG bounds). `std_label` agrees with
  non-empty `std_witnesses`.
- **Slice identification:** `slice` is "S3" on every row, so there is no S1 or S2 flag. S1 = STATE CA & FIRE_YEAR 2020 and
  S2 = FIRE_YEAR 2020 reproduce every published S1 and S2 number exactly. The results text says S1 and S2 were separate runs (S1 drew
  256-vertex discs; S3 reused S2 checkpoints for 2020). The release cannot show that those runs gave the same rows, but
  the published S1/S2 tables are consistent with the S3 rows. A side check against the repo's non-release
  verified_S1.csv and verified_S2.csv also gives identical rid sets.
- **No placebo rows anywhere in the release.** The states files contain only FOD rids, all present in the label files. So
  every C1 number and the probable guard (the DATA_CARD's 5.30 % and 0.21 % included) depend on repo-only CSVs. Clopper-Pearson
  intervals recomputed from the published k/n do reproduce the published intervals.
- **One undocumented reason value:** FOD400626469 (WA 2020, class C, record-only) has `reason` = "no_clear_look (read
  error)" and `scar_status` = "error". The data card lists only four reasons.
- **Searched windows without three-state areas:** 3,484 searched rows (3,483 `scar_status` no_clear_look + the 1 error
  row) have NaN `fire_m2_disc`/`no_fire_m2_disc`/`unknown_m2_disc`, where "all unknown" would be expected.
- 519 probable rows list 2-3 kinds in `kinds` but have no agreeing pair. This is consistent with the declared
  dependencies or disagreement in place and time, not an error.
- Line 106 "rest on" counts match the `witnesses` column. Counting only agreeing independent `pairs` gives slightly
  lower numbers (3,999 / 2,112 / 1,162 / 1,028).
- The text uses two different class-A boundaries: line 152 says "under 0.26 acre" and line 365 says "under 0.25 acre". The data have A up to 0.25 and B
  from 0.251.
- The `split` column (dev/sealed) equals sha256(str(FOD_ID)) mod 10 in 0-2 on a 2,000-row sample (100 %).
- The C2 truth fires, recall by fuel and the dev fuel check cannot be checked at all from v0.1. No truth fire,
  perimeter or truth-run label is in the release.
