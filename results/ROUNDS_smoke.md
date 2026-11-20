# ROUNDS_smoke: pre-loop development and improvement loop

Image data: HPWREN, http://hpwren.ucsd.edu/. Dev sequences only (32 of them, protocol section 3); the sealed sequences have not been run. S1 here is S1-lite (96 composite cases, protocol amendment A2). Accept rule (protocol section 7): S1 improves (no component worse by more than 5%, at least one better by more than 5%) and S2 false-frame count does not increase. S3 and the human offset are never used to accept a change.

## Pre-loop development (rounds 0a to 0e; do not count toward the 12)

The first implementation was run on dev before the loop; the failures below were fixed first because the loop needs a version that runs. Each was looked at in frames.

| round | what was seen | named cause | change | effect (dev) |
|---|---|---|---|---|
| 0a | first S2-style run: 51% of pre-ignition frames showed a "smoke" region. A pooled 99.9th-percentile noise floor gave L0 = 1.0 on cloudy days, a MAD spread gave L0 = 0.02 | the noise floor was either dominated by clouds and shadows (real changes) or ignored glints and edge jitter | per-pixel bar N(x) (largest opacity the pixel showed while smoke-free, 5x5 max), L0 = median of N; a pixel is above noise at max(L0, N(x)) | 51% to 10% of pre frames |
| 0b | a moving tower shadow on the ground gave 13 of 36 false frames in one sequence (viewed) | a shadow dims the background like a veil but keeps its relative contrast and chromaticity | smoke rule needs texture loss >= 15% or chromaticity shift >= 0.02 | removed that sequence's false frames; detection fell (most plumes failed the clause) |
| 0c | S1 detection 22%: planted plumes found as lineages but classed other (viewed, 16 cases) | (i) tiny noise regions inside a growing plume made it impure under a root-set rule; (ii) the veil clause was measured over the faint fringe | one parent per region (largest area); veil measured on the top quarter of opacity | S1 detection 22% to 70%; S3 detected 19 to 29 of 32; false frames up to 198/1122 |
| 0d | placebo regions found where a pixel sat exactly at its own maximum (slowly growing shadow, viewed) | pre frames were tested against a bar built from the same frames | per-frame bar built without the frame's own block and a 2-frame gap | removed an artefact |
| 0e | S1 edge error 50-65 px | the whole frame was compared, including false regions far from the plume | edge error computed in a window around the planted plume (protocol A2 item 3) | edge error at 0.20 now 7.4 px |

Baseline for the loop = version v2 (after 0e): S2 198 false of 1122 pre frames (17.7%, pooled bootstrap interval 8.9% to 27.3%, 14 of 32 sequences); S1-lite: opacity MAE 0.136, bias 0.000, edge error at 0.20 median 7.4 px, detection 70%, first-smoke error median 0 frames; S3 detected 29 of 32, median +240 s.
v2 does not meet the S2 gate (1%) or the S1 targets; the loop therefore starts from a failing baseline, which is stated here.

## Loop

### R1: chromaticity clause 0.02 to 0.05
Frames viewed: 20 false placebo chains over 4 sequences (sunrise ramp, cloud shadows, tower shadow, a second fire's plume visible before ignition). Named cause: ordinary lighting patches on coloured terrain shift chromaticity by more than 0.02. Result: S2 198 to 165 false frames; S1 detection 70% to 54%. **Rejected** (S1 detection worse by more than 5%).
