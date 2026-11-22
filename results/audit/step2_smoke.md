# Step 2 recompute: results/SMOKE_RESULTS.md (main 3fc6ab0) against release smoke-v0.1

Release files used (checksums verified upstream): `S/rel_v01/x/smoke-v0.1/smoke-v0.1/` = `sealed_opacity_edges.tar.gz`, `clips_gifs_stills.tar.gz`, `SMOKE_RESULTS.md`, `SMOKE_EDGE.md`, `PRIOR_ART_SMOKE.md`, `NOTES.md`. Extracted into `S/work_smoke/sealed/` (16 sequence folders) and `S/work_smoke/clips/` (18 GIFs + stills).
Scripts: `S/work_smoke/scripts/smoke_recompute.py` (S2/S3 from `labels.json`), `S/work_smoke/scripts/smoke_npz_check.py` (opacity.npz / edges.json sanity). Outputs: `S/work_smoke/smoke_recompute.out`, `S/work_smoke/smoke_npz_check.out`.
(S = <work>)

**Released SMOKE_RESULTS.md copy vs main:** byte-identical (`cmp` exit 0) to `/home/user/wildfireguardiandata/results/SMOKE_RESULTS.md` at 3fc6ab0. Released `SMOKE_EDGE.md` is also identical to `docs/SMOKE_EDGE.md`.

## 1. Summary

