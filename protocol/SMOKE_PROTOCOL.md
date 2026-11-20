# SMOKE_PROTOCOL: smoke edge, first frame and class rules

Track smoke (brief 52). Committed alone, before any result. Data credit: HPWREN, http://hpwren.ucsd.edu/ (FIgLib images); PyroNear Pyro-SDIS (Apache-2.0, Hugging Face `pyronear/pyro-sdis`).

## 1. Question

Smoke has no agreed edge and no agreed first frame. This track defines both as measurements that need no trained model, implements the definition, tests it against known truth, a placebo and existing human labels, and builds a video tool to show the result.

## 2. Definition (summary; the full two-page text is `docs/SMOKE_EDGE.md`)

1. Label = a measured opacity map alpha(x, t): how far the smoke moves each pixel from the camera's own smoke-free background B(x) towards a smoke endmember S. Background B = per-pixel temporal median of the frames before ignition (offset <= -300 s), after a robust per-channel gain/offset lighting correction of every frame to B. Optional rigid shift correction is applied if the camera moved.
2. An edge = a contour of alpha at a stated level. The lowest named level L0 is the camera's noise floor: the 99.9th percentile of alpha measured on pre-ignition frames against a leave-one-block-out background. Fixed levels above it: 0.10, 0.20, 0.40, 0.60. The continuous map is the label; any level can be cut from it.
3. First smoke = trace back from a confirmed later frame to the earliest frame in which a region above L0 persists and connects forward (overlap in consecutive frames) to the confirmed plume.
4. Each pixel carries a vector: opacity, colour shift, loss of background texture, motion speed, motion direction, attachment to a fixed source point, growth. Classes smoke, cloud, haze or fog, dust, other are plain-sentence rules on that vector. No trained model decides a class.
5. Out of scope: cameras that move without registration (shift drift above 3 px at the working size inside the pre window), night frames (median pre-window luminance below 0.20), sequences with fewer than 60 frames or a changing image size. Each exclusion is reported with its sequence name, never silently.

Working resolution: 512 x 384 (4x area downsample of the 2048 x 1536 source). All pixel distances below are at this size.

## 3. Data and split

Pool: the first 48 sequences, in ascending order of sha256("smoke-v1|" + sequence name), among the FIgLib sequences whose name has the form `YYYYMMDD_FIRE_<camera>` (198 of the 528 listed on 2026-11-20). Rule fixed before any frame was processed; the author looked at thumbnails of the first six sequences in this order (ranks 1 to 6) to learn the image format, before the split was applied and before any code existed. Every sequence is split by rank: rank 1, 4, 7, ... (rank mod 3 = 1) is sealed, the rest dev. Sealed sequences are not processed by any dev run, the improvement loop, or any rule check, and are opened once (section 7). Sequences failing the scope rules in section 2 are excluded from both sets and listed.

**Dev (32):**

- 20180728_FIRE_smer-tcs9-mobo-c
- 20200226_FIRE_rm-e-mobo-c
- 20180809_FIRE_bh-s-mobo-c
- 20200521_FIRE_om-s-mobo-c
- 20191007_FIRE_sm-s-mobo-c
- 20161113_FIRE_bm-n-mobo-c
- 20200911_FIRE_lp-e-mobo-c
- 20200521_FIRE_om-n-mobo-c
- 20191001_FIRE_lp-s-mobo-c
- 20180809_FIRE_mg-w-mobo-c
- 20201013_FIRE_cp-s-mobo-c
- 20180727_FIRE_bh-n-mobo-c
- 20170901_FIRE_om-s-mobo-c
- 20160711_FIRE_ml-n-mobo-c
- 20191006_FIRE_ml-w-mobo-c
- 20201208_FIRE_om-s-mobo-c
- 20191005_FIRE_wc-e-mobo-c
- 20180517_FIRE_rm-n-mobo-c
- 20191001_FIRE_om-s-mobo-c
- 20171016_FIRE_sdsc-e-mobo-c
- 20171010_FIRE_rm-e-mobo-c
- 20191005_FIRE_bm-e-mobo-c
- 20190620_FIRE_rm-w-mobo-c
- 20180813_FIRE_bl-n-mobo-c
- 20180605_FIRE_smer-tcs9-mobo-c
- 20180726_FIRE_so-w-mobo-c
- 20191005_FIRE_vo-n-mobo-c
- 20190922_FIRE_ml-w-mobo-c
- 20200608_FIRE_rm-w-mobo-c
- 20171026_FIRE_rm-n-mobo-c
- 20190924_FIRE_sm-n-mobo-c
- 20180919_FIRE_rm-e-mobo-c

