# Headline numbers, firewitness v0.1 (independent audit)

Every number on this page was recomputed by the auditor from the GitHub release `v0.1` files (tag `v0.1` = `3fc6ab0`).
A number that did not recompute (MISMATCH or CANNOT RECOMPUTE) is not shown; its gate is still listed where it failed.
Commits are the last commits that changed the source file. Method and full tables: `results/AUDIT.md`.

## Labelling

**Sealed recall (caught C2, small fires under 300 acres): not shown.** It cannot be recomputed from release v0.1
because the sealed truth fires, their labels and their standard-label footprints are not released. The gate failed as
pre-registered in class A (results/CAUGHT_RESULTS.md). The labelled-against-standard and verified-only figures that
belong here are therefore missing.

**1. Fires caught that had no label: 4,343 verified** (US 2018-2020, S3), out of 207,508 agency records that no
standard satellite product labelled. That is 2.09 % (Clopper-Pearson 95 %: 2.03-2.16 %). Counts by slice, with the
tiers kept apart and never summed:

| slice | records | standard label | no standard label | verified | probable | record-only |
|---|---|---|---|---|---|---|
| S1 California 2020 | 10,360 | 397 | 9,963 | 92 (0.75-1.13 %) | 522 | 9,349 |
| S2 US 2020 | 74,530 | 4,363 | 70,167 | 1,648 (2.24-2.46 %) | 7,128 | 61,391 |
| S3 US 2018-2020 | 220,975 | 13,467 | 207,508 | 4,343 (2.03-2.16 %) | 20,913 | 182,252 |

Source: `release/caught-v0.1/caught_labels_v0.1_{2018,2019,2020}.parquet`, fields `tier`, `std_label`, `STATE`,
`FIRE_YEAR` (`f61df3e`). S1 and S2 are selected by state and year inside the S3 file (it has no slice column).
*Does not show* that a verified label is right: the placebo false rate that would bound this (C1) is not in the
release and could not be checked.

**2. Scar floor: 2,345 m2 (0.58 acre)** with Sentinel-2 at dNBR threshold 0.10. This is a smallest-findable-scar
formula value, not a measured rate, so it has no n and no interval. Source: `scar_floor_m2`
in the same files (`f61df3e`). *Does not show* the Landsat floor: the published 5,277 m2 recomputes as 5,276 m2.
Also, `firewitness caught floor` prints 1,440 m2 for the same case (it uses a different `n_min`).

## Early onset and live replay

**3. Fires whose first label moved earlier: 45 of 240** (18.8 %, Wilson 95 % 14.3-24.2 %). On those 45, the median
lead over the first standard detection is 42 min (fire bootstrap 95 %: 22-84 min). Source:
`release/live-v0.1/onset_labels.csv`, fields `onset_utc`, `lead_vs_T0_min` (`a30d02d`). *Does not show* that the
onset is the true ignition. It is the first frame distinguishable from the background, and the false-onset control (E1)
could not be recomputed.

**4. Live replay (D1, sealed test): the detector alerted before the operational GOES product on 7 of 97 fires**
(7.2 %, Wilson 95 % 3.5-14.2 %). The median lead is minus infinity, because 57 fires got no alert (bootstrap upper
bound -100 min, seed 0). **Gate D1 failed.** Source: `release/live-v0.1/replay_test.csv`, field `lead_min` (`a30d02d`).
*Does not show* false alerts per day: that number exists only in `replay_test.json`, without the placebo series behind
it. Also, 3 of the 7 count as earlier only because the operational product never detected them.

## Cleaning (US, FPA FOD 1992-2024, 2,661,383 records)

