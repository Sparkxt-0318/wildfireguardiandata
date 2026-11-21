# CAUGHT results (track 50): recorded fires that satellite labels missed

Protocol: `protocol/CAUGHT_PROTOCOL.md` (fixed before results; amendment A1 before any result). Rules frozen at
commit 530a3d5 after the dev rounds in `results/ROUNDS_caught.md`. Tables: `results/caught/`. Records: FPA FOD 7th
edition. Standard label: MODIS C6.1 and VIIRS S-NPP / NOAA-20 375 m active fire (FIRMS archive), MCD64A1, MTBS.
FireCCI51 was not checked (host unreachable, DECISIONS D-502).

Every number below has its n, a 95 % interval (Clopper-Pearson for shares; paired cluster bootstrap over
0.5-degree cell x year for recall differences), the file it comes from, and what it does not show.

## Headline

(filled per slice as each slice completes)

## Slice S1: California 2020 (complete)

10,360 FPA FOD records; 4,037 searched with imagery (the rest are below the 2,345 m2 scar floor or too uncertain in
location; heat evidence was still matched for all). Source: `results/caught/S1_headline.csv`,
`S1_placebo.csv`, `S1_record_only_reasons.csv`, `S1_witnesses.csv`, `verified_S1.csv`, `states_S1.parquet`.
Wall time 0.9 h.

| class | records | standard label | no standard label | of these, now verified (95 % CI of share) | now probable | record-only |
|---|---|---|---|---|---|---|
| A | 5,450 | 71 | 5,379 | **1** (0.00-0.10 % of no-label) | 134 | 5,244 |
| B | 4,240 | 103 | 4,137 | **26** (0.41-0.92 % of no-label) | 315 | 3,796 |
| C | 404 | 70 | 334 | **45** (10.00-17.61 % of no-label) | 51 | 238 |
| D | 111 | 34 | 77 | **16** (12.37-31.54 % of no-label) | 11 | 50 |
| E | 55 | 32 | 23 | **3** (2.78-33.59 % of no-label) | 6 | 14 |
| F | 48 | 37 | 11 | **0** (0.00-28.49 % of no-label) | 4 | 7 |
| G | 52 | 50 | 2 | **1** (1.26-98.74 % of no-label) | 1 | 0 |
| all | 10,360 | 397 | 9,963 | **92** (0.75-1.13 % of no-label) | 522 | 9,349 |

**Headline S1: 92 recorded fires with no standard label now carry a verified label** (class A 1, B 26,
C 45, D 16, E 3, G 1). Verified fires with no standard label rest mostly on a Sentinel-2 scar plus an agency
perimeter, HMS analyst or GOES point, or HMS smoke (`S1_witnesses.csv`).

**C1 placebo (S1):** verified 9 / 3,526 = 0.26 % (0.12-0.48) of searched placebos, 10 / 9,251 = 0.11 % (0.05-0.20) of all
matched placebos: **passes** (<= 1 %). Probable 178 / 3,526 = 5.05 % (4.35-5.82) of searched placebos: **fails this
track's own 5 % guard by a hair** (the dev rate was 4.44 %). 9,251 of 10,360 records got a matched placebo (89 %).

What S1 does not show: a verified label rests on agreement of two kinds in place and time, not on proof the record's
area or cause is right; probable labels carry a placebo-measured false rate near 5 %, so on the order of 200 of the 633
probable S1 labels (5 % of 4,037 searched windows) can be expected to be false; a few placebo windows hold FIRMS detections, i.e. real fires no
agency recorded, which count here as false positives.

## Slice S2: all US 2020 (complete; addition 2026-11-21T06:45Z, frozen v0.1 rules)

74,530 FPA FOD records; 32,340 searched with imagery; 70,163 matched placebos (30,992 searched). DNB night look only
inside California (protocol A1). Source: `results/caught/S2_headline.csv`, `S2_placebo.csv`,
`S2_record_only_reasons.csv`, `S2_witnesses.csv`, `S2_summary.json`, `verified_S2.csv`. The run survived three
container restarts by resuming from its checkpoints (DECISIONS D-512, D-513); wall time of the last resume
2.1 h, about 7 h in all.

