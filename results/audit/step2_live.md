# Step 2 — recompute of results/LIVE_RESULTS.md (main 3fc6ab0) from release live-v0.1 only

Release dir: `S/rel_v01/x/live-v0.1/live-v0.1/` (S = scratchpad). Scripts: `S/work_live/scripts/partA.py`,
`partB.py`, `e1check.py` (independent pandas/numpy; Wilson and fire-bootstrap re-implemented exactly as
`firewitness/live/pipeline.py::wilson` / `boot_median` — z = 1.96; 2,000 resamples, `numpy.random.default_rng(0)`,
percentiles 2.5/97.5; `fit.paired_stats` clips ±inf to ±1e6 before the bootstrap). Run with `python -I scripts/X.py <release dir>`.

## 1. Summary

Counted per number (a table row holding several numbers counts each): **MATCH 100, MISMATCH 2, MISMATCH-MC 0,
CANNOT RECOMPUTE 141, PARAMETER 11 (rows)**. **Mismatches: (1) line 10, fires seen by GOES-18: published 138, release 140
(onset_labels.csv sats "G16+G18" and traceback_by_satellite.csv G18 rows; the file's own E1 denominators 76 + 64 = 140).
(2) line 50, E2 "dev alone 1 of 4": the released labels give 2 of 5 for dev (the 5-of-8 total on the same line = dev 2/5 +
test 3/3); "1 of 4" comes from the dev-only run with dev thresholds, which is not released.** Everything recomputable on the
headline reproduces: D1 7 of 97 (7.2 %, Wilson 3.5–14.2 %), median lead −∞ with bootstrap upper −100 min (seed 0), 57 no
alert, all four size-class rows, dev in-sample 96/16/16.7 %/47 and score −39.6; Part A 45/240 (18.8 %, 14.3–24.2), dev
24/120, test 21/120, by size 9/13/14/9, and all four lead rows (42 [22–84], 120 [25–310] n = 34, 97 [52–125],
34 [−29–106]) exactly with the repo's fire bootstrap (2,000 resamples, numpy default_rng seed 0; the seed is not stated in
LIVE_RESULTS.md and other seeds move bounds by one frame); supplement 3/30 (10 %, 3.5–25.6), 56 min (44–107); E2 test 3/3,
all 5/8 (62 %, 31–86, median 25). File hashes 63bea29b, 6451108f, b4cfd493, 9e2c6bca, 79ef98db and the canonical-JSON
detector hash 69081030 all match. CANNOT RECOMPUTE: 65 numbers of the v0.2 addition (live-v0.2 not in v0.1); 19 D2 /
live-service numbers including **288/288** (no live-log or d2_summary.json in the release); 33 false-alert numbers and the
whole curve except the frozen row's share (only in replay_test.json; placebo series not released; every value equals that
JSON field); 12 E1 numbers (placebo S_pre and dev-only thresholds not released; 19/120 is consistent with the release, but
6/64 West needs h ≤ 30.72 while the released h_A 31.28 gives 5/64); dev cross-validated row 92/6/6.5 %/52 (fit_dev.json);
rounds 12 and −53.7; ~1.05 M pixels and the derived ~110 / ~100 / ~10,000 per day; "about 36" cloudy dev fires; the
"five" long leads read by eye (release has 9 onsets > 3 h).

## 2. Table

Status key: MATCH / MISMATCH / MISMATCH-MC / CANNOT RECOMPUTE / PARAMETER. "CANNOT RECOMPUTE (json)" = the number is
only in a released *results* file (`replay_test.json`) whose inputs (placebo pixel series, alerts at non-frozen thresholds)
are not released; it equals that field (self-reported), but it cannot be recomputed from data. Counted as CANNOT RECOMPUTE.