| # | count | value | source (`release/records-v0.1/`, `8f3e785`) | does not show |
|---|---|---|---|---|
| 5 | duplicates removed | **888** records merged into 883 fires | `crosswalk_us.parquet` (perm_id with several `fpa_fod` ids); `patches_us.jsonl.gz` rule `dup:fs_link` | that the 888 are true duplicates: the planted-duplicate recall (R3a) is not in the release |
| 6 | permanent IDs | **2,660,495** fires; **2** split source ids; **1,425** complex parents | `fires_us.parquet` `perm_id`; `complex_parents_us.parquet` `split` | stability on a re-run or with a held-out year added (R5): not recomputable |
| 7 | locations and times repaired in FPA FOD | **0** and **0** | `patches_us.jsonl.gz` (no `loc:` or `time:` rule) | the 108,921 raw ICS-209 location repairs: they are not in the v0.1 release |
| 8 | values: records altered | **64,873 (2.44 %)**: 63,985 placeholder blanks plus 888 duplicate merges; 172,824 more records with cosmetic fixes only | `patches_us.jsonl.gz`, distinct `record_id` by rule; the independent checker gives the same on the public FPA FOD file | **Gate R3(c) (at most 1 %) failed.** Unit-slip and sequence repairs: none in the release |

Exact counts, no sampling interval. **Perimeters created** and **the published hand cleaning reproduced** (precision,
recall, run time) are not shown: they cannot be recomputed from release v0.1.

## Smoke (sealed HPWREN sequences)

**9. Placebo: smoke in 4 of 503 pre-ignition frames, 0.8 %** (pooled bootstrap over 14 sequences, 95 %: 0.0-2.4 %);
all 4 frames are in one sequence. Source: `release/smoke-v0.1/sealed_opacity_edges.tar.gz`, `labels.json`
`placebo_smoke_frames` (`41f33b4`). *Does not show* the dev placebo, which failed at 7.1 % (not recomputable). The
upper limit is above the 1 % target.

**10. First smoke: found in 13 of 14 sequences, a median of +180 s after the human first-smoke label** (quartiles
+60 to +600 s; no interval published). Same source, `first_smoke_offset_s` (`41f33b4`). *Does not show* that the
method lags the smoke. It takes the largest smoke chain; with the earliest chain the median would be +60 s.

## Fuel (10 sealed tiles, LANDFIRE 2022 map)

**11. Cells called contradicted: 6.74 % of 40,000,000** (consistent 87.39 %, stale 1.03 %, unknown 4.84 %). This is a
census of cells, with no interval. Source: `release/fuel-v0.1/fuel-overlays-v0.1-nocards.zip`, `verdict.tif` per
sealed tile (`d4c696f`). *Does not show* whether those cells are wrong. F1 (7.91) and F2 (0.92 %) need the held-out
field plots, which are not released.

## Scoring

**No scoring number passed the recompute.** The score release holds split files only; no score card or gate output
is released.

## Every failed gate

- Gates whose numbers are shown above: **live D1** (item 4) and **records R3(c)** (item 8).
- Numbers that could not be checked from v0.1, so the outcome is the builders' own:
  - **caught:** C2 class A; C1 probable guard (5 %); v0.2 C1 and C2; the downstream check (not run).
  - **records:** R1 ICS-209-PLUS to FIRED; R1 precision and recall target; R3(a) day-month and time-zone planted
    errors and unit slips; v0.3 G2 gazetteer; v0.4 A1 AM/PM; v0.2 and v0.4 partial sealed calls.
  - **live:** v0.2 E2 and V2.
  - **smoke:** S2 dev placebo; S1 targets; S3 dev detection 66 % against 80 %; S5 window sensitivity.
  - **score:** N5; N3 passes only on the cheats its limit was tuned on.
- Found by this audit:
  - Results numbers that do not recompute: caught (2), live (2), records (1), score (10).
  - Revert is not byte for byte for tables without an id column.
  - `records link`, `ids` and `report` and `live replay` fail on a clean clone.
  - Two released patch files fail the patch checker (v0.3 scar flags, v0.2 gazetteer dev patches).
  - The core evidence combination counts a copied source as an independent witness.
