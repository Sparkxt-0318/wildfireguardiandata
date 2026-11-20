# SMOKE_RESULTS: smoke edge, first frame, classes (track smoke, release v0.1)

Image data: HPWREN, http://hpwren.ucsd.edu/ (FIgLib); PyroNear Pyro-SDIS (Apache-2.0). Method: `docs/SMOKE_EDGE.md` (configuration v1, frozen after round R12). Protocol, with amendments A1 to A3: `protocol/SMOKE_PROTOCOL.md`. Rounds: `results/ROUNDS_smoke.md`. Every number below is produced by `scripts/build_smoke_results.py` from the JSON files in `results/smoke/`; none was typed by hand.

## What was run

- 48 FIgLib sequences chosen by a fixed hash rule before any frame was processed (protocol section 3): 32 dev, 16 sealed (`protocol/sequences_dev.txt`, `sequences_sealed.txt`). Two sealed sequences (`20160718_FIRE_lp-n-iqeye`, `20160718_FIRE_mg-s-iqeye`) have 41 frames and fall under the scope rule "fewer than 60 frames"; they are excluded and listed, so the sealed set has 14 usable sequences.
- The 32 dev sequences were used to develop and choose the rules (12 improvement rounds). The sealed sequences were run once, with the frozen configuration, after round R12. Dev numbers are therefore optimistic; the sealed numbers are the unbiased ones.
- S1 full grid: 2 plume seeds x 3 opacities x 4 smoke colours per sequence (768 composites on dev, 384 on sealed).

## Gates and targets: what was met