| class | records | standard label | no standard label | of these, now verified (95 % CI of share) | now probable | record-only |
|---|---|---|---|---|---|---|
| A | 35,665 | 303 | 35,362 | **5** (0.00-0.03 % of no-label) | 869 | 34,488 |
| B | 30,808 | 1,327 | 29,481 | **612** (1.92-2.25 % of no-label) | 4,436 | 24,433 |
| C | 5,960 | 1,400 | 4,560 | **765** (15.70-17.89 % of no-label) | 1,597 | 2,198 |
| D | 996 | 485 | 511 | **169** (29.00-37.34 % of no-label) | 153 | 189 |
| E | 562 | 357 | 205 | **90** (37.00-50.99 % of no-label) | 53 | 62 |
| F | 343 | 299 | 44 | **6** (5.17-27.35 % of no-label) | 18 | 20 |
| G | 196 | 192 | 4 | **1** (0.63-80.59 % of no-label) | 2 | 1 |
| all | 74,530 | 4,363 | 70,167 | **1,648** (2.24-2.46 % of no-label) | 7,128 | 61,391 |

**Headline S2: 1,648 recorded fires with no standard label now carry a verified label** (A 5,
B 612, C 765, D 169, E 90, F 6, G 1).

**C1 placebo (S2):** verified 51 / 30,992 = 0.16 % (0.12-0.22) of searched placebos and 53 / 70,163 = 0.08 % (0.06-0.10) of all
matched placebos: **passes** (<= 1 %). Probable 1524 / 30,992 = 4.92 % (4.68-5.16) of searched placebos: under this track's
5 % guard in point estimate, with an interval that reaches it.

What S2 does not show: outside California there is no night look; agency perimeters (NIFC history, WFIGS) carry
many of the verified labels (PERIM in 1,126 of the 4,795 verified records), so the share verified depends on how
much a state maps; the probable tier carries a false rate near 5 % of searched windows (about 1,600 of the 8,344
probable labels can be expected to be false).

## Slice S3: all US 2018-2020 (complete; addition 2026-11-21T20:45Z, frozen v0.1 rules)

220,975 FPA FOD records; 94,330 searched with imagery; 209,000 matched placebos (94.6 % of records; 91,224
searched). DNB night look only inside California 2020 (protocol A1). S3 reused the S2 checkpoints for 2020, and its
2020 rows equal S2 exactly (records, tiers, placebo counts). Source: `results/caught/S3_headline.csv`,
`S3_placebo.csv`, `S3_record_only_reasons.csv`, `S3_witnesses.csv`, `S3_summary.json`, `verified_S3_<year>.csv`
(13,793 verified records, with and without a standard label, one file per year; geometry simplified to 0.00005 degree and 5 decimals, the same format as `verified_S2.csv`, which `verified_S3_2020.csv` equals row for row; full-detail geometry is in the release label files). Wall time of the last resume 6.7 h; about 14 h in all,
across container restarts (DECISIONS D-512 to D-514).

| class | records | standard label | no standard label | of these, now verified (95 % CI of share) | now probable | record-only |
|---|---|---|---|---|---|---|
| A | 108,034 | 1,058 | 106,976 | **16** (0.01-0.02 % of no-label) | 1,579 | 105,381 |
| B | 88,914 | 4,274 | 84,640 | **1,522** (1.71-1.89 % of no-label) | 13,380 | 69,738 |
| C | 17,988 | 4,329 | 13,659 | **2,104** (14.80-16.02 % of no-label) | 5,205 | 6,350 |
| D | 2,881 | 1,395 | 1,486 | **449** (27.89-32.62 % of no-label) | 507 | 530 |
| E | 1,619 | 1,020 | 599 | **232** (34.81-42.76 % of no-label) | 178 | 189 |
| F | 999 | 866 | 133 | **19** (8.83-21.41 % of no-label) | 54 | 60 |
| G | 540 | 525 | 15 | **1** (0.17-31.95 % of no-label) | 10 | 4 |
| all | 220,975 | 13,467 | 207,508 | **4,343** (2.03-2.16 % of no-label) | 20,913 | 182,252 |