**Sealed (16):**

- 20200306_FIRE_ml-s-mobo-c
- 20180727_FIRE_bl-e-mobo-c
- 20180910_FIRE_smer-tcs8-mobo-c
- 20191001_FIRE_rm-w-mobo-c
- 20180504_FIRE_bh-n-mobo-c
- 20191001_FIRE_bh-w-mobo-c
- 20160718_FIRE_lp-n-iqeye
- 20160604_FIRE_smer-tcs3-mobo-c
- 20180726_FIRE_so-n-mobo-c
- 20180614_FIRE_hp-s-mobo-c
- 20180606_FIRE_lo-s-mobo-c
- 20191005_FIRE_hp-s-mobo-c
- 20180602_FIRE_smer-tcs9-mobo-c
- 20180605_FIRE_rm-w-mobo-c
- 20180603_FIRE_smer-tcs8-mobo-c
- 20160718_FIRE_mg-s-iqeye

Second set (PyroNear): Pyro-SDIS images carry camera, date and a YOLO box column. Events = images of one camera within 3 hours of each other; an event is usable for the opacity map only if at least 3 earlier images of the same camera within the preceding 6 hours show no box (the background). Events are split by sha256("smoke-v1|" + camera): the lowest 40% of the hash range is sealed. These boxes, and the HPWREN human labels found by the label search (recorded in `results/SMOKE_RESULTS.md`), are used only in S4.

Human offset: the number in each FIgLib file name (seconds from visible plume appearance). Offset 0 is the human first-smoke label. It is never used to fit, tune or accept any change (section 7); it enters only S3.

## 4. Tests

| id | test | data | measure |
|---|---|---|---|
| S1 | known truth: composite plume of known alpha over real pre-ignition frames (testing only, never for fitting). Plume shapes: 2 random seeds per sequence; alpha_max in {0.3, 0.6, 0.9}; endmember in {neutral grey 0.30, 0.55, 0.85, warm (0.55, 0.45, 0.35)}; plume starts at pre-window frame index 28, background built from earlier frames only | pre-ignition frames of every included sequence | opacity MAE and bias where alpha_true >= 0.10, by alpha bin; edge position error (mean symmetric boundary distance) at each fixed level; detection rate and first-smoke time error |
| S2 | placebo: pre-ignition window (offset -2400 to -300 s), blocked 4-fold: each block of consecutive frames is tested with the background built from the other blocks, a 3-frame gap each side | pre-ignition frames of every included sequence | fraction of frames in which any smoke-class region exists; 95% interval by bootstrap over sequences |
| S3 | first-smoke time of the full method (background offset <= -300 s, trace back from the confirmed plume) against human offset 0 | every included sequence | distribution of (method - human) in seconds, sign, share detected |
| S4 | human boxes and masks placed on the opacity scale: for each human annotation, the level (among L0, 0.10, 0.20, 0.40, 0.60) whose region has the highest IoU with it, and that IoU | all human boxes or masks found for included sequences and Pyro-SDIS events | distribution of effective level; IoU; agreement between annotators where an image has two |
| S5 | re-run identity (hash of all outputs) and sensitivity to the background window (end offset -300 / -600 / -1200 s; start -2400 / -1800 s) | every included sequence | hash equality; shift in first-smoke time and in edge position at 0.20 |

## 5. Targets and gates

Targets are set before any result and are not moved. A missed target is reported as missed.

- S1: opacity MAE <= 0.10 and |bias| <= 0.05 where alpha_true >= 0.10; median edge position error <= 4 px at levels 0.20 and 0.40; detection >= 90% of composites with alpha_max >= 0.6; median first-smoke error <= 2 frames. Reported by endmember, so that the effect of an unknown smoke colour is visible.
- S2 (gate): at most 1% of frames in the pre-ignition window show any smoke-class region, point estimate and upper 95% limit both reported.
- S3 (report only, no gate): distribution of the difference, direction, share detected; target for detection share >= 80% of sequences.
- S4 (report only): the effective drawing level per annotator group, and IoU at that level.
- S5 (gate): the re-run is byte-identical on every output. The window sensitivity is reported; target median |shift| <= 1 frame.

## 6. Outputs and tools

`firewitness smoke label`: sequence directory -> per-frame opacity maps, edge contours at the fixed levels, vector, class map, first-smoke frame (npz + json, SHA-256 of inputs recorded). `firewitness video render`: layouts a to d plus the merged-track layouts; MP4 1080p 20 to 40 s, GIF, stills, captions burnt in, colour-blind-safe palette. HPWREN credit burnt into every derived frame.

## 7. Improvement loop and sealed set