- **S2 gate (at most 1% of pre-ignition frames with a smoke region): met on sealed by the point estimate (0.8%, 4 of 503 frames; the upper 95% limit is 2.4%), not met on dev (7.1%, 80 of 1122).** The dev set contains the cases the rules were tuned against (cloud shadows, a moving tower shadow, windy shrubs, hazy sky, one sequence with another fire's plume already visible before ignition, one sunrise). Without the plume-before-ignition sequence the dev rate is 5.0% (54 of 1086). Calling the S2 gate met would rest on 14 sealed sequences of which one has false frames; the interval says it could be 2.4%.
- **S5 gate (byte-identical re-run): met**, 32 of 32 dev and 16 of 16 sealed (14 labelled).
- **S1 targets: not met except bias and first-smoke error.** Opacity MAE is 0.14 (target 0.10); edge error at 0.20 and 0.40 is 6 to 10 px (target 4 px); detection of composites with opacity at least 0.6 is 76% dev and 79% sealed (target 90%). Bias is within 0.05 on average but is -0.12 where the true opacity is 0.7 to 1.0 (the method under-reads thick smoke).
- **S3**: detected in 66% of dev sequences (target 80%) and 93% of sealed sequences (13 of 14). The method's first-smoke time is **later** than the human offset in most sequences: median +180 s on both sets, so the method is about three minutes after the human first-visible plume, and earlier in 19% (dev) and 0% (sealed). That is the opposite of the "labels lag the smoke" hypothesis for this method on these frames; it says the method needs more smoke than a human uses to call the first frame. It does not say which is closer to the physical ignition.
- **S4**: no single effective opacity level emerges (below).

## Headline table

| quantity | value (95% interval where stated) | target | source file (results/smoke/) | what it does not show |
|---|---|---|---|---|
| S2 false pre-ignition frames, dev | 7.1% (80 of 1122); interval [1.7%, 13.6%]; n = 32 sequences | <= 1% (gate) | dev_final.json s2_s3 | frames inside one sequence are correlated; sequences with another fire's smoke or a sunrise in the pre window count as false |
| S3 method minus human first-smoke, dev | median +180 s, quartiles +34 to +480; 21 of 32 detected | report; detected >= 80% | dev_final.json s2_s3 | which of the two is closer to the physical ignition is not known; the human offset is the first visible plume in 1-minute frames |
| S1 opacity MAE, dev | 0.138 [0.117, 0.162]; n = 768 composites | <= 0.10 | dev_final.json s1 | composites follow the same mixing law as the method and rise by construction |
| S1 opacity bias, dev | -0.011 [-0.030, 0.010] | abs <= 0.05 | dev_final.json s1 | bias is -0.12 for true opacity 0.7 to 1.0 |
| S1 edge error at 0.20, dev | median 8.5 px; n = 764 | <= 4 px | dev_final.json s1 | window around the planted plume only; false regions elsewhere are counted separately |
| S1 detection, alpha_max >= 0.6, dev | 75.6% [66.6%, 83.8%] | >= 90% | dev_final.json s1 | dark smoke (0.30) is detected least |
| S5 re-run identity, dev | 32 of 32 | all (gate) | dev_final.json s5 | same machine and library versions |
| S2 false pre-ignition frames, sealed | 0.8% (4 of 503); interval [0.0%, 2.4%]; n = 14 sequences | <= 1% (gate) | sealed_final.json s2_s3 | frames inside one sequence are correlated; sequences with another fire's smoke or a sunrise in the pre window count as false |
| S3 method minus human first-smoke, sealed | median +180 s, quartiles +60 to +600; 13 of 14 detected | report; detected >= 80% | sealed_final.json s2_s3 | which of the two is closer to the physical ignition is not known; the human offset is the first visible plume in 1-minute frames |
| S1 opacity MAE, sealed | 0.143 [0.117, 0.171]; n = 384 composites | <= 0.10 | sealed_final.json s1 | composites follow the same mixing law as the method and rise by construction |
| S1 opacity bias, sealed | -0.019 [-0.046, 0.009] | abs <= 0.05 | sealed_final.json s1 | bias is -0.12 for true opacity 0.7 to 1.0 |
| S1 edge error at 0.20, sealed | median 10.0 px; n = 384 | <= 4 px | sealed_final.json s1 | window around the planted plume only; false regions elsewhere are counted separately |
| S1 detection, alpha_max >= 0.6, sealed | 79.3% [71.5%, 85.9%] | >= 90% | sealed_final.json s1 | dark smoke (0.30) is detected least |
| S5 re-run identity, sealed | 16 of 16 | all (gate) | sealed_final.json s5 | same machine and library versions |
| S4 HPWREN-BB best IoU between box and opacity region | median 0.14, quartiles 0.03 to 0.30; n = 246 boxes, 6 fires | report | s4_final.json | boxes are carried unchanged across many frames while the plume grows; no frame has two annotators |
| S4 Pyro-SDIS best IoU | median 0.00; n = 92 boxes, 10 events; no region for 45 | report | s4_final.json | background from other days: opacity is not reliable here |


## Reading the numbers

**The opacity map recovers planted smoke with a bias that grows with thickness.** On composites the mean error is small, but thick smoke is under-read (-0.12 for true opacity 0.7 to 1.0) and dark smoke (colour 0.30) is the hardest: MAE 0.17 on dev and 0.20 on sealed against 0.11 to 0.15 for the other colours, and detection 63% and 54% against 70% to 81%. This is the effect of the unknown smoke colour: over flat sky the colour and the opacity cannot be separated, and the fallback grey differs from a dark plume.

**Edges are placed within about 6 to 10 px, not 4.** At 512 x 384 a pixel is 4 source pixels; the planted plume has a smooth Gaussian edge and the measured contour is cut at a level plus a 2 px smoothing; the error is largest at the lowest levels, where the contour sits in the faint fringe.

**Where false alarms come from (dev).** 80 false frames in 6 sequences: a hazy cloudy scene (19), a moving tower shadow on the ground (16), a second fire's plume visible before ignition (26, arguably not false), windy foliage (6), a sunrise (9), a fourth scene (20191006 ml-w, 4 frames, not viewed). The first five were viewed in frames (see `results/ROUNDS_smoke.md`). The rules removed 198 to 80 false frames over the loop; they did not reach 1% on dev.

**S4.** HPWREN-BB boxes match no single level: of 246 boxes, the best-matching level was the noise level for 60, 0.10 for 45, 0.20 for 34, 0.40 for 42, 0.60 for 49, and 16 boxes have no region above noise near them; the median best IoU is 0.14. The per-fire pattern differs: boxes of one fire sit at 0.40 to 0.60, those of another at the noise level. The boxes are static rectangles carried over many frames while the plume grows, so a low IoU is expected from the boxes as much as from the method. Pyro-SDIS: 92 boxes in 10 events, background taken from other days with a lighting fit; for 45 boxes no region above noise touches the box and the median IoU is 0.00; this set does not support any statement about annotator level. No image in either set has two annotators, so annotator agreement could not be measured.

**S5 background window.** Moving the end of the background window from -300 s to -600 s or -1200 s, or its start from -2400 s to -1800 s, changes the first-smoke time by a median of 90 to 810 s (dev) and 240 to 900 s (sealed) and loses the detection in 4 to 9 of 31 or 32 dev sequences and in 1 or 2 of 14 sealed sequences. The sign is negative: a longer analysed window starts earlier and picks up earlier false lineages. The edge position at 0.20 moves by 0.2 to 2.3 px. Target: median shift at most one frame; not met for the first-smoke time with the longer windows.

## What these results do not show

- No result here validates the classes cloud, haze or fog, dust and other: no independent class truth exists in these sequences. They are rules, applied and shown, not tested.
- S1 composites are made with the same mixing law that the method inverts, with Gaussian puffs that rise by construction; S1 cannot detect a wrong physical model and may flatter the rise-based part of the rules. Real smoke has texture, shadows inside the plume and colour gradients that the composites lack.
- The first-smoke time is not compared with any independent ignition time, only with the human offset in the file names. No claim is made that either is right.
- The sealed S2 estimate rests on 14 sequences, one of which has false frames; the interval is wide.
- The camera pool is HPWREN fixed cameras in southern California, mostly daytime; the method is not tested on other sites, on night frames, or on moving cameras.
- Dev numbers were used to choose the rules, so they are not a test of the rules.
- The S4 comparison cannot separate annotator effect from the box convention (rectangles carried across frames).

## Detail tables

## Dev sequences

### S2 placebo and S3 first smoke, dev

Source: `results/smoke/dev_final.json` (`s2_s3`, `s2_s3_rows`).

- Sequences: 32 (0 excluded: none).
- **S2**: 80 of 1122 pre-ignition frames show a smoke region = 7.1% (95% bootstrap over sequences [1.7%, 13.6%]); 6 of 32 sequences have at least one false frame. Gate: at most 1%.
- **S3**: smoke confirmed in 21 of 32 sequences (66%; target at least 80%). Method time minus human offset (s), over the detected: median +180, quartiles +34 to +480, 10th to 90th percentile -63 to +960. Earlier than the human label in 19%, later in 76%, within five minutes either way in 71%.

### S1 known truth, dev: 768 composites over 32 sequences (0 excluded)

Source: `results/smoke/dev_final.json` (`s1`, `s1_rows`). Intervals: 95% bootstrap over sequences.

| quantity | value | target | met |
|---|---|---|---|
| opacity MAE where truth >= 0.10 | 0.138 [0.117, 0.162] | <= 0.10 | no |
| opacity bias | -0.011 [-0.030, 0.010] | abs <= 0.05 | yes |
| edge position error at noise level, median over composites (px at 512 x 384), n = 760 | 12.20 | report | - |
| edge position error at 0.10, median over composites (px at 512 x 384), n = 768 | 10.46 | report | - |
| edge position error at 0.20, median over composites (px at 512 x 384), n = 764 | 8.50 | <= 4 px | no |
| edge position error at 0.40, median over composites (px at 512 x 384), n = 503 | 5.96 | <= 4 px | no |
| edge position error at 0.60, median over composites (px at 512 x 384), n = 484 | 7.75 | report | - |
| detection, all composites | 71.2% [62.8%, 79.3%] | report | - |
| detection, alpha_max >= 0.6 | 75.6% [66.6%, 83.8%] | >= 90% | no |
| first-smoke error, median abs (frames), n = 547 | 0.0 | <= 2 | yes |
| planted-plume-free false smoke chains per composite | 0.30 | report | - |

By smoke colour (the effect of an unknown endmember):

| true smoke colour | n | MAE | bias | detection |
|---|---|---|---|---|
| grey030 | 192 | 0.165 | +0.025 | 63% |
| grey055 | 192 | 0.112 | -0.053 | 71% |
| grey085 | 192 | 0.139 | -0.009 | 81% |
| warm | 192 | 0.135 | -0.006 | 70% |

By planted opacity:

| alpha_max | n | MAE | bias | detection |
|---|---|---|---|---|
| 0.3 | 256 | 0.112 | -0.006 | 62% |
| 0.6 | 256 | 0.144 | -0.007 | 73% |
| 0.9 | 256 | 0.157 | -0.019 | 78% |

Bias by true opacity bin (measured minus planted, mean over composites that have pixels in the bin):

| true opacity | n | bias | MAE |
|---|---|---|---|
| 0.1-0.3 | 768 | +0.005 | 0.104 |
| 0.3-0.5 | 768 | -0.015 | 0.169 |
| 0.5-0.7 | 512 | -0.040 | 0.233 |
| 0.7-1.0 | 256 | -0.119 | 0.244 |

### S5 re-run and background window, dev

Source: `results/smoke/dev_final.json` (`s5`).

- Re-run identity: 32 of 32 sequences give byte-identical outputs (hash over every output file; the opacity archive by its decompressed arrays). Gate: all.

| background window | sequences | detected in both runs | lost detection | first-smoke shift, median abs (s) | median (s), IQR | edge shift at 0.20, median (px), n |
|---|---|---|---|---|---|---|
| end-600, start-2400 | 31 | 19 | 9 | 240 | -180, [-330, 0] | 0.52, 20 |
| end-1200, start-2400 | 31 | 20 | 4 | 810 | -810, [-1018, -629] | 2.27, 20 |
| end-300, start-1800 | 32 | 18 | 9 | 90 | 0, [-120, 0] | 1.08, 21 |

## Sealed sequences

### S2 placebo and S3 first smoke, sealed

Source: `results/smoke/sealed_final.json` (`s2_s3`, `s2_s3_rows`).

- Sequences: 16 (2 excluded: [['20160718_FIRE_lp-n-iqeye', 'fewer than 60 frames'], ['20160718_FIRE_mg-s-iqeye', 'fewer than 60 frames']]).
- **S2**: 4 of 503 pre-ignition frames show a smoke region = 0.8% (95% bootstrap over sequences [0.0%, 2.4%]); 1 of 14 sequences have at least one false frame. Gate: at most 1%.
- **S3**: smoke confirmed in 13 of 14 sequences (93%; target at least 80%). Method time minus human offset (s), over the detected: median +180, quartiles +60 to +600, 10th to 90th percentile +0 to +1152. Earlier than the human label in 0%, later in 77%, within five minutes either way in 69%.

### S1 known truth, sealed: 384 composites over 16 sequences (0 excluded)

Source: `results/smoke/sealed_final.json` (`s1`, `s1_rows`). Intervals: 95% bootstrap over sequences.

| quantity | value | target | met |
|---|---|---|---|
| opacity MAE where truth >= 0.10 | 0.143 [0.117, 0.171] | <= 0.10 | no |
| opacity bias | -0.019 [-0.046, 0.009] | abs <= 0.05 | yes |
| edge position error at noise level, median over composites (px at 512 x 384), n = 384 | 12.23 | report | - |
| edge position error at 0.10, median over composites (px at 512 x 384), n = 384 | 11.56 | report | - |
| edge position error at 0.20, median over composites (px at 512 x 384), n = 384 | 10.01 | <= 4 px | no |
| edge position error at 0.40, median over composites (px at 512 x 384), n = 255 | 7.90 | <= 4 px | no |
| edge position error at 0.60, median over composites (px at 512 x 384), n = 248 | 8.94 | report | - |
| detection, all composites | 72.1% [64.8%, 78.9%] | report | - |
| detection, alpha_max >= 0.6 | 79.3% [71.5%, 85.9%] | >= 90% | no |
| first-smoke error, median abs (frames), n = 277 | 0.0 | <= 2 | yes |
| planted-plume-free false smoke chains per composite | 0.26 | report | - |

By smoke colour (the effect of an unknown endmember):

| true smoke colour | n | MAE | bias | detection |
|---|---|---|---|---|
| grey030 | 96 | 0.195 | +0.000 | 54% |
| grey055 | 96 | 0.111 | -0.047 | 78% |
| grey085 | 96 | 0.123 | -0.008 | 81% |
| warm | 96 | 0.145 | -0.022 | 75% |

By planted opacity:

| alpha_max | n | MAE | bias | detection |
|---|---|---|---|---|
| 0.3 | 128 | 0.119 | -0.009 | 58% |
| 0.6 | 128 | 0.150 | -0.016 | 80% |
| 0.9 | 128 | 0.161 | -0.032 | 79% |

Bias by true opacity bin (measured minus planted, mean over composites that have pixels in the bin):

| true opacity | n | bias | MAE |
|---|---|---|---|
| 0.1-0.3 | 384 | -0.008 | 0.105 |
| 0.3-0.5 | 384 | -0.016 | 0.186 |
| 0.5-0.7 | 256 | -0.044 | 0.244 |
| 0.7-1.0 | 128 | -0.125 | 0.244 |

### S5 re-run and background window, sealed

Source: `results/smoke/sealed_final.json` (`s5`).

- Re-run identity: 16 of 16 sequences give byte-identical outputs (hash over every output file; the opacity archive by its decompressed arrays). Gate: all.

| background window | sequences | detected in both runs | lost detection | first-smoke shift, median abs (s) | median (s), IQR | edge shift at 0.20, median (px), n |
|---|---|---|---|---|---|---|
| end-600, start-2400 | 14 | 12 | 2 | 300 | -300, [-600, 0] | 0.19, 12 |
| end-1200, start-2400 | 14 | 12 | 1 | 900 | -900, [-1094, -825] | 0.66, 12 |
| end-300, start-1800 | 14 | 13 | 1 | 240 | -180, [-480, 0] | 0.23, 12 |

### S4 human boxes on the opacity scale

Source: `results/smoke/s4_final.json`. The effective level of a box is the level (noise level, 0.10, 0.20, 0.40, 0.60) whose region, grown from inside the box, has the bounding box with the best IoU against the human box.

**HPWREN-BB boxes (9 fires, FIgLib frames)**: n = 246 boxes.
- effective level counts: noise: 60, 0.10: 45, 0.20: 34, 0.40: 42, 0.60: 49, no region: 16
- best IoU: median 0.14, quartiles 0.03 to 0.30; median IoU at each level: noise: 0.03, 0.10: 0.05, 0.20: 0.03, 0.40: 0.01, 0.60: 0.00
- median opacity inside the box 0.04; share of the box above the noise level, median 0.37
- per fire (n boxes, median best IoU, level counts): 20160604_FIRE_rm-n-mobo- (41, 0.24, {'noise': 1, '0.10': 0, '0.20': 5, '0.40': 12, '0.60': 23}); 20160604_FIRE_smer-tcs3- (41, 0.12, {'noise': 11, '0.10': 9, '0.20': 18, '0.40': 1, '0.60': 0}); 20160619_FIRE_om-e-mobo- (41, 0.05, {'noise': 3, '0.10': 0, '0.20': 0, '0.40': 16, '0.60': 19}); 20160619_FIRE_pi-s-mobo- (41, 0.32, {'noise': 3, '0.10': 7, '0.20': 11, '0.40': 13, '0.60': 7}); 20160711_FIRE_ml-n-mobo- (41, 0.00, {'noise': 32, '0.10': 7, '0.20': 0, '0.40': 0, '0.60': 0}); 20160718_FIRE_mw-e-mobo- (41, 0.18, {'noise': 10, '0.10': 22, '0.20': 0, '0.40': 0, '0.60': 0})
- excluded: [['20160619_FIRE_lp-e-iqeye', 'fewer than 60 frames'], ['20160718_FIRE_lp-n-iqeye', 'fewer than 60 frames'], ['20160718_FIRE_mg-s-iqeye', 'fewer than 60 frames']]

**Pyro-SDIS boxes (relaxed background, protocol A2)**: n = 92 boxes.
- effective level counts: noise: 35, 0.10: 0, 0.20: 1, 0.40: 0, 0.60: 11, no region: 45
- best IoU: median 0.00, quartiles 0.00 to 0.01; median IoU at each level: noise: 0.00, 0.10: 0.00, 0.20: 0.00, 0.40: 0.00, 0.60: 0.00
- median opacity inside the box 0.09; share of the box above the noise level, median 0.00
- usable events processed: 10; skipped: []



## Files

- `results/smoke/dev_final.json`, `sealed_final.json`: S1 rows, S2/S3 rows, S5 rows. `s4_final.json`: S4 rows. Hashes of the inputs are recorded by `firewitness smoke label` in each `labels.json`.
- Release `smoke-v0.1`: opacity maps (`opacity.npz`, uint8 x 255), edge contours (`edges.json`) and `labels.json` for the 14 sealed sequences; the definition document; GIFs and stills of the clips. Clips (MP4) are in `clips/`.
- Reproduce: `firewitness smoke eval protocol/sequences_sealed.txt --tests s23 s1 s5 --full --out results/smoke/sealed_final.json`; `firewitness smoke s4 --out results/smoke/s4_final.json`; `firewitness smoke label <sequence dir> --out <dir>`.