Rows below (one row per line and quantity group): **MATCH 22, MISMATCH 0, MISMATCH-MC 0, CANNOT RECOMPUTE 94, PARAMETER 7.** No mismatches. Everything that the release can support matches: the sealed S2 placebo (4 of 503 pre-ignition frames = 0.8 %, 1 of 14 sequences with false frames; 95 % pooled bootstrap over sequences [0.0 %, 2.4 %], reproduced exactly with the repo's stated scheme, seed 0, 2,000 resamples, and also by an independent 20,000-resample bootstrap with another seed, upper 0.0239), the sealed S3 first-smoke offsets (13 of 14 detected = 93 %, median +180 s, quartiles +60/+600, 10th-90th 0/+1152, earlier 0 %, later 77 %, within 5 min 69 %), the 16/2/14 sealed sequence counts and exclusions, and the description of the released files. **CANNOT RECOMPUTE**: (a) every dev-set number (S1/S2/S3/S5 dev, dev 7.1 % 80/1122, 5.0 % 54/1086, 66 % detection, false-alarm breakdown): no dev labels, opacity maps or `dev_final.json` are in the release; (b) all S1 known-truth numbers, dev and sealed, including the headline sealed opacity MAE 0.143 [0.117, 0.171], bias, edge errors 10.01 px (0.20) and 7.90 px (0.40), detection 79.3 % [71.5, 85.9], colour/opacity breakdowns: the S1 composites (planted plumes) and `s1_rows` (in `results/smoke/sealed_final.json`) are not in the release, and building composites needs the raw FIgLib frames, also not released; (c) S5 re-run identity (16 of 16) and S5 window sensitivity (sealed shifts 240-900 s, 1 or 2 of 14 lost, edge 0.19-0.66 px): need a re-run on raw FIgLib frames, or `s5_identity_rows`/`s5_window_rows` (not released); (d) all S4 numbers (HPWREN-BB / Pyro-SDIS boxes and `s4_final.json` not released); (e) addendum round-log numbers (`ROUNDS_smoke.md`, session scratch logs; not released).

## 2. Table

| line | quantity | published | recomputed | status | source / how |
|---|---|---|---|---|---|
| 3 | configuration v1, frozen after R12; amendments A1-A3 | v1, R12, A1-A3 | - | PARAMETER | labels.json `params_hash` = dbbe4c4d29dea5cc in all 14 labelled sealed folders (single configuration) |
| 7 | total sequences / dev sequences | 48 / 32 | - | CANNOT RECOMPUTE | dev list `protocol/sequences_dev.txt` is not a release file (repo copy lists 32); no dev folders in release |
| 7 | sealed sequences | 16 | 16 | MATCH | 16 folders in sealed_opacity_edges.tar.gz; names identical to repo `protocol/sequences_sealed.txt` |
| 7 | two sealed sequences with 41 frames, excluded | lp-n-iqeye, mg-s-iqeye; 41 frames | same; 41 inputs each, `excluded` = "fewer than 60 frames" | MATCH | labels.json `inputs` (41 entries), `excluded` |
| 7 | scope rule "fewer than 60 frames" | 60 | - | PARAMETER | labels.json params `min_frames` = 60 |
| 7 | usable sealed sequences | 14 | 14 | MATCH | 14 folders with opacity.npz/edges.json and `excluded` null |
| 8 | 12 improvement rounds | 12 | - | CANNOT RECOMPUTE | ROUNDS_smoke.md not in release |
| 9 | S1 grid 2 seeds x 3 opacities x 4 colours | 2x3x4 | - | PARAMETER | protocol |
| 9 | S1 composites dev / sealed | 768 / 384 | - | CANNOT RECOMPUTE | S1 composites / s1_rows not in release |
| 13 | S2 sealed rate, frames | 0.8 %, 4 of 503 | 0.795 %, 4 of 503 | MATCH | labels.json `placebo_smoke_frames` (4 frames, all in 20180602_FIRE_smer-tcs9, offsets -480..-300) over pre-window frames `offsets` in [-2400, -300] (36 per seq, 35 in 20191001 rm-w) |
| 13 | S2 sealed upper 95 % limit | 2.4 % | 2.39 % | MATCH | pooled-rate bootstrap over sequences, `numpy default_rng(0)`, 2,000 (repo scheme `summarise_s23`); independent 20,000 resamples seed 12345 gives same 0.0239 |
| 13 | S2 dev rate, frames | 7.1 %, 80 of 1122 | - | CANNOT RECOMPUTE | dev labels / dev_final.json not in release |
| 13 | S2 dev without plume-before-ignition sequence | 5.0 %, 54 of 1086 | - | CANNOT RECOMPUTE | same |
| 13 | S2 gate limit | 1 % | - | PARAMETER | protocol |
| 13 | sealed: 14 sequences, one with false frames | 14; 1 | 14; 1 | MATCH | labels.json |
| 14 | S5 identity dev | 32 of 32 | - | CANNOT RECOMPUTE | needs re-run on raw FIgLib frames (not released) |
| 14 | S5 identity sealed | 16 of 16 (14 labelled) | 14 labelled: 14 | CANNOT RECOMPUTE | identity needs a re-run on raw frames / `s5_identity_rows` (not released); "14 labelled" matches |
| 15 | opacity MAE | 0.14 (target 0.10) | - | CANNOT RECOMPUTE | S1 rows not released |
| 15 | edge error at 0.20/0.40 | 6 to 10 px (target 4) | - | CANNOT RECOMPUTE | S1 rows not released |
| 15 | detection alpha_max >= 0.6 | 76 % dev, 79 % sealed (target 90 %) | - | CANNOT RECOMPUTE | S1 rows not released |
| 15 | bias within 0.05; -0.12 for truth 0.7-1.0 | 0.05; -0.12 | - | CANNOT RECOMPUTE | S1 rows not released |
| 15 | targets 0.10 / 4 px / 90 % / 0.05 | - | - | PARAMETER | protocol section 6 |
| 16 | S3 detection dev | 66 % (target 80 %) | - | CANNOT RECOMPUTE | dev labels not released |
| 16 | S3 detection sealed | 93 % (13 of 14) | 92.9 % (13 of 14) | MATCH | labels.json `first_smoke_offset_s` non-null in 13; null in 20191005_FIRE_hp-s |
| 16 | median method minus human, sealed | +180 s | +180 s | MATCH | `first_smoke_offset_s - human_offset_s` (human = 0) over 13 detected |
| 16 | median method minus human, dev | +180 s | - | CANNOT RECOMPUTE | dev not released |
| 16 | earlier than human, dev | 19 % | - | CANNOT RECOMPUTE | dev not released |
| 16 | earlier than human, sealed | 0 % | 0 % | MATCH | no detected sealed sequence has negative offset |
| 23 | S2 dev headline: 7.1 %, 80/1122, [1.7 %, 13.6 %], n = 32 | - | - | CANNOT RECOMPUTE | dev_final.json not released |
| 24 | S3 dev: +180, +34 to +480, 21 of 32 | - | - | CANNOT RECOMPUTE | dev |
| 25 | S1 MAE dev 0.138 [0.117, 0.162], n = 768 | - | - | CANNOT RECOMPUTE | S1 |
| 26 | S1 bias dev -0.011 [-0.030, 0.010]; -0.12 | - | - | CANNOT RECOMPUTE | S1 |
| 27 | edge 0.20 dev 8.5 px, n = 764 | - | - | CANNOT RECOMPUTE | S1 |
| 28 | detection dev 75.6 % [66.6, 83.8] | - | - | CANNOT RECOMPUTE | S1 |
| 29 | S5 dev 32 of 32 | - | - | CANNOT RECOMPUTE | S5 |
| 30 | S2 sealed 0.8 % (4 of 503) | 0.8 %, 4/503 | 0.795 %, 4/503 | MATCH | as line 13 |
| 30 | S2 sealed interval, n | [0.0 %, 2.4 %], n = 14 | [0.000, 0.0239], n = 14 | MATCH | seed 0, 2,000, pooled (repo method, reproduced exactly) |
| 31 | S3 sealed median, quartiles, detected | +180; +60 to +600; 13 of 14 | +180; +60, +600; 13 of 14 | MATCH | numpy linear quantiles of [0,0,0,60,120,120,180,300,300,600,960,1200,2280] |
| 32 | S1 opacity MAE sealed | 0.143 [0.117, 0.171], n = 384 | - | CANNOT RECOMPUTE | composites/s1_rows not released; would need raw FIgLib pre-ignition frames + `firewitness.smoke.s1` composites, or `results/smoke/sealed_final.json` s1_rows |
| 33 | S1 bias sealed | -0.019 [-0.046, 0.009] | - | CANNOT RECOMPUTE | same |
| 34 | S1 edge 0.20 sealed | 10.0 px, n = 384 | - | CANNOT RECOMPUTE | same |
| 35 | S1 detection sealed | 79.3 % [71.5 %, 85.9 %] | - | CANNOT RECOMPUTE | same |
| 36 | S5 sealed | 16 of 16 | - | CANNOT RECOMPUTE | re-run needs raw frames |
| 37 | S4 HPWREN-BB: 0.14, 0.03-0.30, 246 boxes, 6 fires | - | - | CANNOT RECOMPUTE | boxes and s4_final.json not released |
| 38 | S4 Pyro-SDIS: 0.00, 92 boxes, 10 events, 45 none | - | - | CANNOT RECOMPUTE | same |
| 43 | thick bias -0.12; dark-smoke MAE 0.17/0.20 vs 0.11-0.15; detection 63 %/54 % vs 70-81 % | - | - | CANNOT RECOMPUTE | S1 rows |
| 45 | edges within 6 to 10 px | 6-10 px | - | CANNOT RECOMPUTE | S1 rows |
| 45 | 512 x 384 working size; 4 source px; 2 px smoothing | - | 512 x 384 in labels.json `working_size` | PARAMETER | |
| 47 | dev false alarms 80 in 6 sequences (19, 16, 26, 6, 9, 4); 198 to 80 | - | - | CANNOT RECOMPUTE | dev / rounds log |
| 49 | S4 level counts 60/45/34/42/49/16, IoU 0.14; Pyro 92, 10, 45, 0.00 | - | - | CANNOT RECOMPUTE | S4 |
| 51 | S5 window: 90-810 s dev, 240-900 s sealed, lost 4-9 of 31/32 dev, 1-2 of 14 sealed, edge 0.2-2.3 px | - | - | CANNOT RECOMPUTE | re-runs with other windows need raw frames; window rows not released |
| 58 | sealed S2 rests on 14 sequences, one with false frames | 14; 1 | 14; 1 | MATCH | labels.json |
| 72 | dev S2 detail: 80/1122, 7.1 %, [1.7, 13.6], 6 of 32 | - | - | CANNOT RECOMPUTE | dev |
| 73 | dev S3 detail: 21/32, 66 %, +180, +34/+480, -63/+960, 19/76/71 % | - | - | CANNOT RECOMPUTE | dev |
| 75 | 768 composites over 32 sequences, 0 excluded | - | - | CANNOT RECOMPUTE | dev S1 |
| 81-91 | dev S1 table (MAE, bias, edge medians 12.20/10.46/8.50/5.96/7.75 with n 760/768/764/503/484, detection 71.2 % and 75.6 % with CIs, first-smoke 0.0 n = 547, 0.30 false chains) | - | - | CANNOT RECOMPUTE (11 rows) | dev S1 |
| 97-100 | dev by colour (n 192, MAE, bias, detection) | - | - | CANNOT RECOMPUTE (4 rows) | dev S1 |
| 106-108 | dev by alpha_max | - | - | CANNOT RECOMPUTE (3 rows) | dev S1 |
| 114-117 | dev by true-opacity bin | - | - | CANNOT RECOMPUTE (4 rows) | dev S1 |
| 123 | dev re-run identity 32 of 32 | - | - | CANNOT RECOMPUTE | dev S5 |
| 127-129 | dev window table | - | - | CANNOT RECOMPUTE (3 rows) | dev S5 |
| 137 | sealed sequences 16, 2 excluded (names, reason) | 16; 2 | 16; 2, same names and reason | MATCH | labels.json |
| 138 | 4 of 503 = 0.8 % | - | 4 / 503 = 0.795 % | MATCH | labels.json |
| 138 | 95 % bootstrap [0.0 %, 2.4 %] | - | [0.000, 0.0239] | MATCH | seed 0, 2,000, pooled; own bootstrap same |
| 138 | 1 of 14 sequences with false frame | 1 of 14 | 1 of 14 | MATCH | 20180602_FIRE_smer-tcs9-mobo-c |
| 139 | detected 13 of 14 (93 %) | 13; 93 % | 13; 92.9 % | MATCH | labels.json |
| 139 | median +180, quartiles +60 to +600 | - | +180; +60; +600 | MATCH | numpy linear quantiles |
| 139 | 10th to 90th percentile | +0 to +1152 | 0.0 to 1152.0 | MATCH | numpy linear quantiles (q10 = 0, q90 = 1152) |
| 139 | earlier / later / within 5 min | 0 % / 77 % / 69 % | 0/13 = 0 %; 10/13 = 76.9 %; 9/13 = 69.2 % | MATCH | `abs(d) <= 300` |
| 141 | 384 composites over 16 sequences, 0 excluded | - | - | CANNOT RECOMPUTE | sealed S1 not released |
| 147 | sealed MAE 0.143 [0.117, 0.171] | - | - | CANNOT RECOMPUTE | sealed S1 |
| 148 | sealed bias -0.019 [-0.046, 0.009] | - | - | CANNOT RECOMPUTE | sealed S1 |
| 149 | edge at noise level 12.23, n = 384 | - | - | CANNOT RECOMPUTE | sealed S1 |
| 150 | edge at 0.10 11.56, n = 384 | - | - | CANNOT RECOMPUTE | sealed S1 |
| 151 | edge at 0.20 10.01, n = 384 | - | - | CANNOT RECOMPUTE | sealed S1 (the release `edges.json` holds contours of the real sequences, not of the composites, so cannot give this) |
| 152 | edge at 0.40 7.90, n = 255 | - | - | CANNOT RECOMPUTE | sealed S1 (same) |
| 153 | edge at 0.60 8.94, n = 248 | - | - | CANNOT RECOMPUTE | sealed S1 |
| 154 | detection all 72.1 % [64.8, 78.9] | - | - | CANNOT RECOMPUTE | sealed S1 |
| 155 | detection alpha_max >= 0.6 79.3 % [71.5, 85.9] | - | - | CANNOT RECOMPUTE | sealed S1 |
| 156 | first-smoke error 0.0 frames, n = 277 | - | - | CANNOT RECOMPUTE | sealed S1 |
| 157 | false smoke chains per composite 0.26 | - | - | CANNOT RECOMPUTE | sealed S1 |
| 163-166 | sealed by colour (n 96, MAE 0.195/0.111/0.123/0.145, bias, detection 54/78/81/75 %) | - | - | CANNOT RECOMPUTE (4 rows) | sealed S1 |
| 172-174 | sealed by alpha_max (n 128) | - | - | CANNOT RECOMPUTE (3 rows) | sealed S1 |
| 180-183 | sealed by true-opacity bin | - | - | CANNOT RECOMPUTE (4 rows) | sealed S1 |
| 189 | sealed re-run identity 16 of 16 | - | - | CANNOT RECOMPUTE | needs raw frames |
| 193-195 | sealed window table (14 seq; 12/12/13 detected; 2/1/1 lost; 300/900/240 s; -300/-900/-180 and IQRs; edge 0.19/0.66/0.23 px, n 12) | - | - | CANNOT RECOMPUTE (3 rows) | needs raw frames or `s5_window_rows` |
| 201-212 | S4 detail (246 boxes, 9 fires header vs 6 fires listed, level counts, IoUs, per-fire, 3 excluded; Pyro 92 boxes, 10 events) | - | - | CANNOT RECOMPUTE (2 rows) | S4 boxes not released |
| 219 | release holds opacity.npz (uint8 x 255), edges.json, labels.json for the 14 sealed sequences | 14 | 14 folders with opacity.npz (`alpha` uint8, max 255) + edges.json (contours at noise, 0.10, 0.20, 0.40, 0.60 per frame) + labels.json; 2 excluded folders carry labels.json only | MATCH | |
| 230-235 | addendum round numbers (S1-lite 0.129, 8.14 px, 70.8-78.1 %, S2 198/164/99/80 of 1122, 17.6 %, 5.2 points) | - | - | CANNOT RECOMPUTE (2 rows) | ROUNDS_smoke.md / session scratch not released |
| 237 | v0 whole-frame edge medians 65.3/63.5/58.2/48.0/49.2 px | - | - | CANNOT RECOMPUTE | `s1_v0.log` not committed or released |
| 239 | 12 loop rounds; rounds named | - | - | PARAMETER | log bookkeeping |

Counting: each "(k rows)" counts k. Totals: MATCH 22, CANNOT RECOMPUTE 94, PARAMETER 7, MISMATCH 0, MISMATCH-MC 0.

## 3. Data problems and observations

1. **Released SMOKE_RESULTS.md is identical to main** (also SMOKE_EDGE.md to docs/). NOTES.md claims (16 folders, 2 with reason; 18 clips = 8 smoke/known-truth/scar/duplicate + 10 satellite) match the archive contents (18 GIFs: 6 `smoke_*`, `scar_pairs_S1`, `duplicates_collapse`, 10 `satellite_*`).
2. **The headline S1 numbers (MAE 0.143, edge 10.01 / 7.90 px, detection 79.3 %) are not checkable from the release.** The release has the opacity maps of the real sealed sequences, not the composites with planted truth, and not the raw FIgLib frames from which composites are built. `results/smoke/sealed_final.json` (`s1_rows`, `s5_*_rows`) is in git but not in release v0.1.
3. **S1 sealed scope differs from S2/S3 scope.** The results say the sealed set "has 14 usable sequences", but S1 sealed is "384 composites over 16 sequences (0 excluded)": the two 41-frame sequences excluded from S2/S3 contribute 48 of the 384 composites (repo `results/smoke/sealed_final.json` s1_rows: 24 each for lp-n-iqeye and mg-s-iqeye). The release has no opacity data for those two, so 1/8 of the sealed S1 population has no released counterpart.
4. **First smoke is the first frame of the largest-mass smoke chain, not the earliest smoke-classed region.** In `opacity.npz` `classes`, 9 of 13 detected sealed sequences have smoke-class pixels before the reported first-smoke frame (e.g. 20180614 hp-s: smoke class from +360 s, reported +1200 s; 20180606 lo-s: +420 vs +960; 20200306 ml-s: +120 vs +600). In 5 sequences (smer-tcs3, bh-n, so-n, bl-e, 20191001 rm-w) a smoke-classed chain starts before human offset 0 (-60 to -180 s). With "earliest smoke-class chain" as first smoke, the sealed S3 median would be +60 s and 5 of 13 (38 %) would be earlier than the human label instead of 0 %. This follows `pipeline.label_sequence` (`main = max(smoke, key=mass)`); the protocol wording "trace back from a confirmed later frame" does not say which chain. Not a mismatch, but the "0 % earlier / method needs more smoke than a human" reading depends on this choice.
5. Pre-window frame counts: 13 sequences have 36 frames in [-2400, -300] s, 20191001_FIRE_rm-w has 35 (irregular 58-62 s spacing) giving 503. 20191001_FIRE_bh-w has 79 frames with gaps up to 120 s; 20180614_FIRE_hp-s has 68 frames (offsets to +1620 only). All above the 60-frame rule.
6. Line 201 says "HPWREN-BB boxes (9 fires...)" while line 37 says 6 fires and 6 per-fire entries plus 3 excluded are listed (6 + 3 = 9); wording only, not checkable from release.
7. S2 sealed placebo frames come from the pipeline's own placebo run recorded in `labels.json`; the full-run class maps show no smoke class in any pre-window frame, consistent with this but not an independent re-detection (raw frames needed for that).