By year (no standard label; verified, probable and record-only kept in separate columns):

| year | records | standard label | no standard label | now verified | now probable | record-only | searched |
|---|---|---|---|---|---|---|---|
| 2018 | 81,733 | 5,161 | 76,572 | **1,680** (A 9, B 556, C 844, D 178, E 84, F 9) | 7,908 | 66,984 | 34,526 |
| 2019 | 64,712 | 3,943 | 60,769 | **1,015** (A 2, B 354, C 495, D 102, E 58, F 4) | 5,877 | 53,877 | 27,464 |
| 2020 | 74,530 | 4,363 | 70,167 | **1,648** (A 5, B 612, C 765, D 169, E 90, F 6, G 1) | 7,128 | 61,391 | 32,340 |

**Headline S3: 4,343 recorded US fires of 2018-2020 with no standard label now carry a verified label** (A 16,
B 1,522, C 2,104, D 449, E 232, F 19, G 1). Of these, 4,001 rest on a Sentinel-2 scar, 2,113 on an agency
perimeter, 1,212 on an HMS analyst point and 1,039 on a GOES point (one fire can have several; `S3_witnesses.csv`).

**C1 placebo (S3):** verified 191 / 91,224 = 0.21 % (0.18-0.24) of searched placebos and 205 / 209,000 = 0.10 %
(0.09-0.11) of all matched placebos: **passes** (<= 1 %). By year, searched: 2018 0.30 % (0.25-0.37), 2019 0.14 %
(0.10-0.20), 2020 0.16 % (0.12-0.22).