After the first version passes S1 to S5 on dev, at most 12 rounds: run on dev, look at the frames of every failure (S1 case outside target, every S2 false frame, every S3 miss), name one cause, change one rule, run again. A change is kept only if S1 improves and S2 does not worsen. "S1 improves": no S1 component (opacity MAE, median edge error at 0.20, detection rate, median first-smoke error) worsens by more than 5% of its value, and at least one improves by more than 5%. "S2 does not worsen": the number of false frames does not increase. S3 and S4 and the human offset are never used to accept a change. Every round is logged in `results/ROUNDS_smoke.md` with the failures inspected, the named cause and the outcome. The sealed sequences are run once with the frozen configuration, after the last round; the result is published as it comes out, whether it meets the targets or not.

## 8. Not claimed

No claim that the opacity map equals physical optical depth, that the smoke endmember is recovered when the background is uniform sky, or that the classes beyond smoke are validated (no independent class truth exists in these sequences). No claim that this is the first opacity or matting formulation for smoke; see `docs/PRIOR_ART_SMOKE.md`.

## 9. Amendment A1 (2026-11-20, before any result): human labels found

The label search found official HPWREN bounding boxes (CSV, `cdn.hpwren.ucsd.edu/HPWREN-FIgLib-Data/Miscellaneous/Labels/HPWREN-BB/CSV/`): 9 fires, 309 frame rows, Filename = FIgLib path, no stated licence. Four of the 9 are in the pool of section 3. The other five (20160604_FIRE_rm-n-mobo-c, 20160619_FIRE_lp-e-iqeye, 20160619_FIRE_om-e-mobo-c, 20160619_FIRE_pi-s-mobo-c, 20160718_FIRE_mw-e-mobo-c) are downloaded and used for S4 only; they are in neither dev nor sealed, are never used to change a rule, and their S4 numbers are reported separately. The AI For Mankind boxes (CC BY-NC-SA 4.0, 640x480, opaque file names) cannot be mapped to FIgLib frames by name and are not used. No openly downloadable contour masks were found; "masks" for FIgLib are therefore not available and S4 for HPWREN is boxes only. The SmokeyNet `night_fires.txt` and `mislabeled_fires.txt` lists are read only to report overlap with the scope exclusions; they never select sequences.

## 10. Amendment A2 (2026-11-20, before any sealed or S3/S4 result)

1. **Improvement loop uses S1-lite.** Inside the loop only, S1 runs one plume seed per sequence and cycles the four endmembers over the three alpha_max values (96 cases on 32 dev sequences) because the full grid (768 cases) takes about 25 minutes per evaluation. Numbers reported in `results/SMOKE_RESULTS.md` use the full grid. The accept rule of section 7 is unchanged.
2. **Pyro-SDIS usable events.** Only 1 of 1,007 events (images of one camera, at most 3 h apart) has the 3 earlier smoke-free images of the same camera within 6 h that section 3 requires. Relaxed rule, fixed now: a background image is any image of the same camera without a box, within 3 days and within 90 minutes of the same time of day; an event needs at least 2 box images and 3 such background images. This gives about 10 events, so Pyro-SDIS S4 is reported with its small n and no interval claim beyond that n. Lighting differences are removed by the same per-channel gain/offset fit as for FIgLib. Pyro-SDIS is S4-only.
3. **S1 edge error** is computed inside a window around the planted plume (the plume support dilated by 40 px at the working size); false regions elsewhere in the frame are counted separately as `false_smoke_chains`. Section 4 compared the whole frame, which mixes plume edge error with false-region count.
4. **Pre-loop development.** Before the loop began, the first implementation was run on dev sequences (S2/S3 style, and an S1 baseline `v0`); problems found there (the noise-floor definition, shadows being classed as smoke) were fixed and are recorded in `results/ROUNDS_smoke.md` as rounds 0a to 0c. They do not count toward the 12 rounds. Sealed sequences were not run.

## 11. Amendment A3 (2026-11-20, before any sealed, S3 or S4 result)

Section 7 required that "S1 improves" for a change to be kept. In the first loop rounds a change that removed 40% of the false pre-ignition frames (S2) left S1 inside its 5% tolerance and was refused only because S1 did not also gain; no change aimed at false alarms can pass that wording. Replacement, applied from round R2 on (rounds R1 to R3 were re-read under it, see the log): a change is kept when (a) no S1 component is worse by more than 5% of its value, (b) the S2 false-frame count does not increase, and (c) at least one S1 component, or the S2 false-frame count, is better by more than 5%. The intent of section 7 (no trade of S1 for S2) is unchanged. S3, S4 and the human offset still play no part.
