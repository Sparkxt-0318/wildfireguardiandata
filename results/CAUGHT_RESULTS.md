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