**Probable guard (this track's own, protocol section 8): fails.** Probable 4,837 / 91,224 = 5.30 % (5.16-5.45) of
searched placebos, above the 5 % guard with an interval that excludes it. By year: 2018 5.67 % (5.43-5.93), 2019
5.28 % (5.02-5.56), 2020 4.92 % (4.68-5.16). The rules were frozen on 2020 dev data (dev rate 4.44 %); the probable
tier is less reliable in 2018 and 2019 than on dev. Nothing was re-tuned. Read the probable tier as about one false
label per 19 searched windows: on the order of 5,000 of the 24,930 probable S3 labels (5.3 % of 94,330 searched
windows) can be expected to be false. The verified tier is not affected by this.

**Disc vertices (orchestrator note 2026-11-21T15:15Z; DECISIONS D-514).** A label without pixel geometry (182,252
record-only labels and 410 probable labels from smoke alone) carries the search disc as its geometry. In S3 that disc
is drawn with 16 vertices, 2.55 % less area than the circle of radius `r_m`. S1 and S2 drew it with 256 vertices
(0.01 % less). No tier, count, recall or three-state area depends on this polygon. Matching and the three-state
table use their own 256-vertex discs, and truth recall (C2) uses pixel labels only (`pipeline.py`, line 143). The
release is built from S3 and simplified to 2 % of the radius, so every released disc has 16 vertices; `r_m` is the
value to use.

What S3 does not show: outside California 2020 there is no night look; agency perimeters carry many verified labels
(PERIM in 5,169 of the 13,793 verified records), so the share verified depends on how much a state maps; class A
is almost entirely below the scar floor (105,065 of 105,381 class-A record-only labels), so a small-fire catch rests
on heat or perimeter evidence; record-only with a clear look and nothing found (56,469 in classes B-G) means no scar
above the floor between the scar dates, not that the record is false.

## C2: recall on the sealed small fires (opened once: run 21:48-22:53Z on 2026-11-20, rules frozen at 530a3d5)

Truth: mapped fires and prescribed burns 2018-2020 below 300 acres (CAL FIRE FRAP wildfire and Rx perimeters, NIFC
perimeter history), sealed split (sha256 of source id mod 10 in 3-9). The pipeline saw a record-like input only
(representative point, 250 m radius, dates, area); perimeter evidence was off. A fire counts as caught when a
verified or probable pixel label meets the polygon (+30 m); the standard label when a standard footprint does.
Interval: paired cluster bootstrap, 2,000 resamples over 0.5-degree cell x year. Source:
`results/caught/C2_sealed_primary_small.csv`.

| class | n | recall, labelled (verified or probable) | recall, standard | difference (95 % interval) | recall, verified only | verified minus standard | gate |
|---|---|---|---|---|---|---|---|
| all | 3711 | 0.639 | 0.306 | +0.333 (+0.308 to +0.358) | 0.299 | -0.008 (-0.020 to +0.004) |  |
| A | 206 | 0.044 | 0.034 | +0.010 (+0.000 to +0.025) | 0.010 | -0.024 (-0.047 to -0.005) | **fail** |
| B | 1029 | 0.490 | 0.114 | +0.376 (+0.335 to +0.419) | 0.096 | -0.017 (-0.033 to -0.003) | pass |
| C | 1857 | 0.733 | 0.357 | +0.376 (+0.345 to +0.408) | 0.349 | -0.008 (-0.027 to +0.011) | pass |
| D | 618 | 0.801 | 0.566 | +0.235 (+0.198 to +0.273) | 0.579 | +0.013 (-0.017 to +0.042) | pass |
| E | 1 | 1.000 | 0.000 | +1.000 (n too small) | 0.000 |  |  |

**C2 result: fails as pre-registered**, because class A (n = 206, fires under 0.26 acre) does not beat the standard
label (+0.010, interval 0.000 to +0.025): almost all class A fires lie below the scar floor (2,345 m2 = 0.58 acre).
Classes B, C and D pass with wide margins. Verified-only recall is not higher than the standard label's in any
class (it needs two independent kinds, and most small fires leave one).

What this does not show: the truth set is mostly California and the West (FRAP, NIFC history); mapped polygons are
the fires agencies chose to map, which are larger and more visible than the typical recorded small fire; the NIFC
dates come from a linked FPA FOD record (DECISIONS D-508), so a wrong link counts as a miss for both methods.
Reference stratum (>= 300 acres, n = 1,008): labelled 0.940 vs standard 0.852. FACTS broadcast burns (secondary,
not gated, n = 1,497; polygon = planned unit): 0.816 vs 0.670. Files `C2_sealed_reference_large.csv`,
`C2_sealed_secondary_facts.csv`.

## Downstream check (once, after the labels were tagged; nothing changed afterwards)

**Fixed margin, held-out miss rate: run, inconclusive.** wildfireguardian Main, research/kcf-margin, with its own code
(score_gofer.py, calibrate.lofo, reach.component_reach, 5 km separate-fire rule) on GOFER v0.2 (28 California fires,
2019-2021, sha256 matching the repo's). Baseline reproduced exactly: leave-one-fire-out miss 6.2 % (0.6-22.1) at 5 h
(R = 3.75 km), 6.6 % (0.7-22.8) at 8 h (R = 5.03 km). The S1 verified labels (California 2020, frozen rules; S3's 2018-2019 California labels did not exist yet, and the
check is not repeated) were added as newly burned 375 m cells
(within 5 km of the known set); 70 labels lie within 5 km of a GOFER fire during its span (31 at the August Complex).
Because a label has dates, not hours, two bounds were computed:

| h | labels counted when | miss at the published R (95 % CI) | R re-derived by LOFO |
|---|---|---|---|
| 5 | whole label interval inside the window (lower) | 5.7 % (unchanged; 0 issue-hours changed) | 3.75 km, 6.2 % |
| 5 | label interval overlaps the window (upper) | 50.9 % (31.5-70.2) | 19.3 km, 6.1 % |
| 8 | lower | 6.0 % (unchanged) | 5.03 km, 6.6 % |
| 8 | upper | 39.9 % (22.0-60.1) | 19.3 km, 6.2 % |

The lower bound cannot change by construction (every label interval is at least a day long); the upper bound counts
a label as burning in every hour its interval overlaps (median interval 3 days, a quarter 50 days or more), so its
jump is mostly that artefact. These labels cannot say whether the margin fails: hour-level timing would be needed.
n = 28 fires, 20,161 (5 h) and 20,077 (8 h) fire-hours. Files: `results/caught/downstream/` (report, numbers,
script).

**Forecast against persistence: NOT RUN.** Its held-out set is six 2024 US fires scored on NIROPS survey polygons
with 375 m covariates and a frozen checkpoint; 2020 fires are its training data and these labels cover 2018-2020
only, so no held-out fire overlaps them.

## Prior art

Agency records were compared with MODIS active fire before: detection rises steeply with fire size and most small
fires are not detected (e.g. Hawbaker et al. 2008; Fusco et al. 2019, for the conterminous US). Burned area at 30 m
from Landsat exists for the conterminous US (USGS Landsat Burned Area product, Hawbaker et al. 2017/2020), and
Sentinel-2 small-fire burned-area maps exist for Africa (FireCCISFD, Roteta et al. 2019), both showing that small
fires add burned area that 500 m products miss. What this track adds is per-record labels for agency-recorded fires
with an evidence tier, a placebo-measured false-label rate, three states with a detection floor, and the
record-only reason for every fire it cannot label; it makes no claim to be first. (Citations from memory, not
re-verified.)

## Addition 2026-11-21T05:00Z: scar area against mapped perimeters by fuel type (v0.1 rules and results unchanged)

Asked by the orchestrator after records v0.3 found that the scar module under-measures timber. **Records ran this
track's module**: `firewitness.caught.scar.make_perimeter`; at records' frozen commit 7ad17a7 the file
`firewitness/caught/scar.py` is identical to the frozen v0.1 rules here (530a3d5; last change a1f74ce, a disk guard
only).

Check here: dev truth fires only (dev split, sha256 of source id mod 10 in 0-2; the sealed fires are not used),
frozen-rule dev run (`truth_dev_r3`, small-fire scar finder `find_scar`, Sentinel-2 then Landsat), fires with a clear
look. Fuel = ESA WorldCover 2020 class at the polygon's representative point. Ratio = accepted scar area / mapped
area, among fires where a scar was found; "inside" = share of the mapped polygon covered by the scar. Verdict rule
borrowed as published by records v0.3 (applied as is, after seeing it): under-measures if the Wilson lower bound of
the share below 0.2 exceeds 0.25; not clear otherwise (n >= 10).

| stratum | fuel | clear looks | scars found | ratio median (quartiles) | below 0.2 (share; Wilson 95 %) | inside median | verdict |
|---|---|---|---|---|---|---|---|
| all | grass | 822 | 703 | 0.82 (0.56-0.96) | 65 (9.2 %; 7.3-11.6) | 0.75 | not clear |
| all | shrub | 76 | 59 | 0.68 (0.38-0.91) | 5 (8.5 %; 3.7-18.4) | 0.60 | not clear |
| all | timber | 628 | 360 | 0.46 (0.15-0.74) | 105 (29.2 %; 24.7-34.1) | 0.37 | not clear |
| primary small | grass | 616 | 503 | 0.85 (0.61-0.99) | 40 (8.0 %; 5.9-10.6) | 0.77 | not clear |
| primary small | shrub | 61 | 46 | 0.71 (0.40-0.95) | 3 (6.5 %; 2.2-17.5) | 0.63 | not clear |
| primary small | timber | 522 | 265 | 0.54 (0.20-0.86) | 66 (24.9 %; 20.1-30.4) | 0.43 | not clear |
| reference large | grass | 206 | 200 | 0.70 (0.43-0.88) | 25 (12.5 %; 8.6-17.8) | 0.69 | not clear |
| reference large | shrub | 15 | 13 | 0.51 (0.28-0.74) | 2 (15.4 %; 4.3-42.2) | 0.46 | not clear |
| reference large | timber | 106 | 95 | 0.32 (0.06-0.49) | 39 (41.1 %; 31.7-51.1) | 0.29 | under-measures |

**Verdict:** grass and shrub are measured reasonably (medians 0.82 and 0.68; fewer than one in ten scars below 0.2),
"not clear" only in the borrowed rule's sense. **Timber is under-measured**: median 0.46, 29 % below 0.2 (lower
bound 24.7 %, a hair under the borrowed rule's 25 %), 41 % below 0.2 for timber fires of 300 acres or more (lower
bound 31.7 %: under-measures), the scar covers a median 37 % of the mapped polygon, and a scar is found in only 57 %
of clear timber looks against 86 % in grass. Understory burns under an unchanged canopy change little in the
satellite's view. Files: `results/caught/fuel_check/dev_scar_ratios.csv`, `dev_ratio_summary.csv`.

**(a) What the label geometry means.** The label geometry marks where a fire was found, not its burned area. In
timber it covers about a third of the mapped burn (median); in grass about three quarters. Do not sum label areas
as burned area. (Also in the data card and docs/CAUGHT_SCAR_API.md.)

**(b) Scar floor by fuel type** (protocol section 7 formula, N_min 8, with T the median threshold of that fuel's dev
looks and dNBR_ref the median dNBR of the scars found in that fuel instead of the fixed 0.25; scars found are the
brighter ones, so these floors are optimistic for timber):

| fuel | sensor | median T | median scar dNBR | floor |
|---|---|---|---|---|
| grass | Sentinel-2 | 0.100 | 0.251 | 2,335 m2 (0.58 acre) |
| grass | Landsat | 0.100 | 0.251 | 5,253 m2 (1.30 acre) |
| shrub | Sentinel-2 | 0.100 | 0.228 | 2,569 m2 (0.63 acre) |
| shrub | Landsat | 0.100 | 0.228 | 5,781 m2 (1.43 acre) |
| timber | Sentinel-2 | 0.118 | 0.233 | 2,968 m2 (0.73 acre) |
| timber | Landsat | 0.118 | 0.233 | 6,679 m2 (1.65 acre) |

**(c) Sealed recall by fuel type**, re-tabulated from the existing sealed run of 2026-11-20 (nothing re-opened,
re-run or re-tuned; primary small stratum):

| fuel | class | n | recall labelled | recall standard | recall verified |
|---|---|---|---|---|---|
| grass | all | 1650 | 0.762 | 0.292 | 0.316 |
| grass | A | 73 | 0.041 | 0.041 | 0.000 |
| grass | B | 460 | 0.622 | 0.096 | 0.096 |
| grass | C | 824 | 0.863 | 0.336 | 0.363 |
| grass | D | 292 | 0.880 | 0.538 | 0.610 |
| shrub | all | 172 | 0.785 | 0.337 | 0.384 |
| shrub | A | 3 | 0.000 | 0.000 | 0.000 |
| shrub | B | 45 | 0.644 | 0.178 | 0.156 |
| shrub | C | 97 | 0.814 | 0.320 | 0.392 |
| shrub | D | 27 | 1.000 | 0.704 | 0.778 |
| timber | all | 1581 | 0.503 | 0.328 | 0.283 |
| timber | A | 88 | 0.045 | 0.034 | 0.011 |
| timber | B | 431 | 0.346 | 0.130 | 0.095 |
| timber | C | 809 | 0.582 | 0.387 | 0.337 |
| timber | D | 253 | 0.680 | 0.581 | 0.526 |
| other | all | 308 | 0.591 | 0.256 | 0.237 |
| other | A | 42 | 0.048 | 0.024 | 0.024 |
| other | B | 93 | 0.430 | 0.097 | 0.075 |
| other | C | 127 | 0.795 | 0.331 | 0.307 |
| other | D | 46 | 0.848 | 0.587 | 0.565 |

Labelled recall is lowest in timber (0.50 against 0.76 in grass; class B 0.35 against 0.62), as the dev check
predicts. File: `results/caught/fuel_check/sealed_recall_by_fuel.csv` (with Wilson intervals). A fix to the scar
finder for timber belongs to v0.2 and is tested on the v0.2 sealed set.