| line | quantity (short) | published | recomputed | status | source file and field / how |
|---|---|---|---|---|---|
| 3-4 | D1 sealed test: fires earlier | 7 of 97 | 7 of 97 | MATCH | replay_test.csv: n = rows with non-empty lead_min = 97; earlier = lead > 0 incl. "+inf" = 7 |
| 4 | D1 share earlier | 7.2 % | 7.216 % | MATCH | 7/97 |
| 4 | D1 share 95 % CI | 3.5–14.2 % | 3.54–14.15 % | MATCH | Wilson z=1.96 (stated, pipeline.wilson) |
| 5 | Part A fires with earlier label | 45 of 240 | 45 of 240 | MATCH | onset_labels.csv: onset_utc non-empty |
| 6, 11 | detector commit a629622; test-opening commit 65a58a4; protocol commit 58958d1 | — | — | PARAMETER | commit ids, not in release |
| 9 | fires | 240 | 240 (240 unique ids) | MATCH | live_fires.csv |
| 9 | per final-size class | 60 | 60/60/60/60 | MATCH | live_fires.csv size_class |
| 9 | dev / sealed test | 120 / 120 | 120 / 120 (30 per class in each) | MATCH | live_fires.csv split |
| 9 | period 2023-01 to 2025-04 | — | discovery 2023-03-19 to 2025-03-31 (inside) | PARAMETER | sampling window |
| 10 | fires with GOES-18 | 138 | **140** | MISMATCH | onset_labels.csv sats = "G16+G18": 140; traceback_by_satellite.csv: 140 G18 rows (dev 76 + test 64, consistent with the E1 denominators 76 and 64 in line 45-46) |
| 11 | sealed test opened 2026-11-21T00:06:02Z | — | — | PARAMETER | date |
| 12 | detector SHA-256 63bea29b… | 63bea29b… | 63bea29b… | MATCH | sha256 of released detector_us.json; also replay_test.json detector_sha256 |
| 14-15 | Wilson 95 %; fire-bootstrap 2,000 resamples | — | — | PARAMETER | method (confirmed in pipeline.py) |
| 23 | onset labels SHA-256 6451108f… | 6451108f… | 6451108f… | MATCH | sha256 onset_labels.csv |
| 24 | per-satellite file SHA-256 b4cfd493… | b4cfd493… | b4cfd493… | MATCH | sha256 traceback_by_satellite.csv |
| 28 | all: n | 240 | 240 | MATCH | onset_labels.csv |
| 28 | all: earlier onset | 45 | 45 | MATCH | onset_utc non-empty |
| 28 | all: share | 18.8 % | 18.75 % | MATCH | 45/240 |
| 28 | all: CI | 14.3–24.2 | 14.32–24.17 | MATCH | Wilson |
| 29 | dev: n | 120 | 120 | MATCH | split = dev |
| 29 | dev: earlier | 24 | 24 | MATCH | |
| 29 | dev: share | 20.0 % | 20.0 % | MATCH | |
| 29 | dev: CI | 13.8–28.0 | 13.82–28.04 | MATCH | Wilson |
| 30 | test: n | 120 | 120 | MATCH | |
| 30 | test: earlier | 21 | 21 | MATCH | |
| 30 | test: share | 17.5 % | 17.5 % | MATCH | |
| 30 | test: CI | 11.7–25.3 | 11.74–25.28 | MATCH | Wilson |
| 32 | by size 10–100 ac | 9/60 | 9/60 | MATCH | size_class 0 |
| 32 | 100–1,000 ac | 13/60 | 13/60 | MATCH | class 1 |
| 32 | 1,000–10,000 ac | 14/60 | 14/60 | MATCH | class 2 |
| 32 | ≥ 10,000 ac | 9/60 | 9/60 | MATCH | class 3 |
| 38 | lead vs first standard detection: n | 45 | 45 | MATCH | lead_vs_T0_min non-null among onsets |
| 38 | median | 42 min | 41.7 | MATCH | median |
| 38 | 95 % CI | 22–84 min | 21.7–83.7 | MATCH | fire bootstrap, 2,000, seed 0 (exact). Other seeds give 22.7–84.7 (MC noise only) |
| 39 | lead vs operational GOES product: n | 34 | 34 | MATCH | lead_vs_fdc_min non-null (11 onset fires have no FDCC detection) |
| 39 | median | 120 min | 120.0 | MATCH | |
| 39 | 95 % CI | 25–310 min | 25.0–310.0 | MATCH | bootstrap seed 0 |
| 40 | lead vs first polar: n | 45 | 45 | MATCH | lead_vs_polar_min |
| 40 | median | 97 min | 96.7 | MATCH | |
| 40 | 95 % CI | 52–125 min | 52.4–124.7 | MATCH | bootstrap seed 0 |
| 41 | lead vs agency discovery: n | 45 | 45 | MATCH | lead_vs_discovery_min |
| 41 | median | 34 min | 33.7 | MATCH | |
| 41 | 95 % CI | −29–106 min | −29.0–106.2 | MATCH | bootstrap seed 0 |
| 44 | E1 99th percentile | — | — | PARAMETER | |
| 44-45 | E1 test East placebo false onsets | 61 / 8,900 | — | CANNOT RECOMPUTE | placebo-anchor S_pre values (and h from dev placebos) not released; source is results/live/traceback_test_A2_summary.json (not in release) |
| 45 | E1 test East placebo rate | 0.69 % | — | CANNOT RECOMPUTE | same (Wilson of 61/8900 = 0.685 %, consistent) |
| 45 | E1 test East placebo upper | 0.88 % | — | CANNOT RECOMPUTE | same (Wilson upper of 61/8900 = 0.879 %, consistent) |
| 45 | E1 test East fires | 19/120 | 19/120 at h_A = 35.52 (released all-fire h_A); h_dev not released | CANNOT RECOMPUTE | traceback_by_satellite.csv S_pre (G16, test). onset ⇔ S_pre ≥ h holds in the file; 19 for any h in (35.5, 58.2]; the stated h is "from dev placebos only", not released |
| 45 | E1 test East fire lower | 10.4 % | (Wilson lower of 19/120 = 10.38 %) | CANNOT RECOMPUTE | depends on the count above |
| 45-46 | E1 test West placebo false onsets | 55 / 4,882 | — | CANNOT RECOMPUTE | placebo values not released |
| 46 | E1 test West placebo rate | 1.13 % | — | CANNOT RECOMPUTE | (Wilson of 55/4882 = 1.127 %, consistent) |
| 46 | E1 test West placebo upper | 1.46 % | — | CANNOT RECOMPUTE | (1.463 %, consistent) |
| 46 | E1 test West fires | 6/64 | 5/64 at released h_A 31.28; 6/64 requires h ≤ 30.72 | CANNOT RECOMPUTE | traceback_by_satellite.csv G18 test S_pre (6th highest = 30.72). h_dev (repo 30.19) not released |
| 46 | E1 test West fire lower | 4.4 % | (Wilson lower of 6/64 = 4.37 %) | CANNOT RECOMPUTE | |
| 46 | E1 dev CV East | 94/9,058 vs 15/120 | — | CANNOT RECOMPUTE | cross-validated placebo thresholds; placebos not released |
| 46 | E1 dev CV West | 61/5,861 vs 12/76 | — | CANNOT RECOMPUTE | same (denominator 76 matches the G18 dev count) |
| 49 | E2 sealed test agree | 3 of 3 | 3 of 3 | MATCH | onset_labels.csv e2_agree, split test |
| 49 | E2 test median abs diff | 15 min | 15.0 | MATCH | e2_abs_diff_min |
| 49 | E2 all agree | 5 of 8 | 5 of 8 | MATCH | |
| 49 | E2 all share | 62 % | 62.5 % | MATCH | half-rounding (62.5 → 62) |
| 49 | E2 all CI | 31–86 % | 30.6–86.3 | MATCH | Wilson |
| 50 | E2 all median | 25 min | 25.0 | MATCH | |
| 50 | E2 dev alone | 1 of 4 | **2 of 5** | MISMATCH | released labels (h_A from all 240 fires), split dev. The published "1 of 4" is the dev-only run (dev thresholds; repo traceback_dev_A2_summary.json, not released) and is not the dev subset of the 5-of-8 just quoted (5 of 8 = dev 2/5 + test 3/3) |
| 52 | fires keeping the anchor | 195 of 240 | 195 | MATCH | label_kind "no earlier onset (anchor kept)" |
| 53 | dev fires under thick cold cloud / no usable mask | about 36 of 120 | — | CANNOT RECOMPUTE | no definition or flag in release (n_clear_pre ≤ 48 gives 30, ≤ 72 gives 47; no cutoff stated) |
| 54 | placebo false-onset rate 1 % | — | — | PARAMETER | |
| 54-55 | expected false onsets among the 45 | about 3–4 | 3.8 (0.01 × 380 fire-satellite traces) | MATCH | traceback_by_satellite.csv rows |
| 56 | long leads (> 3 h) read by eye | five | 9 onsets > 3 h vs anchor (14 vs FDCC, 13 vs polar) | CANNOT RECOMPUTE | which fires were read is not recorded; see data problems (dev alone has exactly 5 > 3 h, but the named Siphon is a test fire) |
| 61-63 | detector cap 40, k 4, decay 0.9, ρ 1.5, ±30 min, radius 2 px | — | equal to detector_us.json config | PARAMETER | |
| 63 | h | 67.06 | 67.0596 (detector_us.json h) | PARAMETER | frozen threshold |
| 63 | budget 1 per 10,000 pixel-site-days | — | — | PARAMETER | |
| 66 | replay_test.json SHA-256 9e2c6bca… | 9e2c6bca… | 9e2c6bca… | MATCH | sha256 |
| 72 | sealed test n | 97 | 97 | MATCH | replay_test.csv (23 rows with neither alert nor operational time excluded) |
| 72 | detector earlier | 7 | 7 | MATCH | 4 finite positive leads + 3 "+inf" (alert, no operational detection) |
| 72 | share | 7.2 % | 7.22 % | MATCH | |
| 72 | share CI | 3.5–14.2 | 3.54–14.15 | MATCH | Wilson |
| 72 | median lead | −∞ (no alert) | −1e6 (= −∞ after clipping) | MATCH | median of 97 leads |
| 72 | median upper bound | −100 min | −99.9 (csv, rounded leads) / −99.87 (json) | MATCH | fire bootstrap, seed 0 (seeds 1, 3 give −110: MC sensitivity) |
| 72 | no alert in window | 57 | 57 | MATCH | lead_min = "-inf" |
| 73 | 10–100 ac: n / earlier / share / no alert | 16 / 1 / 6 % / 11 | 16 / 1 / 6.25 % / 11 | MATCH | replay_test.csv size_class 0 (4 numbers) |
| 74 | 100–1,000 ac | 24 / 1 / 4 % / 11 | 24 / 1 / 4.17 % / 11 | MATCH | class 1 (4 numbers) |
| 75 | 1,000–10,000 ac | 29 / 3 / 10 % / 15 | 29 / 3 / 10.34 % / 15 | MATCH | class 2 (4 numbers) |
| 76 | ≥ 10,000 ac | 28 / 2 / 7 % / 20 | 28 / 2 / 7.14 % / 20 | MATCH | class 3 (4 numbers) |
| 77 | dev cross-validated first version: n / earlier / share / no alert | 92 / 6 / 6.5 % / 52 | — | CANNOT RECOMPUTE | results/live/fit_dev.json cv_held_out_stats (not released; 4 numbers) |
| 78 | dev final version in sample: n / earlier / share / no alert | 96 / 16 / 16.7 % / 47 | 96 / 16 / 16.67 % / 47 | MATCH | replay_dev.csv (4 numbers); also equals detector_us.json dev_in_sample |
| 80 | window anchor −12 h / +2 h | — | — | PARAMETER | |
| 82 | clustered false alerts | 51 | 51 (json) | CANNOT RECOMPUTE | replay_test.json false_rate_at_h_this_split_clustered[1]; placebo series not released |
| 82 | pixel-site-days | 483,771 | 483,771.07 (json) | CANNOT RECOMPUTE | same field [2] |
| 82-83 | clustered rate | 1.05 × 10⁻⁴ | 1.054 × 10⁻⁴ (51/483,771) | CANNOT RECOMPUTE | json [0]; arithmetic consistent |
| 83 | unclustered rate | 9.4 × 10⁻⁴ | 9.36 × 10⁻⁴ (453/483,771) | CANNOT RECOMPUTE | json false_rate_at_h_this_split_per_pixel |
| 83 | US land pixels of GOES-East grid | ~1.05 million | — | CANNOT RECOMPUTE | grid/land mask not released |
| 84 | clustered false alerts per day | about 110 | 110.7 (1.05e6 × 1.054e-4) | CANNOT RECOMPUTE | arithmetic consistent; inputs not recomputable |
| 91 | 10⁻⁶: h / share / median / false rate | 419 / 1.1 % / −∞ / 2 × 10⁻⁶ | json 419.15 / 0.011 / −1e6 / 2.07e-6 | CANNOT RECOMPUTE | replay_test.json curve_thresholds_from_dev (4 numbers; alerts at non-frozen h and dev placebo thresholds not released) |
| 92 | 10⁻⁵ row | 158 / 4.2 % / −∞ / 1.4 × 10⁻⁵ | json 157.7 / 0.042 / −1e6 / 1.45e-5 | CANNOT RECOMPUTE | same (4) |
| 93 | 3 × 10⁻⁵ row | 106 / 7.2 % / −∞ / 5 × 10⁻⁵ | json 106.21 / 0.072 / −1e6 / 4.96e-5 | CANNOT RECOMPUTE | same (4) |
| 94 | 10⁻⁴ (frozen): share / median | 7.2 % / −∞ | 7.22 % / −∞ | MATCH | replay_test.csv (2 numbers; h counted at line 63) |
| 94 | 10⁻⁴ (frozen): false rate | 1.05 × 10⁻⁴ | json 1.054e-4 | CANNOT RECOMPUTE | as line 82 |
| 95 | 3 × 10⁻⁴ row | 44 / 10.2 % / −∞ / 2.7 × 10⁻⁴ | json 44.26 / 0.102 / −1e6 / 2.73e-4 | CANNOT RECOMPUTE | (4) |
| 96 | 10⁻³ row | 24 / 25.5 % / −50 / 8.7 × 10⁻⁴ | json 24.06 / 0.255 / −50.08 / 8.74e-4 | CANNOT RECOMPUTE | (4) |
| 97 | 3 × 10⁻³ row | 12 / 40.8 % / −5 / 2.5 × 10⁻³ | json 11.68 / 0.408 / −5.18 / 2.49e-3 | CANNOT RECOMPUTE | (4) |
| 98 | 10⁻² row | 3.6 / 64.5 % / +10 / 9.0 × 10⁻³ | json 3.63 / 0.645 / +10.27 / 8.98e-3 | CANNOT RECOMPUTE | (4) |
| 101 | events a day at ≤ 10⁻⁴ | ~100 | — | CANNOT RECOMPUTE | as line 84 |
| 101 | earlier on 7 % of fires | 7 % | 7.22 % | MATCH | |
| 102 | events a day at 10⁻² | ~10,000 | 9,424 (1.05e6 × 8.98e-3) | CANNOT RECOMPUTE | derived from json; consistent |
| 105 | improvement rounds | 12 | — | CANNOT RECOMPUTE | ROUNDS_live.md / rounds.json not in release |
| 105 | dev score before rounds | −53.7 min | — | CANNOT RECOMPUTE | same |
| 105-106 | dev score after rounds | −39.6 min | −39.60 | MATCH | replay_dev.csv: mean of lead clipped to [−120, +240] over the 96 fires (−inf → −120); detector_us.json −39.598 |
| 114 | pre-run records | 68 | — | CANNOT RECOMPUTE | live-log branch not in release |
| 115 | unsigned records | one | — | CANNOT RECOMPUTE | same |
| 116 | cycles with candidates / new candidates | 36 / 19 | — | CANNOT RECOMPUTE | same (2 numbers) |
| 117 | processing time per cycle | 25–90 s | — | CANNOT RECOMPUTE | run time, not in release |
| 127 | supplement fires | 30 of 378 | 30; 378 | MATCH | supplement_caught_fires.csv (30 rows); 378 = CA verified records in caught-v0.1 caught_labels_v0.1_2020.parquet (tier verified, STATE CA); all 30 ids are in that set |
| 127 | per size group | 10 | 10/10/10 | MATCH | size_group |
| 133 | ten-fire export | ten | 10 fire directories | MATCH | live_export_v0.1.tar.gz listing (tar tzf) |
| 133 | export SHA-256 79ef98db… | 79ef98db… | 79ef98db… | MATCH | sha256 live_export_v0.1.tar.gz |
| 141 | detector hash 69081030… | 69081030… | 69081030… | MATCH | sha256(json.dumps(detector_us.json, sort_keys=True)) as in firewitness/live/live.py |
| 142 | D2 window records | 288 | — | CANNOT RECOMPUTE | live-log not released (288 = 24 h / 5 min is arithmetic) |
| 147 | 30 of 378, 10 per group (repeat) | — | — | (counted at 127) | |
| 148 | seed 51 | — | — | PARAMETER | |
| 155 | supplement earlier onset | 3 of 30 | 3 of 30 | MATCH | supplement_caught_onset_labels.csv onset_utc non-empty |
| 155 | share | 10 % | 10 % | MATCH | |
| 155 | CI | 3.5–25.6 % | 3.46–25.62 | MATCH | Wilson |
| 155-156 | median lead vs first standard detection | 56 min | 55.6 | MATCH | lead_vs_T0_min of the 3 onsets (43.8, 55.6, 106.7) |
| 156 | bootstrap CI | 44–107 min | 43.8–106.7 | MATCH | seed 0 |
| 156 | n | 3 | 3 | MATCH | |
| 156 | labels: two witnesses / disagree / one witness | 1 / 1 / 1 | 1 / 1 / 1 | MATCH | label_kind (3 numbers) |
| 157 | E2 on supplement | 1 of 2 | 1 of 2 | MATCH | e2_agree = [True, False] |
| 163-200 | v0.2 test addition (all numbers except the two below) | 72 numbers | — | CANNOT RECOMPUTE | live-v0.2 is not part of v0.1 (results/live/v02/*). Counted items: l.167-168 100 fires, 25 per class, 151 fire-satellites (3); l.174-177 12/100, 12 %, 7.0–19.8, 43.7, 28.9–197.7, n 12, 145, 35–618, n 12, 138, 44–607, 115, −37–877, 8 of 12, 0/25, 4/25, 5/25, 3/25 (18); l.178-179 71/7417, 0.96 %, 1.21 %, 10/100, 5.5 %, 40/3896, 1.03 %, 1.39 %, 4/51, 3.1 % (10); l.180-181 2 fires, 102.5 min (2); l.182 16/877, 1.8 %, 1.1–2.9 % (3); l.183-185 1/10, 10 %, 1.8–40.4 %, 2.9 %, 15 min, 0/10 (6); l.186-189 1.49, 1.24–1.81, ρ 0.72, n 49, 37 fires, 75 of 124, 65 (7); l.190-194 14 onsets, 59 MW, 24–113, 28–108 MW, 2,600 m², 1,240–4,750 m², 7 MW, 0–20 MW, 0–2,950 m², FRP 0 (10); l.195-198 18 variants, 4/32, 1 of 10, 10 daytime onsets, 12 %, 7.0–19.8 % (6); plus 800 K / 600–1200 K (PARAMETER, not counted) → 65; plus l.166 commit 03441b2/07031ff/89361ee and SHA ae0ac7b3 (PARAMETER, not counted). Total counted CANNOT here: 65 |
| 169 | v0.2 h_A East / West | 35.52 / 31.28 | 35.52 / 31.28 | MATCH | equal to the v0.1 h_A in traceback_by_satellite.csv (the text says h_A from the 240 v0.1 fires) |
| 199 | v0.1 onset rate and CI (repeat) | 18.8 %, 14.3–24.2 %, 60 per class | 18.75 %, 14.32–24.17, 60 | MATCH | as line 28 (3 numbers) |
| 205-216 | D2 outcome: 288/288 records, 288/288 bundles verified, latency median 4.0 / p95 4.2 / max 8.7 min, 203 candidate entries, 143 cycles, 91 ids, 4 reconciliation files, 17 candidates, 13 unmatched, 4 polar-only, 0 agency | — | — | CANNOT RECOMPUTE | live-log branch and results/live/d2_summary.json not in release (13 numbers; run numbers 5–12 not counted) |
| 220 | D1 repeat: 7 of 97, 7.2 %, 3.5–14.2 % | 7/97, 7.2 %, 3.5–14.2 | same | MATCH | as lines 3-4 (3 numbers) |

## 3. Data problems / observations

1. **Line 10 "138 fires" with GOES-18 is contradicted by the release**: 140 fires have a GOES-18 trace (onset_labels.csv
   `sats`, traceback_by_satellite.csv, and the E1 denominators 76 dev + 64 test used in the same file).
2. **Line 50 "dev alone 1 of 4" (E2)** is not the dev subset of the released labels (2 of 5). It comes from the dev-only run
   with dev-only thresholds (`traceback_dev_A2_summary.json`, not released). The line reads as if it were the dev part of
   "5 of 8"; it is not (5 of 8 = dev 2/5 + test 3/3).
3. **E1 sealed-test West fire count 6/64 (line 46)** uses h from dev placebos (not released). With the released h_A
   (31.28) the release shows 5/64 test GOES-18 onsets; 6/64 needs h ≤ 30.72. Placebo S_pre values for all E1 placebo counts
   are not released, so no E1 number can be recomputed; the gate cannot be checked from the release.
4. **"Detector earlier" (D1, 7 of 97) includes 3 fires whose lead is +inf** (detector alerted, operational product never
   detected in the window: 2023-TXTXS-233991, 2025-OKOKS-250169, 2023-CASRF-000983). Only 4 fires have a finite positive lead
   (20.2, 80.0, 650.0, 1545.3 min). This follows the protocol (§6: alert but no operational detection → +∞), but the text does
   not say it.
5. **Median-lead bootstrap bounds depend on seed**: upper bound of the D1 median is −99.9 with seed 0 (published −100) but −110
   with seeds 1 and 3; Part A CIs shift by about 1 frame with other seeds (e.g. 22.7–84.7 vs 21.7–83.7). Published values
   reproduce exactly only with seed 0 (pipeline.boot_median default), which LIVE_RESULTS.md does not state.
6. **"Five long leads (> 3 h)" (line 56)**: the release has 9 onsets with lead > 3 h vs the anchor (5 dev: Lost, 698 Dan'S
   Branch, Rockhouse, Rough Rock, Matts Creek; 4 test: Oak Street, Smith Branch 2, Road 22, Siphon), 14 vs FDCC. Which five
   were "read by eye" is not recorded; possibly the dev five before the test was opened, but the example Siphon is a test fire.
7. Release replay_test.csv: 120 rows, 23 excluded (neither alert nor operational detection), 3 with no operational
   detection; lead_min consistent with alert/operational times in all rows (checked). No duplicate fire ids in any live file.
8. Released copies equal the repo files cited by the results (sha256 identical): onset_labels_v0.1.csv, traceback_all_A2_by_satellite.csv,
   replay_test.json, replay_test_by_fire.csv, replay_dev_by_fire.csv (= replay_dev.csv), live_fires.csv, detector_us.json.
   `partA_summary.json`, `traceback_test_A2_summary.json`, `fit_dev.json`, `rounds.json`, `d2_summary.json`,
   supplement summary/per-satellite files and all placebo series are **not** in the release although LIVE_RESULTS.md cites them as sources.
9. Line 117/141/142 etc.: no D2 log or live-log record is in release v0.1, so D2 (288/288) cannot be checked at all from the release.
10. The time window "2023-01 to 2025-04" (line 9) is the sampling window; actual discovery dates in the list run 2023-03-19 to 2025-03-31.
11. Supplement discovery times are all 00:00:00Z (date only), consistent with the text's statement that no agency-time lead is reported.
